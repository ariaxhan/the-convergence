"""
Azure OpenAI Integration -- Runtime Pattern

What this demonstrates:
- Using Convergence runtime with Azure OpenAI endpoints
- Environment-based configuration for Azure credentials
- The same select -> call -> evaluate -> update pattern

Prerequisites:
- pip install -e . openai
- Set AZURE_OPENAI_ENDPOINT (e.g. https://myresource.openai.azure.com/)
- Set AZURE_OPENAI_KEY

Suggested prompts / test inputs:
- Add multiple Azure deployments as separate arms
- Compare gpt-4o vs gpt-4o-mini deployments
- Weight cost efficiency more heavily in your reward
"""

# --- Configuration ---
import asyncio
import os
import sys
import uuid
from typing import Any, Dict, List

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.types import RuntimeArmTemplate, RuntimeConfig

# --- Setup ---
SYSTEM = "azure_demo"


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


def check_env():
    missing = []
    if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not os.environ.get("AZURE_OPENAI_KEY"):
        missing.append("AZURE_OPENAI_KEY")
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Set them with:")
        print("  export AZURE_OPENAI_ENDPOINT=https://myresource.openai.azure.com/")
        print("  export AZURE_OPENAI_KEY=your-key-here")
        sys.exit(1)


# --- Execution ---
async def main():
    check_env()

    from openai import AsyncAzureOpenAI

    azure_client = AsyncAzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2024-12-01-preview",
    )

    config = RuntimeConfig(
        system=SYSTEM,
        default_arms=[
            RuntimeArmTemplate(arm_id="precise", params={"temperature": 0.2}),
            RuntimeArmTemplate(arm_id="balanced", params={"temperature": 0.7}),
        ],
    )
    await configure_runtime(SYSTEM, config=config, storage=MemoryStorage())

    # 1. Select
    selection = await runtime_select(SYSTEM, user_id="user_1")
    temperature = selection.params.get("temperature", 0.7)
    print(f"Runtime selected: arm={selection.arm_id}, temperature={temperature}")

    # 2. Call Azure OpenAI
    response = await azure_client.chat.completions.create(
        model="gpt-4o-mini",  # This is your Azure deployment name
        temperature=temperature,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
    )
    text = response.choices[0].message.content
    print(f"Response: {text[:200]}")

    # 3. Evaluate + Update
    reward = 1.0 if "paris" in text.lower() else 0.0
    await runtime_update(SYSTEM, user_id="user_1",
                         decision_id=selection.decision_id, reward=reward)
    print(f"Reward recorded: {reward}")


if __name__ == "__main__":
    asyncio.run(main())
