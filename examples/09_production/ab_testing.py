"""
A/B Testing with Armature

What this demonstrates:
- Running a controlled A/B test using Thompson Sampling
- Statistical significance via z-test on conversion rates
- Exploration bonus to ensure both arms get sufficient samples

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- Set both arms to the same TRUE_RATE and confirm no significance
- Increase USERS to 500 for tighter confidence intervals
"""

# --- Configuration ---
import asyncio
import math
import random

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig
from armature.types.runtime import SelectionStrategyConfig

SYSTEM = "ab_test"
USERS = 100
TRUE_RATES = {"control": 0.45, "treatment": 0.60}

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(arm_id="control", name="Current (Control)", params={}),
        RuntimeArmTemplate(arm_id="treatment", name="New (Treatment)", params={}),
    ],
    selection_strategy=SelectionStrategyConfig(
        exploration_bonus=0.2,
        exploration_min_pulls=15,
        use_stability=False,
    ),
)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    pulls: dict[str, int] = {"control": 0, "treatment": 0}
    conversions: dict[str, int] = {"control": 0, "treatment": 0}

    for i in range(USERS):
        user_id = f"user_{i}"
        sel = await runtime_select(SYSTEM, user_id=user_id)
        converted = random.random() < TRUE_RATES[sel.arm_id]
        reward = 1.0 if converted else 0.0
        await runtime_update(SYSTEM, user_id=user_id, decision_id=sel.decision_id, reward=reward)
        pulls[sel.arm_id] += 1
        if converted:
            conversions[sel.arm_id] += 1

    # --- Results ---
    print("A/B Test Results")
    print("=" * 55)
    for arm in ["control", "treatment"]:
        rate = conversions[arm] / max(pulls[arm], 1)
        ci = 1.96 * math.sqrt(rate * (1 - rate) / max(pulls[arm], 1))
        print(f"  {arm:12s}: {conversions[arm]:3d}/{pulls[arm]:3d} = {rate:.1%} (+/- {ci:.1%})")

    # Z-test for significance
    p1 = conversions["control"] / max(pulls["control"], 1)
    p2 = conversions["treatment"] / max(pulls["treatment"], 1)
    n1, n2 = max(pulls["control"], 1), max(pulls["treatment"], 1)
    pooled = (conversions["control"] + conversions["treatment"]) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2)) if pooled > 0 else 1.0
    z = (p2 - p1) / se if se > 0 else 0.0

    print(f"\n  Z-score: {z:.2f} (>1.96 = significant at p<0.05)")
    if abs(z) > 1.96:
        winner = "treatment" if z > 0 else "control"
        print(f"  Result: SIGNIFICANT -- recommend deploying '{winner}'")
    else:
        print("  Result: NOT SIGNIFICANT -- continue testing or increase sample size")


if __name__ == "__main__":
    asyncio.run(main())
