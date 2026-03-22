"""LLM-as-Judge evaluator for response quality, helpfulness, factuality."""
import json
import uuid
from openai import AsyncOpenAI

from src.models import Conversation, Evaluation, EvaluationScores, Issue
from config import get_settings


LLM_JUDGE_SYSTEM = """You are an expert evaluator for AI agent conversations.
Rate the assistant's responses on:
1. **Response Quality** (0-1): Helpfulness, clarity, relevance
2. **Factuality** (0-1): Accuracy of information, no hallucination
3. **User Alignment** (0-1): Did it address the user's intent?

Output JSON only:
{
  "response_quality": 0.0-1.0,
  "factuality": 0.0-1.0,
  "user_alignment": 0.0-1.0,
  "issues": [{"type": "...", "severity": "critical|warning|info", "description": "..."}],
  "rationale": "brief explanation"
}"""


class LLMJudgeEvaluator:
    """Uses an LLM to assess response quality."""

    def __init__(self, model: str | None = None):
        s = get_settings()
        self.client = AsyncOpenAI(
            api_key=s.openai_api_key or "sk-placeholder",
            base_url=s.openai_base_url,
        )
        self.model = model or s.eval_model

    async def evaluate(self, conversation: Conversation) -> Evaluation:
        """Evaluate conversation with LLM-as-Judge."""
        # Build context from turns
        turns_text = []
        for t in conversation.turns:
            role = t.role.upper()
            content = t.content or ""
            if t.tool_calls:
                for tc in t.tool_calls:
                    content += f"\n[Tool: {tc.tool_name}] params={tc.parameters}"
            turns_text.append(f"{role}: {content}")

        context = "\n".join(turns_text)
        prompt = f"Evaluate this conversation:\n\n{context}\n\nProvide your evaluation JSON."

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": LLM_JUDGE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            text = resp.choices[0].message.content or "{}"
            # Extract JSON (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)

            rq = float(data.get("response_quality", 0.5))
            fact = float(data.get("factuality", 0.5))
            ua = float(data.get("user_alignment", 0.5))
            overall = (rq + fact + ua) / 3

            issues = [
                Issue(
                    type=i.get("type", "quality"),
                    severity=i.get("severity", "info"),
                    description=i.get("description", ""),
                )
                for i in data.get("issues", [])
            ]

            return Evaluation(
                evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
                conversation_id=conversation.conversation_id,
                agent_version=conversation.agent_version,
                scores=EvaluationScores(
                    overall=overall,
                    response_quality=rq,
                    tool_accuracy=0.0,  # Filled by tool evaluator
                    coherence=0.0,  # Filled by coherence evaluator
                ),
                issues_detected=issues,
                evaluator_metadata={"evaluator": "llm_judge", "rationale": data.get("rationale", "")},
            )
        except Exception as e:
            return Evaluation(
                evaluation_id=f"eval_{uuid.uuid4().hex[:12]}",
                conversation_id=conversation.conversation_id,
                agent_version=conversation.agent_version,
                scores=EvaluationScores(overall=0.0, response_quality=0.0),
                issues_detected=[
                    Issue(
                        type="evaluator_error",
                        severity="critical",
                        description=f"LLM Judge failed: {e}",
                    )
                ],
                evaluator_metadata={"evaluator": "llm_judge", "error": str(e)},
            )
