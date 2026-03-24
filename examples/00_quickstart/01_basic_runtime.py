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
import uuid
from typing import Any, Dict, List, Optional

from convergence import configure_runtime, runtime_select
from convergence.types import RuntimeArmTemplate, RuntimeConfig


# ---------------------------------------------------------------------------
# Minimal in-memory storage that satisfies RuntimeStorageProtocol
# ---------------------------------------------------------------------------
class MemoryRuntimeStorage:
    """Lightweight in-memory storage for quickstart examples."""

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
        self,
        *,
        user_id: str,
        agent_type: str,
        arm_pulled: str,
        strategy_params: Dict[str, Any],
        arms_snapshot: List[Dict[str, Any]],
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
        self,
        *,
        user_id: str,
        agent_type: str,
        decision_id: str,
        reward: float,
        engagement: Optional[float] = None,
        grading: Optional[float] = None,
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
