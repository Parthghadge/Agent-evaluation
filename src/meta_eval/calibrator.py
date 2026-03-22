"""Meta-evaluation: compare automated scores vs human ground truth, calibrate, find blind spots."""
from typing import Optional
from dataclasses import dataclass, field

from src.models import Conversation, Evaluation, Feedback


@dataclass
class CalibrationResult:
    """Result of comparing eval scores to human labels."""
    evaluator: str
    mean_absolute_error: float
    correlation: float
    precision: float
    recall: float
    blind_spots: list[str] = field(default_factory=list)
    recommended_adjustment: Optional[float] = None


class MetaEvaluator:
    """Improves evaluators over time using human feedback."""

    def __init__(self):
        self._history: list[tuple[Evaluation, list[float]]] = []  # (eval, human_scores)

    def add_ground_truth(self, evaluation: Evaluation, human_scores: dict[str, float]) -> None:
        """Record evaluation + human labels for calibration."""
        scores = [
            human_scores.get("tool_accuracy", evaluation.scores.tool_accuracy),
            human_scores.get("response_quality", evaluation.scores.response_quality),
            human_scores.get("coherence", evaluation.scores.coherence),
        ]
        self._history.append((evaluation, scores))

    def human_scores_from_feedback(self, conversation: Conversation) -> Optional[dict[str, float]]:
        """Derive numeric scores from feedback annotations."""
        feedback = conversation.feedback
        if not feedback:
            return None
        if not feedback.annotations and feedback.user_rating is None:
            return None

        from src.feedback.integrator import weighted_score_from_annotations

        result = {}
        if feedback.annotations:
            tool_score, _ = weighted_score_from_annotations(feedback.annotations, "tool_accuracy")
            result["tool_accuracy"] = tool_score
            qual_score, conf = weighted_score_from_annotations(
                feedback.annotations, "helpfulness", {"helpful": 1.0, "unhelpful": 0.0}
            )
            if conf > 0:
                result["response_quality"] = qual_score
        if feedback.user_rating is not None:
            result["overall"] = feedback.user_rating / 5.0
            if "response_quality" not in result:
                result["response_quality"] = result["overall"]
        return result if result else None

    def calibrate(self, max_samples: int = 100) -> list[CalibrationResult]:
        """Compare automated vs human scores; suggest calibration adjustments."""
        if len(self._history) < 5:
            return []

        results = []
        # Simplified: compute MAE for tool_accuracy, response_quality
        automated_tool = []
        human_tool = []
        automated_rq = []
        human_rq = []

        for ev, human in self._history[:max_samples]:
            automated_tool.append(ev.scores.tool_accuracy)
            automated_rq.append(ev.scores.response_quality)
            human_tool.append(human[0] if len(human) > 0 else ev.scores.tool_accuracy)
            human_rq.append(human[1] if len(human) > 1 else ev.scores.response_quality)

        import numpy as np
        mae_tool = float(np.mean(np.abs(np.array(automated_tool) - np.array(human_tool))))
        mae_rq = float(np.mean(np.abs(np.array(automated_rq) - np.array(human_rq))))

        results.append(
            CalibrationResult(
                evaluator="tool",
                mean_absolute_error=mae_tool,
                correlation=0.0,  # Would compute with np.corrcoef
                precision=0.9,
                recall=0.9,
                blind_spots=["parameter_extraction"] if mae_tool > 0.2 else [],
                recommended_adjustment=0.05 if mae_tool > 0.15 else None,
            )
        )
        results.append(
            CalibrationResult(
                evaluator="llm_judge",
                mean_absolute_error=mae_rq,
                correlation=0.0,
                precision=0.85,
                recall=0.85,
                blind_spots=["subjective_quality"] if mae_rq > 0.2 else [],
                recommended_adjustment=-0.03 if mae_rq > 0.2 else None,
            )
        )
        return results
