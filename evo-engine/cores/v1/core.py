#!/usr/bin/env python3
"""
evo-engine Core v1 - Evolutionary Chat Engine
Dual-core (A/B) chat with LiteLLM + OpenRouter.
"""
import os, sys, json, subprocess, hashlib, traceback, shutil
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
STATE_FILE = ROOT / ".evo_state.json"

class C:
    R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; GREEN="\033[32m"
    YELLOW="\033[33m"; BLUE="\033[34m"; MAGENTA="\033[35m"; CYAN="\033[36m"; RED="\033[31m"

def cpr(c, m): print(f"{c}{m}{C.R}")

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f: return json.load(f)
    return {}

def save_state(s):
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f: json.dump(s, f, indent=2)

def log_ev(event, data=None):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    e = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, "data": data or {}}
    with open(LOGS_DIR / "core.log", "a") as f: f.write(json.dumps(e) + "\n")


class LLMClient:
    def __init__(self, api_key, model):
        self.api_key = api_key; self.model = model
        os.environ["OPENROUTER_API_KEY"] = api_key

    def chat(self, messages, temperature=0.7, max_tokens=4096):
        try:
            r = litellm.completion(model=self.model, messages=messages,
                                   temperature=temperature, max_tokens=max_tokens,
                                   api_key=self.api_key)
            return r.choices[0].message.content
        except Exception as e:
            log_ev("llm_error", {"error": str(e)}); return f"[LLM ERROR] {e}"

    def gen_code(self, prompt, ctx=""):
        s = ("You are an expert Python developer. Return ONLY Python code, "
             "no markdown fences. Include imports, error handling, docstrings.")
        if ctx: s += f"\nContext:\n{ctx}"
        return self.chat([{"role":"system","content":s},{"role":"user","content":prompt}], 0.3)

    def gen_pipeline(self, prompt, skills):
        s = ('Return ONLY JSON: {"name":"...","steps":[{"skill":"...","version":"v1",'
             '"input":{},"output_key":"step_1"}]}\nSkills: ' + json.dumps(skills))
        return self.chat([{"role":"system","content":s},{"role":"user","content":prompt}], 0.2)


def _clean(code):
    if code.startswith("```"):
        lines = code.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        code = "\n".join(lines[1:end])
    return code


