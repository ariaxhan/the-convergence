"""
Specialist Routing - Thompson Sampling Routes Queries to Experts

What this demonstrates:
- Three specialist agents (code, writing, math) as runtime arms
- Thompson Sampling learns which specialist handles which query type best
- Routing convergence: the right expert gets the right queries over time

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Add a 4th specialist for "research" queries
- Change reward logic to make one specialist dominant
- Increase queries to 100 and watch tighter convergence
"""

import asyncio
import random

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Configuration ---
SYSTEM = "specialist_team"
QUERY_TYPES = ["code", "writing", "math"]

SPECIALISTS = [
    RuntimeArmTemplate(
        arm_id="code_expert",
        name="Code Expert",
        params={"domain": "code", "strength": 0.9},
    ),
    RuntimeArmTemplate(
        arm_id="writing_expert",
        name="Writing Expert",
        params={"domain": "writing", "strength": 0.9},
    ),
    RuntimeArmTemplate(
        arm_id="math_expert",
        name="Math Expert",
        params={"domain": "math", "strength": 0.9},
    ),
]

config = RuntimeConfig(system=SYSTEM, default_arms=SPECIALISTS)


# --- Setup ---
def simulate_reward(specialist_domain: str, query_type: str) -> float:
    """Specialist matching their domain gets high reward."""
    if specialist_domain == query_type:
        return 0.8 + random.uniform(0, 0.2)
    return 0.2 + random.uniform(0, 0.3)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    routing_counts: dict[str, dict[str, int]] = {
        qt: {s.arm_id: 0 for s in SPECIALISTS} for qt in QUERY_TYPES
    }

    for i in range(40):
        query_type = random.choice(QUERY_TYPES)
        selection = await runtime_select(SYSTEM, user_id=f"query_{i}")
        specialist_domain = selection.params.get("domain", "")
        reward = simulate_reward(specialist_domain, query_type)

        await runtime_update(
            SYSTEM, user_id=f"query_{i}", decision_id=selection.decision_id, reward=reward
        )
        routing_counts[query_type][selection.arm_id] += 1

        if (i + 1) % 10 == 0:
            print(f"After {i + 1} queries:")
            for qt in QUERY_TYPES:
                counts = routing_counts[qt]
                leader = max(counts, key=counts.get)  # type: ignore[arg-type]
                print(f"  {qt:8s} -> {leader} ({counts[leader]} times)")
            print()

    print("--- Final Routing Distribution ---")
    for qt in QUERY_TYPES:
        counts = routing_counts[qt]
        total = sum(counts.values())
        parts = [f"{arm}={n}/{total}" for arm, n in counts.items() if n > 0]
        print(f"  {qt:8s}: {', '.join(parts)}")


if __name__ == "__main__":
    asyncio.run(main())
