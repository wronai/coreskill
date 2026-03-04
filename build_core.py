#!/usr/bin/env python3
"""Build script: generates cores/v1/core.py for evo-engine"""
import os
import textwrap
from pathlib import Path

# Use relative path based on script location
CORE_PATH = Path(__file__).parent / "cores" / "v1" / "core.py"

code = textwrap.dedent(r'''
#!/usr/bin/env python3
"""
evo-engine Core v1 - text2pipeline Evolutionary Chat
=====================================================
Auto-detects needed skills, creates pipelines, speaks via TTS.
"""
import os, sys, json, subprocess, hashlib, traceback, shutil, re
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

try:
    import litellm
    litellm.drop_params = True
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm", "-q",
                           "--break-system-packages"])
    import litellm
    litellm.drop_params = True

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / "skills"
PIPELINES_DIR = ROOT / "pipelines"
LOGS_DIR = ROOT / "logs"
REGISTRY_DIR = ROOT / "registry"
STATE_FILE = ROOT / ".evo_state.json"

class C:
    R="\033[0m"; B="\033[1m"; D="\033[2m"; GR="\033[32m"
    YE="\033[33m"; BL="\033[34m"; MA="\033[35m"; CY="\033[36m"; RE="\033[31m"

def cpr(c, m):
    print(f"{c}{m}{C.R}")

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(s):
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(s, indent=2))

def log_ev(event, data=None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    e = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, "data": data or {}}
    with open(LOGS_DIR / "core.log", "a") as f:
        f.write(json.dumps(e) + "\n")


# === LLM ===
class LLM:
    def __init__(self, key, model):
        self.key = key
        self.model = model
        os.environ["OPENROUTER_API_KEY"] = key

    def chat(self, msgs, temp=0.7, mt=4096):
        try:
            r = litellm.completion(model=self.model, messages=msgs,
                                   temperature=temp, max_tokens=mt, api_key=self.key)
            return r.choices[0].message.content
        except Exception as e:
            log_ev("llm_error", {"error": str(e)})
            return f"[LLM ERROR] {e}"

    def gen_code(self, prompt):
        s = ("You are an expert Python developer. Return ONLY Python code. "
             "No markdown fences. Include imports, error handling, docstrings. "
             "Must be a complete runnable module.")
        return self._clean(self.chat([{"role":"system","content":s},
                                       {"role":"user","content":prompt}], temp=0.3))

    def _clean(self, code):
        if not code:
            return code
        if code.startswith("```"):
            lines = code.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            code = "\n".join(lines[1:end])
        return code


# === Skill Loader ===
class SkillLoader:
    """Load and execute skills dynamically."""

    @staticmethod
    def list_skills():
        sk = {}
        if not SKILLS_DIR.exists():
            return sk
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                vs = sorted([v.name for v in d.iterdir()
                             if v.is_dir() and v.name.startswith("v")])
                if vs:
                    sk[d.name] = vs
        return sk

    @staticmethod
    def latest_v(name):
        d = SKILLS_DIR / name
        if not d.exists():
            return None
        vs = sorted([v.name for v in d.iterdir()
                     if v.is_dir() and v.name.startswith("v")])
        return vs[-1] if vs else None

    @staticmethod
    def load_module(name, version=None):
        if not version:
            version = SkillLoader.latest_v(name)
        if not version:
            return None
        p = SKILLS_DIR / name / version / "skill.py"
        if not p.exists():
            return None
        spec = importlib.util.spec_from_file_location(f"sk_{name}_{version}", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def run(name, input_data=None, version=None):
        mod = SkillLoader.load_module(name, version)
        if not mod:
            return {"success": False, "error": f"Skill '{name}' not found"}
        try:
            # Try class-based first
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if isinstance(obj, type) and hasattr(obj, "execute") and attr != "type":
                    result = obj().execute(input_data or {})
                    return {"success": True, "result": result}
            # Module-level execute
            if hasattr(mod, "execute"):
                return {"success": True, "result": mod.execute(input_data or {})}
            return {"success": False, "error": "No execute method"}
        except Exception as e:
            return {"success": False, "error": str(e), "tb": traceback.format_exc()}

    @staticmethod
    def get_registry():
        rp = REGISTRY_DIR / "skills.json"
        if rp.exists():
            return json.loads(rp.read_text())
        # Build from meta.json files
        reg = {"skills": {}, "capability_index": {}}
        for name, versions in SkillLoader.list_skills().items():
            mp = SKILLS_DIR / name / versions[-1] / "meta.json"
            if mp.exists():
                meta = json.loads(mp.read_text())
                caps = meta.get("capabilities", [])
                reg["skills"][name] = {"capabilities": caps}
                for cap in caps:
                    reg["capability_index"][cap] = name
        return reg

    @staticmethod
    def find_skill_for(text):
        """Find a skill that matches the user's request."""
        reg = SkillLoader.get_registry()
        text_lower = text.lower()
        idx = reg.get("capability_index", {})
        for keyword, skill_name in idx.items():
            if keyword in text_lower:
                return skill_name
        return None


# === Skill Creator ===
class SkillCreator:
    def __init__(self, llm):
        self.llm = llm

    def create(self, name, description):
        ev = SkillLoader.latest_v(name)
        nv = f"v{int(ev[1:])+1}" if ev else "v1"
        sd = SKILLS_DIR / name / nv
        sd.mkdir(parents=True, exist_ok=True)

        prompt = (f"Create Python skill '{name}'. {description}\n"
                  "Must have: class with execute(dict)->dict, "
                  "get_info()->dict (with 'capabilities' list), "
                  "health_check()->bool, __main__ test block. "
                  f"Version: {nv}")
        code = self.llm.gen_code(prompt)
        (sd / "skill.py").write_text(code)
        (sd / "Dockerfile").write_text(
            "FROM python:3.12-slim\nWORKDIR /app\nCOPY skill.py .\n"
            'CMD ["python","skill.py"]\n')
        meta = {"name": name, "version": nv, "description": description,
                "capabilities": [], "created_at": datetime.now(timezone.utc).isoformat(),
                "checksum": hashlib.md5(code.encode()).hexdigest()}
        (sd / "meta.json").write_text(json.dumps(meta, indent=2))
        log_ev("skill_created", meta)
        return True, f"Skill '{name}' {nv} created at {sd}"

    def evolve(self, name, feedback):
        cv = SkillLoader.latest_v(name)
        if not cv:
            return False, "Not found"
        old = (SKILLS_DIR / name / cv / "skill.py").read_text()
        prompt = (f"Improve this skill:\n```python\n{old}\n```\n"
                  f"Feedback: {feedback}\nKeep interface: execute, get_info, health_check.")
        code = self.llm.gen_code(prompt)
        nv = f"v{int(cv[1:])+1}"
        nd = SKILLS_DIR / name / nv
        nd.mkdir(parents=True, exist_ok=True)
        (nd / "skill.py").write_text(code)
        odf = SKILLS_DIR / name / cv / "Dockerfile"
        if odf.exists():
            shutil.copy2(str(odf), str(nd / "Dockerfile"))
        meta = {"name": name, "version": nv, "parent": cv,
                "created_at": datetime.now(timezone.utc).isoformat()}
        (nd / "meta.json").write_text(json.dumps(meta, indent=2))
        log_ev("skill_evolved", meta)
        return True, f"'{name}': {cv} -> {nv}"

    def rollback(self, name):
        d = SKILLS_DIR / name
        if not d.exists():
            return False, "Not found"
        vs = sorted([v.name for v in d.iterdir()
                     if v.is_dir() and v.name.startswith("v")])
        if len(vs) < 2:
            return False, "No previous version"
        latest = vs[-1]
        shutil.move(str(d / latest), str(d / f".{latest}_rolled_back"))
        log_ev("rollback", {"name": name, "from": latest, "to": vs[-2]})
        return True, f"Rolled back: {latest} -> {vs[-2]}"


# === Pipeline Engine ===
class PipelineEngine:
    """text2pipeline: natural language -> skill chain -> execute"""

    def __init__(self, llm):
        self.llm = llm

    def build_from_text(self, text):
        """Parse user text into a pipeline of skill calls."""
        skills = SkillLoader.list_skills()
        reg = SkillLoader.get_registry()

        sys_prompt = (
            "You are a pipeline builder. Given user request and available skills, "
            "return ONLY a JSON array of steps. Each step: "
            '{"skill":"name","input":{"key":"value"}}. '
            "If no existing skill fits, include "
            '{"action":"create_skill","name":"...","description":"..."}. '
            f"Available skills: {json.dumps(list(skills.keys()))}. "
            f"Skill capabilities: {json.dumps(reg.get('skills', {}))}"
        )
        raw = self.llm.chat([{"role":"system","content":sys_prompt},
                              {"role":"user","content":text}], temp=0.2)
        raw = self.llm._clean(raw)
        try:
            # Try to find JSON in response
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"skill": "echo", "input": {"text": text, "raw_response": raw}}]

    def execute_pipeline(self, steps, tts_enabled=False):
        """Execute pipeline steps sequentially."""
        results = []
        for i, step in enumerate(steps):
            if step.get("action") == "create_skill":
                cpr(C.YE, f"  [pipeline] Creating skill: {step['name']}")
                # Would create skill here
                results.append({"step": i, "action": "create_skill", "name": step["name"]})
                continue

            skill_name = step.get("skill", "echo")
            inp = step.get("input", {})

            # Pass previous results as context
            if results and isinstance(results[-1], dict):
                prev = results[-1].get("result", {})
                if isinstance(prev, dict):
                    for k, v in prev.items():
                        if k not in inp:
                            inp[f"prev_{k}"] = v

            cpr(C.D, f"  [step {i+1}] {skill_name}")
            r = SkillLoader.run(skill_name, inp)
            results.append({"step": i+1, "skill": skill_name, **r})

            # TTS output if enabled
            if tts_enabled and r.get("success"):
                res = r.get("result", {})
                speak_text = res.get("text") or res.get("output") or str(res)
                if speak_text and skill_name != "tts":
                    SkillLoader.run("tts", {"text": str(speak_text)[:500]})

        return results

    def save_pipeline(self, name, steps):
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
        p = {"name": name, "steps": steps,
             "created_at": datetime.now(timezone.utc).isoformat()}
        (PIPELINES_DIR / f"{name}.json").write_text(json.dumps(p, indent=2))
        return str(PIPELINES_DIR / f"{name}.json")

    def list_pipelines(self):
        if not PIPELINES_DIR.exists():
            return []
        return [f.stem for f in PIPELINES_DIR.glob("*.json")]

    def load_pipeline(self, name):
        p = PIPELINES_DIR / f"{name}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text())


# === Docker Compose ===
def gen_compose(skills, state):
    svc = {}
    for side in ["a", "b"]:
        svc[f"core-{side}"] = {
            "build": {"context": ".", "dockerfile": "Dockerfile.core"},
            "container_name": f"evo-core-{side}",
            "environment": {
                "CORE_ID": side.upper(),
                "CORE_VERSION": str(state.get(f"core_{side}_version", 1)),
                "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
                "MODEL": state.get("model", ""),
            },
            "volumes": ["./cores:/app/cores:ro", "./skills:/app/skills",
                        "./logs:/app/logs", "./pipelines:/app/pipelines"],
            "restart": "unless-stopped",
        }
    for sn, vs in skills.items():
        svc[f"skill-{sn}"] = {
            "build": {"context": f"./skills/{sn}/{vs[-1]}"},
            "container_name": f"evo-skill-{sn}",
            "restart": "unless-stopped",
        }
    out = ROOT / "docker-compose.yml"
    out.write_text(json.dumps({"version": "3.8", "services": svc}, indent=2))
    return str(out)


# === Supervisor ===
class Supervisor:
    def __init__(self, st):
        self.st = st
    def active(self):
        return self.st.get("active_core", "A")
    def switch(self):
        c = self.active()
        n = "B" if c == "A" else "A"
        self.st["active_core"] = n
        save_state(self.st)
        return n


# === Main Chat ===
MODELS = [
    "openrouter/stepfun/step-3.5-flash:free",
    "openrouter/google/gemma-3-1b-it:free",
    "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    "openrouter/qwen/qwen-2.5-72b-instruct:free",
    "openrouter/deepseek/deepseek-chat-v3-0324:free",
    "openrouter/google/gemini-2.0-flash-exp:free",
]

HELP = """
  /skills             List skills        /create <n>   Create skill
  /run <n> [v]     Run skill          /evolve <n>   Improve skill
  /rollback <n>    Rollback           /pipe <text>      Build+run pipeline
  /pipelines          List saved         /compose         Docker compose
  /model <n>       Switch model       /models           Available models
  /tts on|off         Toggle TTS         /core             A/B status
  /switch             Switch core        /log              Recent logs
  /state              System state       /help             This help
  /quit               Exit
"""


def main():
    state = load_state()
    sv = Supervisor(state)

    cpr(C.CY, "\n" + "=" * 50)
    cpr(C.CY, "  evo-engine | text2pipeline Evolutionary AI")
    cpr(C.CY, "  Dual-core A/B | Auto-skills | TTS")
    cpr(C.CY, "=" * 50)

    # API Key
    ak = state.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")
    if not ak:
        cpr(C.YE, "\nPodaj API token do OpenRouter:")
        cpr(C.D, "(https://openrouter.ai/keys)")
        ak = input(f"{C.GR}> {C.R}").strip()
        if not ak:
            cpr(C.RE, "Required.")
            sys.exit(1)

    state["openrouter_api_key"] = ak
    if not state.get("created_at"):
        state["created_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    mdl = state.get("model", "openrouter/stepfun/step-3.5-flash:free")
    tts_on = state.get("tts_enabled", False)

    llm = LLM(ak, mdl)
    creator = SkillCreator(llm)
    pipeline = PipelineEngine(llm)

    cpr(C.D, f"Model: {mdl} | Core: {sv.active()} | TTS: {'ON' if tts_on else 'OFF'}")
    sk = SkillLoader.list_skills()
    if sk:
        cpr(C.GR, f"Skills: {', '.join(f'{n}({vs[-1]})' for n, vs in sk.items())}")
    cpr(C.D, "Type /help or chat naturally.\n")

    # Greet with TTS if enabled
    if tts_on:
        SkillLoader.run("tts", {"text": "System ewolucyjny gotowy. Jak moge pomoc?"})

    conv = []

    while True:
        try:
            ui = input(f"{C.GR}you> {C.R}").strip()
        except (EOFError, KeyboardInterrupt):
            cpr(C.D, "\nBye!")
            break
        if not ui:
            continue

        # === Slash commands ===
        if ui.startswith("/"):
            p = ui.split(maxsplit=2)
            act = p[0].lower()
            a1 = p[1] if len(p) > 1 else ""
            a2 = p[2] if len(p) > 2 else ""

            if act == "/help":
                print(HELP)
            elif act in ("/quit", "/exit"):
                break
            elif act == "/skills":
                for n, vs in SkillLoader.list_skills().items():
                    cpr(C.CY, f"  {n}: {', '.join(vs)} [active: {vs[-1]}]")
            elif act == "/create":
                if not a1:
                    cpr(C.YE, "Usage: /create <skill_name>")
                    continue
                cpr(C.CY, f"Describe '{a1}':")
                desc = input(f"{C.GR}> {C.R}").strip()
                if desc:
                    cpr(C.D, "Generating...")
                    ok, msg = creator.create(a1, desc)
                    cpr(C.GR if ok else C.RE, msg)
            elif act == "/run":
                if not a1:
                    cpr(C.YE, "Usage: /run <skill_name> [input_json]")
                    continue
                inp = json.loads(a2) if a2 else {}
                r = SkillLoader.run(a1, inp)
                print(json.dumps(r, indent=2, default=str, ensure_ascii=False))
                if tts_on and r.get("success"):
                    res = r.get("result", {})
                    txt = res.get("text") or res.get("output") or ""
                    if txt and a1 != "tts":
                        SkillLoader.run("tts", {"text": str(txt)[:300]})
            elif act == "/evolve":
                if not a1:
                    cpr(C.YE, "Usage: /evolve <skill_name>")
                    continue
                cpr(C.CY, "Feedback:")
                fb = input(f"{C.GR}> {C.R}").strip()
                if fb:
                    ok, msg = creator.evolve(a1, fb)
                    cpr(C.GR if ok else C.RE, msg)
            elif act == "/rollback":
                if a1:
                    ok, msg = creator.rollback(a1)
                    cpr(C.GR if ok else C.RE, msg)
            elif act == "/pipe":
                text = " ".join(p[1:]) if len(p) > 1 else ""
                if not text:
                    cpr(C.YE, "Usage: /pipe <description>")
                    continue
                cpr(C.D, "Building pipeline...")
                steps = pipeline.build_from_text(text)
                cpr(C.CY, f"Pipeline ({len(steps)} steps):")
                for i, s in enumerate(steps):
                    cpr(C.D, f"  {i+1}. {s.get('skill', s.get('action','?'))}")
                cpr(C.D, "Executing...")
                results = pipeline.execute_pipeline(steps, tts_enabled=tts_on)
                for r in results:
                    ok = r.get("success", False)
                    cpr(C.GR if ok else C.RE,
                        f"  Step {r.get('step')}: {'OK' if ok else r.get('error','?')}")
                # Save it
                pname = re.sub(r'[^a-z0-9]+', '_', text.lower())[:30]
                pipeline.save_pipeline(pname, steps)
            elif act == "/pipelines":
                for pn in pipeline.list_pipelines():
                    cpr(C.CY, f"  {pn}")
            elif act == "/tts":
                if a1 == "on":
                    tts_on = True
                    state["tts_enabled"] = True
                    save_state(state)
                    SkillLoader.run("tts", {"text": "Tryb glosowy wlaczony"})
                    cpr(C.GR, "TTS ON")
                elif a1 == "off":
                    tts_on = False
                    state["tts_enabled"] = False
                    save_state(state)
                    cpr(C.GR, "TTS OFF")
                else:
                    cpr(C.D, f"TTS: {'ON' if tts_on else 'OFF'}. Usage: /tts on|off")
            elif act == "/compose":
                cpr(C.GR, f"Generated: {gen_compose(SkillLoader.list_skills(), state)}")
            elif act == "/model":
                if not a1:
                    cpr(C.D, f"Current: {state.get('model')}")
                    continue
                nm = a1 if a1.startswith("openrouter/") else f"openrouter/{a1}"
                state["model"] = nm
                save_state(state)
                llm = LLM(ak, nm)
                creator.llm = llm
                pipeline.llm = llm
                cpr(C.GR, f"Model -> {nm}")
            elif act == "/models":
                for m in MODELS:
                    tag = " <-" if m == state.get("model") else ""
                    cpr(C.D, f"  {m}{tag}")
            elif act == "/core":
                a = sv.active()
                cpr(C.CY, f"  A: v{state.get('core_a_version',1)} {'<-ACTIVE' if a=='A' else ''}")
                cpr(C.CY, f"  B: v{state.get('core_b_version',1)} {'<-ACTIVE' if a=='B' else ''}")
            elif act == "/switch":
                cpr(C.GR, f"Switched to {sv.switch()}")
            elif act == "/log":
                lf = LOGS_DIR / "core.log"
                if lf.exists():
                    for ln in lf.read_text().strip().split("\n")[-15:]:
                        cpr(C.D, f"  {ln}")
            elif act == "/state":
                print(json.dumps(state, indent=2))
            else:
                cpr(C.YE, f"Unknown: {act}. /help")
            continue

        # === Natural language ===
        conv.append({"role": "user", "content": ui})

        # Check if user wants TTS activation
        tts_words = ["mow", "mowa", "glos", "tts", "speak", "voice", "powiedz", "czytaj"]
        wants_tts = any(w in ui.lower() for w in tts_words)
        if wants_tts and not tts_on:
            tts_on = True
            state["tts_enabled"] = True
            save_state(state)
            cpr(C.GR, "[TTS wlaczony automatycznie]")
            SkillLoader.run("tts", {"text": "Tryb glosowy wlaczony. Teraz bede mowic."})

        # Check if there is a direct skill match
        matched_skill = SkillLoader.find_skill_for(ui)
        if matched_skill == "tts" and wants_tts:
            # User wants TTS - acknowledge and continue to LLM for response
            pass

        # Get LLM response
        skills = SkillLoader.list_skills()
        pipes = pipeline.list_pipelines()
        sys_p = (
            "Jestes rdzeniem systemu evo-engine - ewolucyjny system AI. "
            "Pomagasz tworzyc skills (moduly Python), pipelines, i automatyzujesz zadania. "
            f"Dostepne skills: {json.dumps(list(skills.keys()))}. "
            f"Pipelines: {pipes}. "
            "Jesli user chce cos zbudowac, zaproponuj /create <n> lub /pipe <opis>. "
            "Jesli user mowi po polsku, odpowiadaj po polsku. "
            "Bądź konkretny i pomocny. Dawaj krotkie odpowiedzi."
        )
        msgs = [{"role": "system", "content": sys_p}] + conv[-20:]
        cpr(C.D, "Thinking...")
        resp = llm.chat(msgs)
        conv.append({"role": "assistant", "content": resp})

        cpr(C.MA, f"evo> {resp}")
        print()

        # Speak response via TTS if enabled
        if tts_on:
            # Clean response for TTS (remove markdown, links, code)
            clean = re.sub(r'```.*?```', '', resp, flags=re.DOTALL)
            clean = re.sub(r'`[^`]+`', '', clean)
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
            clean = re.sub(r'[#*_~]', '', clean)
            clean = clean.strip()
            if clean:
                SkillLoader.run("tts", {"text": clean[:500], "lang": "pl"})


if __name__ == "__main__":
    main()
''').lstrip()

os.makedirs(os.path.dirname(CORE_PATH), exist_ok=True)
with open(CORE_PATH, "w") as f:
    f.write(code)
print(f"Generated: {CORE_PATH} ({len(code)} bytes)")
