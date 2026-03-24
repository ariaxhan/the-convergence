"""
Ollama Integration -- Local Models with Runtime Optimization

What this demonstrates:
- Using Convergence runtime with Ollama local models
- No API key needed -- runtime still optimizes parameters
- How to optimize local model parameters (temperature, model choice)

Prerequisites:
- pip install the-convergence
- Ollama running locally: ollama serve
- At least one model pulled: ollama pull llama3.2

Suggested prompts / test inputs:
- Pull multiple models and add them as separate arms
- Compare local model quality vs cloud providers
- Test with ollama pull phi3 for a smaller, faster model
"""

# --- Configuration ---
import asyncio
import uuid
from typing import Any, Dict, List
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.types import RuntimeArmTemplate, RuntimeConfig


# --- Setup ---
SYSTEM = "ollama_demo"
OLLAMA_URL = "http://localhost:11434"


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


def call_ollama(model: str, prompt: str, temperature: float = 0.7) -> str:
    """Call Ollama API synchronously (no extra dependencies needed)."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }).encode()
    req = Request(f"{OLLAMA_URL}/api/generate", data=payload,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["response"]
    except URLError:
        print(f"Cannot connect to Ollama at {OLLAMA_URL}")
        print("Start it with: ollama serve")
        raise SystemExit(1)


# --- Execution ---
async def main():
    config = RuntimeConfig(
        system=SYSTEM,
        default_arms=[
            RuntimeArmTemplate(arm_id="precise", params={"temperature": 0.2}),
            RuntimeArmTemplate(arm_id="creative", params={"temperature": 0.9}),
        ],
    )
    await configure_runtime(SYSTEM, config=config, storage=MemoryStorage())

    # 1. Select
    selection = await runtime_select(SYSTEM, user_id="local_user")
    temperature = selection.params.get("temperature", 0.7)
    print(f"Runtime selected: arm={selection.arm_id}, temperature={temperature}")

    # 2. Call Ollama
    text = call_ollama("llama3.2", "What is the capital of France?", temperature)
    print(f"Response: {text[:200]}")

    # 3. Evaluate + Update
    reward = 1.0 if "paris" in text.lower() else 0.0
    await runtime_update(SYSTEM, user_id="local_user",
                         decision_id=selection.decision_id, reward=reward)
    print(f"Reward recorded: {reward}")


if __name__ == "__main__":
    asyncio.run(main())
