# Knowledge Examples

Deep dives into the ContextGraph: building, querying, traversing, and extracting insights from entity-relationship graphs.

## Examples

| File | What It Shows |
|------|---------------|
| `basic_graph.py` | Build a WHO/WHAT/HOW graph for a software team |
| `graph_queries.py` | Query a 10+ node graph by entity type, content, and traversal |
| `graph_relationships.py` | All relationship types: OWNS, USES, DEPENDS_ON, PRODUCES, CONSUMES style edges |
| `graph_patterns.py` | Model a real system architecture and extract dependency insights |

## Key Concepts

- **OntologyType**: High-level categories -- WHO (people/teams), WHAT (decisions/artifacts), HOW (processes/methods)
- **EntityType**: Specific types within ontology -- PERSON, TEAM, CONCEPT, ARTIFACT, PROCESS, etc.
- **GraphNode**: Entity with ontology_type, entity_type, content, and metadata
- **GraphEdge**: Directed relationship with relationship_type, weight, and metadata
- **Traversal**: BFS from a focal node with configurable max_depth

## Running

```bash
pip install -e .
python basic_graph.py
python graph_queries.py
python graph_relationships.py
python graph_patterns.py
```
