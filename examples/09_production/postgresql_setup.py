"""
PostgreSQL Storage Setup

What this demonstrates:
- Configuring runtime with persistent storage for production
- SelectionStrategyConfig tuned for production stability
- Stable arm selection with minimal unnecessary switching

Prerequisites:
- pip install armature-ai
- For real PostgreSQL: pip install armature-ai[postgresql]

Suggested prompts / test inputs:
- Increase stability_improvement_threshold to 0.2 for even less switching
- Lower exploration_min_pulls to 3 to see faster armature
"""

# --- Configuration ---
import asyncio
import random

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig
from armature.types.runtime import SelectionStrategyConfig

SYSTEM = "prod_service"
USER = "user_1"

# Production:
# from armature.storage.postgresql import PostgreSQLRuntimeStorage
# storage = PostgreSQLRuntimeStorage(dsn="postgresql://user:pass@host/db", system="prod")
# Development fallback:
storage = MemoryRuntimeStorage()

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(arm_id="formal", name="Formal Tone", params={"tone": "formal"}),
        RuntimeArmTemplate(arm_id="casual", name="Casual Tone", params={"tone": "casual"}),
        RuntimeArmTemplate(arm_id="concise", name="Concise Tone", params={"tone": "concise"}),
    ],
    selection_strategy=SelectionStrategyConfig(
        exploration_bonus=0.1,
        exploration_min_pulls=5,
        use_stability=True,
        stability_min_pulls=10,
        stability_confidence_threshold=0.3,
        stability_improvement_threshold=0.05,
    ),
)

TRUE_RATES = {"formal": 0.7, "casual": 0.5, "concise": 0.6}


# --- Execution ---
async def main() -> None:
    await configure_runtime(SYSTEM, config=config, storage=storage)

    print("Production PostgreSQL Setup (30 iterations)")
    print("=" * 55)
    print("Stability config: min_pulls=10, improvement_threshold=0.05")
    print()

    selections: list[str] = []
    for i in range(1, 31):
        sel = await runtime_select(SYSTEM, user_id=USER)
        reward = 1.0 if random.random() < TRUE_RATES[sel.arm_id] else 0.0
        await runtime_update(SYSTEM, user_id=USER, decision_id=sel.decision_id, reward=reward)
        selections.append(sel.arm_id)

        if i % 10 == 0:
            print(f"Round {i:2d}: selected={sel.arm_id}")
            for arm in sel.arms_state:
                mean = arm.alpha / (arm.alpha + arm.beta)
                print(f"  {arm.arm_id:8s} alpha={arm.alpha:5.1f} beta={arm.beta:5.1f} mean={mean:.3f}")
            print()

    switches = sum(1 for a, b in zip(selections, selections[1:]) if a != b)
    print(f"Total arm switches: {switches}/29 (lower = more stable)")
    print(f"Final 10 selections: {selections[-10:]}")


if __name__ == "__main__":
    asyncio.run(main())
