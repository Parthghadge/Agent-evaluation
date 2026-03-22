"""Integrates human annotations, handles disagreement, confidence-based routing."""
from typing import Optional
from collections import Counter

from src.models import Conversation, Feedback, Annotation, Evaluation


def compute_annotator_agreement(annotations: list[Annotation], annotation_type: str) -> float:
    """Compute agreement (e.g., Krippendorff's alpha simplified) for a label type."""
    filtered = [a for a in annotations if a.type == annotation_type]
    if len(filtered) < 2:
        return 1.0
    labels = [a.label for a in filtered]
    counts = Counter(labels)
    most_common = counts.most_common(1)[0][1]
    return most_common / len(labels)


def weighted_score_from_annotations(
    annotations: list[Annotation],
    annotation_type: str,
    label_to_score: Optional[dict[str, float]] = None,
) -> tuple[float, float]:
    """Compute weighted score from annotations; return (score, confidence)."""
    filtered = [a for a in annotations if a.type == annotation_type]
    if not filtered:
        return 0.5, 0.0  # No data

    default_map = {"correct": 1.0, "incorrect": 0.0, "good": 1.0, "poor": 0.0}
    mapping = label_to_score or default_map

    total_weight = 0.0
    weighted_sum = 0.0
    for a in filtered:
        conf = a.confidence if a.confidence is not None else 0.8
        score = mapping.get(a.label.lower(), 0.5)
        weighted_sum += score * conf
        total_weight += conf

    if total_weight == 0:
        return 0.5, 0.0
    score = weighted_sum / total_weight
    agreement = compute_annotator_agreement(filtered, annotation_type)
    confidence = (total_weight / len(filtered)) * agreement
    return score, min(1.0, confidence)


class FeedbackIntegrator:
    """Integrates feedback signals with evaluations."""

    def should_route_to_human(self, evaluation: Evaluation, conversation: Conversation) -> bool:
        """Confidence-based routing: auto-label vs human review."""
        # Route to human if: low scores, disagreement, or few annotations
        if evaluation.scores.overall < 0.6:
            return True
        if any(i.severity == "critical" for i in evaluation.issues_detected):
            return True

        feedback = conversation.feedback
        if not feedback or not feedback.annotations:
            return False

        for atype in {"tool_accuracy", "helpfulness"}:
            anns = [a for a in feedback.annotations if a.type == atype]
            if len(anns) >= 2 and compute_annotator_agreement(anns, atype) < 0.6:
                return True  # Disagreement -> human review

        return False

    def blend_with_human_feedback(
        self,
        evaluation: Evaluation,
        conversation: Conversation,
        weight_human: float = 0.4,
    ) -> Evaluation:
        """Blend automated eval scores with human annotation-derived scores."""
        feedback = conversation.feedback
        if not feedback or not feedback.annotations:
            return evaluation

        # Get human-derived scores
        tool_score, tool_conf = weighted_score_from_annotations(
            feedback.annotations, "tool_accuracy"
        )
        if tool_conf > 0:
            blended_tool = (
                evaluation.scores.tool_accuracy * (1 - weight_human)
                + tool_score * weight_human * tool_conf
            ) / (1 - weight_human + weight_human * tool_conf)
            evaluation.scores.tool_accuracy = round(blended_tool, 2)

        return evaluation
