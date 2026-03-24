# Research Assistant

Research assistant that builds a knowledge graph from discovered topics while
using Thompson Sampling to optimize which search strategy to employ.

## Modules Demonstrated

- **Runtime MAB** -- selects between broad, focused, and deep-dive search strategies
- **ContextGraph** -- tracks researchers, topics, and methods as WHO/WHAT/HOW nodes
- **Knowledge Schema** -- GraphNode, GraphEdge, EntityType, OntologyType

## Run

```bash
python app.py
```

No API key required. All search results are simulated.
