"""
07 - Knowledge Graph (Context Graph)

What this demonstrates:
- Building a context graph with WHO/WHAT/HOW nodes
- Adding typed edges (relationships) between nodes
- Querying neighbors and traversing the graph
- Extracting context around a focal node

Suggested prompts to explore after running:
- Add more nodes and edges to model your own domain
- Use query_nodes() to filter by entity_type or metadata
- Try extract_context() with different max_depth values

No API keys required. Pure local.
"""

from armature.knowledge.graph import ContextGraph
from armature.knowledge.schema import (
    EntityType,
    GraphEdge,
    GraphNode,
    OntologyType,
)


# --- Build the Graph ---
def build_graph() -> ContextGraph:
    graph = ContextGraph()

    # WHO nodes
    graph.add_node(GraphNode(
        id="alice",
        ontology_type=OntologyType.WHO,
        entity_type=EntityType.PERSON,
        content="Alice - Lead Engineer",
        metadata={"role": "lead", "team": "platform"},
    ))
    graph.add_node(GraphNode(
        id="bob",
        ontology_type=OntologyType.WHO,
        entity_type=EntityType.PERSON,
        content="Bob - ML Engineer",
        metadata={"role": "engineer", "team": "ml"},
    ))
    graph.add_node(GraphNode(
        id="platform_team",
        ontology_type=OntologyType.WHO,
        entity_type=EntityType.TEAM,
        content="Platform Team",
        metadata={"size": 5},
    ))

    # WHAT nodes
    graph.add_node(GraphNode(
        id="mab_system",
        ontology_type=OntologyType.WHAT,
        entity_type=EntityType.ARTIFACT,
        content="Multi-Armed Bandit Selection System",
        metadata={"version": "2.0"},
    ))
    graph.add_node(GraphNode(
        id="deploy_decision",
        ontology_type=OntologyType.WHAT,
        entity_type=EntityType.DECISION,
        content="Decision to use Thompson Sampling over UCB",
        metadata={"date": "2026-01-15"},
    ))

    # HOW nodes
    graph.add_node(GraphNode(
        id="deploy_process",
        ontology_type=OntologyType.HOW,
        entity_type=EntityType.PROCESS,
        content="Blue-green deployment with canary rollout",
        metadata={"stages": 3},
    ))

    # Edges (relationships)
    graph.add_edge(GraphEdge(
        id="e1", source_id="alice", target_id="platform_team",
        relationship_type="leads", weight=1.0,
    ))
    graph.add_edge(GraphEdge(
        id="e2", source_id="alice", target_id="mab_system",
        relationship_type="owns", weight=1.0,
    ))
    graph.add_edge(GraphEdge(
        id="e3", source_id="bob", target_id="mab_system",
        relationship_type="contributes_to", weight=0.8,
    ))
    graph.add_edge(GraphEdge(
        id="e4", source_id="mab_system", target_id="deploy_decision",
        relationship_type="informed_by", weight=0.9,
    ))
    graph.add_edge(GraphEdge(
        id="e5", source_id="mab_system", target_id="deploy_process",
        relationship_type="deployed_via", weight=1.0,
    ))

    return graph


# --- Execution ---
def main() -> None:
    graph = build_graph()

    print("Knowledge Graph Demo")
    print("=" * 55)
    print()

    # Graph stats
    print(f"Nodes: {graph.node_count()}")
    print(f"Edges: {graph.edge_count()}")
    print()

    # Get neighbors of Alice
    print("Alice's neighbors (outgoing edges):")
    neighbors = graph.get_neighbors("alice")
    for node in neighbors:
        print(f"  -> {node.content} ({node.entity_type.value})")
    print()

    # Get neighbors of the MAB system
    print("MAB System's neighbors:")
    neighbors = graph.get_neighbors("mab_system")
    for node in neighbors:
        print(f"  -> {node.content} ({node.entity_type.value})")
    print()

    # Traverse from Alice (depth 2)
    print("Traversal from Alice (depth=2):")
    nodes = graph.traverse("alice", max_depth=2)
    for node in nodes:
        print(f"  [{node.ontology_type.value:4s}] {node.content}")
    print()

    # Query by entity type
    print("All PERSON nodes:")
    people = graph.query_nodes(entity_type=EntityType.PERSON)
    for person in people:
        print(f"  {person.content}")
    print()

    # Extract context
    print("Context around 'mab_system' (depth=1):")
    context = graph.extract_context("mab_system", max_depth=1)
    print(f"  Summary: {context['summary']}")
    print(f"  Related: {len(context['related_nodes'])} nodes")
    print(f"  Edges:   {len(context['edges'])} connections")


if __name__ == "__main__":
    main()
