from .base import RetrievalStrategy
from .semantic import SemanticRetrievalStrategy

class RetrievalFactory:
    """
    Factory to create retrieval strategies based on configuration.
    """
    @staticmethod
    def get_strategy(strategy_type: str) -> RetrievalStrategy:
        if strategy_type == "semantic":
            return SemanticRetrievalStrategy()
        # Future: elif strategy_type == "lexical": return LexicalRetrievalStrategy()
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy_type}")
