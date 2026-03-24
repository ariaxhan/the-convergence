"""
Customer Support Bot -- Convergence end-to-end example.

What this demonstrates:
  - Thompson Sampling (Runtime MAB) to select the best response strategy
  - SemanticCache with a simple hash-based embedding for FAQ deduplication
  - Confidence extraction to flag uncertain responses for human review

Suggested prompts to explore after reading:
  - Change the reward profiles to make "technical" win instead of "casual"
  - Lower the confidence threshold from 0.5 to 0.3 and observe escalation count
  - Add a fourth arm (e.g. "empathetic") and re-run
"""
from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Dict, List

from convergence import (
    RuntimeArmTemplate,
    RuntimeConfig,
    configure_runtime,
    runtime_select,
    runtime_update,
)
from convergence.cache.semantic import SemanticCache
from convergence.evaluators.confidence import extract_confidence
from convergence.storage.memory import MemoryRuntimeStorage

SYSTEM, USER_ID = "support_bot", "demo_user"
QUERIES = [
    "How do I reset my password?", "My order hasn't arrived yet",
    "Can I get a refund?", "How does the API rate limit work?",
    "I'm getting error 503 on checkout", "What payment methods do you accept?",
    "How do I cancel my subscription?", "The app crashes on startup",
    "Do you ship internationally?", "How do I enable two-factor auth?",
]
# (mean, std) -- "casual" is intentionally best to show convergence
STRATEGY_REWARDS: Dict[str, tuple] = {
    "formal": (0.50, 0.15), "casual": (0.75, 0.10), "technical": (0.60, 0.12),
}
SIMULATED_RESPONSES: Dict[str, str] = {
    "formal": "Thank you for contacting us. Your request has been noted. Confidence: 72%",
    "casual": "Hey! Totally get it -- let me help you out right away. Confidence: 85%",
    "technical": "I think the issue might relate to the backend service. Perhaps check logs.",
}

def hash_embedding(text: str) -> List[float]:
    """Deterministic 32-dim embedding from SHA-256 for demo purposes."""
    return [b / 255.0 for b in hashlib.sha256(text.lower().encode()).digest()]

async def main() -> None:
    storage = MemoryRuntimeStorage()
    config = RuntimeConfig(system=SYSTEM, default_arms=[
        RuntimeArmTemplate(arm_id=k, name=k.title(), params={"tone": k})
        for k in STRATEGY_REWARDS
    ])
    await configure_runtime(SYSTEM, config=config, storage=storage)
    cache = SemanticCache(embedding_fn=hash_embedding, backend="memory", threshold=0.95)

    wins: Dict[str, int] = {k: 0 for k in STRATEGY_REWARDS}
    cache_hits, escalations, total = 0, 0, 30

    print(f"{'='*60}\n  Customer Support Bot -- Learning Loop\n{'='*60}\n")
    for i in range(total):
        query = random.choice(QUERIES)
        cached = await cache.get(query)
        if cached is not None:
            cache_hits += 1
            print(f"  [{i+1:02d}] CACHE HIT  | {query[:40]}")
            continue

        sel = await runtime_select(SYSTEM, user_id=USER_ID)
        strategy = sel.arm_id
        response_text = SIMULATED_RESPONSES[strategy]
        confidence = extract_confidence(response_text)
        escalated = confidence is not None and confidence < 0.5
        if escalated:
            escalations += 1

        mean, std = STRATEGY_REWARDS[strategy]
        reward = max(0.0, min(1.0, random.gauss(mean, std)))
        wins[strategy] += 1
        if sel.decision_id:
            await runtime_update(SYSTEM, user_id=USER_ID, decision_id=sel.decision_id, reward=reward)
        await cache.set(query, {"content": response_text, "strategy": strategy})
        flag = " ** ESCALATE **" if escalated else ""
        print(f"  [{i+1:02d}] {strategy:10s} | reward={reward:.2f} | conf={confidence or 0:.2f}{flag}")

    # -- Summary
    print(f"\n{'='*60}\n  Results\n{'='*60}")
    print(f"  Strategy selections: {wins}")
    print(f"  Cache hits: {cache_hits}/{total}  |  Escalations: {escalations}")
    arms = await storage.get_arms(user_id=USER_ID, agent_type="default")
    print("\n  Final arm estimates:")
    for arm in arms:
        m, p = arm.get("mean_estimate") or 0, arm.get("total_pulls", 0)
        print(f"    {arm.get('name', arm['arm_id']):12s} | pulls={p:3d} | mean={m:.3f} | {'#' * int(m * 30)}")
    print("\n  The bandit should converge toward 'Casual' (highest reward profile).\n")

if __name__ == "__main__":
    asyncio.run(main())
