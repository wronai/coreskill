#!/usr/bin/env python3
"""
Benchmark skill — analyzes LLM models and recommends the best for specific goals.
Usage: execute({"goal": "coding", "budget": "free", "constraints": ["fast", "polish"]})
"""
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import re


# Test prompts for different evaluation scenarios
BENCHMARK_TESTS = {
    "coding": {
        "prompt": "Write a Python function that reverses a string without using slicing or built-in reverse methods. Include docstring and error handling.",
        "criteria": ["function definition", "docstring", "error handling", "no slice notation"]
    },
    "reasoning": {
        "prompt": "If a train travels 120 km in 2 hours, and then 80 km in 1.5 hours, what is the average speed for the entire journey? Show your reasoning step by step.",
        "criteria": ["step by step", "correct formula", "correct answer", "km/h unit"]
    },
    "polish": {
        "prompt": "Napisz krótkie podsumowanie (2-3 zdania) o sztucznej inteligencji w języku polskim.",
        "criteria": ["polish language", "2-3 sentences", "AI topic", "coherent"]
    },
    "json": {
        "prompt": 'Return ONLY a JSON object with keys: "name", "age", "city". No markdown, no explanation.',
        "criteria": ["valid json", "no markdown", "all keys present"]
    },
    "speed": {
        "prompt": "Say 'hello' and nothing else.",
        "criteria": ["response"]
    }
}


class GoalType(Enum):
    CODING = "coding"
    CHAT = "chat"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CREATIVE = "creative"
    GENERAL = "general"


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
    tier: str  # free, local, paid


