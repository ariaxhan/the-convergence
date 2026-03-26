"""
Result types for Armature SDK.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OptimizationRunResult(BaseModel):
    """Result of optimization run."""
    success: bool
    best_config: Dict[str, Any]
    best_score: float
    configs_generated: int
    generations_run: int
    optimization_run_id: str
    timestamp: datetime
    events: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

