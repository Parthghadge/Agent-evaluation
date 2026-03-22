"""Base evaluator interface."""
from abc import ABC, abstractmethod
from src.models import Conversation, Evaluation


class BaseEvaluator(ABC):
    """Base class for all evaluators."""

    @abstractmethod
    async def evaluate(self, conversation: Conversation) -> Evaluation:
        """Evaluate a conversation and return results."""
        pass
