"""
Sequential Pipeline with Per-Step Optimization

What this demonstrates:
- 3-step pipeline: classify -> generate -> validate
- Each step has its own Thompson Sampling runtime
- Arms converge independently per step
- Overall pipeline success rate improves over time

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- Change TRUE_RATES to make different arms better
- Add a 4th pipeline step and watch armature
- Set all rates equal and see how long armature takes

No API keys required. Pure local.
"""

import asyncio
import random

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
ROUNDS = 30
USER = "pipeline_user"

def _arm(aid, name):
    return RuntimeArmTemplate(arm_id=aid, name=name, params={})

STEPS = {
    "classify": {
        "arms": [_arm("keyword", "Keyword"), _arm("semantic", "Semantic")],
        "true_rates": {"keyword": 0.5, "semantic": 0.8},
    },
    "generate": {
        "arms": [_arm("concise", "Concise"), _arm("detailed", "Detailed")],
        "true_rates": {"concise": 0.7, "detailed": 0.4},
    },
    "validate": {
        "arms": [_arm("strict", "Strict"), _arm("lenient", "Lenient")],
        "true_rates": {"strict": 0.6, "lenient": 0.75},
    },
}


# --- Execution ---
async def main() -> None:
    storages = {}
    for step_name, step_cfg in STEPS.items():
        storages[step_name] = MemoryRuntimeStorage()
        config = RuntimeConfig(system=step_name, default_arms=step_cfg["arms"])
        await configure_runtime(step_name, config=config,
                                storage=storages[step_name])

    counts = {s: {} for s in STEPS}
    pipeline_results = []

    for i in range(ROUNDS):
        step_ok = True
        for step_name, step_cfg in STEPS.items():
            sel = await runtime_select(step_name, user_id=USER)
            arm = sel.arm_id
            counts[step_name][arm] = counts[step_name].get(arm, 0) + 1

            success = random.random() < step_cfg["true_rates"][arm]
            reward = 1.0 if success else 0.0
            await runtime_update(step_name, user_id=USER,
                                 decision_id=sel.decision_id, reward=reward)
            if not success:
                step_ok = False
        pipeline_results.append(step_ok)

    # --- Output ---
    print("Sequential Pipeline Optimization (30 rounds)")
    print("=" * 55)
    print("Pipeline: classify -> generate -> validate\n")

    for step_name, step_cfg in STEPS.items():
        best = max(step_cfg["true_rates"], key=step_cfg["true_rates"].get)
        print(f"  {step_name}:")
        for arm_id, count in sorted(counts[step_name].items()):
            marker = " <-- best" if arm_id == best else ""
            print(f"    {arm_id}: selected {count}/{ROUNDS}{marker}")

    print("\nPipeline success rate by window:")
    for start in range(0, ROUNDS, 10):
        window = pipeline_results[start:start + 10]
        rate = sum(window) / len(window) * 100
        bar = "#" * int(rate / 5)
        print(f"  Rounds {start + 1:2d}-{start + len(window):2d}: "
              f"{rate:5.1f}% {bar}")


if __name__ == "__main__":
    asyncio.run(main())
