"""
01 - Basic Runtime Selection

What this demonstrates:
- Configuring the runtime with two arms (Thompson Sampling MAB)
- Selecting an arm for a user
- Inspecting the selection result (arm_id, params, sampled_value)

Suggested prompts to explore after running:
- Run it multiple times -- which arm gets picked more often?
- Add a third arm and observe the distribution
- Change the arm params and watch how they flow through

No API keys required. Pure local.
"""

import asyncio

from convergence import configure_runtime, runtime_select
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "quickstart_demo"

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(
            arm_id="formal",
            name="Formal Tone",
            params={"tone": "formal", "temperature": 0.3},
        ),
        RuntimeArmTemplate(
            arm_id="casual",
            name="Casual Tone",
            params={"tone": "casual", "temperature": 0.7},
        ),
    ],
)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    # Select an arm for a user via Thompson Sampling
    selection = await runtime_select(SYSTEM, user_id="user_1")

    print(f"Selected arm:    {selection.arm_id}")
    print(f"Parameters:      {selection.params}")
    print(f"Sampled value:   {selection.sampled_value:.4f}")
    print(f"Decision ID:     {selection.decision_id}")
    print()
    print("Arms state at decision time:")
    for arm_state in selection.arms_state:
        print(f"  {arm_state.arm_id}: sampled={arm_state.sampled_value:.4f} "
              f"alpha={arm_state.alpha:.1f} beta={arm_state.beta:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
