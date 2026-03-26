"""
Groq Integration -- Runtime Pattern

What this demonstrates:
- Using Armature runtime with Groq's fast inference API
- How runtime optimizes parameters for speed-focused providers
- The same select -> call -> evaluate -> update pattern

Prerequisites:
- pip install -e . groq
- Set GROQ_API_KEY environment variable

Suggested prompts / test inputs:
- Compare Groq response times against OpenAI in your scoring
- Try different Llama models as separate arms
- Weight speed more heavily in your reward calculation
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
SYSTEM = "groq_demo"


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
    if not os.environ.get("GROQ_API_KEY"):
        print("Missing GROQ_API_KEY. Set it with: export GROQ_API_KEY=gsk_...")
        sys.exit(1)


# --- Execution ---
async def main():
    check_api_key()

    from groq import AsyncGroq

    groq_client = AsyncGroq()

    config = RuntimeConfig(
        system=SYSTEM,
        default_arms=[
            RuntimeArmTemplate(arm_id="fast", params={"temperature": 0.3, "model": "llama-3.1-8b-instant"}),
            RuntimeArmTemplate(arm_id="quality", params={"temperature": 0.5, "model": "llama-3.1-70b-versatile"}),
        ],
    )
    await configure_runtime(SYSTEM, config=config, storage=MemoryStorage())

    # 1. Select
    selection = await runtime_select(SYSTEM, user_id="user_1")
    model = selection.params.get("model", "llama-3.1-8b-instant")
    temperature = selection.params.get("temperature", 0.5)
    print(f"Runtime selected: arm={selection.arm_id}, model={model}")

    # 2. Call Groq
    response = await groq_client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )
    text = response.choices[0].message.content
    print(f"Response: {text[:200]}")

    # 3. Evaluate
    reward = 1.0 if "paris" in text.lower() else 0.0

    # 4. Update
    await runtime_update(SYSTEM, user_id="user_1",
                         decision_id=selection.decision_id, reward=reward)
    print(f"Reward recorded: {reward}")


if __name__ == "__main__":
    asyncio.run(main())
