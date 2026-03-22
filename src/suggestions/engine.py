"""Generates actionable improvement suggestions from failure patterns."""
from collections import defaultdict
from typing import Optional

from src.models import Conversation, Evaluation, ImprovementSuggestion, Issue


class SuggestionEngine:
    """Detects failure patterns and suggests prompt/tool improvements."""

    def __init__(self):
        self._issue_counts: dict[str, int] = defaultdict(int)
        self._conversations_by_issue: dict[str, list[str]] = defaultdict(list)

    def ingest_evaluation(self, evaluation: Evaluation) -> None:
        """Track issues for pattern detection."""
        for issue in evaluation.issues_detected:
            key = f"{issue.type}:{issue.severity}"
            self._issue_counts[key] += 1
            self._conversations_by_issue[key].append(evaluation.conversation_id)

    def get_failure_patterns(self, min_count: int = 5) -> list[dict]:
        """Identify recurring failure patterns."""
        patterns = []
        for key, count in self._issue_counts.items():
            if count >= min_count:
                issue_type, severity = key.split(":", 1)
                patterns.append(
                    {
                        "issue_type": issue_type,
                        "severity": severity,
                        "count": count,
                        "example_ids": self._conversations_by_issue[key][:5],
                    }
                )
        return patterns

    def suggest_prompt_fixes(
        self,
        patterns: list[dict],
        agent_version: Optional[str] = None,
    ) -> list[ImprovementSuggestion]:
        """Generate prompt improvement suggestions from patterns."""
        suggestions = []
        prompt_hints = {
            "tool_hallucination": (
                "Add explicit parameter extraction instructions with examples",
                "Reduce inferred/hallucinated parameters in tool calls",
            ),
            "context_resolution": (
                "Add instruction to summarize user preferences in long conversations",
                "Improve context maintenance across 5+ turns",
            ),
            "latency": (
                "Reduce context window or add caching for frequent tool results",
                "Optimize response latency to meet SLA",
            ),
            "tool_execution": (
                "Add validation examples for tool parameters in system prompt",
                "Reduce tool execution failures from bad parameters",
            ),
        }
        for p in patterns:
            hint = prompt_hints.get(p["issue_type"])
            if hint:
                suggestions.append(
                    ImprovementSuggestion(
                        type="prompt",
                        suggestion=hint[0],
                        rationale=hint[1],
                        confidence=0.6 + 0.1 * min(p["count"] // 5, 3),
                        example_conversation_ids=p.get("example_ids", [])[:5],
                    )
                )
        return suggestions

    def suggest_tool_fixes(
        self,
        patterns: list[dict],
    ) -> list[ImprovementSuggestion]:
        """Generate tool schema/parameter improvement suggestions."""
        suggestions = []
        for p in patterns:
            if p["issue_type"] in ("tool_execution", "tool_hallucination"):
                suggestions.append(
                    ImprovementSuggestion(
                        type="tool",
                        suggestion="Add parameter description improvements and validation rules",
                        rationale="Recurring tool issues suggest schema gaps",
                        confidence=0.65,
                        affected_component="tool_schema",
                        example_conversation_ids=p.get("example_ids", [])[:5],
                    )
                )
        return suggestions