class BenchmarkSkill:
    """Analyzes and benchmarks LLM models for goal-based recommendations."""
    
    def __init__(self):
        self.last_results: List[ModelScore] = []
        self.benchmark_history: List[Dict] = []
        self._config = self._load_config()
        
        # Load provider quality and speed tiers from config
        self.PROVIDER_QUALITY = self._config.get("provider_scores", {})
        self.SPEED_TIERS = self._config.get("speed_tiers", {})
    
    def _load_config(self) -> Dict:
        """Load model configuration from config/models.json"""
        # Try multiple paths to find config
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
                except Exception as e:
                    print(f"[Benchmark] Error loading config from {config_path}: {e}")
                    continue
        
        # Fallback to embedded defaults
        print("[Benchmark] Warning: Could not load models.json, using defaults")
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
    
    # Provider quality tiers (coding capability) - loaded from config
    PROVIDER_QUALITY = {}  # Loaded in __init__
    
    # Speed tiers (relative to model size) - loaded from config
    SPEED_TIERS = {}  # Loaded in __init__
    
    # Goal-specific model preferences
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
            "preferred_providers": [],  # All acceptable
            "min_context": 4000,
        },
    }

    # Optimization profiles - adjust weights for different priorities
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
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point.
        
        params:
            - goal: "coding" | "chat" | "reasoning" | "summarization" | "translation" | "creative" | "general"
            - budget: "free" | "cheap" | "any" (default: free)
            - constraints: list of "fast", "reliable", "large_context", "polish", "english"
            - profile: "fastest" | "best_quality" | "ignore_cost" | "free_only" | "balanced" | "large_context"
            - available_models: list of model IDs to consider (optional)
            - limit: max recommendations (default: 3)
        """
        try:
            goal_str = params.get("goal", "general")
            goal = GoalType(goal_str) if goal_str in [g.value for g in GoalType] else GoalType.GENERAL
            
            action = params.get("action", "recommend")
            
            if action == "recommend":
                return self._recommend_models(params, goal)
            elif action == "compare":
                return self._compare_models(params)
            elif action == "analyze":
                return self._analyze_current_model(params)
            elif action == "run_benchmark":
                return self._run_live_benchmark(params)
            elif action == "list_goals":
                return self._list_goal_profiles()
            elif action == "list_profiles":
                return self._list_benchmark_profiles()
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _recommend_models(self, params: Dict, goal: GoalType) -> Dict[str, Any]:
        """Recommend best models for a specific goal with optional profile."""
        budget = params.get("budget", "free")
        constraints = params.get("constraints", [])
        available_models = params.get("available_models", None)
        limit = params.get("limit", 3)
        profile_name = params.get("profile", "balanced")
        
        # Get base profile for this goal
        base_profile = self.GOAL_PROFILES.get(goal, self.GOAL_PROFILES[GoalType.GENERAL]).copy()
        
        # Apply BENCHMARK_PROFILE overrides if specified
        benchmark_profile = self.BENCHMARK_PROFILES.get(profile_name)
        if benchmark_profile:
            base_profile["quality_weight"] = benchmark_profile.get("quality_weight", base_profile["quality_weight"])
            base_profile["speed_weight"] = benchmark_profile.get("speed_weight", base_profile["speed_weight"])
            base_profile["context_weight"] = benchmark_profile.get("context_weight", base_profile.get("context_weight", 0.15))
            base_profile["cost_weight"] = benchmark_profile.get("cost_weight", base_profile["cost_weight"])
            # Override budget if profile specifies it
            if "budget" in benchmark_profile:
                budget = benchmark_profile["budget"]
            # Add constraints from profile
            if "constraints" in benchmark_profile:
                constraints = list(set(constraints + benchmark_profile["constraints"]))
        
        # Define candidate models based on budget
        candidates = self._get_candidate_models(budget, available_models)
        
        # Score each candidate
        scored_models = []
        for model_id in candidates:
            score = self._calculate_model_score(
                model_id, goal, base_profile, constraints
            )
            scored_models.append(score)
        
        # Sort by overall score
        scored_models.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Filter by constraints
        filtered = self._apply_constraints(scored_models, constraints, base_profile)
        
        # Store results
        self.last_results = filtered
        
        # Build recommendations
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
        
        # Store benchmark record
        benchmark_record = {
            "timestamp": time.time(),
            "goal": goal.value,
            "budget": budget,
            "profile": profile_name,
            "constraints": constraints,
            "top_model": recommendations[0]["model_id"] if recommendations else None,
            "all_scores": [asdict(m) for m in filtered[:10]],
        }
        self.benchmark_history.append(benchmark_record)
        
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
        
        # Get models from JSON config
        free_models = self._get_models_from_tier("free", enabled_only=True)
        paid_models = self._get_models_from_tier("paid", enabled_only=True)
        
        if budget == "free":
            return free_models
        elif budget == "cheap":
            return free_models + paid_models
        else:  # any
            return free_models + paid_models
    
    def _calculate_model_score(
        self, model_id: str, goal: GoalType, profile: Dict, constraints: List[str]
    ) -> ModelScore:
        """Calculate comprehensive score for a model."""
        provider = model_id.split("/")[0] if "/" in model_id else "unknown"
        if provider == "openrouter" and "/" in model_id:
            provider = model_id.split("/")[1] if "/" in model_id else "unknown"
        
        # Quality score (0-1)
        base_quality = self.PROVIDER_QUALITY.get(provider, 0.70)
        
        # Size-based adjustments
        size_bonus = 0.0
        if "70b" in model_id or "120b" in model_id:
            size_bonus = 0.08
        elif "27b" in model_id or "32b" in model_id:
            size_bonus = 0.05
        elif "14b" in model_id:
            size_bonus = 0.02
        
        # Coding-specific bonuses
        if goal == GoalType.CODING:
            if any(x in model_id.lower() for x in ["coder", "code"]):
                size_bonus += 0.05
            if "instruct" in model_id.lower():
                size_bonus += 0.03
        
        quality_score = min(1.0, base_quality + size_bonus)
        
        # Speed score (0-1) - inverse of size
        speed_score = 0.70  # default
        for size, speed in self.SPEED_TIERS.items():
            if size in model_id.lower():
                speed_score = speed
                break
        
        # Reliability score (0-1)
        reliability_score = 0.85  # default
        if ":free" in model_id:
            reliability_score = 0.75  # free tier less reliable (rate limits)
        elif provider in ["anthropic", "openai", "google"]:
            reliability_score = 0.95
        
        # Cost score (0-1, higher = cheaper/better)
        if ":free" in model_id:
            cost_score = 1.0
        elif "haiku" in model_id or "flash" in model_id or "mini" in model_id:
            cost_score = 0.85
        else:
            cost_score = 0.50
        
        # Context length estimation
        context_length = self._estimate_context_length(model_id)
        
        # Calculate weighted overall score
        overall = (
            quality_score * profile["quality_weight"] +
            speed_score * profile["speed_weight"] +
            reliability_score * 0.10 +  # reliability is always important
            cost_score * profile["cost_weight"]
        )
        
        # Constraint bonuses
        if "fast" in constraints and speed_score > 0.85:
            overall += 0.05
        if "reliable" in constraints and reliability_score > 0.90:
            overall += 0.05
        
        # Determine tier
        tier = "paid"
        if ":free" in model_id:
            tier = "free"
        elif model_id.startswith("ollama/"):
            tier = "local"
        
        # Recommended use cases
        recommended_for = self._determine_use_cases(model_id, quality_score, speed_score)
        
        return ModelScore(
            model_id=model_id,
            provider=provider,
            overall_score=overall,
            quality_score=quality_score,
            speed_score=speed_score,
            reliability_score=reliability_score,
            cost_score=cost_score,
            context_length=context_length,
            recommended_for=recommended_for,
            tier=tier,
        )
    
    def _estimate_context_length(self, model_id: str) -> int:
        """Estimate context length from model name."""
        # Extract known context lengths
        if "70b" in model_id or "llama-3.3" in model_id:
            return 128000
        elif "120b" in model_id:
            return 131072
        elif "27b" in model_id:
            return 131072
        elif "mistral-small" in model_id:
            return 32000
        elif "gemma-3-4b" in model_id:
            return 32768
        elif "gemma-3-12b" in model_id:
            return 131072
        elif "gemma-3-27b" in model_id:
            return 131072
        elif "3b" in model_id or "4b" in model_id:
            return 32768
        return 8192
    
    def _determine_use_cases(self, model_id: str, quality: float, speed: float) -> List[str]:
        """Determine what this model is good for."""
        uses = []
        model_lower = model_id.lower()
        
        if quality > 0.90:
            uses.append("complex reasoning")
        if quality > 0.85 and ("coder" in model_lower or "code" in model_lower):
            uses.append("code generation")
        if speed > 0.85:
            uses.append("fast responses")
        if "instruct" in model_lower:
            uses.append("instruction following")
        if quality > 0.80 and not uses:
            uses.append("general tasks")
        
        return uses
    
    def _apply_constraints(
        self, models: List[ModelScore], constraints: List[str], profile: Dict
    ) -> List[ModelScore]:
        """Filter models based on constraints."""
        result = models
        
        if "fast" in constraints:
            # Prefer speed over raw quality
            result = sorted(result, key=lambda x: x.speed_score * 0.6 + x.quality_score * 0.4, reverse=True)
        
        if "large_context" in constraints:
            min_ctx = profile.get("min_context", 16000) * 2
            result = [m for m in result if m.context_length >= min_ctx]
        
        if "polish" in constraints:
            # Boost models known for Polish
            polish_good = ["meta-llama", "openai", "google"]
            for m in result:
                if any(p in m.provider for p in polish_good):
                    m.overall_score += 0.03
            result.sort(key=lambda x: x.overall_score, reverse=True)
        
        return result
    
    def _explain_recommendation(
        self, score: ModelScore, goal: GoalType, constraints: List[str]
    ) -> str:
        """Generate human-readable explanation."""
        parts = []
        
        if score.quality_score > 0.90:
            parts.append("excellent quality")
        elif score.quality_score > 0.80:
            parts.append("good quality")
        
        if score.speed_score > 0.85:
            parts.append("fast")
        
        if score.tier == "free":
            parts.append("free tier")
        elif score.cost_score > 0.80:
            parts.append("cost-effective")
        
        if score.reliability_score > 0.90:
            parts.append("high reliability")
        
        if "polish" in constraints:
            parts.append("good Polish support")
        
        return ", ".join(parts) if parts else "balanced option"
    
    def _generate_summary(self, recommendations: List[Dict], goal: GoalType) -> str:
        """Generate summary text."""
        if not recommendations:
            return "No suitable models found."
        
        top = recommendations[0]
        return (
            f"Best for {goal.value}: {top['model_id'].split('/')[-1]} "
            f"(score: {top['overall_score']}) — {top['why']}"
        )
    
    def _compare_models(self, params: Dict) -> Dict[str, Any]:
        """Compare specific models side by side."""
        models = params.get("models", [])
        goal_str = params.get("goal", "general")
        goal = GoalType(goal_str) if goal_str in [g.value for g in GoalType] else GoalType.GENERAL
        
        if not models:
            return {"success": False, "error": "No models specified for comparison"}
        
        profile = self.GOAL_PROFILES.get(goal, self.GOAL_PROFILES[GoalType.GENERAL])
        
        results = []
        for model_id in models:
            score = self._calculate_model_score(model_id, goal, profile, [])
            results.append({
                "model_id": model_id,
                "overall": round(score.overall_score, 2),
                "quality": round(score.quality_score, 2),
                "speed": round(score.speed_score, 2),
                "reliability": round(score.reliability_score, 2),
                "cost": round(score.cost_score, 2),
                "context": score.context_length,
            })
        
        results.sort(key=lambda x: x["overall"], reverse=True)
        
        return {
            "success": True,
            "goal": goal.value,
            "comparison": results,
            "winner": results[0]["model_id"] if results else None,
        }
    
    def _analyze_current_model(self, params: Dict) -> Dict[str, Any]:
        """Analyze currently configured model."""
        current_model = params.get("current_model", "")
        goal_str = params.get("goal", "general")
        goal = GoalType(goal_str) if goal_str in [g.value for g in GoalType] else GoalType.GENERAL
        
        if not current_model:
            return {"success": False, "error": "No current_model specified"}
        
        profile = self.GOAL_PROFILES.get(goal, self.GOAL_PROFILES[GoalType.GENERAL])
        score = self._calculate_model_score(current_model, goal, profile, [])
        
        # Check if there are better alternatives
        budget = "free" if ":free" in current_model else ("local" if current_model.startswith("ollama/") else "any")
        candidates = self._get_candidate_models(budget, None)
        all_scores = [self._calculate_model_score(m, goal, profile, []) for m in candidates]
        all_scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        rank = next((i for i, s in enumerate(all_scores, 1) if s.model_id == current_model), "?")
        better = [s.model_id for s in all_scores if s.overall_score > score.overall_score][:3]
        
        return {
            "success": True,
            "current_model": current_model,
            "goal": goal.value,
            "analysis": {
                "overall_score": round(score.overall_score, 2),
                "rank": rank,
                "quality": round(score.quality_score, 2),
                "speed": round(score.speed_score, 2),
                "reliability": round(score.reliability_score, 2),
            },
            "verdict": "good" if score.overall_score > 0.75 else ("ok" if score.overall_score > 0.60 else "poor"),
            "alternatives": better,
            "recommendation": f"Consider switching to {better[0].split('/')[-1]}" if better and rank != 1 else "Current model is optimal",
        }

    def _run_live_benchmark(self, params: Dict) -> Dict[str, Any]:
        """Run actual live benchmark tests - inline implementation."""
        models = params.get("models", [])
        api_key = params.get("api_key", os.environ.get("OPENROUTER_API_KEY", ""))
        test_types = params.get("tests", ["speed", "coding", "json"])
        timeout = params.get("timeout_per_model", 25)

        if not models:
            budget = params.get("budget", "free")
            models = self._get_candidate_models(budget, None)[:5]

        results = []
        for model_id in models:
            scores = {}
            latencies = []
            errors = []
            for test_type in test_types:
                test = BENCHMARK_TESTS.get(test_type, BENCHMARK_TESTS["speed"])
                start = time.time()
                try:
                    response = self._call_model_for_benchmark(model_id, api_key, test["prompt"], timeout)
                    latency = time.time() - start
                    latencies.append(latency)
                    quality = self._score_benchmark_response(response, test["criteria"], test_type)
                    scores[test_type] = {"latency_ms": round(latency * 1000, 1), "quality": round(quality, 2)}
                except Exception as e:
                    latencies.append(timeout)
                    errors.append(str(e)[:50])
                    scores[test_type] = {"latency_ms": timeout * 1000, "quality": 0.0, "error": str(e)[:50]}

            avg_latency = sum(latencies) / len(latencies) if latencies else timeout
            avg_quality = sum(s["quality"] for s in scores.values() if "quality" in s) / max(1, len([s for s in scores.values() if "quality" in s]))
            latency_score = max(0, 1 - (avg_latency / 5.0))
            combined = (avg_quality * 0.7) + (latency_score * 0.3)

            results.append({
                "model_id": model_id,
                "provider": model_id.split("/")[1] if "/" in model_id else "unknown",
                "combined_score": round(combined, 3),
                "avg_quality": round(avg_quality, 2),
                "avg_latency_ms": round(avg_latency * 1000, 1),
                "latency_score": round(latency_score, 2),
                "test_scores": scores,
                "errors": errors if errors else None,
            })

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        best = results[0] if results else None

        summary_lines = [
            f"Best: {best['model_id'].split('/')[-1] if best else 'none'} (score: {best['combined_score'] if best else 0})",
            "Top 3:",
        ]
        for i, r in enumerate(results[:3], 1):
            name = r['model_id'].split('/')[-1][:22]
            summary_lines.append(f"  {i}. {name} s={r['combined_score']:.2f} q={r['avg_quality']:.2f}")

        return {
            "success": True,
            "tested_models": len(results),
            "test_types": test_types,
            "results": results[:10],
            "best_model": best["model_id"] if best else None,
            "best_score": best["combined_score"] if best else 0,
            "summary": "\n".join(summary_lines),
        }

    def _call_model_for_benchmark(self, model: str, api_key: str, prompt: str, timeout: int) -> str:
        """Make LLM call via litellm for benchmarking."""
        try:
            import litellm
            litellm.suppress_debug_info = True
            is_local = model.startswith("ollama/")
            kw = dict(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=500, timeout=timeout)
            if not is_local and api_key:
                kw["api_key"] = api_key
            response = litellm.completion(**kw)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"Model call failed: {str(e)[:80]}")

    def _score_benchmark_response(self, response: str, criteria: List[str], test_type: str) -> float:
        """Score benchmark response quality."""
        if not response:
            return 0.0
        response_lower = response.lower()
        score = 0.0
        if test_type == "coding":
            if "def " in response: score += 0.3
            if '"""' in response or "'''" in response: score += 0.2
            if "try:" in response and "except" in response: score += 0.2
            if 100 < len(response) < 2000: score += 0.15
        elif test_type == "polish":
            polish_words = ["sztuczna", "inteligencja", "ai", "technologia"]
            matches = sum(1 for w in polish_words if w in response_lower)
            score += min(0.5, matches * 0.1)
            if len(response) > 50: score += 0.3
        elif test_type == "json":
            try:
                json_str = response
                if "```json" in response: json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response: json_str = response.split("```")[1].split("```")[0].strip()
                data = json.loads(json_str)
                if all(k in data for k in ["name", "age", "city"]): score = 1.0
            except: pass
        elif test_type == "speed":
            score = 1.0 if len(response) > 0 else 0.0
        return min(1.0, score)
    
    def _list_goal_profiles(self) -> Dict[str, Any]:
        """List available goal profiles."""
        profiles = {}
        for goal, profile in self.GOAL_PROFILES.items():
            profiles[goal.value] = {
                "quality_weight": profile["quality_weight"],
                "speed_weight": profile["speed_weight"],
                "preferred_providers": profile["preferred_providers"][:3],
            }
        
        return {
            "success": True,
            "available_goals": list(GoalType),
            "profiles": profiles,
        }

    def _list_benchmark_profiles(self) -> Dict[str, Any]:
        """List available benchmark optimization profiles."""
        profiles = {}
        for name, profile in self.BENCHMARK_PROFILES.items():
            profiles[name] = {
                "description": profile["description"],
                "weights": {
                    "quality": profile.get("quality_weight", 0.35),
                    "speed": profile.get("speed_weight", 0.35),
                    "context": profile.get("context_weight", 0.15),
                    "cost": profile.get("cost_weight", 0.15),
                },
                "budget": profile.get("budget", "any"),
                "constraints": profile.get("constraints", []),
            }
        
        return {
            "success": True,
            "available_profiles": list(self.BENCHMARK_PROFILES.keys()),
            "profiles": profiles,
        }


# Module-level execute for direct import
def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute benchmark skill with given parameters."""
    skill = BenchmarkSkill()
    return skill.execute(params)


def get_info():
    return {"name": "benchmark", "version": "v1", "description": "benchmark skill"}


def health_check():
    return True

