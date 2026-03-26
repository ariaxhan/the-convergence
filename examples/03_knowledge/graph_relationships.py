"""
Graph Relationship Types

What this demonstrates:
- All relationship types: OWNS, USES, DEPENDS_ON, PRODUCES, CONSUMES
- Building a supply-chain-style graph with diverse edges
- Finding paths between nodes via traversal
- Analyzing dependency chains

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Add a BREAKS relationship type for failure analysis
- Add circular dependencies and observe traversal behavior
"""

# --- Configuration ---
from armature.knowledge.graph import ContextGraph
from armature.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType

RELATIONSHIP_TYPES = ["OWNS", "USES", "DEPENDS_ON", "PRODUCES", "CONSUMES"]

# --- Setup ---
graph = ContextGraph()

NODES = [
    GraphNode(id="team_a", ontology_type=OntologyType.WHO, entity_type=EntityType.TEAM, content="Data Team"),
    GraphNode(id="team_b", ontology_type=OntologyType.WHO, entity_type=EntityType.TEAM, content="ML Team"),
    GraphNode(id="pipeline", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="ETL Pipeline"),
    GraphNode(id="model", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="ML Model"),
    GraphNode(id="dataset", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="Training Dataset"),
    GraphNode(id="api", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="Prediction API"),
    GraphNode(id="spark", ontology_type=OntologyType.HOW, entity_type=EntityType.METHOD, content="Apache Spark"),
    GraphNode(id="pytorch", ontology_type=OntologyType.HOW, entity_type=EntityType.METHOD, content="PyTorch"),
]

EDGES = [
    GraphEdge(id="e1", source_id="team_a", target_id="pipeline", relationship_type="OWNS", weight=1.0),
    GraphEdge(id="e2", source_id="team_b", target_id="model", relationship_type="OWNS", weight=1.0),
    GraphEdge(id="e3", source_id="pipeline", target_id="spark", relationship_type="USES", weight=1.0),
    GraphEdge(id="e4", source_id="model", target_id="pytorch", relationship_type="USES", weight=1.0),
    GraphEdge(id="e5", source_id="model", target_id="dataset", relationship_type="DEPENDS_ON", weight=0.9),
    GraphEdge(id="e6", source_id="pipeline", target_id="dataset", relationship_type="PRODUCES", weight=1.0),
    GraphEdge(id="e7", source_id="api", target_id="model", relationship_type="CONSUMES", weight=0.8),
    GraphEdge(id="e8", source_id="api", target_id="dataset", relationship_type="DEPENDS_ON", weight=0.5),
]


def find_by_relationship(rel_type: str) -> list:
    """Find all edges of a given relationship type."""
    results = []
    for node_id in [n.id for n in NODES]:
        for edge in graph.get_outgoing_edges(node_id):
            if edge.relationship_type == rel_type:
                src = graph.get_node(edge.source_id)
                tgt = graph.get_node(edge.target_id)
                results.append((src.content, rel_type, tgt.content, edge.weight))
    return results


# --- Execution ---
if __name__ == "__main__":
    for node in NODES:
        graph.add_node(node)
    for edge in EDGES:
        graph.add_edge(edge)

    print(f"Graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    # Show all relationships grouped by type
    for rel_type in RELATIONSHIP_TYPES:
        edges = find_by_relationship(rel_type)
        print(f"{rel_type} ({len(edges)}):")
        for src, rel, tgt, weight in edges:
            print(f"  {src} --{rel}--> {tgt} (weight={weight})")
        if not edges:
            print("  (none)")
        print()

    # Dependency chain: What does the API depend on?
    print("Dependency chain from 'Prediction API':")
    visited = set()
    queue = ["api"]
    depth = 0
    while queue and depth < 3:
        next_queue = []
        for node_id in queue:
            if node_id in visited:
                continue
            visited.add(node_id)
            node = graph.get_node(node_id)
            indent = "  " * (depth + 1)
            if depth > 0:
                print(f"{indent}{node.content}")
            else:
                print(f"  {node.content}")
            for edge in graph.get_outgoing_edges(node_id):
                if edge.relationship_type in ("DEPENDS_ON", "CONSUMES"):
                    next_queue.append(edge.target_id)
        queue = next_queue
        depth += 1
