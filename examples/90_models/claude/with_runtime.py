"""
Claude Integration -- With Runtime MAB Selection

What this demonstrates:
- ClaudeClient combined with runtime Thompson Sampling
- Configuring multiple arms with different temperatures
- How the runtime influences Claude parameters over time

Prerequisites:
- pip install the-convergence anthropic
- Set ANTHROPIC_API_KEY environment variable

Suggested prompts / test inputs:
- Run multiple times to see which arm converges as the winner
- Add a third arm with temperature=0.9 for creative responses
- Change the reward logic to prefer shorter answers
"""

# --- Configuration ---
import asyncio
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from convergence import configure_runtime
from convergence.clients import ClaudeClient
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Setup ---
SYSTEM = "claude_runtime_demo"


class MemoryStorage:
    """Minimal in-memory storage for the demo."""

    def __init__(self):
        self._arms: Dict[str, List[Dict[str, Any]]] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}

    def _key(self, user_id: str, agent_type: str) -> str:
        return f"{user_id}:{agent_type}"

    async def get_arms(self, *, user_id: str, agent_type: str) -> List[Any]:
        return self._arms.get(self._key(user_id, agent_type), [])

    async def initialize_arms(self, *, user_id: str, agent_type: str, arms: List[Dict[str, Any]]) -> None:
        key = self._key(user_id, agent_type)
        if key not in self._arms:
            self._arms[key] = [
                {"arm_id": a["arm_id"], "name": a.get("name"), "params": a.get("params", {}),
                 "alpha": 1.0, "beta": 1.0, "total_pulls": 0, "total_reward": 0.0,
                 "mean_estimate": None, "metadata": {}}
                for a in arms
            ]

    async def create_decision(self, *, user_id: str, agent_type: str, arm_pulled: str,
                              strategy_params: Dict[str, Any], arms_snapshot: List[Dict[str, Any]],
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        did = uuid.uuid4().hex[:12]
        self._decisions[did] = {"arm_id": arm_pulled, "user_id": user_id, "agent_type": agent_type}
        return did

    async def update_performance(self, *, user_id: str, agent_type: str, decision_id: str,
                                 reward: float, engagement=None, grading=None,
                                 metadata=None, computed_update=None) -> Dict[str, Any]:
        decision = self._decisions.get(decision_id, {})
        key = self._key(user_id, agent_type)
        for arm in self._arms.get(key, []):
            if arm["arm_id"] == decision.get("arm_id") and computed_update:
                arm.update({k: computed_update[k] for k in computed_update if k in arm})
        return {"success": True}

    async def get_decision(self, *, user_id: str, decision_id: str) -> Dict[str, Any]:
        return self._decisions.get(decision_id, {})


def check_api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY. Set it with: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)


# --- Execution ---
async def main():
    check_api_key()

    config = RuntimeConfig(
        system=SYSTEM,
        default_arms=[
            RuntimeArmTemplate(arm_id="precise", name="Low Temperature",
                               params={"temperature": 0.2}),
            RuntimeArmTemplate(arm_id="creative", name="High Temperature",
                               params={"temperature": 0.8}),
        ],
    )
    storage = MemoryStorage()
    await configure_runtime(SYSTEM, config=config, storage=storage)

    client = ClaudeClient(
        system=SYSTEM,
        system_prompt="You are a helpful assistant. Be concise.",
        model="claude-sonnet-4-5",
    )

    response = await client.chat(
        message="Explain quantum entanglement in one sentence.",
        user_id="demo_user",
    )

    print(f"Content:      {response.content[:200]}")
    print(f"Confidence:   {response.confidence}")
    print(f"Decision ID:  {response.decision_id}")
    print(f"Params used:  {response.params}")

    # Record outcome -- the runtime learns from this
    if response.decision_id:
        reward = 1.0 if response.confidence and response.confidence > 0.7 else 0.3
        await client.record_outcome(
            decision_id=response.decision_id,
            user_id="demo_user",
            reward=reward,
        )
        print(f"Reward sent:  {reward}")


if __name__ == "__main__":
    asyncio.run(main())
