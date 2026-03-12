"""
Tests for Context Graph — the KNOWLEDGE layer.

Tests node/edge operations, traversal, and persistence.
Uses real databases (SQLite, Memory) — no mocks.
"""

import pytest

from convergence.knowledge.schema import (
    GraphNode,
    GraphEdge,
    OntologyType,
    EntityType,
)
from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.storage import GraphStorage


# =============================================================================
# SCHEMA TESTS
# =============================================================================


class TestGraphSchema:
    """Test Pydantic models for nodes and edges."""

    def test_create_node_who(self):
        """Should create WHO ontology node."""
        node = GraphNode(
            id="person-1",
            ontology_type=OntologyType.WHO,
            entity_type=EntityType.PERSON,
            content="Alice Smith",
            metadata={"role": "engineer"},
        )

        assert node.id == "person-1"
        assert node.ontology_type == OntologyType.WHO
        assert node.entity_type == EntityType.PERSON
        assert node.content == "Alice Smith"
        assert node.metadata["role"] == "engineer"

    def test_create_node_what(self):
        """Should create WHAT ontology node."""
        node = GraphNode(
            id="decision-1",
            ontology_type=OntologyType.WHAT,
            entity_type=EntityType.DECISION,
            content="Use Thompson Sampling for MAB",
        )

        assert node.ontology_type == OntologyType.WHAT
        assert node.entity_type == EntityType.DECISION

    def test_create_node_how(self):
        """Should create HOW ontology node."""
        node = GraphNode(
            id="process-1",
            ontology_type=OntologyType.HOW,
            entity_type=EntityType.PROCESS,
            content="Daily standup meeting",
        )

        assert node.ontology_type == OntologyType.HOW
        assert node.entity_type == EntityType.PROCESS

    def test_create_edge(self):
        """Should create edge between nodes."""
        edge = GraphEdge(
            id="edge-1",
            source_id="person-1",
            target_id="decision-1",
            relationship_type="made",
            weight=1.0,
        )

        assert edge.source_id == "person-1"
        assert edge.target_id == "decision-1"
        assert edge.relationship_type == "made"
        assert edge.weight == 1.0

    def test_node_serialization(self):
        """Node should be JSON serializable."""
        node = GraphNode(
            id="test-1",
            ontology_type=OntologyType.WHO,
            entity_type=EntityType.TEAM,
            content="Engineering Team",
        )

        data = node.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "test-1"

    def test_edge_serialization(self):
        """Edge should be JSON serializable."""
        edge = GraphEdge(
            id="edge-1",
            source_id="a",
            target_id="b",
            relationship_type="connects",
        )

        data = edge.model_dump()
        assert isinstance(data, dict)


# =============================================================================
# CONTEXT GRAPH OPERATIONS TESTS
# =============================================================================


class TestContextGraphOperations:
    """Test in-memory graph operations."""

    @pytest.fixture
    def graph(self):
        """Create empty context graph."""
        return ContextGraph()

    def test_add_node(self, graph):
        """Should add node to graph."""
        node = GraphNode(
            id="node-1",
            ontology_type=OntologyType.WHO,
            entity_type=EntityType.PERSON,
            content="Test Person",
        )

        graph.add_node(node)

        assert graph.has_node("node-1")
        assert graph.get_node("node-1") == node

    def test_add_multiple_nodes(self, graph):
        """Should add multiple nodes."""
        for i in range(5):
            node = GraphNode(
                id=f"node-{i}",
                ontology_type=OntologyType.WHAT,
                entity_type=EntityType.CONCEPT,
                content=f"Concept {i}",
            )
            graph.add_node(node)

        assert graph.node_count() == 5

    def test_add_edge(self, graph):
        """Should add edge between nodes."""
        # Add nodes first
        graph.add_node(GraphNode(
            id="a",
            ontology_type=OntologyType.WHO,
            entity_type=EntityType.PERSON,
            content="Person A",
        ))
        graph.add_node(GraphNode(
            id="b",
            ontology_type=OntologyType.WHAT,
            entity_type=EntityType.DECISION,
            content="Decision B",
        ))

        # Add edge
        edge = GraphEdge(
            id="edge-ab",
            source_id="a",
            target_id="b",
            relationship_type="made",
        )
        graph.add_edge(edge)

        assert graph.has_edge("edge-ab")
        assert graph.edge_count() == 1

    def test_get_node_not_found(self, graph):
        """Should raise KeyError for missing node."""
        with pytest.raises(KeyError):
            graph.get_node("nonexistent")

    def test_remove_node(self, graph):
        """Should remove node from graph."""
        node = GraphNode(
            id="to-remove",
            ontology_type=OntologyType.HOW,
            entity_type=EntityType.PROCESS,
            content="To be removed",
        )
        graph.add_node(node)
        assert graph.has_node("to-remove")

        graph.remove_node("to-remove")

        assert not graph.has_node("to-remove")

    def test_remove_node_removes_edges(self, graph):
        """Removing node should remove connected edges."""
        # Setup: A -> B -> C
        graph.add_node(GraphNode(id="a", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="A"))
        graph.add_node(GraphNode(id="b", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="B"))
        graph.add_node(GraphNode(id="c", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="C"))

        graph.add_edge(GraphEdge(id="e1", source_id="a", target_id="b", relationship_type="knows"))
        graph.add_edge(GraphEdge(id="e2", source_id="b", target_id="c", relationship_type="knows"))

        # Remove B
        graph.remove_node("b")

        # Both edges should be gone
        assert not graph.has_edge("e1")
        assert not graph.has_edge("e2")


