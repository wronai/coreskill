#!/usr/bin/env python3
"""
evo-engine Supervisor — A/B core management, versioning, rollback.
"""
import json
import shutil
from datetime import datetime, timezone

from .config import ROOT, save_state


class Supervisor:
    """Manages core versions: can create coreB/C/D, test, promote, rollback."""
    def __init__(self, st, logger):
        self.st = st
        self.log = logger

    def active(self): return self.st.get("active_core", "A")

    def active_version(self):
        return self.st.get(f"core_{self.active().lower()}_version", 1)

    def list_cores(self):
        """List all available core versions."""
        cores_dir = ROOT / "cores"
        if not cores_dir.exists(): return []
        return sorted([d.name for d in cores_dir.iterdir()
                       if d.is_dir() and d.name.startswith("v") and (d / "core.py").exists()])

    def switch(self):
        c = self.active()
        n = "B" if c == "A" else "A"
        self.st["active_core"] = n
        self.st["last_healthy_core"] = c
        save_state(self.st)
        self.log.core("core_switch", {"from": c, "to": n})
        return n

    def health(self, cid):
        v = self.st.get(f"core_{cid.lower()}_version", 1)
        return (ROOT / "cores" / f"v{v}" / "core.py").exists()

    def create_next_core(self, desc=""):
        """Create new core version by copying current."""
        cur_v = self.active_version()
        new_v = cur_v + 1
        src = ROOT / "cores" / f"v{cur_v}" / "core.py"
        dst_dir = ROOT / "cores" / f"v{new_v}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst_dir / "core.py"))
        meta = {"version": new_v, "parent": cur_v, "description": desc,
                "created_at": datetime.now(timezone.utc).isoformat()}
        (dst_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.core("core_created", meta)
        return new_v, str(dst_dir / "core.py")

    def promote_core(self, version):
        """Switch active core to use new version."""
        cid = self.active()
        self.st[f"core_{cid.lower()}_version"] = version
        save_state(self.st)
        self.log.core("core_promoted", {"core": cid, "version": version})
        return cid, version

    def rollback_core(self):
        """Rollback to previous core version."""
        cur_v = self.active_version()
        if cur_v <= 1: return False, "Already at v1"
        prev_v = cur_v - 1
        cid = self.active()
        self.st[f"core_{cid.lower()}_version"] = prev_v
        save_state(self.st)
        self.log.core("core_rollback", {"from": cur_v, "to": prev_v})
        return True, f"Core {cid}: v{cur_v} -> v{prev_v}"

    def recover(self):
        a = self.active()
        o = "B" if a == "A" else "A"
        if self.health(o): return self.switch()
        self.st.update({"core_a_version": 1, "core_b_version": 1, "active_core": "A"})
        save_state(self.st)
        return "A"
