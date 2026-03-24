"""
Graph Patterns: System Architecture

What this demonstrates:
- Modeling a real system architecture as a context graph
- Finding all services that DEPEND_ON a database
- Tracing what a service PRODUCES and who CONSUMES it
- Extracting architectural insights from graph queries

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Add a "monitoring" service that CONSUMES events from all services
- Find single points of failure (nodes with high in-degree)
"""

# --- Configuration ---
from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.schema import EntityType, GraphEdge, GraphNode, OntologyType

# --- Setup ---
graph = ContextGraph()

# Services (WHAT/ARTIFACT)
SERVICES = [
    ("user_svc", "User Service"), ("order_svc", "Order Service"),
    ("payment_svc", "Payment Service"), ("notify_svc", "Notification Service"),
    ("analytics_svc", "Analytics Service"),
]
# Infrastructure (WHAT/ARTIFACT)
INFRA = [
    ("postgres", "PostgreSQL"), ("redis", "Redis"),
    ("kafka", "Kafka"), ("s3", "S3 Bucket"),
]
# Events (WHAT/CONCEPT)
EVENTS = [
    ("order_event", "OrderCreated Event"), ("payment_event", "PaymentProcessed Event"),
]

EDGES_DATA = [
    ("user_svc", "postgres", "DEPENDS_ON"), ("order_svc", "postgres", "DEPENDS_ON"),
    ("payment_svc", "postgres", "DEPENDS_ON"), ("order_svc", "redis", "USES"),
    ("user_svc", "redis", "USES"), ("order_svc", "kafka", "PRODUCES"),
    ("payment_svc", "kafka", "PRODUCES"), ("notify_svc", "kafka", "CONSUMES"),
    ("analytics_svc", "kafka", "CONSUMES"), ("analytics_svc", "s3", "PRODUCES"),
    ("order_svc", "order_event", "PRODUCES"), ("payment_svc", "payment_event", "PRODUCES"),
    ("notify_svc", "order_event", "CONSUMES"), ("analytics_svc", "payment_event", "CONSUMES"),
]


def build_graph() -> None:
    """Build the architecture graph."""
    for sid, label in SERVICES:
        graph.add_node(GraphNode(id=sid, ontology_type=OntologyType.WHAT,
                                 entity_type=EntityType.ARTIFACT, content=label,
                                 metadata={"kind": "service"}))
    for iid, label in INFRA:
        graph.add_node(GraphNode(id=iid, ontology_type=OntologyType.WHAT,
                                 entity_type=EntityType.ARTIFACT, content=label,
                                 metadata={"kind": "infrastructure"}))
    for eid, label in EVENTS:
        graph.add_node(GraphNode(id=eid, ontology_type=OntologyType.WHAT,
                                 entity_type=EntityType.CONCEPT, content=label,
                                 metadata={"kind": "event"}))
    for i, (src, tgt, rel) in enumerate(EDGES_DATA):
        graph.add_edge(GraphEdge(id=f"e{i}", source_id=src, target_id=tgt,
                                 relationship_type=rel, weight=1.0))


# --- Execution ---
if __name__ == "__main__":
    build_graph()
    print(f"Architecture Graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    # Q1: What services depend on PostgreSQL?
    pg_dependents = []
    for edge in graph.get_incoming_edges("postgres"):
        if edge.relationship_type == "DEPENDS_ON":
            pg_dependents.append(graph.get_node(edge.source_id).content)
    print(f"Services depending on PostgreSQL ({len(pg_dependents)}):")
    for svc in pg_dependents:
        print(f"  {svc}")

    # Q2: What does Order Service produce and who consumes it?
    print("\nOrder Service produces:")
    for edge in graph.get_outgoing_edges("order_svc"):
        if edge.relationship_type == "PRODUCES":
            target = graph.get_node(edge.target_id)
            consumers = []
            for in_edge in graph.get_incoming_edges(edge.target_id):
                if in_edge.relationship_type == "CONSUMES":
                    consumers.append(graph.get_node(in_edge.source_id).content)
            print(f"  {target.content} -> consumed by: {', '.join(consumers) or 'nobody'}")

    # Q3: Single points of failure (high in-degree infrastructure)
    print("\nInfrastructure dependency counts:")
    for iid, label in INFRA:
        in_edges = graph.get_incoming_edges(iid)
        dep_count = len([e for e in in_edges if e.relationship_type in ("DEPENDS_ON", "USES")])
        risk = "HIGH RISK" if dep_count >= 3 else "ok"
        print(f"  {label}: {dep_count} dependents [{risk}]")

    # Q4: Context extraction around a focal service
    print("\nContext around 'Order Service' (depth=1):")
    context = graph.extract_context("order_svc", max_depth=1)
    print(f"  {context['summary']}")
    for n in context["related_nodes"]:
        print(f"    [{n['entity_type']}] {n['content']}")
