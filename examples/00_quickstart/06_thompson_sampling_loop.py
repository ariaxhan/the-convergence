"""
06 - Thompson Sampling Convergence

What this demonstrates:
- Thompson Sampling converging over 50 rounds
- Two arms with different true reward rates
- ASCII visualization of selection frequency over time
- How exploration naturally decreases as confidence grows

Suggested prompts to explore after running:
- Make both arms have similar rates (0.5 vs 0.55) -- how many rounds to converge?
- Add a third arm and watch the three-way competition
- Set one arm to 0.0 reward and see how fast it gets abandoned

No API keys required. Pure local.
"""

import asyncio
import random
from typing import Dict, List

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "thompson_demo"
USER = "user_1"
ROUNDS = 50

# True reward rates (the system does not know these)
TRUE_RATES = {"arm_a": 0.7, "arm_b": 0.3}

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(arm_id="arm_a", name="Arm A (0.7)", params={"strategy": "A"}),
        RuntimeArmTemplate(arm_id="arm_b", name="Arm B (0.3)", params={"strategy": "B"}),
    ],
)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    counts: Dict[str, int] = {"arm_a": 0, "arm_b": 0}
    history: List[str] = []

    for i in range(ROUNDS):
        selection = await runtime_select(SYSTEM, user_id=USER)
        arm = selection.arm_id

        reward = 1.0 if random.random() < TRUE_RATES[arm] else 0.0

        await runtime_update(
            SYSTEM, user_id=USER, decision_id=selection.decision_id, reward=reward,
        )

        counts[arm] += 1
        history.append(arm)

    # --- ASCII Visualization ---
    print("Thompson Sampling Convergence (50 rounds)")
    print("=" * 55)
    print(f"True rates: Arm A = {TRUE_RATES['arm_a']}, Arm B = {TRUE_RATES['arm_b']}")
    print()

    # Show selection timeline in 5-round buckets
    print("Selection timeline (each char = 1 round, A or B):")
    print()
    for start in range(0, ROUNDS, 10):
        chunk = history[start : start + 10]
        bar = "".join("A" if h == "arm_a" else "B" for h in chunk)
        print(f"  Rounds {start + 1:2d}-{start + len(chunk):2d}: [{bar}]")

    print()
    print("Selection frequency:")
    total = sum(counts.values())
    for arm_id in ["arm_a", "arm_b"]:
        count = counts[arm_id]
        pct = count / total * 100
        bar = "#" * int(pct / 2)
        print(f"  {arm_id}: {count:3d}/{total} ({pct:5.1f}%) {bar}")

    print()
    if counts["arm_a"] > counts["arm_b"]:
        print("Arm A (the better arm) was selected more often. Convergence achieved.")
    else:
        print("Arm B was selected more (unusual with these rates -- run again).")


if __name__ == "__main__":
    asyncio.run(main())
