"""In-memory store for conversations (production would use Postgres/Redis)."""
from typing import Optional
from src.models import Conversation, Evaluation


class ConversationStore:
    """Simple in-memory store. Replace with DB in production."""

    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
        self._evaluations: dict[str, list[Evaluation]] = {}

    async def save_conversation(self, conv: Conversation) -> None:
        self._conversations[conv.conversation_id] = conv

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    async def save_evaluation(self, eval_result: Evaluation) -> None:
        key = eval_result.conversation_id
        if key not in self._evaluations:
            self._evaluations[key] = []
        self._evaluations[key].append(eval_result)

    async def get_evaluations(self, conversation_id: str) -> list[Evaluation]:
        return self._evaluations.get(conversation_id, [])

    async def list_conversations(
        self, agent_version: Optional[str] = None, limit: int = 100
    ) -> list[Conversation]:
        items = list(self._conversations.values())
        if agent_version:
            items = [c for c in items if c.agent_version == agent_version]
        return items[-limit:]
