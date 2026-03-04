"""
Live Benchmark Extension for Benchmark Skill
Provides real-time model testing capabilities
"""
import json
import time
import os
from typing import Dict, List, Any

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


def run_live_benchmark(params: Dict, get_candidate_models_func) -> Dict[str, Any]:
    """Run actual live benchmark tests against models."""
    models = params.get("models", [])
    api_key = params.get("api_key", os.environ.get("OPENROUTER_API_KEY", ""))
    test_types = params.get("tests", ["speed", "coding", "json", "polish"])
    max_time_per_model = params.get("timeout_per_model", 30)

    if not models:
        budget = params.get("budget", "free")
        models = get_candidate_models_func(budget, None)[:5]

    results = []
    print(f"[Benchmark] Testing {len(models)} models with {len(test_types)} test types...")

    for model_id in models:
        print(f"[Benchmark] Testing {model_id}...")
        model_result = test_single_model(model_id, api_key, test_types, max_time_per_model)
        results.append(model_result)

    # Sort by combined score
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    best = results[0] if results else None

    return {
        "success": True,
        "tested_models": len(results),
        "test_types": test_types,
        "results": results[:10],
        "best_model": best["model_id"] if best else None,
        "best_score": best["combined_score"] if best else 0,
        "summary": generate_benchmark_summary(results),
    }


def test_single_model(model_id: str, api_key: str, test_types: List[str], timeout: int) -> Dict:
    """Test a single model across multiple dimensions."""
    scores = {}
    latencies = []
    errors = []

    for test_type in test_types:
        test = BENCHMARK_TESTS.get(test_type, BENCHMARK_TESTS["speed"])
        start = time.time()
        try:
            response = call_model_api(model_id, api_key, test["prompt"], timeout)
            latency = time.time() - start
            latencies.append(latency)
            quality_score = score_response(response, test["criteria"], test_type)
            scores[test_type] = {
                "latency_ms": round(latency * 1000, 1),
                "quality": round(quality_score, 2),
                "response_length": len(response),
            }
        except Exception as e:
            latencies.append(timeout)
            errors.append(str(e)[:100])
            scores[test_type] = {
                "latency_ms": timeout * 1000,
                "quality": 0.0,
                "error": str(e)[:100],
            }

    avg_latency = sum(latencies) / len(latencies) if latencies else timeout
    avg_quality = sum(s["quality"] for s in scores.values() if "quality" in s) / max(1, len([s for s in scores.values() if "quality" in s]))
    latency_score = max(0, 1 - (avg_latency / 5.0))
    combined = (avg_quality * 0.7) + (latency_score * 0.3)

    return {
        "model_id": model_id,
        "provider": model_id.split("/")[1] if "/" in model_id else "unknown",
        "combined_score": round(combined, 3),
        "avg_quality": round(avg_quality, 2),
        "avg_latency_ms": round(avg_latency * 1000, 1),
        "latency_score": round(latency_score, 2),
        "test_scores": scores,
        "errors": errors if errors else None,
    }


def call_model_api(model: str, api_key: str, prompt: str, timeout: int) -> str:
    """Make actual LLM call via litellm."""
    try:
        import litellm
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
        is_local = model.startswith("ollama/")
        kw = dict(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
            timeout=timeout,
        )
        if not is_local and api_key:
            kw["api_key"] = api_key
        response = litellm.completion(**kw)
        return response.choices[0].message.content or ""
    except Exception as e:
        raise Exception(f"Model call failed: {str(e)[:80]}")


def score_response(response: str, criteria: List[str], test_type: str) -> float:
    """Score response quality based on test criteria."""
    if not response:
        return 0.0
    score = 0.0
    response_lower = response.lower()

    if test_type == "coding":
        if "def " in response: score += 0.3
        if '"""' in response or "'''" in response: score += 0.2
        if "try:" in response and "except" in response: score += 0.2
        if "[" not in response or "::" not in response: score += 0.15
        if 100 < len(response) < 2000: score += 0.15
    elif test_type == "reasoning":
        steps = ["120", "80", "200", "3.5", "km", "hour", "speed"]
        matches = sum(1 for s in steps if s in response_lower)
        score += (matches / len(steps)) * 0.6
        if "=" in response: score += 0.2
        if "57.1" in response or "57,1" in response: score += 0.2
    elif test_type == "polish":
        polish_words = ["sztuczna", "inteligencja", "ai", "technologia", "system"]
        matches = sum(1 for w in polish_words if w in response_lower)
        score += min(0.4, matches * 0.1)
        sentences = [s.strip() for s in response.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if 2 <= len(sentences) <= 4: score += 0.3
        if len(response) > 50: score += 0.3
    elif test_type == "json":
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            data = json.loads(json_str)
            if all(k in data for k in ["name", "age", "city"]):
                score = 1.0
            elif isinstance(data, dict):
                score = 0.5
        except:
            score = 0.0
    elif test_type == "speed":
        score = 1.0 if len(response) > 0 else 0.0

    return min(1.0, score)


def generate_benchmark_summary(results: List[Dict]) -> str:
    """Generate human-readable benchmark summary."""
    if not results:
        return "No models tested successfully."
    best = results[0]
    lines = [
        f"🏆 Best: {best['model_id'].split('/')[-1]} (score: {best['combined_score']})",
        f"   Quality: {best['avg_quality']}, Latency: {best['avg_latency_ms']}ms",
        "",
        "📊 Top 3 Models:",
    ]
    for i, r in enumerate(results[:3], 1):
        name = r['model_id'].split('/')[-1][:25]
        lines.append(f"   {i}. {name:<25} score={r['combined_score']:.2f} q={r['avg_quality']:.2f} lat={r['avg_latency_ms']:.0f}ms")
    return "\n".join(lines)
