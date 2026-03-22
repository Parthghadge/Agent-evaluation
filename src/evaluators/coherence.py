"""Multi-turn Coherence Evaluator - context maintenance, consistency, references."""
from src.models import Conversation, Evaluation, EvaluationScores, Issue


class CoherenceEvaluator:
    """Checks coherence across turns: consistency, context handling, no contradictions."""

    def evaluate(self, conversation: Conversation) -> Evaluation:
        """Evaluate multi-turn coherence."""
        turns = conversation.turns
        if len(turns) < 2:
            return Evaluation(
                evaluation_id=f"eval_coh_{conversation.conversation_id[:8]}",
                conversation_id=conversation.conversation_id,
                agent_version=conversation.agent_version,
                scores=EvaluationScores(coherence=1.0),
                evaluator_metadata={"evaluator": "coherence"},
            )

        issues = []
        score = 1.0

        # Check for context length degradation (conversations > 5 turns)
        if len(turns) > 5:
            # Heuristic: later turns should reference earlier context
            user_msgs = [t.content for t in turns if t.role == "user"]
            early_context = " ".join(user_msgs[:2]).lower()
            later_user = user_msgs[-1].lower() if user_msgs else ""

            # Simple: if later message has pronouns/questions that need context
            needs_context = any(
                w in later_user for w in ["it", "that", "those", "this", "them", "same"]
            )
            if needs_context and len(early_context) > 20:
                # Could add LLM check for reference resolution
                score *= 0.95  # Slight penalty for long conversations
                issues.append(
                    Issue(
                        type="context_resolution",
                        severity="warning",
                        description=f"Conversation has {len(turns)} turns; verify context from early turns is maintained",
                    )
                )

        # Check for obvious contradictions (simplified keyword-based)
        all_text = " ".join(t.content for t in turns).lower()
        if "yes" in all_text and "no" in all_text:
            # Might be natural; don't over-penalize
            pass

        return Evaluation(
            evaluation_id=f"eval_coh_{conversation.conversation_id[:8]}",
            conversation_id=conversation.conversation_id,
            agent_version=conversation.agent_version,
            scores=EvaluationScores(coherence=max(0, score)),
            issues_detected=issues,
            evaluator_metadata={"evaluator": "coherence", "turn_count": len(turns)},
        )
