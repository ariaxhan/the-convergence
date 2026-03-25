"""
Monitoring Dashboard

What this demonstrates:
- Tracking arm selection counts, rewards, regret, and confidence intervals
- Periodic dashboard output suitable for Prometheus/Grafana export
- Cumulative regret calculation against the optimal arm

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Change TRUE_RATES to make arms closer and watch regret grow
- Increase ROUNDS to 500 to see tighter confidence intervals
"""

# --- Configuration ---
import asyncio
import math
import random

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

SYSTEM = "monitored_service"
USER = "user_1"
ROUNDS = 100
TRUE_RATES = {"alpha": 0.75, "beta": 0.50, "gamma": 0.30}
OPTIMAL = max(TRUE_RATES.values())

config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(arm_id=aid, name=aid.title(), params={})
        for aid in TRUE_RATES
    ],
)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    pulls: dict[str, int] = {a: 0 for a in TRUE_RATES}
    rewards: dict[str, float] = {a: 0.0 for a in TRUE_RATES}
    cumulative_regret = 0.0

    print("Monitoring Dashboard (100 iterations)")
    print("=" * 65)

    for i in range(1, ROUNDS + 1):
        sel = await runtime_select(SYSTEM, user_id=USER)
        reward = 1.0 if random.random() < TRUE_RATES[sel.arm_id] else 0.0
        await runtime_update(SYSTEM, user_id=USER, decision_id=sel.decision_id, reward=reward)

        pulls[sel.arm_id] += 1
        rewards[sel.arm_id] += reward
        cumulative_regret += OPTIMAL - TRUE_RATES[sel.arm_id]

        # In production, export to Prometheus:
        # convergence_arm_pulls.labels(arm=sel.arm_id).inc()
        # convergence_reward.labels(arm=sel.arm_id).observe(reward)
        # convergence_regret.set(cumulative_regret)

        if i % 25 == 0:
            explores = sum(1 for a in TRUE_RATES if pulls[a] < 5)
            print(f"\n--- Dashboard at round {i} ---")
            print(f"  Cumulative regret: {cumulative_regret:.2f}")
            print(f"  Exploration ratio: {explores}/{len(TRUE_RATES)} arms under-explored")
            print(f"  {'Arm':<8} {'Pulls':>6} {'Avg Reward':>11} {'CI Width':>9}")
            print(f"  {'-'*8} {'-'*6} {'-'*11} {'-'*9}")
            for aid in TRUE_RATES:
                avg = rewards[aid] / pulls[aid] if pulls[aid] > 0 else 0.0
                ci = 1.96 * math.sqrt(avg * (1 - avg) / max(pulls[aid], 1))
                print(f"  {aid:<8} {pulls[aid]:>6} {avg:>11.3f} {ci:>9.3f}")

    print(f"\nFinal regret: {cumulative_regret:.2f} (lower = better arm selection)")


if __name__ == "__main__":
    asyncio.run(main())
