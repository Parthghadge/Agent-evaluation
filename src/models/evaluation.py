"""Evaluation output models matching the sample schema."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EvaluationScores(BaseModel):
    """Aggregated evaluation scores."""
    overall: float = 0.0
    response_quality: float = 0.0
    tool_accuracy: float = 0.0
    coherence: float = 0.0


class ToolEvaluation(BaseModel):
    """Tool-specific evaluation results."""
    selection_accuracy: float = 0.0
    parameter_accuracy: float = 0.0
    execution_success: bool = False
    hallucinated_params: bool = False


class Issue(BaseModel):
    """Detected issue in the conversation."""
    type: str  # e.g., "latency", "context_loss"
    severity: str  # "critical" | "warning" | "info"
    description: str
    turn_id: Optional[int] = None
    details: Optional[dict] = None


class ImprovementSuggestion(BaseModel):
    """Auto-generated improvement suggestion."""
    type: str  # "prompt" | "tool"
    suggestion: str
    rationale: str
    confidence: float = 0.0
    affected_component: Optional[str] = None
    example_conversation_ids: list[str] = Field(default_factory=list)


class Evaluation(BaseModel):
    """Complete evaluation output."""
    evaluation_id: str
    conversation_id: str
    agent_version: str
    scores: EvaluationScores = Field(default_factory=EvaluationScores)
    tool_evaluation: Optional[ToolEvaluation] = None
    issues_detected: list[Issue] = Field(default_factory=list)
    improvement_suggestions: list[ImprovementSuggestion] = Field(default_factory=list)
    evaluator_metadata: Optional[dict] = None
    created_at: Optional[str] = None
