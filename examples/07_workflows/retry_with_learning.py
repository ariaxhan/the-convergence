"""
Retry with Learning

What this demonstrates:
- First attempt with low confidence triggers a retry
- Thompson Sampling naturally tries a different arm on retry
- Over time, bad arms get fewer first-attempt selections
- Retry rate decreases as the system learns

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Set all true_conf values equal and see if retries persist
- Lower the retry threshold to 0.3 and watch retry rate drop
- Add more arms and observe exploration vs exploitation

No API keys required. Pure local.
"""

import asyncio
import random

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "retry_demo"
USER = "retry_user"
ROUNDS = 30
RETRY_THRESHOLD = 0.5

ARMS = [
    RuntimeArmTemplate(arm_id="safe", name="Safe", params={}),
    RuntimeArmTemplate(arm_id="creative", name="Creative", params={}),
    RuntimeArmTemplate(arm_id="analytical", name="Analytical", params={}),
]
TRUE_CONF = {"safe": 0.4, "creative": 0.75, "analytical": 0.6}


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    config = RuntimeConfig(system=SYSTEM, default_arms=ARMS)
    await configure_runtime(SYSTEM, config=config, storage=storage)

    first_ok, retry_ok, retry_count = 0, 0, 0
    window_retries = []

    for i in range(ROUNDS):
        sel = await runtime_select(SYSTEM, user_id=USER)
        conf = TRUE_CONF[sel.arm_id] + random.uniform(-0.15, 0.15)
        conf = max(0.0, min(1.0, conf))

        if conf >= RETRY_THRESHOLD:
            first_ok += 1
            await runtime_update(SYSTEM, user_id=USER,
                                 decision_id=sel.decision_id, reward=1.0)
            window_retries.append(False)
        else:
            await runtime_update(SYSTEM, user_id=USER,
                                 decision_id=sel.decision_id, reward=0.2)
            retry_count += 1
            window_retries.append(True)

            sel2 = await runtime_select(SYSTEM, user_id=USER)
            conf2 = TRUE_CONF[sel2.arm_id] + random.uniform(-0.15, 0.15)
            retry_reward = 1.0 if conf2 >= RETRY_THRESHOLD else 0.3
            await runtime_update(SYSTEM, user_id=USER,
                                 decision_id=sel2.decision_id, reward=retry_reward)
            if conf2 >= RETRY_THRESHOLD:
                retry_ok += 1

    # --- Output ---
    print("Retry with Learning (30 rounds)")
    print("=" * 55)
    print(f"True confidence: {TRUE_CONF}")
    print(f"Retry threshold: {RETRY_THRESHOLD}\n")

    print(f"  First-attempt success: {first_ok}/{ROUNDS}")
    print(f"  Retries triggered:     {retry_count}/{ROUNDS}")
    print(f"  Retry success:         {retry_ok}/{retry_count}"
          if retry_count else "  No retries needed")

    print("\nRetry rate by window:")
    for start in range(0, ROUNDS, 10):
        window = window_retries[start:start + 10]
        rate = sum(window) / len(window) * 100
        bar = "#" * int(rate / 5)
        print(f"  Rounds {start + 1:2d}-{start + len(window):2d}: "
              f"{rate:5.1f}% retried {bar}")


if __name__ == "__main__":
    asyncio.run(main())