class SkillManager:
    def __init__(self, llm): self.llm = llm; SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def list_skills(self):
        sk = {}
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                vs = sorted([v.name for v in d.iterdir() if v.is_dir() and v.name.startswith("v")])
                if vs: sk[d.name] = vs
        return sk

    def latest_v(self, name):
        d = SKILLS_DIR / name
        if not d.exists(): return None
        vs = sorted([v.name for v in d.iterdir() if v.is_dir() and v.name.startswith("v")])
        return vs[-1] if vs else None

    def create_skill(self, name, desc):
        ev = self.latest_v(name)
        nv = f"v{int(ev[1:])+1}" if ev else "v1"
        sd = SKILLS_DIR / name / nv; sd.mkdir(parents=True, exist_ok=True)
        prompt = (f"Create Python skill '{name}'. {desc}\n"
                  f"Needs: class with execute(dict)->dict, get_info()->dict, health_check()->bool, "
                  f"__main__ test block. Version: {nv}")
        code = _clean(self.llm.gen_code(prompt))
        (sd/"skill.py").write_text(code)
        (sd/"Dockerfile").write_text("FROM python:3.12-slim\nWORKDIR /app\nCOPY skill.py .\n"
                                     'CMD ["python","skill.py"]\n')
        meta = {"name":name,"version":nv,"description":desc,
                "created_at":datetime.now(timezone.utc).isoformat(),
                "checksum":hashlib.md5(code.encode()).hexdigest()}
        (sd/"meta.json").write_text(json.dumps(meta, indent=2))
        log_ev("skill_created", meta)
        return True, f"Skill '{name}' {nv} created"

    def exec_skill(self, name, version=None, inp=None):
        if not version: version = self.latest_v(name)
        if not version: return {"success":False,"error":f"'{name}' not found"}
        mp = SKILLS_DIR/name/version/"meta.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            if m.get("rolled_back"):
                vs = sorted([v.name for v in (SKILLS_DIR/name).iterdir()
                             if v.is_dir() and v.name.startswith("v") and v.name != version])
                if vs: version = vs[-1]
        p = SKILLS_DIR/name/version/"skill.py"
        if not p.exists(): return {"success":False,"error":f"Not found: {p}"}
        try:
            spec = importlib.util.spec_from_file_location(f"sk_{name}", str(p))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            info = mod.get_info() if hasattr(mod,"get_info") else {"name":name}
            for a in dir(mod):
                o = getattr(mod, a)
                if isinstance(o, type) and hasattr(o, "execute"):
                    return {"success":True,"result":o().execute(inp or {}),"info":info}
            if hasattr(mod,"execute"):
                return {"success":True,"result":mod.execute(inp or {}),"info":info}
            return {"success":True,"result":info}
        except Exception as e:
            return {"success":False,"error":str(e),"tb":traceback.format_exc()}

    def evolve(self, name, feedback):
        cv = self.latest_v(name)
        if not cv: return False, "Not found"
        old = (SKILLS_DIR/name/cv/"skill.py").read_text()
        prompt = f"Improve this skill:\n```python\n{old}\n```\nFeedback: {feedback}"
        code = _clean(self.llm.gen_code(prompt))
        nv = f"v{int(cv[1:])+1}"; nd = SKILLS_DIR/name/nv
        nd.mkdir(parents=True, exist_ok=True)
        (nd/"skill.py").write_text(code)
        odf = SKILLS_DIR/name/cv/"Dockerfile"
        if odf.exists(): shutil.copy2(str(odf), str(nd/"Dockerfile"))
        meta = {"name":name,"version":nv,"parent":cv,
                "created_at":datetime.now(timezone.utc).isoformat()}
        (nd/"meta.json").write_text(json.dumps(meta, indent=2))
        log_ev("skill_evolved", meta)
        return True, f"'{name}' evolved: {cv} -> {nv}"

    def rollback(self, name):
        d = SKILLS_DIR/name
        if not d.exists(): return False, "Not found"
        vs = sorted([v.name for v in d.iterdir() if v.is_dir() and v.name.startswith("v")])
        if len(vs) < 2: return False, "No previous version"
        mp = d/vs[-1]/"meta.json"
        if mp.exists():
            m = json.loads(mp.read_text()); m["rolled_back"] = True
            mp.write_text(json.dumps(m, indent=2))
        log_ev("rollback", {"name":name,"from":vs[-1],"to":vs[-2]})
        return True, f"Rolled back: {vs[-1]} -> {vs[-2]}"


class PipelineManager:
    def __init__(self, sm, llm):
        self.sm=sm; self.llm=llm; PIPELINES_DIR.mkdir(parents=True, exist_ok=True)

    def list_p(self): return [f.stem for f in PIPELINES_DIR.glob("*.json")]

    def create_p(self, name, desc):
        raw = _clean(self.llm.gen_pipeline(desc, list(self.sm.list_skills().keys())))
        try: pd = json.loads(raw)
        except: return False, f"Invalid JSON: {raw[:200]}"
        pd["created_at"] = datetime.now(timezone.utc).isoformat()
        (PIPELINES_DIR/f"{name}.json").write_text(json.dumps(pd, indent=2))
        return True, f"Pipeline '{name}' created"

    def run_p(self, name, ini=None):
        pf = PIPELINES_DIR/f"{name}.json"
        if not pf.exists(): return {"success":False,"error":"Not found"}
        pipe = json.loads(pf.read_text()); res = {}; cur = ini or {}
        for i, st in enumerate(pipe.get("steps",[])):
            si = st.get("input",{}); si.update(cur)
            cpr(C.DIM, f"  Step {i+1}: {st.get('skill')}")
            r = self.sm.exec_skill(st.get("skill"), st.get("version"), si)
            res[st.get("output_key",f"step_{i+1}")] = r
            if not r.get("success"): return {"success":False,"failed":i+1,"results":res}
            if isinstance(r.get("result"), dict): cur.update(r["result"])
        return {"success":True, "results":res}


