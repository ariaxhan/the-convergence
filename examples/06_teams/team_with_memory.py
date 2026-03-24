"""
Team with Memory - Agents Sharing a ContextGraph

What this demonstrates:
- Two agents sharing a ContextGraph for collective knowledge
- Agent 1 discovers facts and adds nodes to the graph
- Agent 2 queries the graph before deciding, improving over time
- Knowledge accumulation enabling better decisions

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Add a third agent that only reads but never writes
- Increase iterations to 40 and track graph density
- Add edge weights based on discovery confidence
"""

import asyncio
import random

from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType

# --- Configuration ---
DOMAINS = ["python", "rust", "typescript", "go"]
FACTS = {"python": "prototyping", "rust": "performance", "typescript": "web", "go": "concurrency"}
N = OntologyType.WHAT


class DiscoveryAgent:
    """Discovers facts and writes them to the shared graph."""
    def __init__(self, aid: str, g: ContextGraph):
        self.agent_id, self.config, self.g = aid, {"role": "discoverer"}, g

    async def act(self, state: dict) -> dict:
        d, i = random.choice(DOMAINS), state["iteration"]
        nid = f"fact_{d}_{i}"
        self.g.add_node(GraphNode(id=nid, ontology_type=N, entity_type=EntityType.CONCEPT,
                                  content=f"{d}: {FACTS[d]}", metadata={"domain": d}))
        if self.g.has_node(f"root_{d}"):
            self.g.add_edge(GraphEdge(id=f"e_{nid}", source_id=f"root_{d}",
                                      target_id=nid, relationship_type="has_fact"))
        return {"thought": f"Found {d}, {self.g.node_count()} nodes", "strategy": "explore",
                "action": f"added_{nid}"}

    async def learn(self, exp: dict) -> None: pass


class QueryAgent:
    """Reads the shared graph before deciding."""
    def __init__(self, aid: str, g: ContextGraph):
        self.agent_id, self.config, self.g = aid, {"role": "querier"}, g
        self.decisions: list[str] = []

    async def act(self, state: dict) -> dict:
        known = self.g.query_nodes(entity_type=EntityType.CONCEPT)
        d = random.choice(DOMAINS)
        rel = [n for n in known if n.metadata.get("domain") == d]
        dec = f"Informed on {d} ({len(rel)} facts)" if rel else f"Blind guess on {d}"
        self.decisions.append(dec)
        return {"thought": dec, "strategy": "exploit" if rel else "explore", "action": dec}

    async def learn(self, exp: dict) -> None: pass


# --- Execution ---
async def main() -> None:
    graph = ContextGraph()
    for d in DOMAINS:
        graph.add_node(GraphNode(id=f"root_{d}", ontology_type=N,
                                 entity_type=EntityType.ARTIFACT, content=f"{d} root"))
    disc, query = DiscoveryAgent("discoverer", graph), QueryAgent("querier", graph)

    print("--- Knowledge Accumulation ---")
    for i in range(1, 21):
        st = {"iteration": i, "task": {"type": "learning", "difficulty": 0.5}}
        await disc.act(st)
        r = await query.act(st)
        if i % 5 == 0:
            c = graph.query_nodes(entity_type=EntityType.CONCEPT)
            print(f"Iter {i:2d}: {graph.node_count()} nodes, {len(c)} concepts, "
                  f"{graph.edge_count()} edges | {r['action']}")

    informed = sum(1 for d in query.decisions if "Informed" in d)
    print(f"\nFinal: {graph.node_count()} nodes, {graph.edge_count()} edges")
    print(f"Informed: {informed}/{len(query.decisions)} ({informed/len(query.decisions):.0%})")


if __name__ == "__main__":
    asyncio.run(main())
