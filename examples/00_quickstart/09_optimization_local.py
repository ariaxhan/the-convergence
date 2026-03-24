"""
09 - SDK Optimization with a Local Function

What this demonstrates:
- run_optimization with a local callable (no HTTP endpoint)
- Defining a search space with float and categorical parameters
- Custom evaluator function scoring the results
- Evolutionary optimization finding the best configuration

Suggested prompts to explore after running:
- Change the objective function to something more complex
- Widen the search space and increase generations
- Add more parameters to the search space

No API keys required. Uses a local function instead of an API endpoint.
"""

import asyncio
from typing import Any, Dict

from convergence import run_optimization
from convergence.types import (
    ApiConfig,
    ConvergenceConfig,
    EvaluationConfig,
    RunnerConfig,
    SearchSpaceConfig,
)


# ---------------------------------------------------------------------------
# The function we want to optimize. In production this could be an LLM call,
# a retrieval pipeline, or any system with tunable parameters.
# ---------------------------------------------------------------------------
async def my_function(params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulated system: quality depends on temperature and strategy.

    Optimal: temperature ~0.4, strategy 'balanced'
    """
    temp = params.get("temperature", 0.5)
    strategy = params.get("strategy", "fast")

    # Simulated quality: peaks at temp=0.4 for 'balanced'
    strategy_bonus = {"balanced": 0.3, "fast": 0.0, "thorough": 0.15}
    bonus = strategy_bonus.get(strategy, 0.0)

    # Gaussian-ish quality centered at 0.4
    quality = max(0.0, 1.0 - 4.0 * (temp - 0.4) ** 2) + bonus
    quality = min(1.0, quality)

    return {"content": f"result (temp={temp}, strategy={strategy})", "quality": quality}


# ---------------------------------------------------------------------------
# Evaluator: scores the output of my_function
# ---------------------------------------------------------------------------
def my_evaluator(response: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, float]:
    """Extract quality metric from the response."""
    return {"quality": response.get("quality", 0.0)}


# --- Configuration ---
config = ConvergenceConfig(
    api=ApiConfig(name="local_function", endpoint="http://localhost:0/unused"),
    search_space=SearchSpaceConfig(
        parameters={
            "temperature": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.1},
            "strategy": {"type": "categorical", "choices": ["fast", "balanced", "thorough"]},
        }
    ),
    runner=RunnerConfig(generations=5, population=10),
    evaluation=EvaluationConfig(
        required_metrics=["quality"],
        weights={"quality": 1.0},
    ),
)


# --- Execution ---
async def main() -> None:
    print("Local Function Optimization Demo")
    print("=" * 55)
    print()
    print("Optimizing: quality = f(temperature, strategy)")
    print("Search space: temperature [0.0-1.0], strategy [fast/balanced/thorough]")
    print("Optimal: temperature ~0.4, strategy 'balanced'")
    print()

    result = await run_optimization(
        config,
        evaluator=my_evaluator,
        local_function=my_function,
        logging_mode="summary",
    )

    print(f"Success:            {result.success}")
    print(f"Best config:        {result.best_config}")
    print(f"Best score:         {result.best_score:.4f}")
    print(f"Configs evaluated:  {result.configs_generated}")
    print(f"Generations run:    {result.generations_run}")
    print(f"Run ID:             {result.optimization_run_id}")


if __name__ == "__main__":
    asyncio.run(main())
