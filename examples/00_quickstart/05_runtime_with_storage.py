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
- Increase iterations to 100 and observe stronger convergence

No API keys required. Pure local.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.types import RuntimeArmTemplate, RuntimeConfig


# ---------------------------------------------------------------------------
# In-memory storage (same pattern as 01, repeated here for self-containment)
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
                {
                    "arm_id": a["arm_id"],
                    "name": a.get("name"),
                    "params": a.get("params", {}),
                    "alpha": 1.0,
                    "beta": 1.0,
                    "total_pulls": 0,
                    "total_reward": 0.0,
                    "mean_estimate": None,
                    "metadata": {},
                }
                for a in arms
            ]

    async def create_decision(
        self, *, user_id: str, agent_type: str, arm_pulled: str,
        strategy_params: Dict[str, Any], arms_snapshot: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        decision_id = uuid.uuid4().hex[:12]
        self._decisions[decision_id] = {
            "decision_id": decision_id,
            "user_id": user_id,
            "agent_type": agent_type,
            "arm_id": arm_pulled,
            "params": strategy_params,
            "arms_snapshot": arms_snapshot,
            "metadata": metadata or {},
        }
        return decision_id

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
                arm["alpha"] = computed_update.get("alpha", arm["alpha"])
                arm["beta"] = computed_update.get("beta", arm["beta"])
                arm["total_pulls"] = computed_update.get("total_pulls", arm["total_pulls"])
                arm["total_reward"] = computed_update.get("total_reward", arm["total_reward"])
                arm["mean_estimate"] = computed_update.get("mean_estimate")
                arm["avg_reward"] = computed_update.get("avg_reward")
        return {"success": True}

    async def get_decision(self, *, user_id: str, decision_id: str) -> Dict[str, Any]:
        return self._decisions.get(decision_id, {})


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
