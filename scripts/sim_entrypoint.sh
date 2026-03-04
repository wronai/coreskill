#!/bin/bash
# evo-engine Simulation Entrypoint
# Runs simulation with configurable iterations and logging

set -e

ITERATIONS=${SIM_ITERATIONS:-3}
SCENARIO=${SIM_SCENARIO:-}
VERBOSE=${SIM_VERBOSE:-1}

echo "=== evo-engine Simulation ==="
echo "Iterations: $ITERATIONS"
echo "Scenario: ${SCENARIO:-all}"
echo "Verbose: $VERBOSE"
echo "Model: ${EVO_MODEL:-auto}"
echo "API Key: ${OPENROUTER_API_KEY:+set}"
echo "=============================="

# Ensure directories
mkdir -p /app/logs/simulation /app/logs/evo /app/logs/nfo /app/logs/skills

# Build command
CMD="python scripts/simulate.py --iterations $ITERATIONS"
if [ -n "$SCENARIO" ]; then
    CMD="$CMD --scenario $SCENARIO"
fi
if [ "$VERBOSE" = "1" ]; then
    CMD="$CMD --verbose"
fi

echo "[ENTRYPOINT] Running: $CMD"
echo ""

# Run simulation
$CMD
EXIT_CODE=$?

echo ""
echo "=== Simulation finished (exit: $EXIT_CODE) ==="

# Show summary if available
if [ -f /app/logs/simulation/final_report.json ]; then
    echo ""
    echo "=== Final Report ==="
    python -c "
import json
r = json.loads(open('/app/logs/simulation/final_report.json').read())
print(f\"Success: {r['successful']}/{r['total_scenarios']} ({r['success_rate']}%)\")
print(f\"Skills created: {r['unique_skills_created']}\")
print(f\"Errors: {r['total_errors']}\")
print(f\"Avg duration: {r['avg_duration_ms']}ms\")
"
fi

# Show evolution journal if available
if [ -f /app/logs/simulation/journal_summary.json ]; then
    echo ""
    echo "=== Evolution Journal ==="
    python -c "
import json
j = json.loads(open('/app/logs/simulation/journal_summary.json').read())
print(f\"Evolutions: {j.get('total_evolutions', 0)}\")
print(f\"Success rate: {j.get('success_rate', 0)}%\")
print(f\"Avg quality: {j.get('avg_quality', 0):.3f}\")
print(f\"Avg duration: {j.get('avg_duration_ms', 0):.0f}ms\")
ts = j.get('top_strategies', [])
if ts:
    print(f\"Top strategies: {', '.join(f'{s[0]}({s[1]}%)' for s in ts[:3])}\")
"
fi

exit $EXIT_CODE
