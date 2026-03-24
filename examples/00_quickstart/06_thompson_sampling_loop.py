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
import uuid
from typing import Any, Dict, List, Optional

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.types import RuntimeArmTemplate, RuntimeConfig


# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
class MemoryRuntimeStorage:
    def __init__(self) -> None:
        self._arms: Dict[str, List[Dict[str, Any]]] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}

    def _key(self, user_id: str, agent_type: str) -> str:
        return f"{user_id}:{agent_type}"

    async def get_arms(self, *, user_id: str, agent_type: str) -> List[Any]:
        return self._arms.get(self._key(user_id, agent_type), [])

    async def initialize_arms(
        self, *, user_id: str, agent_type: str, arms: List[Dict[str, Any]]
    ) -> None:
        key = self._key(user_id, agent_type)
        if key not in self._arms:
            self._arms[key] = [
                {"arm_id": a["arm_id"], "name": a.get("name"), "params": a.get("params", {}),
                 "alpha": 1.0, "beta": 1.0, "total_pulls": 0, "total_reward": 0.0,
                 "mean_estimate": None, "metadata": {}}
                for a in arms
            ]

    async def create_decision(
        self, *, user_id: str, agent_type: str, arm_pulled: str,
        strategy_params: Dict[str, Any], arms_snapshot: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        did = uuid.uuid4().hex[:12]
        self._decisions[did] = {
            "decision_id": did, "user_id": user_id, "agent_type": agent_type,
            "arm_id": arm_pulled, "params": strategy_params,
            "arms_snapshot": arms_snapshot, "metadata": metadata or {},
        }
        return did

    async def update_performance(
        self, *, user_id: str, agent_type: str, decision_id: str, reward: float,
        engagement: Optional[float] = None, grading: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        computed_update: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        decision = self._decisions.get(decision_id, {})
        arm_id = decision.get("arm_id")
        key = self._key(user_id, agent_type)
        for arm in self._arms.get(key, []):
            if arm["arm_id"] == arm_id and computed_update:
                for k in ["alpha", "beta", "total_pulls", "total_reward", "mean_estimate", "avg_reward"]:
                    if k in computed_update:
                        arm[k] = computed_update[k]
        return {"success": True}

    async def get_decision(self, *, user_id: str, decision_id: str) -> Dict[str, Any]:
        return self._decisions.get(decision_id, {})


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
