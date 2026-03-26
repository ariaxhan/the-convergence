"""
10 - Full Armature Loop

What this demonstrates:
- All components working together in a single flow
- Runtime MAB selecting a strategy
- Confidence extraction on the response
- Semantic cache reducing redundant work
- Knowledge graph tracking decisions
- Reward evaluation closing the learning loop

This is the "armature moment" -- every piece feeding into the next,
the system learning and improving with each cycle.

No API keys required. Pure local.
"""

import asyncio
import hashlib
import math
import random
from typing import Any, Dict, List

from armature import (
    RewardEvaluatorConfig,
    RewardMetricConfig,
    RuntimeRewardEvaluator,
    configure_runtime,
    runtime_select,
    runtime_update,
)
from armature.cache.semantic import SemanticCache
from armature.evaluators.confidence import extract_confidence
from armature.knowledge.graph import ContextGraph
from armature.knowledge.schema import (
    EntityType,
    GraphEdge,
    GraphNode,
    OntologyType,
)
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig

# ---------------------------------------------------------------------------
# Hash-based embedding for cache
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 64

def hash_embedding(text: str) -> List[float]:
    words = text.lower().strip().split()
    vector = [0.0] * EMBEDDING_DIM
    for word in words:
        digest = hashlib.sha256(word.encode()).digest()
        for i in range(EMBEDDING_DIM):
            vector[i] += digest[i % len(digest)] / 255.0
    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    return vector


# ---------------------------------------------------------------------------
# Simulated LLM response
# ---------------------------------------------------------------------------
def simulate_llm(query: str, params: Dict[str, Any]) -> str:
    """Simulate an LLM response with confidence language based on params."""
    tone = params.get("tone", "neutral")
    if tone == "confident":
        return f"I am absolutely certain: the answer to '{query}' is 42. Confidence: 92%"
    elif tone == "hedging":
        return f"I think maybe the answer to '{query}' might possibly be 42."
    else:
        return f"The answer to '{query}' is 42."


# --- Configuration ---
SYSTEM = "full_loop"
USER = "user_1"

runtime_config = RuntimeConfig(
    system=SYSTEM,
    default_arms=[
        RuntimeArmTemplate(
            arm_id="confident_tone",
            name="Confident Tone",
            params={"tone": "confident", "temperature": 0.3},
        ),
        RuntimeArmTemplate(
            arm_id="hedging_tone",
            name="Hedging Tone",
            params={"tone": "hedging", "temperature": 0.7},
        ),
    ],
)

reward_config = RewardEvaluatorConfig(
    metrics={
        "confidence": RewardMetricConfig(name="confidence", weight=0.4),
        "user_satisfaction": RewardMetricConfig(name="user_satisfaction", weight=0.6),
    }
)


# --- Execution ---
async def main() -> None:
    print("Full Armature Loop")
    print("=" * 60)
    print()

    # 1. Setup components
    storage = MemoryRuntimeStorage()
    await configure_runtime(SYSTEM, config=runtime_config, storage=storage)

    cache = SemanticCache(embedding_fn=hash_embedding, backend="memory", threshold=0.99)
    graph = ContextGraph()
    reward_evaluator = RuntimeRewardEvaluator(reward_config)

    queries = [
        "What is the meaning of life?",
        "What is the meaning of life?",  # Should cache hit
        "How does photosynthesis work?",
        "Explain quantum computing",
        "What is the meaning of existence?",  # Semantically similar to #1
    ]

    for i, query in enumerate(queries, 1):
        print(f"--- Round {i}: \"{query}\" ---")

        # 2. Check cache first
        cached = await cache.get(query)
        if cached:
            print(f"  [CACHE HIT] similarity={cached['similarity']:.3f}")
            print(f"  Content: {cached['content'][:60]}...")
            print()
            continue

        # 3. Runtime selects an arm (Thompson Sampling)
        selection = await runtime_select(SYSTEM, user_id=USER)
        print(f"  [RUNTIME]  arm={selection.arm_id} params={selection.params}")

        # 4. Generate response (simulated)
        response_text = simulate_llm(query, selection.params)
        print(f"  [RESPONSE] {response_text[:70]}...")

        # 5. Extract confidence
        confidence = extract_confidence(response_text)
        print(f"  [CONFIDENCE] {confidence}")

        # 6. Cache the response
        await cache.set(query, {"content": response_text, "confidence": confidence})

        # 7. Record in knowledge graph
        node_id = f"query_{i}"
        graph.add_node(GraphNode(
            id=node_id,
            ontology_type=OntologyType.WHAT,
            entity_type=EntityType.ARTIFACT,
            content=query,
            metadata={"arm": selection.arm_id, "confidence": confidence},
        ))
        if i > 1:
            graph.add_edge(GraphEdge(
                id=f"seq_{i}",
                source_id=f"query_{i - 1}",
                target_id=node_id,
                relationship_type="followed_by",
                weight=1.0,
            ))

        # 8. Evaluate composite reward
        user_satisfaction = random.uniform(0.5, 1.0)  # Simulated user signal
        signals = {
            "confidence": confidence if confidence is not None else 0.5,
            "user_satisfaction": user_satisfaction,
        }
        reward = reward_evaluator.evaluate(signals)
        print(f"  [REWARD]   {reward:.3f} (confidence={confidence}, satisfaction={user_satisfaction:.2f})")

        # 9. Update runtime with reward (closing the loop)
        if selection.decision_id:
            await runtime_update(
                SYSTEM,
                user_id=USER,
                decision_id=selection.decision_id,
                reward=reward,
            )
            print(f"  [LEARN]    Updated arm '{selection.arm_id}' with reward={reward:.3f}")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print(f"  Knowledge graph: {graph.node_count()} nodes, {graph.edge_count()} edges")
    print("  Cache entries stored: queries processed with deduplication")
    print()
    print("The loop: SELECT -> GENERATE -> EVALUATE -> CACHE -> LEARN -> REPEAT")
    print("Each cycle makes the next one better. That is armature.")


if __name__ == "__main__":
    asyncio.run(main())
