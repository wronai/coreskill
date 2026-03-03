#!/usr/bin/env python3
"""
evo-engine SkillManager — skill CRUD, testing, diagnosis, evolution.
With ProviderSelector integration for capability/provider architecture.
"""
import json
import hashlib
import shutil
import subprocess
import sys
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

from .config import SKILLS_DIR, save_state, cpr, C
from .utils import clean_code
from .preflight import SkillPreflight


def _load_bootstrap_skill(name):
    """Load a bootstrap skill class directly. Returns instance or None."""
    # New structure: providers/<provider>/v1/skill.py
    prov_dir = SKILLS_DIR / name / "providers"
    if prov_dir.is_dir():
        for provider in sorted(prov_dir.iterdir()):
            if provider.is_dir() and not provider.name.startswith("."):
                for vdir in sorted(provider.iterdir(), reverse=True):
                    p = vdir / "skill.py"
                    if p.exists():
                        return _load_skill_from_path(p, f"boot_{name}")
    # Legacy structure: v1/skill.py
    p = SKILLS_DIR / name / "v1" / "skill.py"
    if not p.exists(): return None
    return _load_skill_from_path(p, f"boot_{name}")


def _load_skill_from_path(p, mod_name="skill"):
    """Load a skill module and return first class instance with execute()."""
    try:
        spec = importlib.util.spec_from_file_location(mod_name, str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and hasattr(obj, "execute") and attr != "type":
                return obj()
        return None
    except Exception:
        return None


class SkillManager:
    def __init__(self, llm, logger, provider_selector=None):
        self.llm = llm
        self.log = logger
        self.provider_selector = provider_selector
        self.preflight = SkillPreflight()
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        # Load bootstrap skills for internal use
        self._devops = _load_bootstrap_skill("devops")
        self._deps = _load_bootstrap_skill("deps")
        self._git = _load_bootstrap_skill("git_ops")

    def _collect_versions(self, skill_dir):
        """Collect version dirs from a skill or provider directory."""
        return sorted([v.name for v in skill_dir.iterdir()
                       if v.is_dir() and v.name.startswith("v")
                       and not v.name.startswith("__")])

    def list_skills(self):
        sk = {}
        if not SKILLS_DIR.exists(): return sk
        for d in sorted(SKILLS_DIR.iterdir()):
            if not d.is_dir() or d.name.startswith("."): continue
            prov_dir = d / "providers"
            if prov_dir.is_dir():
                all_versions = []
                for provider in sorted(prov_dir.iterdir()):
                    if provider.is_dir() and not provider.name.startswith("."):
                        all_versions.extend(self._collect_versions(provider))
                if all_versions:
                    sk[d.name] = sorted(set(all_versions))
                continue
            vs = self._collect_versions(d)
            if vs: sk[d.name] = vs
        return sk

    def latest_v(self, name):
        d = SKILLS_DIR / name
        if not d.exists(): return None

        # New structure: check active provider
        provider = self._active_provider(name)
        if provider:
            prov_dir = d / "providers" / provider
            if prov_dir.is_dir():
                vs = []
                for v in prov_dir.iterdir():
                    if v.is_dir() and v.name.startswith("v") and v.name[1:].isdigit():
                        vs.append(v.name)
                vs.sort(key=lambda x: int(x[1:]))
                return vs[-1] if vs else None

        # Legacy structure
        vs = []
        for v in d.iterdir():
            if v.is_dir() and v.name.startswith("v") and v.name[1:].isdigit():
                vs.append(v.name)
        vs.sort(key=lambda x: int(x[1:]))
        return vs[-1] if vs else None

    def _active_provider(self, name):
        """Get the active provider for a capability. Returns provider name or None."""
        if self.provider_selector:
            providers = self.provider_selector.list_providers(name)
            if providers and providers != ["default"]:
                return self.provider_selector.select(name)
        return None

    def skill_path(self, name, version=None):
        if not version: version = self.latest_v(name)
        if not version: return None

        # New structure: check provider path
        provider = self._active_provider(name)
        if provider:
            p = SKILLS_DIR / name / "providers" / provider / version / "skill.py"
            if p.exists():
                return p

        # Legacy structure
        return SKILLS_DIR / name / version / "skill.py"

    def create_skill(self, name, desc):
        ev = self.latest_v(name)
        nv = f"v{int(ev[1:])+1}" if ev else "v1"

        # Determine target directory (new or legacy structure)
        provider = self._active_provider(name)
        if provider:
            sd = SKILLS_DIR / name / "providers" / provider / nv
        else:
            sd = SKILLS_DIR / name / nv
        sd.mkdir(parents=True, exist_ok=True)

        # Gather system context from deps skill
        sys_ctx = ""
        if self._deps:
            scan = self._deps.scan_system()
            caps = scan.get("capabilities", {})
            sys_ctx = f"\nSystem capabilities: {json.dumps(caps)}"

        learning = self.log.learn_summary(name)
        prompt = (f"Create Python skill '{name}'. {desc}\n"
                  f"Requirements:\n"
                  f"- class with execute(input_data:dict)->dict\n"
                  f"- execute() MUST return dict with 'success':True/False key\n"
                  f"- get_info()->dict function\n"
                  f"- health_check()->bool function\n"
                  f"- if __name__=='__main__' test block\n"
                  f"- Use ONLY stdlib + available system commands. NO pip packages.\n"
                  f"- Version: {nv}"
                  f"{sys_ctx}")
        code = clean_code(self.llm.gen_code(prompt, learning=learning))
        if not code or "[ERROR]" in code:
            self.log.skill(name, "create_failed", {"error": "LLM returned no code"})
            return False, "Failed to generate code"

        (sd / "skill.py").write_text(code)
        (sd / "Dockerfile").write_text(
            f"FROM python:3.12-slim\nWORKDIR /app\nCOPY skill.py .\n"
            f'CMD ["python","skill.py"]\n')
        meta = {"name": name, "version": nv, "description": desc,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "checksum": hashlib.md5(code.encode()).hexdigest()}
        (sd / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.skill(name, "skill_created", meta)

        # Git commit if available
        if self._git:
            self._git.commit_skill_version(name, nv, str(sd))

        return True, f"Skill '{name}' {nv} created"

    def diagnose_skill(self, name, version=None):
        """Use devops+deps to fully diagnose a skill. Returns diagnostic dict."""
        p = self.skill_path(name, version)
        if not p or not p.exists():
            return {"phase": "missing", "error": f"Skill '{name}' not found"}

        if not self._devops:
            # Fallback: raw subprocess test
            return self._raw_test(name, version)

        # Full diagnostic via devops skill
        result = self._devops.test_skill(str(p))
        phase = result.get("phase", "unknown")

        # Enrich with deps info if dependency problem
        if phase == "deps" and self._deps:
            missing = result.get("missing", [])
            alternatives = {}
            for mod in missing:
                alt = self._deps.suggest_alternatives(mod)
                if alt.get("success"):
                    alternatives[mod] = alt["alternative"]
            result["alternatives"] = alternatives

        self.log.skill(name, "diagnosis", result)
        return result

    def _raw_test(self, name, version=None):
        """Fallback test without devops skill."""
        p = self.skill_path(name, version)
        if not p: return {"phase": "missing", "error": "not found"}
        try:
            r = subprocess.run([sys.executable, str(p)],
                              capture_output=True, text=True, timeout=15,
                              cwd=str(p.parent))
            ok = r.returncode == 0
            return {"success": ok, "phase": "runtime",
                    "output": r.stdout[-500:],
                    "error": r.stderr[-500:] if not ok else None}
        except subprocess.TimeoutExpired:
            return {"success": False, "phase": "runtime", "error": "Timeout"}
        except Exception as e:
            return {"success": False, "phase": "runtime", "error": str(e)}

    def test_skill(self, name, version=None):
        """Test skill. Returns (success, output_or_error)."""
        diag = self.diagnose_skill(name, version)
        ok = diag.get("success", False)
        if ok:
            return True, diag.get("output", "OK")
        return False, diag.get("error", json.dumps(diag, default=str)[:300])

    def _resolve_skill_path(self, name, version):
        """Resolve skill path, skipping rolled-back versions."""
        p = self.skill_path(name, version)
        if not p or not p.exists():
            p = SKILLS_DIR / name / version / "skill.py"

        mp = p.parent / "meta.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            if m.get("rolled_back"):
                parent_dir = p.parent.parent
                vs = sorted([v.name for v in parent_dir.iterdir()
                             if v.is_dir() and v.name.startswith("v") and v.name != version])
                if vs:
                    p = parent_dir / vs[-1] / "skill.py"
        return p

    def _load_and_run(self, name, version, p, inp):
        """Load skill module and execute. Returns result dict."""
        spec = importlib.util.spec_from_file_location(
            f"sk_{name}_{version}_{id(self)}", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        info = mod.get_info() if hasattr(mod, "get_info") else {"name": name}
        for a in dir(mod):
            o = getattr(mod, a)
            if isinstance(o, type) and hasattr(o, "execute"):
                result = o().execute(inp or {})
                self.log.skill(name, "exec_success", {"version": version})
                return {"success": True, "result": result, "info": info}
        if hasattr(mod, "execute"):
            result = mod.execute(inp or {})
            self.log.skill(name, "exec_success", {"version": version})
            return {"success": True, "result": result, "info": info}
        return {"success": True, "result": info}

    def check_health(self, name):
        """Check if a skill passes preflight and health_check()."""
        p = self.skill_path(name)
        if not p or not p.exists():
            return False
        pf = self.preflight.check_all(p)
        if not pf.ok:
            return False
        try:
            spec = importlib.util.spec_from_file_location(f"hc_{name}", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "health_check"):
                return bool(mod.health_check())
            return True
        except Exception:
            return False

    def _preflight_and_fix(self, p, name):
        """Run preflight on skill, auto-fix imports if possible. Returns PreflightResult."""
        pf = self.preflight.check_all(p)
        if not pf.ok and pf.stage == "imports" and pf.details.get("missing_imports"):
            code = p.read_text()
            fixed = self.preflight.auto_fix_imports(code)
            if fixed != code:
                p.write_text(fixed)
                self.log.skill(name, "auto_fix", {"fixed": pf.details["missing_imports"]})
                cpr(C.DIM, f"[PREFLIGHT] Auto-fixed imports in {name}: {pf.details['missing_imports']}")
                pf = self.preflight.check_all(p)
        return pf

    def exec_skill(self, name, version=None, inp=None):
        """Execute skill with preflight validation."""
        if not version: version = self.latest_v(name)
        if not version: return {"success": False, "error": f"'{name}' not found"}

        p = self._resolve_skill_path(name, version)
        if not p.exists(): return {"success": False, "error": f"Not found: {p}"}

        # Pre-flight check with auto-fix
        pf = self._preflight_and_fix(p, name)
        if not pf.ok:
            self.log.skill(name, "preflight_fail", pf.to_dict())
            return {"success": False, "error": f"Preflight ({pf.stage}): {pf.error}",
                    "preflight": pf.to_dict()}

        try:
            return self._load_and_run(name, version, p, inp)
        except Exception as e:
            self.log.skill(name, "exec_error", {"error": str(e), "version": version})
            return {"success": False, "error": str(e), "tb": traceback.format_exc()}

    def smart_evolve(self, name, feedback, user_msg=""):
        """Evolve skill using devops diagnosis + deps alternatives."""
        cv = self.latest_v(name)
        if not cv: return False, "Not found"
        p = self.skill_path(name, cv)
        old = p.read_text()

        # Get diagnosis from devops
        diag = self.diagnose_skill(name, cv)
        phase = diag.get("phase", "unknown")

        # Build smart prompt using devops.generate_fix_prompt
        if self._devops:
            prompt = self._devops.generate_fix_prompt(str(p), diag)
            if isinstance(prompt, dict):
                prompt = prompt.get("prompt", "")
        else:
            prompt = (f"Fix this Python skill:\n```python\n{old}\n```\n"
                      f"Error: {feedback}\n")

        # Add system capabilities context
        if self._deps:
            scan = self._deps.scan_system()
            prompt += f"\nAvailable system tools: {json.dumps(scan.get('capabilities', {}))}"

        # Add learning from logs
        learning = self.log.learn_summary(name)
        if learning != "No history":
            prompt += f"\nLearnings: {learning}"

        if user_msg:
            prompt += f"\nUser wanted: {user_msg}"

        prompt += ("\nReturn ONLY the complete fixed Python code."
                   "\nMUST use only stdlib + available system commands."
                   "\nexecute() MUST return dict with 'success' key.")

        code = clean_code(self.llm.gen_code(prompt))
        if not code or "[ERROR]" in code:
            return False, "LLM failed to generate fix"

        # Pre-flight new code before saving
        code = self.preflight.auto_fix_imports(code)

        nv = f"v{int(cv[1:]) + 1}"
        # Determine target directory
        provider = self._active_provider(name)
        if provider:
            nd = SKILLS_DIR / name / "providers" / provider / nv
        else:
            nd = SKILLS_DIR / name / nv
        nd.mkdir(parents=True, exist_ok=True)
        (nd / "skill.py").write_text(code)
        # Copy Dockerfile from previous version
        old_dir = p.parent
        odf = old_dir / "Dockerfile"
        if odf.exists(): shutil.copy2(str(odf), str(nd / "Dockerfile"))
        meta = {"name": name, "version": nv, "parent": cv, "phase": phase,
                "created_at": datetime.now(timezone.utc).isoformat()}
        (nd / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.skill(name, "skill_evolved", meta)

        if self._git:
            self._git.commit_skill_version(name, nv, str(nd))

        return True, f"'{name}' evolved: {cv} -> {nv}"

    def evolve(self, name, feedback):
        """Backward-compatible evolve - delegates to smart_evolve."""
        return self.smart_evolve(name, feedback)

    def rollback(self, name):
        d = SKILLS_DIR / name

        # Check new structure first
        provider = self._active_provider(name)
        if provider:
            d = SKILLS_DIR / name / "providers" / provider

        if not d.exists(): return False, "Not found"
        vs = sorted([v.name for v in d.iterdir() if v.is_dir() and v.name.startswith("v")])
        if len(vs) < 2: return False, "No previous version"
        mp = d / vs[-1] / "meta.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            m["rolled_back"] = True
            mp.write_text(json.dumps(m, indent=2))
        self.log.skill(name, "rollback", {"from": vs[-1], "to": vs[-2]})
        return True, f"Rolled back: {vs[-1]} -> {vs[-2]}"
