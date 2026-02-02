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
        elif strategy_type == "lexical":
            from .lexical import LexicalRetrievalStrategy
            return LexicalRetrievalStrategy()
        elif strategy_type == "semantic-rerank":
            from .rerank import SemanticRerankingRetrievalStrategy
            return SemanticRerankingRetrievalStrategy()
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy_type}")
