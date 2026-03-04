"""repair_journal.py — Persistent trial database for repair attempts.

Tracks every repair attempt with full context:
- What was the error
- What fix was tried
- Did it work or fail
- LLM analysis of the situation
- Successful fixes become "known good" patterns

This enables the system to LEARN from past repair attempts and
never repeat failing fixes, while reusing successful ones.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from .config import cpr, C


@dataclass
class RepairAttempt:
    """Single repair attempt record."""
    timestamp: str
    skill_name: str
    error_signature: str          # Normalized error (for matching)
    error_full: str               # Full error text
    fix_type: str                 # e.g. "amixer_unmute", "vosk_model_path", "pip_install"
    fix_command: str              # Actual command/action taken
    fix_result: str               # "success", "fail", "partial"
    result_detail: str = ""       # What happened after fix
    llm_analysis: str = ""        # LLM's diagnosis (if consulted)
    llm_suggestion: str = ""      # LLM's suggested fix
    context: dict = field(default_factory=dict)  # Extra context
    duration_ms: int = 0


@dataclass
class KnownFix:
    """A proven fix pattern extracted from successful attempts."""
    error_pattern: str            # Error signature to match
    fix_type: str
    fix_command: str
    success_count: int = 0
    fail_count: int = 0
    last_success: str = ""
    confidence: float = 0.0       # success_count / (success_count + fail_count)


class RepairJournal:
    """Persistent journal of all repair attempts with LLM-powered learning.
    
    Stores JSONL at logs/repair/repair_journal.jsonl
    Known fixes at logs/repair/known_fixes.json
    """
    
    JOURNAL_DIR = Path("logs/repair")
    JOURNAL_FILE = JOURNAL_DIR / "repair_journal.jsonl"
    KNOWN_FIXES_FILE = JOURNAL_DIR / "known_fixes.json"
    MAX_JOURNAL_ENTRIES = 1000
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._known_fixes: Dict[str, List[KnownFix]] = {}  # error_pattern → fixes
        self._recent_attempts: List[RepairAttempt] = []
        
        self.JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        self._load_known_fixes()
        self._load_recent_attempts()
    
    # ─── Recording ──────────────────────────────────────────────────
    
    def record_attempt(self, skill_name: str, error: str, fix_type: str,
                       fix_command: str, success: bool, detail: str = "",
                       llm_analysis: str = "", llm_suggestion: str = "",
                       context: dict = None, duration_ms: int = 0) -> RepairAttempt:
        """Record a repair attempt and update known fixes."""
        sig = self._error_signature(error)
        attempt = RepairAttempt(
            timestamp=datetime.now(timezone.utc).isoformat(),
            skill_name=skill_name,
            error_signature=sig,
            error_full=error[:500],
            fix_type=fix_type,
            fix_command=fix_command[:300],
            fix_result="success" if success else "fail",
            result_detail=detail[:300],
            llm_analysis=llm_analysis[:500],
            llm_suggestion=llm_suggestion[:500],
            context=context or {},
            duration_ms=duration_ms,
        )
        
        self._recent_attempts.append(attempt)
        self._append_journal(attempt)
        self._update_known_fix(sig, fix_type, fix_command, success)
        
        return attempt
    
    def record_success(self, skill_name: str, context: str = ""):
        """Record that a skill is working (for tracking recovery)."""
        self._append_journal(RepairAttempt(
            timestamp=datetime.now(timezone.utc).isoformat(),
            skill_name=skill_name,
            error_signature="",
            error_full="",
            fix_type="none_needed",
            fix_command="",
            fix_result="healthy",
            result_detail=context[:300],
        ))
    
    # ─── Querying ───────────────────────────────────────────────────
    
    def get_known_fix(self, error: str) -> Optional[KnownFix]:
        """Find the best known fix for an error pattern."""
        sig = self._error_signature(error)
        fixes = self._known_fixes.get(sig, [])
        if not fixes:
            return None
        # Return highest confidence fix
        return max(fixes, key=lambda f: f.confidence)
    
    def get_failed_fixes(self, error: str) -> List[str]:
        """Get list of fix_types that have failed for this error — avoid repeating."""
        sig = self._error_signature(error)
        fixes = self._known_fixes.get(sig, [])
        return [f.fix_type for f in fixes if f.confidence < 0.3 and f.fail_count >= 2]
    
    def get_history(self, skill_name: str = "", last_n: int = 20) -> List[RepairAttempt]:
        """Get recent repair attempts, optionally filtered by skill."""
        attempts = self._recent_attempts
        if skill_name:
            attempts = [a for a in attempts if a.skill_name == skill_name]
        return attempts[-last_n:]
    
    def get_stats(self) -> dict:
        """Get overall repair statistics."""
        total = len(self._recent_attempts)
        successes = sum(1 for a in self._recent_attempts if a.fix_result == "success")
        fails = sum(1 for a in self._recent_attempts if a.fix_result == "fail")
        known = sum(len(fixes) for fixes in self._known_fixes.values())
        high_conf = sum(
            1 for fixes in self._known_fixes.values()
            for f in fixes if f.confidence >= 0.7
        )
        return {
            "total_attempts": total,
            "successes": successes,
            "fails": fails,
            "success_rate": successes / max(total, 1),
            "known_fix_patterns": known,
            "high_confidence_fixes": high_conf,
        }
    
    # ─── LLM-powered diagnosis ──────────────────────────────────────
    
    def ask_llm_diagnosis(self, skill_name: str, error: str,
                          attempted_fixes: List[str] = None,
                          system_context: str = "") -> dict:
        """Ask LLM to diagnose an error and suggest fixes.
        
        Returns: {"diagnosis": str, "suggested_fix": str, "fix_command": str, "confidence": str}
        """
        if not self.llm:
            return {"diagnosis": "", "suggested_fix": "", "fix_command": "", "confidence": "low"}
        
        # Build context from repair history
        history_ctx = ""
        history = self.get_history(skill_name, last_n=5)
        if history:
            history_lines = []
            for h in history:
                history_lines.append(
                    f"  - [{h.fix_result}] {h.fix_type}: {h.fix_command[:80]} → {h.result_detail[:60]}")
            history_ctx = "Poprzednie próby naprawy:\n" + "\n".join(history_lines)
        
        failed_fixes = self.get_failed_fixes(error)
        avoid_ctx = ""
        if failed_fixes:
            avoid_ctx = f"\nNIE próbuj tych (już zawiodły): {', '.join(failed_fixes)}"
        
        prompt = f"""Jesteś ekspertem od diagnostyki systemowej Linux.

