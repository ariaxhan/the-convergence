"""
Basic Context Graph

What this demonstrates:
- Building a WHO/WHAT/HOW graph for a software team
- Adding nodes with OntologyType and EntityType
- Adding directed edges with relationship_type
- Querying node counts by type

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Add a third team member who USES both Python and React
- Add a "DevOps" HOW node and connect it to both backend and frontend
"""

# --- Configuration ---
from armature.knowledge.graph import ContextGraph
from armature.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType

# --- Setup ---
graph = ContextGraph()

# WHO nodes: team members
PEOPLE = [
    GraphNode(id="alice", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON,
              content="Alice", metadata={"role": "backend engineer"}),
    GraphNode(id="bob", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON,
              content="Bob", metadata={"role": "frontend engineer"}),
]

# WHAT nodes: components
COMPONENTS = [
    GraphNode(id="backend", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT,
              content="Backend Service", metadata={"language": "python"}),
    GraphNode(id="frontend", ontology_type=OntologyType.WHAT, entity_type=EntityType.ARTIFACT,
              content="Frontend App", metadata={"framework": "react"}),
]

# HOW nodes: technologies
TECHNOLOGIES = [
    GraphNode(id="python", ontology_type=OntologyType.HOW, entity_type=EntityType.METHOD,
              content="Python", metadata={"version": "3.11"}),
    GraphNode(id="react", ontology_type=OntologyType.HOW, entity_type=EntityType.METHOD,
              content="React", metadata={"version": "18"}),
]

EDGES = [
    GraphEdge(id="e1", source_id="alice", target_id="backend", relationship_type="OWNS", weight=1.0),
    GraphEdge(id="e2", source_id="bob", target_id="frontend", relationship_type="OWNS", weight=1.0),
    GraphEdge(id="e3", source_id="backend", target_id="python", relationship_type="USES", weight=1.0),
    GraphEdge(id="e4", source_id="frontend", target_id="react", relationship_type="USES", weight=1.0),
]


# --- Execution ---
if __name__ == "__main__":
    for node in PEOPLE + COMPONENTS + TECHNOLOGIES:
        graph.add_node(node)
    for edge in EDGES:
        graph.add_edge(edge)

    print(f"Graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    # Count by ontology type
    for ont_type in OntologyType:
        nodes = graph.get_nodes_by_ontology(ont_type)
        labels = [n.content for n in nodes]
        print(f"  {ont_type.value.upper()} ({len(nodes)}): {', '.join(labels)}")

    # Show relationships
    print("\nRelationships:")
    for person in PEOPLE:
        neighbors = graph.get_neighbors(person.id)
        for neighbor in neighbors:
            edge = next(e for e in graph.get_outgoing_edges(person.id) if e.target_id == neighbor.id)
            print(f"  {person.content} --{edge.relationship_type}--> {neighbor.content}")

    # Traverse from Alice
    print("\nTraversal from Alice (depth=2):")
    reachable = graph.traverse("alice", max_depth=2)
    for node in reachable:
        print(f"  [{node.ontology_type.value}] {node.content}")
