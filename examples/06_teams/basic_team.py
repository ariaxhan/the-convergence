"""
Basic Team - Three Agents with Different Strategies

What this demonstrates:
- Creating agents that implement the Agent protocol (agent_id, config, act, learn)
- Running a team of agents in CivilizationRuntime
- Comparing performance across different exploration strategies

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- Change strategy strings to see how reward changes
- Add a 4th agent with strategy "cooperate"
- Increase max_iterations to 100 and watch armature
"""

import asyncio

from armature.core.runtime import CivilizationRuntime


# --- Configuration ---
class SimpleAgent:
    """Agent with a fixed strategy for explore/exploit decisions."""

    def __init__(self, agent_id: str, strategy: str = "explore"):
        self.agent_id = agent_id
        self.config = {"strategy": strategy}
        self.reward_history: list[float] = []

    async def act(self, state: dict) -> dict:
        task_type = state.get("task", {}).get("type", "unknown")
        thought = (
            f"I see a {task_type} task. My strategy is {self.config['strategy']}. "
            f"Based on {len(self.reward_history)} past experiences, I will proceed carefully."
        )
        return {
            "thought": thought,
            "strategy": self.config["strategy"],
            "action": f"handle_{task_type}",
        }

    async def learn(self, experience: dict) -> None:
        self.reward_history.append(experience.get("reward", 0.0))


# --- Setup ---
agents = [
    SimpleAgent("explorer", strategy="explore"),
    SimpleAgent("exploiter", strategy="exploit"),
    SimpleAgent("balanced", strategy="cooperate"),
]


# --- Execution ---
async def main() -> None:
    runtime = CivilizationRuntime(
        agents=agents,
        max_iterations=30,
        evolution_enabled=False,
        verbose=False,
    )
    state = await runtime.run()

    print("\n--- Team Results ---")
    for agent in agents:
        m = state.metrics[agent.agent_id]
        explore_ratio = m.mab_explorations / max(m.total_actions, 1)
        print(
            f"{agent.agent_id:12s} | "
            f"avg_reward={m.avg_reward:.3f} | "
            f"actions={m.total_actions} | "
            f"explore_ratio={explore_ratio:.0%}"
        )


if __name__ == "__main__":
    asyncio.run(main())
