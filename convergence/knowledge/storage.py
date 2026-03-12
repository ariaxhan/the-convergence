"""SQLite persistence for Context Graph."""

import json
from typing import Optional

import aiosqlite

from convergence.knowledge.graph import ContextGraph
from convergence.knowledge.schema import (
    EntityType,
    GraphEdge,
    GraphNode,
    OntologyType,
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT PRIMARY KEY,
    ontology_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    content TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES graph_nodes(id),
    target_id TEXT REFERENCES graph_nodes(id),
    relationship_type TEXT,
    weight REAL DEFAULT 1.0,
    metadata TEXT
);
"""


class GraphStorage:
    """SQLite-based persistence for Context Graph."""

    def __init__(self, db_path: str, backend: str = "sqlite") -> None:
        """Initialize storage with database path."""
        self.db_path = db_path
        self.backend = backend
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to database and initialize schema."""
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.executescript(_SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # =========================================================================
    # Node Persistence
    # =========================================================================

    async def save_node(self, node: GraphNode) -> None:
        """Save a node to the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        await self._conn.execute(
            """
            INSERT OR REPLACE INTO graph_nodes
            (id, ontology_type, entity_type, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node.id,
                node.ontology_type.value,
                node.entity_type.value,
                node.content,
                json.dumps(node.metadata),
                node.created_at,
            ),
        )
        await self._conn.commit()

    async def load_node(self, node_id: str) -> GraphNode:
        """Load a node from the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        async with self._conn.execute(
            "SELECT id, ontology_type, entity_type, content, metadata, created_at FROM graph_nodes WHERE id = ?",
            (node_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            raise KeyError(f"Node '{node_id}' not found")

        return GraphNode(
            id=row[0],
            ontology_type=OntologyType(row[1]),
            entity_type=EntityType(row[2]),
            content=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            created_at=row[5],
        )

    async def delete_node(self, node_id: str) -> None:
        """Delete a node from the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        await self._conn.execute("DELETE FROM graph_nodes WHERE id = ?", (node_id,))
        await self._conn.commit()

    # =========================================================================
    # Edge Persistence
    # =========================================================================

    async def save_edge(self, edge: GraphEdge) -> None:
        """Save an edge to the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        await self._conn.execute(
            """
            INSERT OR REPLACE INTO graph_edges
            (id, source_id, target_id, relationship_type, weight, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.relationship_type,
                edge.weight,
                json.dumps(edge.metadata),
            ),
        )
        await self._conn.commit()

    async def load_edge(self, edge_id: str) -> GraphEdge:
        """Load an edge from the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        async with self._conn.execute(
            "SELECT id, source_id, target_id, relationship_type, weight, metadata FROM graph_edges WHERE id = ?",
            (edge_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            raise KeyError(f"Edge '{edge_id}' not found")

        return GraphEdge(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            relationship_type=row[3],
            weight=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
        )

    async def delete_edge(self, edge_id: str) -> None:
        """Delete an edge from the database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        await self._conn.execute("DELETE FROM graph_edges WHERE id = ?", (edge_id,))
        await self._conn.commit()

    # =========================================================================
    # Full Graph Operations
    # =========================================================================

    async def save_graph(self, graph: ContextGraph) -> None:
        """Save entire graph to database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # Save all nodes
        for node in graph._nodes.values():
            await self.save_node(node)

        # Save all edges
        for edge in graph._edges.values():
            await self.save_edge(edge)

    async def load_graph(self) -> ContextGraph:
        """Load entire graph from database."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        graph = ContextGraph()

        # Load all nodes
        async with self._conn.execute(
            "SELECT id, ontology_type, entity_type, content, metadata, created_at FROM graph_nodes"
        ) as cursor:
            async for row in cursor:
                node = GraphNode(
                    id=row[0],
                    ontology_type=OntologyType(row[1]),
                    entity_type=EntityType(row[2]),
                    content=row[3],
                    metadata=json.loads(row[4]) if row[4] else {},
                    created_at=row[5],
                )
                graph.add_node(node)

        # Load all edges
        async with self._conn.execute(
            "SELECT id, source_id, target_id, relationship_type, weight, metadata FROM graph_edges"
        ) as cursor:
            async for row in cursor:
                edge = GraphEdge(
                    id=row[0],
                    source_id=row[1],
                    target_id=row[2],
                    relationship_type=row[3],
                    weight=row[4],
                    metadata=json.loads(row[5]) if row[5] else {},
                )
                graph.add_edge(edge)

        return graph
