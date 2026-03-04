#!/usr/bin/env python3
"""
SelfHealing - Autonomiczna naprawa systemu CoreSkill
Z podziałem na zadania w pętli z autorefleksją
"""
import re
import ast
import sys
import json
import time
import hashlib
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class HealingStage(Enum):
    """Stadia procesu naprawy."""
    DETECT = "detect"           # Wykrywanie problemu
    ANALYZE = "analyze"         # Analiza przyczyny
    PLAN = "plan"               # Planowanie naprawy
    EXECUTE = "execute"         # Wykonanie naprawy
    VERIFY = "verify"           # Weryfikacja naprawy
    REFLECT = "reflect"         # Refleksja i uczenie się


@dataclass
class HealingTask:
    """Pojedyncze zadanie naprawy."""
    id: str
    target_skill: str
    issue_type: str  # syntax, import, logic, performance
    description: str
    stage: HealingStage = HealingStage.DETECT
    attempts: int = 0
    max_attempts: int = 3
    success: bool = False
    error_history: List[str] = field(default_factory=list)
    fix_strategy: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealingResult:
    """Wynik procesu naprawy."""
    task_id: str
    success: bool
    strategy_used: str
    attempts_made: int
    final_stage: HealingStage
    error_signature: str
    reflection: str
    learned_rule: Optional[str] = None


class ErrorFingerprint:
    """Tworzy unikalny odcisk palca błędu."""
    
    @staticmethod
    def create(error: str, skill_name: str) -> str:
        """Tworzy fingerprint błędu."""
        # Uproszczony fingerprint - pierwsze 100 znaków błędu
        normalized = error[:100].lower().strip()
        normalized = re.sub(r"[^a-z0-9]", "_", normalized)
        return f"{skill_name}:{hashlib.md5(normalized.encode()).hexdigest()[:12]}"


class SelfReflectionEngine:
    """Silnik autorefleksji i uczenia się z napraw."""
    
    def __init__(self, state: Dict):
        self.state = state
        self.healing_memory = state.setdefault("healing_memory", {
            "learned_rules": {},      # Zasady nauczone z napraw
            "error_patterns": {},     # Wzorce błędów
            "strategy_success": {}    # Skuteczność strategii
        })
    
    def reflect(self, result: HealingResult, task: HealingTask) -> str:
        """Refleksja po naprawie - co się nauczyliśmy."""
        reflections = []
        
        if result.success:
            reflections.append(f"✓ Strategia '{result.strategy_used}' skuteczna dla {task.issue_type}")
            # Nauka reguły
            rule = f"If {task.issue_type} in {task.target_skill}, use {result.strategy_used}"
            self._learn_rule(task.issue_type, rule, result.strategy_used)
        else:
            reflections.append(f"✗ Strategie nie pomogły po {result.attempts_made} próbach")
            reflections.append(f"  Sugestia: Ręczna naprawa lub eskalacja do LLM")
        
        # Aktualizacja statystyk strategii
        self._update_strategy_stats(result.strategy_used, result.success)
        
        return "\n".join(reflections)
    
    def _learn_rule(self, issue_type: str, rule: str, strategy: str):
        """Zapisuje nauczoną regułę."""
        learned = self.healing_memory["learned_rules"]
        if issue_type not in learned:
            learned[issue_type] = []
        if rule not in learned[issue_type]:
            learned[issue_type].append(rule)
    
    def _update_strategy_stats(self, strategy: str, success: bool):
        """Aktualizuje statystyki skuteczności strategii."""
        stats = self.healing_memory["strategy_success"]
        if strategy not in stats:
            stats[strategy] = {"success": 0, "fail": 0}
        if success:
            stats[strategy]["success"] += 1
        else:
            stats[strategy]["fail"] += 1
    
    def get_best_strategy(self, issue_type: str, error_message: str) -> str:
        """Wybiera najlepszą strategię na podstawie historii."""
        # Sprawdź nauczone reguły
        learned = self.healing_memory["learned_rules"].get(issue_type, [])
        if learned:
            return learned[0].split("use ")[-1] if "use " in learned[0] else "normal_evolve"
        
        # Wybór na podstawie typu błędu
        if "syntax" in issue_type or "indent" in error_message.lower():
            return "auto_fix_syntax"
        elif "import" in issue_type or "module" in error_message.lower():
            return "auto_fix_imports"
        elif "attribute" in error_message.lower() or "has no" in error_message.lower():
            return "auto_fix_interface"
        
        return "normal_evolve"


