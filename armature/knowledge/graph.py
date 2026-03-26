"""In-memory Context Graph implementation."""

from typing import Any, Dict, List, Optional, Set

from armature.knowledge.schema import (
    EntityType,
    GraphEdge,
    GraphNode,
    OntologyType,
)


class ContextGraph:
    """In-memory graph for storing and traversing context relationships."""

    def __init__(self) -> None:
        """Initialize empty graph."""
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._outgoing: Dict[str, Set[str]] = {}  # node_id -> set of edge_ids
        self._incoming: Dict[str, Set[str]] = {}  # node_id -> set of edge_ids

    # =========================================================================
    # Node Operations
    # =========================================================================

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        if node.id not in self._outgoing:
            self._outgoing[node.id] = set()
        if node.id not in self._incoming:
            self._incoming[node.id] = set()

    def get_node(self, node_id: str) -> GraphNode:
        """Get a node by ID. Raises KeyError if not found."""
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists."""
        return node_id in self._nodes

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all connected edges."""
        if node_id not in self._nodes:
            return

        # Remove all outgoing edges
        for edge_id in list(self._outgoing.get(node_id, [])):
            self.remove_edge(edge_id)

        # Remove all incoming edges
        for edge_id in list(self._incoming.get(node_id, [])):
            self.remove_edge(edge_id)

        # Remove node
        del self._nodes[node_id]
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)

    def node_count(self) -> int:
        """Return the number of nodes in the graph."""
        return len(self._nodes)

    # =========================================================================
    # Edge Operations
    # =========================================================================

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self._edges[edge.id] = edge

        # Track outgoing from source
        if edge.source_id not in self._outgoing:
            self._outgoing[edge.source_id] = set()
        self._outgoing[edge.source_id].add(edge.id)

        # Track incoming to target
        if edge.target_id not in self._incoming:
            self._incoming[edge.target_id] = set()
        self._incoming[edge.target_id].add(edge.id)

    def get_edge(self, edge_id: str) -> GraphEdge:
        """Get an edge by ID. Raises KeyError if not found."""
        if edge_id not in self._edges:
            raise KeyError(f"Edge '{edge_id}' not found")
        return self._edges[edge_id]

    def has_edge(self, edge_id: str) -> bool:
        """Check if an edge exists."""
        return edge_id in self._edges

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the graph."""
        if edge_id not in self._edges:
            return

        edge = self._edges[edge_id]

        # Remove from outgoing set
        if edge.source_id in self._outgoing:
            self._outgoing[edge.source_id].discard(edge_id)

        # Remove from incoming set
        if edge.target_id in self._incoming:
            self._incoming[edge.target_id].discard(edge_id)

        # Remove edge
        del self._edges[edge_id]

    def edge_count(self) -> int:
        """Return the number of edges in the graph."""
        return len(self._edges)

    # =========================================================================
    # Traversal
    # =========================================================================

    def get_neighbors(
        self, node_id: str, relationship_type: Optional[str] = None
    ) -> List[GraphNode]:
        """Get adjacent nodes (targets of outgoing edges)."""
        neighbors: List[GraphNode] = []

        for edge_id in self._outgoing.get(node_id, []):
            edge = self._edges[edge_id]
            if relationship_type is None or edge.relationship_type == relationship_type:
                if edge.target_id in self._nodes:
                    neighbors.append(self._nodes[edge.target_id])

        return neighbors

    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        """Get edges pointing to a node."""
        edges: List[GraphEdge] = []
        for edge_id in self._incoming.get(node_id, []):
            edges.append(self._edges[edge_id])
        return edges

    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Get edges from a node."""
        edges: List[GraphEdge] = []
        for edge_id in self._outgoing.get(node_id, []):
            edges.append(self._edges[edge_id])
        return edges

    def traverse(self, start_id: str, max_depth: int = 1) -> List[GraphNode]:
        """Traverse graph from start node to max_depth, returning all visited nodes."""
        visited: Set[str] = set()
        result: List[GraphNode] = []

        # BFS traversal
        current_level: Set[str] = {start_id}

        for _ in range(max_depth + 1):
            next_level: Set[str] = set()

            for node_id in current_level:
                if node_id in visited:
                    continue
                visited.add(node_id)

                if node_id in self._nodes:
                    result.append(self._nodes[node_id])

                    # Get neighbors for next level
                    for edge_id in self._outgoing.get(node_id, []):
                        edge = self._edges[edge_id]
                        if edge.target_id not in visited:
                            next_level.add(edge.target_id)

            current_level = next_level

        return result

    # =========================================================================
    # Filtering
    # =========================================================================

    def get_nodes_by_ontology(self, ontology_type: OntologyType) -> List[GraphNode]:
        """Filter nodes by ontology type."""
        return [n for n in self._nodes.values() if n.ontology_type == ontology_type]

    def query_nodes(
        self,
        entity_type: Optional[EntityType] = None,
        content_contains: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[GraphNode]:
        """Query nodes with multiple filter criteria."""
        results: List[GraphNode] = []

        for node in self._nodes.values():
            # Filter by entity type
            if entity_type is not None and node.entity_type != entity_type:
                continue

            # Filter by content substring
            if content_contains is not None and content_contains not in node.content:
                continue

            # Filter by metadata
            if metadata_filter is not None:
                match = True
                for key, value in metadata_filter.items():
                    if key not in node.metadata or node.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(node)

        return results

    # =========================================================================
    # Context Extraction
    # =========================================================================

    def extract_context(
        self, focal_node_id: str, max_depth: int = 2
    ) -> Dict[str, Any]:
        """Extract context around a focal node for agent consumption."""
        focal_node = self.get_node(focal_node_id)

        # Get all nodes in range
        nodes = self.traverse(focal_node_id, max_depth)
        related_nodes = [n for n in nodes if n.id != focal_node_id]

        # Collect all relevant edges
        edge_list: List[Dict[str, Any]] = []
        visited_node_ids = {n.id for n in nodes}

        for node in nodes:
            for edge_id in self._outgoing.get(node.id, []):
                edge = self._edges[edge_id]
                if edge.target_id in visited_node_ids:
                    edge_list.append(edge.model_dump())

        return {
            "focal_node": focal_node.model_dump(),
            "related_nodes": [n.model_dump() for n in related_nodes],
            "edges": edge_list,
            "summary": f"Context for '{focal_node.content}' with {len(related_nodes)} related nodes",
        }
