"""
Gradual Rollout (Canary Deployment)

What this demonstrates:
- Phased introduction of a new arm alongside the incumbent
- Phase 1: exploration bonus ensures the new arm gets sampled
- Phase 2: reduced bonus lets Thompson Sampling weigh in
- Phase 3: full Thompson Sampling for natural armature

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- Set the new arm's TRUE_RATE below incumbent to watch rollback
- Add a Phase 4 with use_stability=True for lock-in behavior
"""

# --- Configuration ---
import asyncio
import random

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig
from armature.types.runtime import SelectionStrategyConfig

SYSTEM = "canary"
USER = "user_1"
TRUE_RATES = {"incumbent": 0.55, "canary": 0.70}

PHASES = [
    ("Phase 1: Explore", 30, SelectionStrategyConfig(
        exploration_bonus=0.3, exploration_min_pulls=10, use_stability=False,
    )),
    ("Phase 2: Reduce bonus", 30, SelectionStrategyConfig(
        exploration_bonus=0.1, exploration_min_pulls=5, use_stability=False,
    )),
    ("Phase 3: Full TS", 40, SelectionStrategyConfig(
        exploration_bonus=0.0, use_stability=True,
        stability_min_pulls=10, stability_improvement_threshold=0.05,
    )),
]

BASE_ARMS = [
    RuntimeArmTemplate(arm_id="incumbent", name="Incumbent", params={}),
    RuntimeArmTemplate(arm_id="canary", name="Canary (New)", params={}),
]


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()

    print("Gradual Rollout: Canary Deployment")
    print("=" * 55)
    print(f"True rates: incumbent={TRUE_RATES['incumbent']}, canary={TRUE_RATES['canary']}")
    print()

    for phase_name, rounds, strategy in PHASES:
        phase_config = RuntimeConfig(
            system=SYSTEM,
            default_arms=BASE_ARMS,
            selection_strategy=strategy,
        )
        await configure_runtime(SYSTEM, config=phase_config, storage=storage)

        canary_count = 0
        for _ in range(rounds):
            sel = await runtime_select(SYSTEM, user_id=USER)
            reward = 1.0 if random.random() < TRUE_RATES[sel.arm_id] else 0.0
            await runtime_update(
                SYSTEM, user_id=USER, decision_id=sel.decision_id, reward=reward,
            )
            if sel.arm_id == "canary":
                canary_count += 1

        pct = canary_count / rounds * 100
        print(f"  {phase_name:24s}: canary selected {pct:5.1f}% ({canary_count}/{rounds})")

    print()
    print("If canary % increases across phases, the new arm is winning.")
    print("If it decreases, Thompson Sampling is rolling back to incumbent.")


if __name__ == "__main__":
    asyncio.run(main())
