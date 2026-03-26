"""
Competitive Selection - Natural Selection Among Agents

What this demonstrates:
- 5 agents with varying exploration rates competing for survival
- Evolution events that rank agents by fitness
- How natural selection pressure favors better-adapted strategies

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- Change exploration rates to find the optimal range
- Set evolution_frequency=10 for more frequent selection events
- Add agents with extreme rates (0.0 or 1.0) to see them fail
"""

import asyncio
import random

from armature.core.runtime import CivilizationRuntime

# --- Configuration ---
EXPLORATION_RATES = [0.1, 0.3, 0.5, 0.7, 0.9]
STRATEGIES = ["exploit", "exploit", "explore", "explore", "explore"]


class CompetitiveAgent:
    """Agent whose strategy depends on its exploration rate."""

    def __init__(self, agent_id: str, explore_rate: float):
        self.agent_id = agent_id
        self.config = {"explore_rate": explore_rate}
        self.reward_history: list[float] = []

    async def act(self, state: dict) -> dict:
        task = state.get("task", {})
        exploring = random.random() < self.config["explore_rate"]
        strategy = "explore" if exploring else "exploit"
        thought = (
            f"Task difficulty={task.get('difficulty', '?')}. "
            f"My explore_rate={self.config['explore_rate']}. "
            f"Choosing to {strategy} based on probabilistic threshold."
        )
        return {"thought": thought, "strategy": strategy, "action": "compete"}

    async def learn(self, experience: dict) -> None:
        self.reward_history.append(experience.get("reward", 0.0))


# --- Setup ---
agents = [
    CompetitiveAgent(f"agent_{rate:.0%}", rate)
    for rate in EXPLORATION_RATES
]


# --- Execution ---
async def main() -> None:
    runtime = CivilizationRuntime(
        agents=agents,
        max_iterations=60,
        evolution_enabled=True,
        evolution_frequency=15,
        verbose=False,
    )
    state = await runtime.run()

    print("\n--- Fitness Rankings (Final) ---")
    ranked = sorted(
        state.metrics.values(), key=lambda m: m.fitness_score, reverse=True
    )
    for i, m in enumerate(ranked, 1):
        agent = next(a for a in agents if a.agent_id == m.agent_id)
        print(
            f"  {i}. {m.agent_id:10s} | "
            f"fitness={m.fitness_score:.3f} | "
            f"avg_reward={m.avg_reward:.3f} | "
            f"explore_rate={agent.config['explore_rate']:.0%}"
        )
    print(f"\nWinner: {ranked[0].agent_id} survived natural selection.")


if __name__ == "__main__":
    asyncio.run(main())
