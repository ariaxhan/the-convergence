"""Load multi_metric.yaml and display the optimization plan.

Shows how weighted multi-metric configs are parsed and summarized.
"""

from __future__ import annotations

from pathlib import Path

from convergence.optimization.config_loader import ConfigLoader


def main() -> None:
    config_path = Path(__file__).parent / "multi_metric.yaml"
    config = ConfigLoader.load(str(config_path))

    print("Metric weights:")
    for name, metric in config.evaluation.metrics.items():
        pct = int(metric.weight * 100)
        direction = metric.type.replace("_", " ")
        threshold = getattr(metric, "threshold", None)
        suffix = f", threshold >= {threshold}" if threshold else ""
        print(f"  {name}: {pct}% ({direction}{suffix})")

    total = sum(m.weight for m in config.evaluation.metrics.values())
    print(f"  Total weight: {total}")

    print("\nThis would optimize for:", end="")
    parts = []
    for name, metric in config.evaluation.metrics.items():
        parts.append(f"{name} ({int(metric.weight * 100)}%)")
    print(f" {', '.join(parts)}")

    print("\nSearch space parameters:")
    for name, param in config.search_space.parameters.items():
        print(f"  {name}: {param}")

    patience = config.optimization.early_stopping.patience
    print(f"\nEarly stopping: {patience} generations without improvement")


if __name__ == "__main__":
    main()
