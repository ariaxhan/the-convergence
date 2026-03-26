"""
05 - Runtime with Persistent Storage

What this demonstrates:
- Runtime MAB with an in-memory storage backend (simulating persistence)
- Select -> Update loop: arms learn from reward signals
- Bayesian updates: alpha/beta shift after each reward
- Running 20 iterations and watching the arms evolve

Suggested prompts to explore after running:
- Change the reward values and see how arms shift
- Add a third arm with different reward characteristics
- Increase iterations to 100 and observe stronger armature

No API keys required. Pure local.
"""

import asyncio

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "persistent_demo"
USER = "user_1"

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(arm_id="fast", name="Fast Response", params={"max_tokens": 128}),
        RuntimeArmTemplate(arm_id="thorough", name="Thorough Response", params={"max_tokens": 512}),
    ],
)


# --- Execution ---
async def main() -> None:
    import random

    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    print("Runtime Learning Loop (20 iterations)")
    print("=" * 55)
    print()
    print("Simulating: 'thorough' arm has 0.8 true reward rate,")
    print("            'fast' arm has 0.4 true reward rate.")
    print()

    # True reward rates (unknown to the system)
    true_rates = {"fast": 0.4, "thorough": 0.8}

    for i in range(1, 21):
        selection = await runtime_select(SYSTEM, user_id=USER)

        # Simulate reward based on true rate
        true_rate = true_rates[selection.arm_id]
        reward = 1.0 if random.random() < true_rate else 0.0

        await runtime_update(
            SYSTEM,
            user_id=USER,
            decision_id=selection.decision_id,
            reward=reward,
        )

        if i % 5 == 0:
            print(f"Round {i:2d}: selected={selection.arm_id:10s} reward={reward:.0f}")
            for arm in selection.arms_state:
                print(f"          {arm.arm_id:10s} alpha={arm.alpha:.1f} beta={arm.beta:.1f} "
                      f"sampled={arm.sampled_value:.3f}")
            print()

    print("After 20 rounds, the system should favor 'thorough' (higher true rate).")


if __name__ == "__main__":
    asyncio.run(main())