class SelfHealingOrchestrator:
    """Orkiestrator procesu autonaprawy z podziałem na zadania."""
    
    def __init__(self, llm_client, skill_manager, state: Dict):
        self.llm = llm_client
        self.sm = skill_manager
        self.state = state
        self.reflection = SelfReflectionEngine(state)
        self.active_tasks: Dict[str, HealingTask] = {}
        self.results: List[HealingResult] = []
        
        # Strategie naprawy
        self.strategies: Dict[str, Callable] = {
            "auto_fix_syntax": self._fix_syntax,
            "auto_fix_imports": self._fix_imports,
            "auto_fix_interface": self._fix_interface,
            "normal_evolve": self._evolve_with_llm,
            "rewrite_from_scratch": self._rewrite_skill,
        }
    
    def heal_skill(self, skill_name: str, error_info: Dict) -> HealingResult:
        """Główna metoda naprawy - pętla z autorefleksją."""
        # Stwórz zadanie naprawy
        task = HealingTask(
            id=f"heal_{skill_name}_{int(time.time())}",
            target_skill=skill_name,
            issue_type=error_info.get("type", "unknown"),
            description=error_info.get("message", "Unknown error"),
        )
        self.active_tasks[task.id] = task
        
        print(f"[HEAL] Rozpoczynam naprawę: {skill_name}")
        print(f"[HEAL] Błąd: {task.description[:80]}...")
        
        # Pętla naprawy
        while task.attempts < task.max_attempts and not task.success:
            task.attempts += 1
            print(f"\n[HEAL] Próba {task.attempts}/{task.max_attempts}")
            
            # Stage 1-4: Wykonaj strategię
            result = self._execute_healing_cycle(task)
            
            if result.success:
                task.success = True
                task.stage = HealingStage.VERIFY
                break
            else:
                task.error_history.append(result.error_signature)
                task.stage = HealingStage.ANALYZE  # Ponowna analiza
        
        # Stage 6: Refleksja
        task.stage = HealingStage.REFLECT
        reflection_text = self.reflection.reflect(result, task)
        print(f"\n[HEAL] Refleksja:\n{reflection_text}")
        
        # Zapisz wynik
        result.reflection = reflection_text
        self.results.append(result)
        
        return result
    
    def _execute_healing_cycle(self, task: HealingTask) -> HealingResult:
        """Wykonuje jeden cykl naprawy."""
        # Wybierz strategię
        strategy_name = self.reflection.get_best_strategy(
            task.issue_type, task.description
        )
        task.fix_strategy = strategy_name
        print(f"[HEAL] Strategia: {strategy_name}")
        
        # Wykonaj naprawę
        fix_func = self.strategies.get(strategy_name, self._evolve_with_llm)
        success, error_sig = fix_func(task.target_skill, task.description)
        
        return HealingResult(
            task_id=task.id,
            success=success,
            strategy_used=strategy_name,
            attempts_made=task.attempts,
            final_stage=task.stage,
            error_signature=error_sig
        )
    
    def _fix_syntax(self, skill_name: str, error_msg: str) -> tuple:
        """Automatyczna naprawa błędów składni."""
        skill_path = self._get_skill_path(skill_name)
        if not skill_path:
            return False, "skill_not_found"
        
        try:
            code = skill_path.read_text()
            
            # Naprawy składni
            fixes = [
                (r"\n\n\n+", "\n\n"),  # Usuń nadmiarowe puste linie
                (r"\t", "    "),        # Zamień taby na spacje
                (r":\s*\n\s*pass", ":\n    pass"),  # Popraw pusty pass
            ]
            
            for pattern, replacement in fixes:
                code = re.sub(pattern, replacement, code)
            
            # Sprawdź składnię
            try:
                ast.parse(code)
                skill_path.write_text(code)
                print(f"[HEAL] ✓ Naprawiono składnię")
                return True, ""
            except SyntaxError as e:
                return False, f"syntax:{e}"
                
        except Exception as e:
            return False, f"fix_error:{e}"
    
    def _fix_imports(self, skill_name: str, error_msg: str) -> tuple:
        """Automatyczna naprawa importów."""
        skill_path = self._get_skill_path(skill_name)
        if not skill_path:
            return False, "skill_not_found"
        
        # Wyekstrahuj brakujące moduły z błędu
        missing = re.findall(r"No module named '(\w+)'", error_msg)
        missing += re.findall(r"cannot import name '(\w+)'", error_msg)
        
        if not missing:
            return False, "no_missing_modules_detected"
        
        try:
            code = skill_path.read_text()
            
            # Dodaj obsługę brakujących importów
            for module in missing:
                # Sprawdź czy już jest try/except
                if f"try:\n    import {module}" not in code:
                    import_fix = f"""
try:
    import {module}
except ImportError:
    {module} = None
"""
                    code = import_fix + "\n" + code
            
            skill_path.write_text(code)
            print(f"[HEAL] ✓ Dodano obsługę brakujących importów: {missing}")
            return True, ""
            
        except Exception as e:
            return False, f"fix_import_error:{e}"
    
    def _fix_interface(self, skill_name: str, error_msg: str) -> tuple:
        """Naprawa interfejsu skillu."""
        skill_path = self._get_skill_path(skill_name)
        if not skill_path:
            return False, "skill_not_found"
        
        try:
            code = skill_path.read_text()
            
            # Sprawdź czy są wymagane funkcje
            has_get_info = "def get_info(" in code
            has_execute = "def execute(" in code
            
            # Dodaj brakujące funkcje
            if not has_get_info:
                code += """

def get_info():
    return {"name": "%(skill)s", "version": "v1"}
""" % {"skill": skill_name}
            
            if not has_execute:
                code += """

def execute(params):
    return {"success": False, "error": "Not implemented"}
"""
            
            skill_path.write_text(code)
            print(f"[HEAL] ✓ Naprawiono interfejs (get_info: {has_get_info}, execute: {has_execute})")
            return True, ""
            
        except Exception as e:
            return False, f"fix_interface_error:{e}"
    
    def _evolve_with_llm(self, skill_name: str, error_msg: str) -> tuple:
        """Ewolucja z pomocą LLM."""
        # Użyj EvoEngine do ewolucji
        try:
            from cores.v1.evo_engine import EvoEngine
            evo = EvoEngine(self.sm, self.llm, None)
            
            result = evo.smart_evolve(
                skill_name,
                f"Napraw błąd: {error_msg[:200]}",
                iterations=1
            )
            
            success = result.get("success", False)
            print(f"[HEAL] {'✓' if success else '✗'} Ewolucja LLM: {result.get('message', 'unknown')}")
            return success, result.get("error", "")
            
        except Exception as e:
            return False, f"evolve_error:{e}"
    
    def _rewrite_skill(self, skill_name: str, error_msg: str) -> tuple:
        """Przepisanie skillu od nowa."""
        print(f"[HEAL] Przepisywanie skillu {skill_name} od nowa...")
        return self._evolve_with_llm(skill_name, "Rewrite from scratch: " + error_msg)
    
    def _get_skill_path(self, skill_name: str) -> Optional[Path]:
        """Znajduje ścieżkę do pliku skillu."""
        from cores.v1.config import SKILLS_DIR
        
        # Sprawdź standardowe lokalizacje
        paths = [
            SKILLS_DIR / skill_name / "v1" / "skill.py",
            SKILLS_DIR / skill_name / "stable" / "skill.py",
            SKILLS_DIR / skill_name / "latest" / "skill.py",
        ]
        
        # Sprawdź strukturę providera
        cap_dir = SKILLS_DIR / skill_name
        if cap_dir.exists():
            for prov in ["espeak", "vosk", "duckduckgo", "shell"]:
                paths.append(cap_dir / "providers" / prov / "stable" / "skill.py")
        
        for p in paths:
            if p.exists():
                return p
        
        return None
    
    def get_healing_report(self) -> str:
        """Generuje raport z procesów naprawy."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        
        lines = [
            f"=== Raport Autonaprawy ===",
            f"Całkowite próby: {total}",
            f"Udane naprawy: {successful} ({100*successful/total:.1f}%)",
            "",
            "Skuteczność strategii:",
        ]
        
        stats = self.reflection.healing_memory["strategy_success"]
        for strategy, counts in sorted(stats.items(), key=lambda x: x[1]["success"], reverse=True):
            total_s = counts["success"] + counts["fail"]
            rate = 100 * counts["success"] / total_s if total_s > 0 else 0
            lines.append(f"  {strategy}: {counts['success']}/{total_s} ({rate:.0f}%)")
        
        return "\n".join(lines)


# Convenience function for direct usage
def heal_skill(skill_name: str, error_info: Dict, llm_client, skill_manager, state: Dict) -> HealingResult:
    """Funkcja pomocnicza do szybkiej naprawy skillu."""
    orchestrator = SelfHealingOrchestrator(llm_client, skill_manager, state)
    return orchestrator.heal_skill(skill_name, error_info)
