"""Tool Call Evaluator - verifies tool selection, parameters, hallucination, execution."""
from src.models import Conversation, Evaluation, ToolEvaluation, Issue, EvaluationScores


class ToolCallEvaluator:
    """Evaluates tool usage: selection, parameters, hallucination, execution."""

    def evaluate(self, conversation: Conversation) -> Evaluation:
        """Evaluate tool calls in the conversation."""
        tool_calls = []
        for t in conversation.turns:
            tool_calls.extend(t.tool_calls)

        if not tool_calls:
            return Evaluation(
                evaluation_id=f"eval_tool_{conversation.conversation_id[:8]}",
                conversation_id=conversation.conversation_id,
                agent_version=conversation.agent_version,
                scores=EvaluationScores(tool_accuracy=1.0),
                tool_evaluation=ToolEvaluation(
                    selection_accuracy=1.0,
                    parameter_accuracy=1.0,
                    execution_success=True,
                    hallucinated_params=False,
                ),
            )

        # Check execution success
        successes = [tc for tc in tool_calls if self._is_success(tc)]
        exec_success = len(successes) == len(tool_calls)

        # Parameter accuracy: params present and plausible (basic heuristic)
        param_ok = 0
        hallucinated = False
        for tc in tool_calls:
            if tc.parameters and isinstance(tc.parameters, dict):
                # Check if params seem derived from context (simple: not empty placeholders)
                vals = [str(v).lower() for v in tc.parameters.values() if v]
                if any(v in ("null", "n/a", "unknown", "") for v in vals):
                    hallucinated = True
                param_ok += 1
            else:
                param_ok += 0.5  # Partial if empty but tool ran
        param_accuracy = param_ok / len(tool_calls) if tool_calls else 1.0

        # Selection accuracy: assume correct if execution succeeded (simplified)
        selection_accuracy = 1.0 if exec_success else 0.7

        tool_eval = ToolEvaluation(
            selection_accuracy=selection_accuracy,
            parameter_accuracy=param_accuracy,
            execution_success=exec_success,
            hallucinated_params=hallucinated,
        )

        issues = []
        if hallucinated:
            issues.append(
                Issue(
                    type="tool_hallucination",
                    severity="warning",
                    description="Possible hallucinated or placeholder parameters in tool calls",
                )
            )
        if not exec_success:
            issues.append(
                Issue(
                    type="tool_execution",
                    severity="critical",
                    description="One or more tool calls failed",
                )
            )

        tool_accuracy = (selection_accuracy + param_accuracy + (1.0 if exec_success else 0)) / 3

        return Evaluation(
            evaluation_id=f"eval_tool_{conversation.conversation_id[:8]}",
            conversation_id=conversation.conversation_id,
            agent_version=conversation.agent_version,
            scores=EvaluationScores(tool_accuracy=tool_accuracy),
            tool_evaluation=tool_eval,
            issues_detected=issues,
            evaluator_metadata={"evaluator": "tool_call"},
        )

    def _is_success(self, tc) -> bool:
        if tc.success is not None:
            return tc.success
        if tc.result and isinstance(tc.result, dict):
            return tc.result.get("status") == "success"
        return True  # Assume success if no result
