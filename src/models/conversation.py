"""Conversation data models matching the sample schema."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single tool invocation within an assistant turn."""
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    latency_ms: Optional[int] = None
    success: Optional[bool] = None


class Turn(BaseModel):
    """A single turn in the conversation."""
    turn_id: int
    role: str  # "user" | "assistant"
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    timestamp: Optional[str] = None


class Annotation(BaseModel):
    """Human or automated annotation."""
    type: str  # e.g., "tool_accuracy", "helpfulness"
    label: str
    annotator_id: str
    confidence: Optional[float] = None
    notes: Optional[str] = None


class OpsReview(BaseModel):
    """Operations team quality review."""
    quality: str  # e.g., "good", "poor"
    notes: Optional[str] = None
    escalated: bool = False


class Feedback(BaseModel):
    """Aggregated feedback signals."""
    user_rating: Optional[int] = None  # 1-5 scale
    ops_review: Optional[OpsReview] = None
    annotations: list[Annotation] = Field(default_factory=list)
    implicit_signals: Optional[dict[str, Any]] = None  # early_exit, rephrasing, etc.


class ConversationMetadata(BaseModel):
    """Conversation-level metadata."""
    total_latency_ms: Optional[int] = None
    mission_completed: Optional[bool] = None
    exit_reason: Optional[str] = None
    custom: Optional[dict[str, Any]] = None


class Conversation(BaseModel):
    """Full conversation with context for evaluation."""
    conversation_id: str
    agent_version: str
    turns: list[Turn] = Field(default_factory=list)
    feedback: Optional[Feedback] = None
    metadata: Optional[ConversationMetadata] = None
