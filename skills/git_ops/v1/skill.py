"""
git_ops skill - Local git operations for skill versioning.
Bootstrap skill for evo-engine. No external dependencies.
"""
import subprocess
import os
import json
from pathlib import Path
import nfo


@nfo.logged
class GitOpsSkill:
    """Manage local git repos for skill development and versioning."""

    def __init__(self, work_dir=None):
        self.work_dir = work_dir or os.getcwd()

    def _run(self, cmd, cwd=None):
        """Run git command, return (success, stdout, stderr)."""
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                cwd=cwd or self.work_dir)
            return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
        except Exception as e:
            return False, "", str(e)

    def init(self, path=None):
        """Initialize git repo."""
        p = path or self.work_dir
        ok, out, err = self._run(["git", "init"], cwd=p)
        if ok:
            # Set default config if needed
            self._run(["git", "config", "user.email", "evo@engine.local"], cwd=p)
            self._run(["git", "config", "user.name", "evo-engine"], cwd=p)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def status(self, path=None):
        """Get git status."""
        ok, out, err = self._run(["git", "status", "--short"], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def add(self, files=".", path=None):
        """Stage files."""
        ok, out, err = self._run(["git", "add", files], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def commit(self, message, path=None):
        """Commit staged changes."""
        ok, out, err = self._run(["git", "commit", "-m", message], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def log(self, n=10, path=None):
        """Get recent commits."""
        ok, out, err = self._run(
            ["git", "log", f"-{n}", "--oneline", "--no-decorate"], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def diff(self, path=None):
        """Get current diff."""
        ok, out, err = self._run(["git", "diff", "--stat"], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def tag(self, tag_name, message="", path=None):
        """Create a tag."""
        cmd = ["git", "tag", "-a", tag_name, "-m", message or tag_name]
        ok, out, err = self._run(cmd, cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def checkout(self, ref, path=None):
        """Checkout branch or commit."""
        ok, out, err = self._run(["git", "checkout", ref], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def revert_file(self, file_path, path=None):
        """Revert a single file to last committed state."""
        ok, out, err = self._run(["git", "checkout", "--", file_path], cwd=path)
        return {"success": ok, "output": out, "error": err if not ok else None}

    def commit_skill_version(self, skill_name, version, skill_dir):
        """Commit a new skill version with proper tagging."""
        self.add(".", path=skill_dir)
        msg = f"skill/{skill_name}/{version}: auto-evolved"
        result = self.commit(msg, path=skill_dir)
        if result["success"]:
            self.tag(f"{skill_name}-{version}", msg, path=skill_dir)
        return result

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "status")
        path = input_data.get("path", self.work_dir)
        dispatch = {
            "init": lambda: self.init(path),
            "status": lambda: self.status(path),
            "add": lambda: self.add(input_data.get("files", "."), path),
            "commit": lambda: self.commit(input_data.get("message", "auto"), path),
            "log": lambda: self.log(input_data.get("n", 10), path),
            "diff": lambda: self.diff(path),
            "tag": lambda: self.tag(input_data.get("tag", "v1"), input_data.get("message", ""), path),
            "checkout": lambda: self.checkout(input_data.get("ref", "main"), path),
            "revert_file": lambda: self.revert_file(input_data.get("file", ""), path),
            "commit_skill": lambda: self.commit_skill_version(
                input_data.get("skill_name", ""),
                input_data.get("version", "v1"),
                path),
        }
        fn = dispatch.get(action)
        if not fn:
            return {"success": False, "error": f"Unknown action: {action}"}
        return fn()


def get_info():
    return {
        "name": "git_ops",
        "version": "v1",
        "description": "Local git operations for skill versioning and development",
        "actions": ["init", "status", "add", "commit", "log", "diff", "tag",
                     "checkout", "revert_file", "commit_skill"],
        "author": "evo-engine"
    }


def health_check():
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False


if __name__ == "__main__":
    g = GitOpsSkill()
    print(f"Health: {health_check()}")
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Status: {g.status()}")