# =============================================================================
# TRAVERSAL TESTS
# =============================================================================


class TestContextGraphTraversal:
    """Test graph traversal operations."""

    @pytest.fixture
    def populated_graph(self):
        """Create graph with test data."""
        graph = ContextGraph()

        # People (WHO)
        graph.add_node(GraphNode(id="alice", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Alice"))
        graph.add_node(GraphNode(id="bob", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Bob"))
        graph.add_node(GraphNode(id="charlie", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Charlie"))

        # Decisions (WHAT)
        graph.add_node(GraphNode(id="dec1", ontology_type=OntologyType.WHAT, entity_type=EntityType.DECISION, content="Use Python"))
        graph.add_node(GraphNode(id="dec2", ontology_type=OntologyType.WHAT, entity_type=EntityType.DECISION, content="Use PostgreSQL"))

        # Processes (HOW)
        graph.add_node(GraphNode(id="proc1", ontology_type=OntologyType.HOW, entity_type=EntityType.PROCESS, content="Code Review"))

        # Edges
        graph.add_edge(GraphEdge(id="e1", source_id="alice", target_id="dec1", relationship_type="made"))
        graph.add_edge(GraphEdge(id="e2", source_id="bob", target_id="dec1", relationship_type="approved"))
        graph.add_edge(GraphEdge(id="e3", source_id="alice", target_id="dec2", relationship_type="made"))
        graph.add_edge(GraphEdge(id="e4", source_id="charlie", target_id="proc1", relationship_type="owns"))
        graph.add_edge(GraphEdge(id="e5", source_id="dec1", target_id="proc1", relationship_type="requires"))

        return graph

    def test_get_neighbors(self, populated_graph):
        """Should get adjacent nodes."""
        neighbors = populated_graph.get_neighbors("alice")

        neighbor_ids = [n.id for n in neighbors]
        assert "dec1" in neighbor_ids
        assert "dec2" in neighbor_ids
        assert len(neighbors) == 2

    def test_get_neighbors_by_relationship(self, populated_graph):
        """Should filter neighbors by relationship type."""
        neighbors = populated_graph.get_neighbors("alice", relationship_type="made")

        neighbor_ids = [n.id for n in neighbors]
        assert "dec1" in neighbor_ids
        assert "dec2" in neighbor_ids

    def test_get_incoming_edges(self, populated_graph):
        """Should get edges pointing to node."""
        edges = populated_graph.get_incoming_edges("dec1")

        assert len(edges) == 2
        source_ids = [e.source_id for e in edges]
        assert "alice" in source_ids
        assert "bob" in source_ids

    def test_get_outgoing_edges(self, populated_graph):
        """Should get edges from node."""
        edges = populated_graph.get_outgoing_edges("alice")

        assert len(edges) == 2
        target_ids = [e.target_id for e in edges]
        assert "dec1" in target_ids
        assert "dec2" in target_ids

    def test_traverse_depth_1(self, populated_graph):
        """Should traverse to depth 1."""
        nodes = populated_graph.traverse("alice", max_depth=1)

        node_ids = [n.id for n in nodes]
        assert "alice" in node_ids  # Start node
        assert "dec1" in node_ids
        assert "dec2" in node_ids
        assert "proc1" not in node_ids  # Depth 2

    def test_traverse_depth_2(self, populated_graph):
        """Should traverse to depth 2."""
        nodes = populated_graph.traverse("alice", max_depth=2)

        node_ids = [n.id for n in nodes]
        assert "alice" in node_ids
        assert "dec1" in node_ids
        assert "proc1" in node_ids  # Now included

    def test_filter_by_ontology_type(self, populated_graph):
        """Should filter nodes by ontology type."""
        who_nodes = populated_graph.get_nodes_by_ontology(OntologyType.WHO)

        assert len(who_nodes) == 3
        assert all(n.ontology_type == OntologyType.WHO for n in who_nodes)


# =============================================================================
# EXTRACT CONTEXT TESTS
# =============================================================================


class TestExtractContext:
    """Test context extraction for agent consumption."""

    @pytest.fixture
    def populated_graph(self):
        """Create graph with test data."""
        graph = ContextGraph()

        graph.add_node(GraphNode(id="project", ontology_type=OntologyType.WHAT, entity_type=EntityType.CONCEPT, content="The Convergence"))
        graph.add_node(GraphNode(id="goal", ontology_type=OntologyType.WHAT, entity_type=EntityType.DECISION, content="Build self-evolving agents"))
        graph.add_node(GraphNode(id="alice", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Alice (Lead)"))
        graph.add_node(GraphNode(id="mab", ontology_type=OntologyType.HOW, entity_type=EntityType.PROCESS, content="Multi-Armed Bandit"))

        graph.add_edge(GraphEdge(id="e1", source_id="project", target_id="goal", relationship_type="has_goal"))
        graph.add_edge(GraphEdge(id="e2", source_id="alice", target_id="project", relationship_type="leads"))
        graph.add_edge(GraphEdge(id="e3", source_id="project", target_id="mab", relationship_type="uses"))

        return graph

    def test_extract_context_returns_dict(self, populated_graph):
        """Context extraction should return structured dict."""
        context = populated_graph.extract_context("project", max_depth=2)

        assert isinstance(context, dict)
        assert "focal_node" in context
        assert "related_nodes" in context
        assert "edges" in context

    def test_extract_context_includes_relationships(self, populated_graph):
        """Context should include relationship information."""
        context = populated_graph.extract_context("project", max_depth=1)

        # Should have edges from project
        assert len(context["edges"]) >= 2

    def test_extract_context_for_agent(self, populated_graph):
        """Context should be usable by agent."""
        context = populated_graph.extract_context("project", max_depth=2)

        # Should have human-readable summary
        assert "summary" in context or "focal_node" in context

        # Related nodes should have content
        for node in context["related_nodes"]:
            assert "content" in node or hasattr(node, "content")


# =============================================================================
# PERSISTENCE TESTS — SQLITE
# =============================================================================


class TestGraphStorageSQLite:
    """Test graph persistence with SQLite."""

    @pytest.fixture
    async def storage(self, tmp_path):
        """Create SQLite graph storage."""
        db_path = tmp_path / "test_graph.db"
        storage = GraphStorage(db_path=str(db_path), backend="sqlite")
        await storage.connect()
        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_load_node(self, storage):
        """Should persist node to SQLite."""
        node = GraphNode(
            id="persist-1",
            ontology_type=OntologyType.WHO,
            entity_type=EntityType.PERSON,
            content="Persisted Person",
            metadata={"test": True},
        )

        await storage.save_node(node)
        loaded = await storage.load_node("persist-1")

        assert loaded.id == node.id
        assert loaded.content == node.content
        assert loaded.metadata["test"] is True

    @pytest.mark.asyncio
    async def test_save_and_load_edge(self, storage):
        """Should persist edge to SQLite."""
        # Create nodes first
        await storage.save_node(GraphNode(id="a", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="A"))
        await storage.save_node(GraphNode(id="b", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="B"))

        edge = GraphEdge(
            id="edge-persist",
            source_id="a",
            target_id="b",
            relationship_type="knows",
            weight=0.8,
        )

        await storage.save_edge(edge)
        loaded = await storage.load_edge("edge-persist")

        assert loaded.id == edge.id
        assert loaded.source_id == "a"
        assert loaded.target_id == "b"
        assert loaded.weight == 0.8

    @pytest.mark.asyncio
    async def test_load_full_graph(self, storage):
        """Should load entire graph from storage."""
        # Save multiple nodes and edges
        await storage.save_node(GraphNode(id="n1", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="N1"))
        await storage.save_node(GraphNode(id="n2", ontology_type=OntologyType.WHAT, entity_type=EntityType.DECISION, content="N2"))
        await storage.save_node(GraphNode(id="n3", ontology_type=OntologyType.HOW, entity_type=EntityType.PROCESS, content="N3"))
        await storage.save_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relationship_type="r1"))
        await storage.save_edge(GraphEdge(id="e2", source_id="n2", target_id="n3", relationship_type="r2"))

        graph = await storage.load_graph()

        assert graph.node_count() == 3
        assert graph.edge_count() == 2

    @pytest.mark.asyncio
    async def test_save_full_graph(self, storage):
        """Should save entire graph to storage."""
        graph = ContextGraph()
        graph.add_node(GraphNode(id="x", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="X"))
        graph.add_node(GraphNode(id="y", ontology_type=OntologyType.WHAT, entity_type=EntityType.CONCEPT, content="Y"))
        graph.add_edge(GraphEdge(id="xy", source_id="x", target_id="y", relationship_type="related"))

        await storage.save_graph(graph)

        # Load into new graph
        loaded = await storage.load_graph()

        assert loaded.node_count() == 2
        assert loaded.edge_count() == 1

    @pytest.mark.asyncio
    async def test_graph_survives_reconnect(self, tmp_path):
        """Graph should survive storage reconnection."""
        db_path = tmp_path / "test_reconnect.db"

        # First session
        storage1 = GraphStorage(db_path=str(db_path), backend="sqlite")
        await storage1.connect()
        await storage1.save_node(GraphNode(id="survive", ontology_type=OntologyType.WHO, entity_type=EntityType.PERSON, content="Survivor"))
        await storage1.close()

        # Second session
        storage2 = GraphStorage(db_path=str(db_path), backend="sqlite")
        await storage2.connect()
        loaded = await storage2.load_node("survive")
        await storage2.close()

        assert loaded.id == "survive"
        assert loaded.content == "Survivor"


# =============================================================================
# QUERY TESTS
# =============================================================================


class TestGraphQueries:
    """Test graph query operations."""

    @pytest.fixture
    def populated_graph(self):
        """Create graph with diverse data."""
        graph = ContextGraph()

        # Multiple WHO nodes
        for i in range(5):
            graph.add_node(GraphNode(
                id=f"person-{i}",
                ontology_type=OntologyType.WHO,
                entity_type=EntityType.PERSON,
                content=f"Person {i}",
                metadata={"index": i},
            ))

        # Multiple WHAT nodes
        for i in range(3):
            graph.add_node(GraphNode(
                id=f"decision-{i}",
                ontology_type=OntologyType.WHAT,
                entity_type=EntityType.DECISION,
                content=f"Decision {i}",
            ))

        return graph

    def test_query_by_entity_type(self, populated_graph):
        """Should query nodes by entity type."""
        persons = populated_graph.query_nodes(entity_type=EntityType.PERSON)

        assert len(persons) == 5
        assert all(n.entity_type == EntityType.PERSON for n in persons)

    def test_query_by_content_contains(self, populated_graph):
        """Should query nodes by content substring."""
        matches = populated_graph.query_nodes(content_contains="Person 1")

        assert len(matches) == 1
        assert matches[0].id == "person-1"

    def test_query_by_metadata(self, populated_graph):
        """Should query nodes by metadata."""
        matches = populated_graph.query_nodes(metadata_filter={"index": 3})

        assert len(matches) == 1
        assert matches[0].id == "person-3"
