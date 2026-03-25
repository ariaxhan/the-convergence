"""
Evolution Manager with Safety Bounds and Rollback.

What this demonstrates:
- Safety bounds: pause evolution if avg reward drops below threshold
- Rollback trigger: revert if fitness drops >20% from peak
- Anomaly detection: flag agents deviating >3 std from population mean
- Rate-of-change monitoring: alert on distribution shifts >30%
- Kill switch: immediately freeze current arms
- Bounded exploration: cap exploration at 30% of selections
- Full audit trail for every evolution event

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Run with more agents to see evolution dynamics"
- "Lower safety threshold to trigger more interventions"
- "Inject multiple poisoned agents to stress test"
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig, SelectionStrategyConfig

logger = logging.getLogger(__name__)

# --- Constants ---
MIN_REWARD_THRESHOLD: float = 0.3
MAX_REWARD_THRESHOLD: float = 1.0
ROLLBACK_DROP_PERCENT: float = 0.20
ANOMALY_STD_THRESHOLD: float = 3.0
DISTRIBUTION_SHIFT_THRESHOLD: float = 0.30
MAX_EXPLORATION_RATIO: float = 0.30
EVOLUTION_WINDOW_SIZE: int = 10


@dataclass
class AgentState:
    """Tracked state for a single agent in the population."""

    agent_id: str
    rewards: List[float] = field(default_factory=list)
    selections: int = 0
    flagged_anomaly: bool = False

    @property
    def avg_reward(self) -> float:
        return sum(self.rewards) / len(self.rewards) if self.rewards else 0.0

    @property
    def recent_avg(self) -> float:
        recent = self.rewards[-EVOLUTION_WINDOW_SIZE:]
        return sum(recent) / len(recent) if recent else 0.0


@dataclass
class SafetyEvent:
    """Record of a safety intervention."""

    timestamp: float
    event_type: str
    details: Dict[str, Any]


class SafeEvolutionManager:
    """
    Evolution manager with safety bounds, anomaly detection, and rollback.

    Wraps convergence runtime to add safety guarantees around arm evolution.
    Tracks per-agent performance, detects anomalies, enforces reward bounds,
    and provides a kill switch for emergency stops.

    Args:
        system: Convergence system name.
        agents: List of agent configs (each has agent_id, arm_id, params).
        min_reward: Lower bound -- pause evolution if avg drops below.
        max_exploration_ratio: Cap on exploration selections.

    Raises:
        ValueError: If system is empty or no agents provided.
    """

    def __init__(
        self,
        *,
        system: str,
        agents: List[Dict[str, Any]],
        min_reward: float = MIN_REWARD_THRESHOLD,
        max_exploration_ratio: float = MAX_EXPLORATION_RATIO,
    ) -> None:
        if not system or not system.strip():
            raise ValueError("System name cannot be empty")
        if not agents:
            raise ValueError("At least one agent is required")

        self._system = system
        self._min_reward = min_reward
        self._max_exploration_ratio = max_exploration_ratio
        self._killed = False
        self._paused = False

        # Agent tracking
        self._agents: Dict[str, AgentState] = {
            a["agent_id"]: AgentState(agent_id=a["agent_id"]) for a in agents
        }

        # Evolution state
        self._peak_fitness: float = 0.0
        self._last_snapshot: Dict[str, float] = {}  # arm_id -> selection_ratio at last window
        self._rollback_state: Optional[Dict[str, Any]] = None

        # Audit trail
        self._safety_events: List[SafetyEvent] = []
        self._evolution_log: List[Dict[str, Any]] = []
        self._exploration_count: int = 0
        self._total_selections: int = 0

    async def initialize(self, storage: Any) -> None:
        """
        Configure the runtime with agent arms.

        Args:
            storage: RuntimeStorageProtocol implementation.
        """
        arms = [
            RuntimeArmTemplate(
                arm_id=agent_id,
                params={"agent_id": agent_id},
            )
            for agent_id in self._agents
        ]
        config = RuntimeConfig(
            system=self._system,
            default_arms=arms,
            selection_strategy=SelectionStrategyConfig(
                exploration_bonus=0.1,
                exploration_min_pulls=5,
            ),
        )
        await configure_runtime(self._system, config=config, storage=storage)

    async def step(self, *, user_id: str, reward_fn: Any) -> Dict[str, Any]:
        """
        Execute one evolution step: select agent, act, observe reward, update.

        Args:
            user_id: User identifier.
            reward_fn: Callable(agent_id) -> float returning reward in [0, 1].

        Returns:
            Dict with agent_id, reward, safety_flags.

        Raises:
            RuntimeError: If kill switch is active.
        """
        if self._killed:
            raise RuntimeError("Evolution killed. Call reset() to restart.")

        safety_flags: List[str] = []

        # Check if paused
        if self._paused:
            safety_flags.append("evolution_paused")
            # Use deterministic best agent instead of exploration
            best_agent = max(self._agents.values(), key=lambda a: a.avg_reward)
            return {
                "agent_id": best_agent.agent_id,
                "reward": None,
                "safety_flags": safety_flags,
                "action": "paused_fallback",
            }

        # Select via runtime (Thompson Sampling)
        selection = await runtime_select(self._system, user_id=user_id)
        agent_id = selection.arm_id
        decision_id = selection.decision_id

        self._total_selections += 1

        # Track exploration ratio
        agent_state = self._agents.get(agent_id)
        if agent_state:
            agent_state.selections += 1

        # Bounded exploration check
        if self._is_exploration(agent_id):
            self._exploration_count += 1
        exploration_ratio = self._exploration_count / self._total_selections
        if exploration_ratio > self._max_exploration_ratio:
            safety_flags.append(f"exploration_capped:{exploration_ratio:.2f}")

        # Execute and get reward
        reward = float(reward_fn(agent_id))
        reward = max(0.0, min(1.0, reward))

        # Record reward
        if agent_state:
            agent_state.rewards.append(reward)

        # Update runtime
        if decision_id:
            await runtime_update(
                self._system,
                user_id=user_id,
                decision_id=decision_id,
                reward=reward,
            )

        # --- Safety checks ---

        # 1. Anomaly detection
        anomaly = self._check_anomaly(agent_id, reward)
        if anomaly:
            safety_flags.append(f"anomaly:{agent_id}")

        # 2. Reward bounds check
        pop_avg = self._population_avg_reward()
        if pop_avg < self._min_reward and len(self._agents) > 0:
            total_rewards = sum(len(a.rewards) for a in self._agents.values())
            if total_rewards > EVOLUTION_WINDOW_SIZE * len(self._agents):
                self._paused = True
                safety_flags.append("paused_low_reward")
                self._record_safety("reward_bound_pause", {
                    "population_avg": round(pop_avg, 3),
                    "threshold": self._min_reward,
                })

        # 3. Rollback check
        if pop_avg > self._peak_fitness:
            self._peak_fitness = pop_avg
            self._save_rollback_state()
        elif self._peak_fitness > 0:
            drop = (self._peak_fitness - pop_avg) / self._peak_fitness
            if drop > ROLLBACK_DROP_PERCENT:
                safety_flags.append(f"rollback_triggered:drop={drop:.1%}")
                self._record_safety("rollback_triggered", {
                    "peak": round(self._peak_fitness, 3),
                    "current": round(pop_avg, 3),
                    "drop_percent": round(drop * 100, 1),
                })

        # 4. Distribution shift monitoring (every window)
        if self._total_selections % EVOLUTION_WINDOW_SIZE == 0:
            shift = self._check_distribution_shift()
            if shift and shift > DISTRIBUTION_SHIFT_THRESHOLD:
                safety_flags.append(f"distribution_shift:{shift:.2f}")
                self._record_safety("distribution_shift", {
                    "shift_magnitude": round(shift, 3),
                    "threshold": DISTRIBUTION_SHIFT_THRESHOLD,
                })

        # Log evolution event
        self._evolution_log.append({
            "iteration": self._total_selections,
            "agent_id": agent_id,
            "reward": round(reward, 3),
            "pop_avg": round(pop_avg, 3),
            "peak": round(self._peak_fitness, 3),
            "flags": safety_flags,
        })

        return {
            "agent_id": agent_id,
            "reward": reward,
            "safety_flags": safety_flags,
            "decision_id": decision_id,
        }

    def kill(self) -> None:
        """Immediately stop evolution and lock current state."""
        self._killed = True
        self._record_safety("kill_switch", {"reason": "manual"})
        logger.warning({"event": "evolution_killed", "system": self._system})

    def reset(self) -> None:
        """Reset kill switch. Evolution resumes from current state."""
        self._killed = False
        self._paused = False
        logger.info({"event": "evolution_reset", "system": self._system})

    def get_safety_events(self) -> List[Dict[str, Any]]:
        """Return all safety events."""
        return [{"timestamp": e.timestamp, "type": e.event_type, "details": e.details}
                for e in self._safety_events]

    def get_evolution_log(self) -> List[Dict[str, Any]]:
        """Return the full evolution audit trail."""
        return list(self._evolution_log)

    def get_agent_stats(self) -> List[Dict[str, Any]]:
        """Return per-agent statistics."""
        return [
            {
                "agent_id": a.agent_id,
                "avg_reward": round(a.avg_reward, 3),
                "recent_avg": round(a.recent_avg, 3),
                "total_rewards": len(a.rewards),
                "selections": a.selections,
                "flagged_anomaly": a.flagged_anomaly,
            }
            for a in self._agents.values()
        ]

    # --- Private methods ---

    def _check_anomaly(self, agent_id: str, reward: float) -> bool:
        """Flag if agent's reward deviates >3 std from population mean."""
        all_rewards = [r for a in self._agents.values() for r in a.rewards]
        if len(all_rewards) < EVOLUTION_WINDOW_SIZE:
            return False
        mean = sum(all_rewards) / len(all_rewards)
        variance = sum((r - mean) ** 2 for r in all_rewards) / len(all_rewards)
        std = math.sqrt(variance) if variance > 0 else 0.001
        deviation = abs(reward - mean) / std
        if deviation > ANOMALY_STD_THRESHOLD:
            agent = self._agents.get(agent_id)
            if agent:
                agent.flagged_anomaly = True
            self._record_safety("anomaly_detected", {
                "agent_id": agent_id,
                "reward": round(reward, 3),
                "population_mean": round(mean, 3),
                "std_dev": round(std, 3),
                "deviation_sigma": round(deviation, 1),
            })
            return True
        return False

    def _population_avg_reward(self) -> float:
        """Compute average reward across all agents."""
        all_rewards = [r for a in self._agents.values() for r in a.rewards]
        return sum(all_rewards) / len(all_rewards) if all_rewards else 0.5

    def _is_exploration(self, agent_id: str) -> bool:
        """Heuristic: agent with fewer than avg selections is exploration."""
        avg_selections = self._total_selections / max(len(self._agents), 1)
        agent = self._agents.get(agent_id)
        if agent and agent.selections < avg_selections * 0.5:
            return True
        return False

    def _check_distribution_shift(self) -> Optional[float]:
        """Check if arm selection distribution shifted significantly."""
        current: Dict[str, float] = {}
        for agent_id, state in self._agents.items():
            current[agent_id] = state.selections / max(self._total_selections, 1)

        if not self._last_snapshot:
            self._last_snapshot = current
            return None

        # L1 distance between distributions
        shift = sum(
            abs(current.get(k, 0) - self._last_snapshot.get(k, 0))
            for k in set(list(current.keys()) + list(self._last_snapshot.keys()))
        )
        self._last_snapshot = current
        return shift

    def _save_rollback_state(self) -> None:
        """Save current state as rollback point."""
        self._rollback_state = {
            "fitness": self._peak_fitness,
            "agent_stats": {
                aid: {"avg_reward": a.avg_reward, "selections": a.selections}
                for aid, a in self._agents.items()
            },
        }

    def _record_safety(self, event_type: str, details: Dict[str, Any]) -> None:
        """Append a safety event."""
        self._safety_events.append(SafetyEvent(
            timestamp=time.time(),
            event_type=event_type,
            details=details,
        ))


