"""Orchestrates all evaluators and merges results."""
import uuid
from datetime import datetime

from src.models import (
    Conversation,
    Evaluation,
    EvaluationScores,
    ToolEvaluation,
    Issue,
    ImprovementSuggestion,
)
from .llm_judge import LLMJudgeEvaluator
from .tool_evaluator import ToolCallEvaluator
from .coherence import CoherenceEvaluator
from .heuristics import HeuristicEvaluator


class EvaluationPipeline:
    """Runs all evaluators and produces unified evaluation output."""

    def __init__(self, use_llm: bool = True):
        self.llm = LLMJudgeEvaluator() if use_llm else None
        self.tool_eval = ToolCallEvaluator()
        self.coherence = CoherenceEvaluator()
        self.heuristics = HeuristicEvaluator()
        self._suggestion_engine = None  # Lazy init to avoid circular import

    async def evaluate(self, conversation: Conversation) -> Evaluation:
        """Run full evaluation pipeline."""
        eval_id = f"eval_{uuid.uuid4().hex[:12]}"

        # Run evaluators (tool, coherence, heuristics are sync)
        tool_result = self.tool_eval.evaluate(conversation)
        coh_result = self.coherence.evaluate(conversation)
        heur_result = self.heuristics.evaluate(conversation)

        # LLM is async (may fail if no API key)
        llm_result = None
        if self.llm:
            try:
                llm_result = await self.llm.evaluate(conversation)
                if llm_result and any(
                    i.type == "evaluator_error" for i in llm_result.issues_detected
                ):
                    llm_result = None  # Fallback to heuristic
            except Exception:
                llm_result = None

        # Merge scores (fallback rq when LLM unavailable)
        rq = (
            llm_result.scores.response_quality
            if llm_result and llm_result.scores.response_quality > 0
            else 0.8
        )
        ta = tool_result.scores.tool_accuracy
        coh = coh_result.scores.coherence
        heur = heur_result.scores.overall if heur_result.scores.overall > 0 else 1.0

        overall = (rq * 0.3 + ta * 0.3 + coh * 0.2 + heur * 0.2)

        # Merge issues
        all_issues: list[Issue] = []
        for r in [tool_result, coh_result, heur_result, llm_result]:
            if r:
                all_issues.extend(r.issues_detected)

        # Dedupe by description
        seen = set()
        unique_issues = []
        for i in all_issues:
            key = (i.type, i.description[:50])
            if key not in seen:
                seen.add(key)
                unique_issues.append(i)

        # Improvement suggestions
        suggestions = await self._generate_suggestions(conversation, unique_issues, tool_result)

        return Evaluation(
            evaluation_id=eval_id,
            conversation_id=conversation.conversation_id,
            agent_version=conversation.agent_version,
            scores=EvaluationScores(
                overall=round(overall, 2),
                response_quality=round(rq, 2),
                tool_accuracy=round(ta, 2),
                coherence=round(coh, 2),
            ),
            tool_evaluation=tool_result.tool_evaluation,
            issues_detected=unique_issues,
            improvement_suggestions=suggestions,
            evaluator_metadata={
                "pipeline": True,
                "evaluators": ["tool", "coherence", "heuristic"] + (["llm"] if llm_result else []),
            },
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    async def _generate_suggestions(
        self,
        conversation: Conversation,
        issues: list[Issue],
        tool_result,
    ) -> list[ImprovementSuggestion]:
        """Generate improvement suggestions from issues."""
        suggestions = []

        for issue in issues:
            if issue.type == "latency":
                suggestions.append(
                    ImprovementSuggestion(
                        type="prompt",
                        suggestion="Consider reducing context length or caching frequent tool results",
                        rationale="Latency exceeds target; optimize response path",
                        confidence=0.7,
                        example_conversation_ids=[conversation.conversation_id],
                    )
                )
            if issue.type == "tool_hallucination":
                suggestions.append(
                    ImprovementSuggestion(
                        type="prompt",
                        suggestion="Add explicit parameter extraction instructions and validation examples",
                        rationale="Reduce date/parameter inference errors",
                        confidence=0.72,
                        example_conversation_ids=[conversation.conversation_id],
                    )
                )
            if issue.type == "context_resolution":
                suggestions.append(
                    ImprovementSuggestion(
                        type="prompt",
                        suggestion="Add instruction to explicitly summarize user preferences in long conversations",
                        rationale="Improve context maintenance across 5+ turns",
                        confidence=0.65,
                        example_conversation_ids=[conversation.conversation_id],
                    )
                )
            if issue.type == "tool_execution" and tool_result and tool_result.tool_evaluation:
                suggestions.append(
                    ImprovementSuggestion(
                        type="tool",
                        suggestion="Review tool schema and add missing validation rules",
                        rationale="Tool execution failures may indicate schema/validation gaps",
                        confidence=0.68,
                        affected_component="tool_schema",
                        example_conversation_ids=[conversation.conversation_id],
                    )
                )

        return suggestions
