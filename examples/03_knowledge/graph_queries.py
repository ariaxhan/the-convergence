"""
Graph Queries

What this demonstrates:
- Building a larger graph with 12 nodes
- Querying by entity type (PERSON, ARTIFACT, CONCEPT)
- Content-based search with query_nodes
- BFS traversal with configurable depth

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Add metadata_filter to query_nodes to find nodes by role or version
- Try max_depth=3 traversal to see full reachability
"""

# --- Configuration ---
from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType

# --- Setup ---
graph = ContextGraph()

NODES = [
    GraphNode(id="alice", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Alice (Lead)", metadata={"role": "lead"}),
    GraphNode(id="bob", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Bob (Dev)", metadata={"role": "developer"}),
    GraphNode(id="carol", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Carol (QA)", metadata={"role": "qa"}),
    GraphNode(id="team", ontology_type=OntologyType.WHO, entity_type=EntityType.TEAM, content="Core Team"),
    GraphNode(id="api", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="REST API", metadata={"version": "2.1"}),
    GraphNode(id="db", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="PostgreSQL DB"),
    GraphNode(id="cache", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT, content="Redis Cache"),
    GraphNode(id="auth", ontology_type=OntologyType.WHAT, entity_type=EntityType.CONCEPT, content="Auth System"),
    GraphNode(id="microservices", ontology_type=OntologyType.WHAT, entity_type=EntityType.DECISION, content="Adopt Microservices"),
    GraphNode(id="ci_cd", ontology_type=OntologyType.HOW, entity_type=EntityType.PROCESS, content="CI/CD Pipeline"),
    GraphNode(id="tdd", ontology_type=OntologyType.HOW, entity_type=EntityType.METHOD, content="Test-Driven Development"),
    GraphNode(id="agile", ontology_type=OntologyType.HOW, entity_type=EntityType.WORKFLOW, content="Agile Sprints"),
]

EDGES = [
    GraphEdge(id="e1", source_id="alice", target_id="team", relationship_type="MEMBER_OF"),
    GraphEdge(id="e2", source_id="bob", target_id="team", relationship_type="MEMBER_OF"),
    GraphEdge(id="e3", source_id="carol", target_id="team", relationship_type="MEMBER_OF"),
    GraphEdge(id="e4", source_id="alice", target_id="api", relationship_type="OWNS"),
    GraphEdge(id="e5", source_id="bob", target_id="db", relationship_type="OWNS"),
    GraphEdge(id="e6", source_id="api", target_id="db", relationship_type="DEPENDS_ON"),
    GraphEdge(id="e7", source_id="api", target_id="cache", relationship_type="USES"),
    GraphEdge(id="e8", source_id="api", target_id="auth", relationship_type="USES"),
    GraphEdge(id="e9", source_id="team", target_id="agile", relationship_type="FOLLOWS"),
    GraphEdge(id="e10", source_id="carol", target_id="tdd", relationship_type="USES"),
    GraphEdge(id="e11", source_id="team", target_id="ci_cd", relationship_type="USES"),
]


# --- Execution ---
if __name__ == "__main__":
    for node in NODES:
        graph.add_node(node)
    for edge in EDGES:
        graph.add_edge(edge)

    print(f"Graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    # Query: Who are the people?
    people = graph.query_nodes(entity_type=EntityType.PERSON)
    print(f"People ({len(people)}):")
    for p in people:
        print(f"  {p.content} [{p.metadata.get('role', 'n/a')}]")

    # Query: What artifacts exist?
    artifacts = graph.query_nodes(entity_type=EntityType.ARTIFACT)
    print(f"\nArtifacts ({len(artifacts)}):")
    for a in artifacts:
        print(f"  {a.content}")

    # Query: Content search
    auth_nodes = graph.query_nodes(content_contains="Auth")
    print(f"\nNodes containing 'Auth': {[n.content for n in auth_nodes]}")

    # Query: Metadata filter
    leads = graph.query_nodes(metadata_filter={"role": "lead"})
    print(f"Leads: {[n.content for n in leads]}")

    # Traversal from API node
    print(f"\nTraversal from 'REST API' (depth=1):")
    reachable = graph.traverse("api", max_depth=1)
    for node in reachable:
        print(f"  [{node.entity_type.value}] {node.content}")

    # Deeper traversal
    print(f"\nTraversal from 'Alice' (depth=2):")
    reachable = graph.traverse("alice", max_depth=2)
    for node in reachable:
        print(f"  [{node.ontology_type.value}] {node.content}")
