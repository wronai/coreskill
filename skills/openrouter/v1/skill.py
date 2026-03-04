#!/usr/bin/env python3
"""
OpenRouter API skill — discovers free LLM models for evo-engine.
Usage: execute({"action": "discover_free", "purpose": "coding", "limit": 10})
"""
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional


class OpenRouterSkill:
    """OpenRouter API client for discovering and ranking free LLM models."""
    
    API_URL = "https://openrouter.ai/api/v1/models"
    
    # Provider quality ranking for coding (higher = better for code)
    PROVIDER_RANK = {
        "nvidia": 100,
        "anthropic": 95,
        "openai": 90,
        "google": 85,
        "meta-llama": 80,
        "qwen": 75,
        "mistralai": 70,
        "deepseek": 65,
        "microsoft": 60,
        "perplexity": 50,
    }
    
    # Model families good for coding
    CODING_FAMILIES = [
        "coder", "code", "deepseek-coder", "qwen-coder",
        "claude", "gpt", "llama", "mistral"
    ]
    
    def __init__(self):
        self.last_models: List[Dict] = []
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point.
        
        params:
            - action: "discover_free" | "search" | "get_info"
            - purpose: "coding" | "chat" | "general" (default: general)
            - limit: max results (default: 10)
            - provider: filter by provider (optional)
            - query: search query for "search" action
        """
        action = params.get("action", "discover_free")
        
        try:
            if action == "discover_free":
                return self._discover_free(params)
            elif action == "search":
                return self._search_models(params)
            elif action == "get_info":
                return self._get_model_info(params)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fetch_models(self) -> List[Dict]:
        """Fetch all models from OpenRouter API."""
        req = urllib.request.Request(
            self.API_URL,
            headers={"Accept": "application/json"},
            method="GET"
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        
        return data.get("data", [])
    
    def _score_model(self, model: Dict, purpose: str = "general") -> int:
        """Score a model based on purpose. Higher = better."""
        model_id = model.get("id", "").lower()
        
        score = 0
        
        # Provider bonus
        for provider, rank in self.PROVIDER_RANK.items():
            if provider in model_id:
                score += rank
                break
        
        # Free models get bonus (they're rate-limited but free)
        if ":free" in model_id:
            score += 50
        
        # Coding purpose scoring
        if purpose == "coding":
            for family in self.CODING_FAMILIES:
                if family in model_id:
                    score += 30
                    break
            # Prefer instruct/finetuned for coding
            if "instruct" in model_id or "-it-" in model_id:
                score += 20
        
        # Size bonus (larger models tend to be better)
        context = model.get("context_length", 0)
        if context >= 128000:
            score += 25
        elif context >= 32000:
            score += 15
        elif context >= 8000:
            score += 5
        
        return score
    
    def _discover_free(self, params: Dict) -> Dict[str, Any]:
        """Discover free models ranked by quality."""
        purpose = params.get("purpose", "general")
        limit = params.get("limit", 10)
        
        try:
            all_models = self._fetch_models()
        except urllib.error.URLError as e:
            return {"success": False, "error": f"API unreachable: {e}"}
        
        # Filter free models
        free_models = [
            m for m in all_models 
            if ":free" in m.get("id", "")
        ]
        
        if not free_models:
            return {
                "success": True,
                "models": [],
                "message": "No free models available right now. Try paid models."
            }
        
        # Score and sort (use key to avoid comparing dicts)
        scored = [
            (self._score_model(m, purpose), m) 
            for m in free_models
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Format results
        results = []
        for score, model in scored[:limit]:
            model_id = model.get("id", "")
            results.append({
                "id": model_id,
                "name": model.get("name", model_id),
                "provider": model_id.split("/")[0] if "/" in model_id else "unknown",
                "description": model.get("description", ""),
                "context_length": model.get("context_length", 0),
                "pricing": model.get("pricing", {}),
                "score": score,
                "recommended_for": self._get_recommended_use(model_id, purpose),
            })
        
        self.last_models = results
        
        return {
            "success": True,
            "models": results,
            "count": len(results),
            "purpose": purpose,
            "top_recommendation": results[0] if results else None,
        }
    
    def _search_models(self, params: Dict) -> Dict[str, Any]:
        """Search models by query string."""
        query = params.get("query", "").lower()
        limit = params.get("limit", 10)
        free_only = params.get("free_only", True)
        
        if not query:
            return {"success": False, "error": "Query parameter required"}
        
        try:
            all_models = self._fetch_models()
        except urllib.error.URLError as e:
            return {"success": False, "error": f"API unreachable: {e}"}
        
        # Filter by query
        matches = [
            m for m in all_models
            if query in m.get("id", "").lower() 
            or query in m.get("name", "").lower()
            or query in m.get("description", "").lower()
        ]
        
        if free_only:
            matches = [m for m in matches if ":free" in m.get("id", "")]
        
        # Score and sort (use key to avoid comparing dicts)
        scored = [(self._score_model(m), m) for m in matches]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, model in scored[:limit]:
            model_id = model.get("id", "")
            results.append({
                "id": model_id,
                "name": model.get("name", model_id),
                "provider": model_id.split("/")[0] if "/" in model_id else "unknown",
                "description": model.get("description", ""),
                "context_length": model.get("context_length", 0),
                "pricing": model.get("pricing", {}),
                "is_free": ":free" in model_id,
            })
        
        return {
            "success": True,
            "models": results,
            "count": len(results),
            "query": query,
        }
    
    def _get_model_info(self, params: Dict) -> Dict[str, Any]:
        """Get detailed info about a specific model."""
        model_id = params.get("model_id", "")
        
        if not model_id:
            return {"success": False, "error": "model_id parameter required"}
        
        try:
            all_models = self._fetch_models()
        except urllib.error.URLError as e:
            return {"success": False, "error": f"API unreachable: {e}"}
        
        for model in all_models:
            if model.get("id") == model_id:
                return {
                    "success": True,
                    "model": {
                        "id": model.get("id"),
                        "name": model.get("name"),
                        "description": model.get("description"),
                        "context_length": model.get("context_length"),
                        "max_tokens": model.get("max_completion_tokens"),
                        "pricing": model.get("pricing"),
                        "architecture": model.get("architecture", {}),
                        "top_provider": model.get("top_provider", {}),
                        "per_request_limits": model.get("per_request_limits"),
                    }
                }
        
        return {"success": False, "error": f"Model {model_id} not found"}
    
    def _get_recommended_use(self, model_id: str, purpose: str) -> str:
        """Get recommended use case for a model."""
        model_lower = model_id.lower()
        
        if "coder" in model_lower or "code" in model_lower:
            return "programming, code generation"
        elif "claude" in model_lower or "gpt-4" in model_lower:
            return "complex reasoning, analysis"
        elif "llama" in model_lower or "qwen" in model_lower:
            return "general chat, coding"
        elif "mistral" in model_lower:
            return "fast responses, general tasks"
        elif "gemma" in model_lower:
            return "lightweight tasks, quick answers"
        else:
            return "general purpose"


# Module-level execute for direct import
def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute OpenRouter skill with given parameters."""
    skill = OpenRouterSkill()
    return skill.execute(params)