Skill: {skill_name}
Błąd: {error[:400]}
{f'Kontekst systemowy: {system_context}' if system_context else ''}
{history_ctx}
{avoid_ctx}
{f'Już próbowano: {", ".join(attempted_fixes)}' if attempted_fixes else ''}

Odpowiedz TYLKO w formacie JSON:
{{"diagnosis": "krótka analiza przyczyny (1-2 zdania)",
 "suggested_fix": "co zrobić (1-2 zdania)",
 "fix_command": "konkretna komenda bash do wykonania (lub 'manual' jeśli wymaga interwencji użytkownika)",
 "confidence": "high/medium/low"}}"""
        
        try:
            response = self.llm.complete(
                [{"role": "system", "content": "Odpowiadaj TYLKO poprawnym JSON."},
                 {"role": "user", "content": prompt}],
                max_tokens=300,
            )
            # Parse JSON from response
            text = response.strip()
            # Extract JSON if wrapped in markdown
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            result = json.loads(text)
            return {
                "diagnosis": result.get("diagnosis", ""),
                "suggested_fix": result.get("suggested_fix", ""),
                "fix_command": result.get("fix_command", ""),
                "confidence": result.get("confidence", "low"),
            }
        except Exception as e:
            return {"diagnosis": f"LLM error: {e}", "suggested_fix": "",
                    "fix_command": "", "confidence": "low"}
    
    def ask_llm_and_try(self, skill_name: str, error: str,
                        system_context: str = "",
                        attempted_fixes: List[str] = None,
                        dry_run: bool = False) -> dict:
        """Full cycle: ask LLM → try suggested fix → record result.
        
        Returns: {"diagnosis": str, "fix_tried": str, "success": bool, "detail": str}
        """
        import subprocess
        
        diagnosis = self.ask_llm_diagnosis(
            skill_name, error,
            attempted_fixes=attempted_fixes,
            system_context=system_context)
        
        cpr(C.CYAN, f"  [LLM] Diagnoza: {diagnosis.get('diagnosis', '?')[:100]}")
        cpr(C.CYAN, f"  [LLM] Sugestia: {diagnosis.get('suggested_fix', '?')[:100]}")
        
        fix_cmd = diagnosis.get("fix_command", "").strip()
        if not fix_cmd or fix_cmd == "manual" or dry_run:
            return {
                "diagnosis": diagnosis.get("diagnosis", ""),
                "fix_tried": "",
                "success": False,
                "detail": "LLM suggests manual intervention" if fix_cmd == "manual" else "no command",
            }
        
        # Safety check — don't run destructive commands
        dangerous = ["rm -rf", "mkfs", "dd if=/dev/zero", "format", "> /dev/"]
        if any(d in fix_cmd for d in dangerous):
            cpr(C.RED, f"  [LLM] Odrzucono niebezpieczną komendę: {fix_cmd[:60]}")
            return {
                "diagnosis": diagnosis.get("diagnosis", ""),
                "fix_tried": fix_cmd,
                "success": False,
                "detail": "Command rejected as dangerous",
            }
        
        cpr(C.DIM, f"  [LLM] Wykonuję: {fix_cmd[:100]}")
        t0 = time.time()
        try:
            r = subprocess.run(fix_cmd, shell=True, capture_output=True,
                               text=True, timeout=30)
            duration = int((time.time() - t0) * 1000)
            success = r.returncode == 0
            detail = (r.stdout or r.stderr or "")[:200]
            
            self.record_attempt(
                skill_name=skill_name, error=error,
                fix_type=f"llm_{diagnosis.get('confidence', 'low')}",
                fix_command=fix_cmd,
                success=success,
                detail=detail,
                llm_analysis=diagnosis.get("diagnosis", ""),
                llm_suggestion=diagnosis.get("suggested_fix", ""),
                duration_ms=duration,
            )
            
            if success:
                cpr(C.GREEN, f"  [LLM] ✓ Komenda wykonana pomyślnie")
            else:
                cpr(C.YELLOW, f"  [LLM] ✗ Komenda zawiodła: {detail[:80]}")
            
            return {
                "diagnosis": diagnosis.get("diagnosis", ""),
                "fix_tried": fix_cmd,
                "success": success,
                "detail": detail,
            }
        except Exception as e:
            self.record_attempt(
                skill_name=skill_name, error=error,
                fix_type="llm_cmd_error",
                fix_command=fix_cmd,
                success=False,
                detail=str(e)[:200],
                llm_analysis=diagnosis.get("diagnosis", ""),
            )
            return {
                "diagnosis": diagnosis.get("diagnosis", ""),
                "fix_tried": fix_cmd,
                "success": False,
                "detail": str(e),
            }
    
    # ─── Internal ───────────────────────────────────────────────────
    
    def _error_signature(self, error: str) -> str:
        """Normalize error to a matchable signature.
        Strips paths, numbers, timestamps to find recurring patterns."""
        import re
        sig = error.strip()[:200].lower()
        sig = re.sub(r'/[^\s:]+', '<path>', sig)
        sig = re.sub(r'\b\d+\b', '<N>', sig)
        sig = re.sub(r'\s+', ' ', sig)
        return sig
    
    def _append_journal(self, attempt: RepairAttempt):
        """Append to JSONL journal file."""
        try:
            with open(self.JOURNAL_FILE, "a") as f:
                f.write(json.dumps(asdict(attempt), ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def _update_known_fix(self, error_sig: str, fix_type: str,
                          fix_command: str, success: bool):
        """Update known fix database."""
        if error_sig not in self._known_fixes:
            self._known_fixes[error_sig] = []
        
        # Find existing or create new
        existing = None
        for f in self._known_fixes[error_sig]:
            if f.fix_type == fix_type:
                existing = f
                break
        
        if existing:
            if success:
                existing.success_count += 1
                existing.last_success = datetime.now(timezone.utc).isoformat()
            else:
                existing.fail_count += 1
            total = existing.success_count + existing.fail_count
            existing.confidence = existing.success_count / max(total, 1)
        else:
            fix = KnownFix(
                error_pattern=error_sig,
                fix_type=fix_type,
                fix_command=fix_command[:300],
                success_count=1 if success else 0,
                fail_count=0 if success else 1,
                last_success=datetime.now(timezone.utc).isoformat() if success else "",
                confidence=1.0 if success else 0.0,
            )
            self._known_fixes[error_sig].append(fix)
        
        self._save_known_fixes()
    
    def _save_known_fixes(self):
        """Persist known fixes to disk."""
        try:
            data = {}
            for sig, fixes in self._known_fixes.items():
                data[sig] = [asdict(f) for f in fixes]
            with open(self.KNOWN_FIXES_FILE, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _load_known_fixes(self):
        """Load known fixes from disk."""
        try:
            if self.KNOWN_FIXES_FILE.exists():
                with open(self.KNOWN_FIXES_FILE) as f:
                    data = json.load(f)
                for sig, fixes_data in data.items():
                    self._known_fixes[sig] = [
                        KnownFix(**fd) for fd in fixes_data
                    ]
        except Exception:
            self._known_fixes = {}
    
    def _load_recent_attempts(self):
        """Load recent attempts from JSONL."""
        try:
            if self.JOURNAL_FILE.exists():
                lines = self.JOURNAL_FILE.read_text().strip().split("\n")
                # Load last N entries
                for line in lines[-self.MAX_JOURNAL_ENTRIES:]:
                    if line.strip():
                        d = json.loads(line)
                        self._recent_attempts.append(RepairAttempt(**d))
        except Exception:
            self._recent_attempts = []
    
    def format_report(self, skill_name: str = "") -> str:
        """Human-readable repair report."""
        stats = self.get_stats()
        lines = [
            f"=== Repair Journal ===",
            f"Łączne próby: {stats['total_attempts']} "
            f"(✓ {stats['successes']} / ✗ {stats['fails']})",
            f"Skuteczność: {stats['success_rate']:.0%}",
            f"Znane wzorce napraw: {stats['known_fix_patterns']} "
            f"(pewne: {stats['high_confidence_fixes']})",
        ]
        
        history = self.get_history(skill_name, last_n=10)
        if history:
            lines.append(f"\nOstatnie próby{f' ({skill_name})' if skill_name else ''}:")
            for h in history:
                icon = "✓" if h.fix_result == "success" else "✗"
                lines.append(f"  {icon} [{h.skill_name}] {h.fix_type}: "
                             f"{h.result_detail[:60] or h.error_signature[:60]}")
        
        return "\n".join(lines)
