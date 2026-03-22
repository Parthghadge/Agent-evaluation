"""Heuristic evaluator - format compliance, latency, required fields."""
from src.models import Conversation, Evaluation, EvaluationScores, Issue
from config import get_settings


class HeuristicEvaluator:
    """Format compliance, latency thresholds, required fields."""

    def __init__(self, latency_threshold_ms: int | None = None):
        s = get_settings()
        self.latency_threshold = latency_threshold_ms or s.latency_threshold_ms

    def evaluate(self, conversation: Conversation) -> Evaluation:
        """Run heuristic checks."""
        issues = []
        score = 1.0

        # Latency check
        meta = conversation.metadata
        if meta and meta.total_latency_ms is not None:
            if meta.total_latency_ms > self.latency_threshold:
                issues.append(
                    Issue(
                        type="latency",
                        severity="warning",
                        description=f"Response latency {meta.total_latency_ms}ms exceeds {self.latency_threshold}ms target",
                    )
                )
                score -= 0.1

        # Per-turn latency
        for t in conversation.turns:
            for tc in t.tool_calls:
                if tc.latency_ms and tc.latency_ms > 2000:
                    issues.append(
                        Issue(
                            type="tool_latency",
                            severity="info",
                            description=f"Tool {tc.tool_name} took {tc.latency_ms}ms",
                            turn_id=t.turn_id,
                        )
                    )

        # Format: assistant turns should have content or tool_calls
        for t in conversation.turns:
            if t.role == "assistant":
                if not t.content and not t.tool_calls:
                    issues.append(
                        Issue(
                            type="format",
                            severity="warning",
                            description="Assistant turn has no content or tool calls",
                            turn_id=t.turn_id,
                        )
                    )
                    score -= 0.05

        return Evaluation(
            evaluation_id=f"eval_heur_{conversation.conversation_id[:8]}",
            conversation_id=conversation.conversation_id,
            agent_version=conversation.agent_version,
            scores=EvaluationScores(overall=max(0, score)),
            issues_detected=issues,
            evaluator_metadata={"evaluator": "heuristic"},
        )