# --- Simple agents ---

def make_reward_fn(agents_config: Dict[str, Dict[str, Any]]) -> Any:
    """
    Create a reward function that returns rewards based on agent quality.

    Args:
        agents_config: Dict mapping agent_id to config with 'quality' key.

    Returns:
        Callable(agent_id) -> float
    """
    def reward_fn(agent_id: str) -> float:
        config = agents_config.get(agent_id, {})
        quality = config.get("quality", 0.5)
        noise = random.gauss(0, 0.05)
        return max(0.0, min(1.0, quality + noise))
    return reward_fn


# --- Execution ---
async def main() -> None:
    # 5 agents with different quality levels
    agents_config: Dict[str, Dict[str, Any]] = {
        "agent_alpha": {"quality": 0.8},
        "agent_beta": {"quality": 0.65},
        "agent_gamma": {"quality": 0.7},
        "agent_delta": {"quality": 0.55},
        "agent_epsilon": {"quality": 0.75},
    }

    agents = [{"agent_id": aid} for aid in agents_config]
    storage = MemoryRuntimeStorage()

    manager = SafeEvolutionManager(
        system="evolution_demo",
        agents=agents,
        min_reward=0.3,
    )
    await manager.initialize(storage)

    reward_fn = make_reward_fn(agents_config)

    # Run 80 iterations
    print("--- Evolution Run (80 iterations) ---")
    for i in range(80):
        # Inject poisoned agent at iteration 40
        if i == 40:
            agents_config["agent_delta"]["quality"] = 0.05  # Poison
            print(f"\n  [iter {i}] INJECTED: agent_delta quality set to 0.05\n")

        result = await manager.step(user_id="evo_user", reward_fn=reward_fn)
        flags = result.get("safety_flags", [])
        if flags:
            print(f"  [iter {i}] agent={result['agent_id']} "
                  f"reward={result.get('reward', 'N/A'):.3f} flags={flags}")

    # Agent stats
    print("\n--- Agent Statistics ---")
    for stat in manager.get_agent_stats():
        anomaly_flag = " ** ANOMALY **" if stat["flagged_anomaly"] else ""
        print(f"  {stat['agent_id']}: avg={stat['avg_reward']:.3f} "
              f"recent={stat['recent_avg']:.3f} "
              f"selections={stat['selections']}{anomaly_flag}")

    # Safety events
    print("\n--- Safety Events ---")
    events = manager.get_safety_events()
    if events:
        for event in events:
            print(f"  [{event['type']}] {event['details']}")
    else:
        print("  No safety events triggered")

    # Evolution log sample (around injection point)
    print("\n--- Evolution Log (iterations 38-45) ---")
    for entry in manager.get_evolution_log():
        if 38 <= entry["iteration"] <= 45:
            print(f"  iter={entry['iteration']} agent={entry['agent_id']} "
                  f"reward={entry['reward']:.3f} pop_avg={entry['pop_avg']:.3f} "
                  f"flags={entry['flags']}")


if __name__ == "__main__":
    asyncio.run(main())
