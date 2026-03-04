#!/usr/bin/env python3
import json
import time
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import urllib.request
import urllib.error


@dataclass
class ModelScore:
    model_id: str
    provider: str
    overall_score: float
    quality_score: float
    speed_score: float
    reliability_score: float
    cost_score: float
    context_length: int
    recommended_for: List[str]
    tier: str


class GoalType(Enum):
    CODING = "coding"
    CHAT = "chat"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CREATIVE = "creative"
    GENERAL = "general"


class BenchmarkSkill:
    """Analyzes and benchmarks LLM models for goal-based recommendations."""
    
    def __init__(self):
        self.last_results: List[ModelScore] = []
        self.benchmark_history: List[Dict] = []
        self._config = self._load_config()
        self.PROVIDER_QUALITY = self._config.get("provider_scores", {})
        self.SPEED_TIERS = self._config.get("speed_tiers", {})
    
    def _load_config(self) -> Dict:
        """Load model configuration from config/models.json"""
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "config" / "models.json",
            Path.cwd() / "config" / "models.json",
            Path("/home/tom/github/wronai/coreskill/evo-engine/config/models.json"),
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        return json.load(f)
                except Exception:
                    continue
        
        return {
            "tiers": {
                "free": {"models": []},
                "local": {"models": []},
                "paid": {"models": []}
            },
            "provider_scores": {
                "anthropic": 0.98, "openai": 0.95, "google": 0.92,
                "xiaomi": 0.90, "qwen": 0.88, "meta-llama": 0.88,
                "nvidia": 0.90, "mistralai": 0.85, "deepseek": 0.82,
                "microsoft": 0.78, "perplexity": 0.75
            },
            "speed_tiers": {
                "3b": 0.95, "4b": 0.93, "7b": 0.88, "8b": 0.86,
                "14b": 0.78, "27b": 0.70, "32b": 0.65, "70b": 0.55, "120b": 0.40
            },
            "default": "openrouter/meta-llama/llama-3.3-70b-instruct:free"
        }
    
    def _get_models_from_tier(self, tier: str, enabled_only: bool = True) -> List[str]:
        """Get model IDs from a specific tier."""
        tier_data = self._config.get("tiers", {}).get(tier, {})
        models = tier_data.get("models", [])
        
        if enabled_only:
            models = [m for m in models if m.get("enabled", True)]
        
        return [m["id"] for m in models]
    
    GOAL_PROFILES = {
        GoalType.CODING: {
            "quality_weight": 0.50,
            "speed_weight": 0.25,
            "context_weight": 0.15,
            "cost_weight": 0.10,
            "preferred_providers": ["anthropic", "openai", "meta-llama", "qwen", "deepseek"],
            "min_context": 8000,
        },
        GoalType.CHAT: {
            "quality_weight": 0.40,
            "speed_weight": 0.35,
            "context_weight": 0.15,
            "cost_weight": 0.10,
            "preferred_providers": ["anthropic", "openai", "meta-llama", "mistralai"],
            "min_context": 4000,
        },
        GoalType.REASONING: {
            "quality_weight": 0.55,
            "speed_weight": 0.15,
            "context_weight": 0.20,
            "cost_weight": 0.10,
            "preferred_providers": ["anthropic", "openai", "google", "meta-llama"],
            "min_context": 16000,
        },
        GoalType.SUMMARIZATION: {
            "quality_weight": 0.35,
            "speed_weight": 0.30,
            "context_weight": 0.25,
            "cost_weight": 0.10,
            "preferred_providers": ["google", "anthropic", "openai", "meta-llama"],
            "min_context": 32000,
        },
        GoalType.CREATIVE: {
            "quality_weight": 0.45,
            "speed_weight": 0.25,
            "context_weight": 0.15,
            "cost_weight": 0.15,
            "preferred_providers": ["anthropic", "openai", "meta-llama", "mistralai"],
            "min_context": 4000,
        },
        GoalType.GENERAL: {
            "quality_weight": 0.35,
            "speed_weight": 0.30,
            "context_weight": 0.20,
            "cost_weight": 0.15,
            "preferred_providers": [],
            "min_context": 4000,
        },
    }
    
    BENCHMARK_PROFILES = {
        "fastest": {
            "quality_weight": 0.20,
            "speed_weight": 0.60,
            "context_weight": 0.10,
            "cost_weight": 0.10,
            "description": "Najszybszy model, nawet kosztem jakości",
        },
        "best_quality": {
            "quality_weight": 0.70,
            "speed_weight": 0.10,
            "context_weight": 0.15,
            "cost_weight": 0.05,
            "description": "Najlepsza jakość, bez względu na koszt i prędkość",
        },
        "ignore_cost": {
            "quality_weight": 0.50,
            "speed_weight": 0.30,
            "context_weight": 0.15,
            "cost_weight": 0.05,
            "description": "Nie zwraca uwagi na koszt (dostępne też płatne)",
        },
        "free_only": {
            "quality_weight": 0.45,
            "speed_weight": 0.30,
            "context_weight": 0.15,
            "cost_weight": 0.10,
            "description": "Tylko darmowe modele",
            "budget": "free",
        },
        "balanced": {
            "quality_weight": 0.35,
            "speed_weight": 0.35,
            "context_weight": 0.15,
            "cost_weight": 0.15,
            "description": "Zbalansowane podejście (domyślne)",
        },
        "large_context": {
            "quality_weight": 0.30,
            "speed_weight": 0.20,
            "context_weight": 0.45,
            "cost_weight": 0.05,
            "description": "Duży kontekst (256k+) priorytet",
            "constraints": ["large_context"],
        },
    }
    
    def _get_api_key(self) -> str:
        """Get API key from env, state file, or params."""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if api_key:
            return api_key
        
        state_paths = [
            Path.cwd() / ".evo_state.json",
            Path.home() / ".evo_state.json",
        ]
        for state_path in state_paths:
            if state_path.exists():
                try:
                    with open(state_path, 'r') as f:
                        state = json.load(f)
                        api_key = state.get("openrouter_api_key", "")
                        if api_key:
                            return api_key
                except Exception:
                    continue
        
        return ""
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point."""
        try:
            text = params.get("text", "")
            if text:
                if any(word in text.lower() for word in ["płatny", "platny", "paid", "płatne", "platne"]):
                    params["budget"] = "any"
                    params["profile"] = "ignore_cost"
                if "kodowania" in text.lower() or "kodowanie" in text.lower() or "coding" in text.lower():
                    params["goal"] = "coding"
                elif "chat" in text.lower() or "czat" in text.lower():
                    params["goal"] = "chat"
                elif "reasoning" in text.lower() or "wnioskowanie" in text.lower():
                    params["goal"] = "reasoning"
                if any(word in text.lower() for word in ["najszybszy", "fastest", "szybki"]):
                    params["profile"] = "fastest"
                elif any(word in text.lower() for word in ["najlepszy", "best", "jakość", "quality"]):
                    params["profile"] = "best_quality"
            
            goal_str = params.get("goal", "general")
            goal = GoalType(goal_str) if goal_str in [g.value for g in GoalType] else GoalType.GENERAL
            
            action = params.get("action", "recommend")
            
            if action == "recommend":
                if not self._get_api_key():
                    return {
                        "success": False,
                        "error": "LIVE benchmark wymaga OPENROUTER_API_KEY. Użyj /apikey aby dodać klucz.",
                    }
                action = "recommend_live"
            
            if action == "recommend_live":
                return self._recommend_models_live(params, goal)
            elif action == "compare":
                return self._compare_models(params)
            elif action == "analyze":
                return self._analyze_current_model(params)
            elif action == "list_goals":
                return self._list_goal_profiles()
            elif action == "list_profiles":
                return self._list_benchmark_profiles()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _recommend_models_live(self, params: Dict, goal: GoalType) -> Dict[str, Any]:
        """Recommend models based on static scoring (no live API calls)."""
        budget = params.get("budget", "free")
        constraints = params.get("constraints", [])
        available_models = params.get("available_models", None)
        limit = params.get("limit", 3)
        profile_name = params.get("profile", "balanced")
        
        benchmark_profile = self.BENCHMARK_PROFILES.get(profile_name, self.BENCHMARK_PROFILES["balanced"])
        if "budget" in benchmark_profile:
            budget = benchmark_profile["budget"]
        
        candidates = self._get_candidate_models(budget, available_models)
        
        base_profile = self.GOAL_PROFILES.get(goal, self.GOAL_PROFILES[GoalType.GENERAL]).copy()
        
        if benchmark_profile:
            base_profile["quality_weight"] = benchmark_profile.get("quality_weight", base_profile["quality_weight"])
            base_profile["speed_weight"] = benchmark_profile.get("speed_weight", base_profile["speed_weight"])
            base_profile["context_weight"] = benchmark_profile.get("context_weight", base_profile.get("context_weight", 0.15))
            base_profile["cost_weight"] = benchmark_profile.get("cost_weight", base_profile["cost_weight"])
        
        scored_models = []
        for model_id in candidates:
            score = self._calculate_model_score(model_id, goal, base_profile, constraints)
            scored_models.append(score)
        
        scored_models.sort(key=lambda x: x.overall_score, reverse=True)
        filtered = self._apply_constraints(scored_models, constraints, base_profile)
        
        self.last_results = filtered
        
        recommendations = []
        for i, m in enumerate(filtered[:limit], 1):
            rec = {
                "rank": i,
                "model_id": m.model_id,
                "provider": m.provider,
                "overall_score": round(m.overall_score, 2),
                "breakdown": {
                    "quality": round(m.quality_score, 2),
                    "speed": round(m.speed_score, 2),
                    "reliability": round(m.reliability_score, 2),
                    "cost": round(m.cost_score, 2),
                },
                "context_length": m.context_length,
                "tier": m.tier,
                "why": self._explain_recommendation(m, goal, constraints),
            }
            recommendations.append(rec)
        
        profile_desc = benchmark_profile["description"] if benchmark_profile else "custom"
        
        return {
            "success": True,
            "goal": goal.value,
            "budget": budget,
            "profile": profile_name,
            "profile_description": profile_desc,
            "constraints": constraints,
            "recommendations": recommendations,
            "summary": self._generate_summary(recommendations, goal),
        }
    
    def _get_candidate_models(self, budget: str, available_models: Optional[List[str]]) -> List[str]:
        """Get list of models to evaluate from JSON config."""
        if available_models:
            return available_models
        
        free_models = self._get_models_from_tier("free", enabled_only=True)
        paid_models = self._get_models_from_tier("paid", enabled_only=True)
        
        if budget == "free":
            return free_models
        elif budget == "cheap":
            return free_models + paid_models
        else:
            return free_models + paid_models
    
    def _calculate_model_score(self, model_id: str, goal: GoalType, profile: Dict, constraints: List[str]) -> ModelScore:
        """Calculate comprehensive score for a model."""
        provider = model_id.split("/")[0] if "/" in model_id else "unknown"
        if provider == "openrouter" and "/" in model_id:
            provider = model_id.split("/")[1] if "/" in model_id else "unknown"
        
        base_quality = self.PROVIDER_QUALITY.get(provider, 0.70)
        
        size_bonus = 0.0
        if "70b" in model_id or "120b" in model_id:
            size_bonus = 0.08
        elif "27b" in model_id or "32b" in model_id:
            size_bonus = 0.05
        elif "14b" in model_id:
            size_bonus = 0.02
        
        if goal == GoalType.CODING:
            if any(x in model_id.lower() for x in ["coder", "code"]):
                size_bonus += 0.05
            if "instruct" in model_id.lower():
                size_bonus += 0.03
        
        quality_score = min(1.0, base_quality + size_bonus)
        
        speed_score = 0.70
        for size, speed in self.SPEED_TIERS.items():
            if size in model_id.lower():
                speed_score = speed
                break
        
        reliability_score = 0.85
        if ":free" in model_id:
            reliability_score = 0.75
        elif provider in ["anthropic", "openai", "google"]:
            reliability_score = 0.95
        
        if ":free" in model_id:
            cost_score = 1.0
        elif "haiku" in model_id or "flash" in model_id or "mini" in model_id:
            cost_score = 0.85
        else:
            cost_score = 0.50
        
        context_length = self._estimate_context_length(model_id)
        
        overall = (
            quality_score * profile["quality_weight"] +
            speed_score * profile["speed_weight"] +
            cost_score * profile["cost_weight"]
        )
        
        if "fast" in constraints and speed_score > 0.85:
            overall += 0.05
        if "reliable" in constraints and reliability_score > 0.90:
            overall += 0.05
        
        tier = "paid"
        if ":free" in model_id:
            tier = "free"
        elif model_id.startswith("ollama/"):
            tier = "local"
        
        recommended_for = self._determine_use_cases(model_id, quality_score, speed_score)
        
        return ModelScore(
            model_id=model_id,
            provider=provider,
            overall_score=overall,
            quality_score=quality_score,
            speed_score=speed_score,
            reliability_score=reliability_score,
            cost_score=cost_score,