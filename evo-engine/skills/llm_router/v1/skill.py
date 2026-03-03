import subprocess
import json
import urllib.request
import shutil
import time


class LLMRouterSkill:
    """
    Model discovery & health checking skill (evolvable).
    - Detects local ollama models
    - Discovers free OpenRouter models
    - Tests model health (ping with minimal request)
    - Returns ranked model lists per tier
    """

    def execute(self, params: dict) -> dict:
        action = params.get("action", "status")
        if action == "discover_local":
            return self._discover_local()
        elif action == "discover_remote":
            return self._discover_remote()
        elif action == "health_check":
            model = params.get("model", "")
            api_key = params.get("api_key", "")
            return self._health_check(model, api_key)
        elif action == "status":
            return self._full_status(params.get("api_key", ""))
        return {"success": False, "error": f"Unknown action: {action}"}

    def _discover_local(self) -> dict:
        """Detect available ollama models."""
        if not shutil.which("ollama"):
            return {"success": True, "models": [], "ollama_installed": False}
        try:
            r = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return {"success": False, "error": r.stderr[:200]}
            models = []
            for line in r.stdout.strip().split("\n")[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                name = parts[0]
                size = parts[2] + " " + parts[3] if len(parts) >= 4 else "?"
                models.append({"name": name, "id": f"ollama/{name}", "size": size})
            return {"success": True, "models": models, "ollama_installed": True,
                    "count": len(models)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _discover_remote(self) -> dict:
        """Fetch free models from OpenRouter API."""
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            free = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                pricing = m.get("pricing", {})
                prompt_price = float(pricing.get("prompt", "1") or "1")
                if prompt_price == 0:
                    free.append({
                        "id": f"openrouter/{mid}",
                        "name": mid.split("/")[-1],
                        "context": m.get("context_length", 0),
                    })
            free.sort(key=lambda x: x.get("context", 0), reverse=True)
            return {"success": True, "models": free, "count": len(free)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _health_check(self, model: str, api_key: str = "") -> dict:
        """Ping a model with minimal request to check if it's alive."""
        try:
            import litellm
            kw = dict(
                model=model,
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=3, timeout=15
            )
            if not model.startswith("ollama/") and api_key:
                kw["api_key"] = api_key
            t0 = time.time()
            r = litellm.completion(**kw)
            dt = time.time() - t0
            return {"success": True, "model": model, "latency_s": round(dt, 2),
                    "response": r.choices[0].message.content.strip()[:20]}
        except Exception as e:
            return {"success": False, "model": model, "error": str(e)[:200]}

    def _full_status(self, api_key: str = "") -> dict:
        """Full status: local + remote discovery."""
        local = self._discover_local()
        return {
            "success": True,
            "local": local,
            "ollama_installed": local.get("ollama_installed", False),
            "local_count": local.get("count", 0),
        }


def get_info():
    return {
        "name": "llm_router",
        "version": "v1",
        "description": "Model discovery & health: detect ollama, discover OpenRouter free models, test model health"
    }


def health_check():
    return shutil.which("ollama") is not None