def gen_compose(skills, state):
    svc = {}
    for side in ["a","b"]:
        svc[f"core-{side}"] = {
            "build":{"context":".","dockerfile":"Dockerfile.core"},
            "container_name":f"evo-core-{side}",
            "environment":{"CORE_ID":side.upper(),
                          "CORE_VERSION":str(state.get(f"core_{side}_version",1)),
                          "OPENROUTER_API_KEY":"${OPENROUTER_API_KEY}",
                          "MODEL":state.get("model","")},
            "volumes":["./cores:/app/cores:ro","./skills:/app/skills",
                       "./logs:/app/logs","./pipelines:/app/pipelines"],
            "restart":"unless-stopped"}
    for sn, vs in skills.items():
        svc[f"skill-{sn}"] = {
            "build":{"context":f"./skills/{sn}/{vs[-1]}"},
            "container_name":f"evo-skill-{sn}",
            "restart":"unless-stopped"}
    out = ROOT/"docker-compose.yml"
    out.write_text(json.dumps({"version":"3.8","services":svc}, indent=2))
    return str(out)


class Supervisor:
    def __init__(self, st): self.st = st
    def active(self): return self.st.get("active_core","A")
    def switch(self):
        c = self.active(); n = "B" if c=="A" else "A"
        self.st["active_core"]=n; self.st["last_healthy_core"]=c
        save_state(self.st); log_ev("core_switch",{"from":c,"to":n}); return n
    def health(self, cid):
        v = self.st.get(f"core_{cid.lower()}_version",1)
        return (ROOT/"cores"/f"v{v}"/"core.py").exists()
    def recover(self):
        a=self.active(); o="B" if a=="A" else "A"
        if self.health(o): return self.switch()
        self.st.update({"core_a_version":1,"core_b_version":1,"active_core":"A"})
        save_state(self.st); return "A"


MODELS = [
    "openrouter/stepfun/step-3.5-flash:free",
    "openrouter/google/gemma-3-1b-it:free",
    "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    "openrouter/qwen/qwen-2.5-72b-instruct:free",
    "openrouter/deepseek/deepseek-chat-v3-0324:free",
    "openrouter/google/gemini-2.0-flash-exp:free",
]

HELP = """
  /skills            List skills       /create <n>    Create skill
  /run <n> [v]    Run skill          /evolve <n>    Improve skill
  /rollback <n>   Rollback           /pipeline list|create|run <n>
  /compose           Docker compose     /model <n>  Switch model
  /models            Available models   /core          A/B status
  /switch            Switch core        /log           Recent logs
  /state             System state       /help          This help
  /quit              Exit
"""


