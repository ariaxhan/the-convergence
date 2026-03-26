"""
OpenAI Integration -- Runtime Pattern

What this demonstrates:
- Using Armature runtime with OpenAI's API
- The select -> call -> evaluate -> update pattern
- How runtime optimizes parameters across requests

Prerequisites:
- pip install -e . openai
- Set OPENAI_API_KEY environment variable

Suggested prompts / test inputs:
- Run 10+ times to see Thompson Sampling converge
- Add more temperature arms to explore the parameter space
- Change the scoring to prefer longer or shorter answers
"""

# --- Configuration ---
import asyncio
import os
import sys
import uuid
from typing import Any, Dict, List

from armature import configure_runtime, runtime_select, runtime_update
from armature.types import RuntimeArmTemplate, RuntimeConfig

# --- Setup ---
SYSTEM = "openai_demo"


class MemoryStorage:
    """Minimal in-memory storage for the demo."""

    def __init__(self):
        self._arms: Dict[str, List[Dict[str, Any]]] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}

    def _key(self, uid: str, at: str) -> str:
        return f"{uid}:{at}"

    async def get_arms(self, *, user_id: str, agent_type: str) -> List[Any]:
        return self._arms.get(self._key(user_id, agent_type), [])

    async def initialize_arms(self, *, user_id: str, agent_type: str, arms: List[Dict[str, Any]]) -> None:
        key = self._key(user_id, agent_type)
        if key not in self._arms:
            self._arms[key] = [
                {"arm_id": a["arm_id"], "params": a.get("params", {}),
                 "alpha": 1.0, "beta": 1.0, "total_pulls": 0, "total_reward": 0.0,
                 "mean_estimate": None, "metadata": {}}
                for a in arms
            ]

    async def create_decision(self, *, user_id: str, agent_type: str, arm_pulled: str,
                              strategy_params: Dict, arms_snapshot: List, metadata=None) -> str:
        did = uuid.uuid4().hex[:12]
        self._decisions[did] = {"arm_id": arm_pulled, "user_id": user_id, "agent_type": agent_type}
        return did

    async def update_performance(self, *, user_id: str, agent_type: str, decision_id: str,
                                 reward: float, **kwargs) -> Dict:
        return {"success": True}

    async def get_decision(self, *, user_id: str, decision_id: str) -> Dict:
        return self._decisions.get(decision_id, {})


def check_api_key():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY. Set it with: export OPENAI_API_KEY=sk-...")
        sys.exit(1)


# --- Execution ---
async def main():
    check_api_key()

    from openai import AsyncOpenAI

    openai_client = AsyncOpenAI()

    config = RuntimeConfig(
        system=SYSTEM,
        default_arms=[
            RuntimeArmTemplate(arm_id="precise", params={"temperature": 0.2}),
            RuntimeArmTemplate(arm_id="balanced", params={"temperature": 0.7}),
        ],
    )
    await configure_runtime(SYSTEM, config=config, storage=MemoryStorage())

    # 1. Select -- runtime picks parameters
    selection = await runtime_select(SYSTEM, user_id="user_1")
    temperature = selection.params.get("temperature", 0.7)
    print(f"Runtime selected: arm={selection.arm_id}, temperature={temperature}")

    # 2. Call -- use selected parameters with OpenAI
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )
    text = response.choices[0].message.content
    print(f"Response: {text[:200]}")

    # 3. Evaluate -- score the response
    reward = 1.0 if "paris" in text.lower() else 0.0

    # 4. Update -- runtime learns from the outcome
    await runtime_update(SYSTEM, user_id="user_1",
                         decision_id=selection.decision_id, reward=reward)
    print(f"Reward recorded: {reward}")


if __name__ == "__main__":
    asyncio.run(main())
