"""
Research Assistant -- Convergence end-to-end example.

What this demonstrates:
  - Thompson Sampling (Runtime MAB) to select the best search strategy
  - ContextGraph to build and traverse a knowledge graph on the fly
  - GraphNode/GraphEdge with WHO/WHAT/HOW ontology categories

Suggested prompts to explore after reading:
  - Add more topics/researchers and observe richer graph connectivity
  - Change reward profiles so "deep_dive" wins and see how it converges
  - Use graph.extract_context() on a topic node to see surrounding knowledge
"""
from __future__ import annotations

import asyncio
import random
from typing import Dict, Tuple

from convergence import (
    RuntimeArmTemplate,
    RuntimeConfig,
    configure_runtime,
    runtime_select,
    runtime_update,
)
from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType
from convergence.storage.memory import MemoryRuntimeStorage

SYSTEM, USER_ID = "research_assistant", "researcher_1"
RESEARCHERS = ["Alice", "Bob", "Carol"]
TOPICS = [
    "transformer architectures", "reinforcement learning", "knowledge graphs",
    "multi-agent systems", "causal inference", "federated learning",
]
METHODS = ["survey", "experiment", "meta-analysis", "simulation"]
# (mean, std) -- "focused" is intentionally best
STRATEGY_REWARDS: Dict[str, Tuple[float, float]] = {
    "broad": (0.55, 0.15), "focused": (0.78, 0.10), "deep_dive": (0.62, 0.18),
}

def simulate_search(strategy: str, topic: str) -> Dict:
    mean, std = STRATEGY_REWARDS[strategy]
    quality = max(0.0, min(1.0, random.gauss(mean, std)))
    related = random.sample([t for t in TOPICS if t != topic], k=min(2, len(TOPICS) - 1))
    return {"quality": quality, "related": related, "method": random.choice(METHODS)}

async def main() -> None:
    storage = MemoryRuntimeStorage()
    config = RuntimeConfig(system=SYSTEM, default_arms=[
        RuntimeArmTemplate(arm_id=k, name=k.replace("_", " ").title(), params={"depth": k})
        for k in STRATEGY_REWARDS
    ])
    await configure_runtime(SYSTEM, config=config, storage=storage)

    graph = ContextGraph()
    for name in RESEARCHERS:
        graph.add_node(GraphNode(
            id=f"who_{name.lower()}", ontology_type=OntologyType.WHO,
            entity_type=EntityType.PERSON, content=name))
    for topic in TOPICS:
        graph.add_node(GraphNode(
            id=f"what_{topic.replace(' ', '_')}", ontology_type=OntologyType.WHAT,
            entity_type=EntityType.CONCEPT, content=topic))

    edge_n, picks = 0, {k: 0 for k in STRATEGY_REWARDS}
    print(f"{'='*60}\n  Research Assistant -- Knowledge Graph + MAB\n{'='*60}")
    print(f"  Initial graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    for i in range(20):
        topic = random.choice(TOPICS)
        researcher = random.choice(RESEARCHERS)
        sel = await runtime_select(SYSTEM, user_id=USER_ID)
        strategy = sel.arm_id
        picks[strategy] += 1
        result = simulate_search(strategy, topic)
        quality = float(result["quality"])
        if sel.decision_id:
            await runtime_update(SYSTEM, user_id=USER_ID, decision_id=sel.decision_id, reward=quality)

        tid = topic.replace(" ", "_")
        # researcher -> topic
        edge_n += 1
        graph.add_edge(GraphEdge(id=f"e_{edge_n}", source_id=f"who_{researcher.lower()}",
                                 target_id=f"what_{tid}", relationship_type="researches", weight=quality))
        # topic -> method (HOW)
        method_id = f"how_{result['method']}"
        if not graph.has_node(method_id):
            graph.add_node(GraphNode(id=method_id, ontology_type=OntologyType.HOW,
                                     entity_type=EntityType.METHOD, content=str(result["method"])))
        edge_n += 1
        graph.add_edge(GraphEdge(id=f"e_{edge_n}", source_id=f"what_{tid}",
                                 target_id=method_id, relationship_type="uses_method", weight=quality))
        # related topics
        for rel in result["related"]:
            edge_n += 1
            graph.add_edge(GraphEdge(id=f"e_{edge_n}", source_id=f"what_{tid}",
                                     target_id=f"what_{rel.replace(' ', '_')}", relationship_type="related_to"))

        print(f"  [{i+1:02d}] {strategy:10s} | topic={topic:28s} | q={quality:.2f} "
              f"| {graph.node_count()}N {graph.edge_count()}E")

    # -- Summary
    print(f"\n{'='*60}\n  Results\n{'='*60}")
    print(f"  Strategy picks: {picks}")
    print(f"  Final graph:    {graph.node_count()} nodes, {graph.edge_count()} edges")
    print("\n  Researcher connections:")
    for name in RESEARCHERS:
        topics = [n.content for n in graph.get_neighbors(f"who_{name.lower()}")]
        print(f"    {name}: {', '.join(topics[:5])}")
    arms = await storage.get_arms(user_id=USER_ID, agent_type="default")
    print("\n  Arm convergence:")
    for arm in arms:
        m, p = arm.get("mean_estimate") or 0, arm.get("total_pulls", 0)
        print(f"    {arm.get('name', arm['arm_id']):12s} | pulls={p:3d} | mean={m:.3f} | {'#' * int(m * 30)}")
    print("\n  The bandit should converge toward 'Focused' (highest quality profile).\n")

if __name__ == "__main__":
    asyncio.run(main())
