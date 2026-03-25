"""
Human-in-the-Loop Escalation

What this demonstrates:
- Auto-respond when confident, flag for human review when not
- Thompson Sampling learns which arm produces confident responses
- Auto-response rate increases over time as the system converges
- Simulated human override for low-confidence responses

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Lower the auto-respond threshold and watch automation increase
- Make both arms have similar confidence and see slower convergence
- Track which arm gets flagged for human review most often

No API keys required. Pure local.
"""

import asyncio
import random

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "hitl_demo"
USER = "hitl_user"
ROUNDS = 30
AUTO_THRESHOLD = 0.7

ARMS = [
    RuntimeArmTemplate(arm_id="direct", name="Direct Response", params={}),
    RuntimeArmTemplate(arm_id="cautious", name="Cautious Response", params={}),
]
TRUE_CONF = {"direct": 0.8, "cautious": 0.5}


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    config = RuntimeConfig(system=SYSTEM, default_arms=ARMS)
    await configure_runtime(SYSTEM, config=config, storage=storage)

    results = []

    for i in range(ROUNDS):
        sel = await runtime_select(SYSTEM, user_id=USER)
        conf = TRUE_CONF[sel.arm_id] + random.uniform(-0.15, 0.15)
        conf = max(0.0, min(1.0, conf))

        if conf >= AUTO_THRESHOLD:
            reward = 1.0  # simulated user satisfaction
            action = "auto"
        else:
            reward = 0.5  # human override costs time
            action = "human"

        await runtime_update(SYSTEM, user_id=USER,
                             decision_id=sel.decision_id, reward=reward)
        results.append({"arm": sel.arm_id, "conf": conf, "action": action})

    # --- Output ---
    print("Human-in-the-Loop Escalation (30 rounds)")
    print("=" * 55)
    print(f"Auto-respond threshold: {AUTO_THRESHOLD}")
    print(f"True confidence: {TRUE_CONF}\n")

    print("Auto vs Human by 10-query window:")
    for start in range(0, ROUNDS, 10):
        window = results[start:start + 10]
        auto = sum(1 for r in window if r["action"] == "auto")
        human = len(window) - auto
        auto_bar = "A" * auto + "H" * human
        print(f"  Rounds {start + 1:2d}-{start + len(window):2d}: "
              f"auto={auto} human={human} [{auto_bar}]")

    print("\nArm selection breakdown:")
    for arm_id in ["direct", "cautious"]:
        arm_results = [r for r in results if r["arm"] == arm_id]
        auto_count = sum(1 for r in arm_results if r["action"] == "auto")
        print(f"  {arm_id}: {len(arm_results)} selections, "
              f"{auto_count} auto-responded")

    total_auto = sum(1 for r in results if r["action"] == "auto")
    print(f"\nOverall: {total_auto}/{ROUNDS} auto-responded "
          f"({total_auto / ROUNDS * 100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