def main():
    state = load_state(); sv = Supervisor(state)
    cpr(C.CYAN, "\n" + "="*48)
    cpr(C.CYAN, "  evo-engine | Evolutionary AI System")
    cpr(C.CYAN, "  Self-healing dual-core | Skill builder")
    cpr(C.CYAN, "="*48)

    ak = state.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY","")
    if not ak:
        cpr(C.YELLOW, "\nPodaj API token do OpenRouter:")
        cpr(C.DIM, "(https://openrouter.ai/keys)")
        ak = input(f"{C.GREEN}> {C.R}").strip()
        if not ak: cpr(C.RED, "Required."); sys.exit(1)
    state["openrouter_api_key"] = ak
    if not state.get("created_at"):
        state["created_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    mdl = state.get("model","openrouter/stepfun/step-3.5-flash:free")
    cpr(C.DIM, f"Model: {mdl} | Core: {sv.active()}")
    llm = LLMClient(ak, mdl); sm = SkillManager(llm); pm = PipelineManager(sm, llm)
    sk = sm.list_skills()
    if sk: cpr(C.GREEN, f"Skills: {', '.join(sk.keys())}")
    else: cpr(C.YELLOW, "No skills. /create <n> or chat.")
    cpr(C.DIM, "/help for commands\n")

    conv = []
    while True:
        try: ui = input(f"{C.GREEN}you> {C.R}").strip()
        except (EOFError, KeyboardInterrupt): cpr(C.DIM,"\nBye!"); break
        if not ui: continue

        if not ui.startswith("/"):
            conv.append({"role":"user","content":ui})
            sp = (f"You are evo-engine AI core. Skills:{json.dumps(sm.list_skills())} "
                  f"Pipelines:{pm.list_p()} Core:{sv.active()}. "
                  "Help build skills/pipelines. If Polish, respond in Polish. Be concise.")
            cpr(C.DIM, "Thinking...")
            r = llm.chat([{"role":"system","content":sp}]+conv[-20:])
            conv.append({"role":"assistant","content":r})
            cpr(C.MAGENTA, f"evo> {r}\n"); continue

        p = ui.split(maxsplit=2); act=p[0].lower()
        a1=p[1] if len(p)>1 else ""; a2=p[2] if len(p)>2 else ""

        if act=="/help": print(HELP)
        elif act in ("/quit","/exit"): break
        elif act=="/skills":
            for n,vs in sm.list_skills().items(): cpr(C.CYAN,f"  {n}: {', '.join(vs)}")
        elif act=="/create":
            if not a1: cpr(C.YELLOW,"Usage: /create <n>"); continue
            cpr(C.CYAN,f"Describe '{a1}':"); d=input(f"{C.GREEN}> {C.R}").strip()
            if d: cpr(C.DIM,"Generating..."); ok,m=sm.create_skill(a1,d); cpr(C.GREEN if ok else C.RED,m)
        elif act=="/run":
            if not a1: cpr(C.YELLOW,"Usage: /run <n>"); continue
            print(json.dumps(sm.exec_skill(a1, a2 or None), indent=2, default=str))
        elif act=="/evolve":
            if not a1: cpr(C.YELLOW,"Usage: /evolve <n>"); continue
            cpr(C.CYAN,"Feedback:"); fb=input(f"{C.GREEN}> {C.R}").strip()
            if fb: ok,m=sm.evolve(a1,fb); cpr(C.GREEN if ok else C.RED,m)
        elif act=="/rollback":
            if a1: ok,m=sm.rollback(a1); cpr(C.GREEN if ok else C.RED,m)
        elif act=="/pipeline":
            if a1=="list":
                for p2 in pm.list_p(): cpr(C.CYAN,f"  {p2}")
            elif a1=="create":
                n=input(f"{C.CYAN}Name: {C.R}").strip()
                d=input(f"{C.CYAN}Describe: {C.R}").strip()
                if n and d: ok,m=pm.create_p(n,d); cpr(C.GREEN if ok else C.RED,m)
            elif a1=="run" and a2:
                print(json.dumps(pm.run_p(a2), indent=2, default=str))
        elif act=="/compose":
            cpr(C.GREEN, f"Generated: {gen_compose(sm.list_skills(), state)}")
        elif act=="/model":
            if not a1: cpr(C.DIM,f"Current: {state.get('model')}"); continue
            nm = a1 if a1.startswith("openrouter/") else f"openrouter/{a1}"
            state["model"]=nm; save_state(state)
            llm=LLMClient(ak,nm); sm.llm=llm; pm.llm=llm
            cpr(C.GREEN,f"Model -> {nm}")
        elif act=="/models":
            for m2 in MODELS:
                t=" <-" if m2==state.get("model") else ""
                cpr(C.DIM,f"  {m2}{t}")
        elif act=="/core":
            a=sv.active()
            cpr(C.CYAN,f"  A: v{state.get('core_a_version',1)} {'<-ACTIVE' if a=='A' else ''}")
            cpr(C.CYAN,f"  B: v{state.get('core_b_version',1)} {'<-ACTIVE' if a=='B' else ''}")
        elif act=="/switch": cpr(C.GREEN,f"Switched to {sv.switch()}")
        elif act=="/log":
            lf=LOGS_DIR/"core.log"
            if lf.exists():
                for ln in lf.read_text().strip().split("\n")[-15:]: cpr(C.DIM,f"  {ln}")
        elif act=="/state": print(json.dumps(state, indent=2))
        else: cpr(C.YELLOW,f"Unknown: {act}. /help")

if __name__ == "__main__":
    main()
