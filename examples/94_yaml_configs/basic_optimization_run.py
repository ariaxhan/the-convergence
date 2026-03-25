"""Load and validate basic_optimization.yaml.

Demonstrates ConfigLoader usage without running a full optimization.
Won't run without a real API endpoint — this shows loading and validation.
"""

from __future__ import annotations

from pathlib import Path

from convergence.optimization.config_loader import ConfigLoader


def main() -> None:
    config_path = Path(__file__).parent / "basic_optimization.yaml"
    config = ConfigLoader.load(str(config_path))

    print("Parsed config:")
    print(f"  API name:    {config.api.name}")
    print(f"  Endpoint:    {config.api.endpoint}")

    print("\nSearch space:")
    for name, param in config.search_space.parameters.items():
        print(f"  {name}: {param}")

    print("\nEvaluation metrics:")
    for name, metric in config.evaluation.metrics.items():
        print(f"  {name} (weight={metric.weight}, {metric.type})")

    pop = config.optimization.evolution.population_size
    gens = config.optimization.evolution.generations
    print(f"\nOptimization: {gens} generations x {pop} population")
    print("Ready to run. Use: convergence optimize basic_optimization.yaml")


if __name__ == "__main__":
    main()
