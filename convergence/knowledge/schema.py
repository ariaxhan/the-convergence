"""Schema definitions for the Knowledge layer Context Graph."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OntologyType(str, Enum):
    """High-level ontology categories for graph nodes."""

    WHO = "who"  # People, teams, organizations
    WHAT = "what"  # Decisions, concepts, artifacts
    HOW = "how"  # Processes, methods, workflows


class EntityType(str, Enum):
    """Specific entity types within ontology categories."""

    # WHO
    PERSON = "person"
    TEAM = "team"
    ORGANIZATION = "organization"
    # WHAT
    DECISION = "decision"
    CONCEPT = "concept"
    ARTIFACT = "artifact"
    # HOW
    PROCESS = "process"
    METHOD = "method"
    WORKFLOW = "workflow"


class GraphNode(BaseModel):
    """A node in the context graph representing an entity."""

    id: str
    ontology_type: OntologyType
    entity_type: EntityType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class GraphEdge(BaseModel):
    """An edge in the context graph representing a relationship."""

    id: str
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
