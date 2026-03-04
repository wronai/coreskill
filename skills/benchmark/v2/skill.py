#!/usr/bin/env python3
"""
Benchmark skill — analyzes LLM models and recommends the best for specific goals.
Usage: execute({"goal": "coding", "budget": "free", "constraints": ["fast", "polish"]})
"""
import json
import time
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


# Mock live_benchmark module if it's not available
try:
    import live_benchmark
except ImportError:
    class MockLiveBenchmark:
        def run_live_benchmark(self, params: Dict, get_candidates_func) -> Dict[str, Any]:
            print("[Benchmark] Warning: live_benchmark module not found. Skipping live benchmark.")
            return {"success": False, "error": "live_benchmark module not available"}
    live_benchmark = MockLiveBenchmark()


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
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point.
        
        params:
            - goal: "coding" | "chat" | "reasoning" | "summarization" | "translation" | "creative" | "general"
            - budget: "free" | "cheap" | "any" (default: free)
            - constraints: list of "fast", "reliable", "large_context", "polish", "english"
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
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _recommend_models(self, params: Dict, goal: GoalType) -> Dict[str, Any]:
        """Recommend best models for a specific goal."""
        budget = params.get("budget", "free")
        constraints = params.get("constraints", [])
        available_models = params.get("available_models", None)
        limit = params.get("limit", 3)
        
        # Get profile for this goal
        profile = self.GOAL_PROFILES.get(goal, self.GOAL_PROFILES[GoalType.GENERAL])
        
        # Define candidate models based on budget
        candidates = self._get_candidate_models(budget, available_models)
        
        # Score each candidate
        scored_models = []
        for model_id in candidates:
            score = self._calculate_model_score(
                model_id, goal, profile, constraints
            )
            scored_models.append(score)
        
        # Sort by overall score
        scored_models.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Filter by constraints
        filtered = self._apply_constraints(scored_models, constraints, profile)
        
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
            "constraints": constraints,
            "top_model": recommendations[0]["model_id"] if recommendations else None,
            "all_scores": [asdict(m) for m in filtered[:10]],
        }
        self.benchmark_history.append(benchmark_record)
        
        return {
            "success": True,
            "goal": goal.value,
            "budget": budget,
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
            reliability_score