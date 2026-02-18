from .base import IngestionStrategy
from .strategies.standard import StandardIngestionStrategy

class IngestionFactory:
    """
    Factory to create ingestion strategies.
    """
    @staticmethod
    def get_strategy(strategy_type: str) -> IngestionStrategy:
        if strategy_type == "standard":
            return StandardIngestionStrategy()
        elif strategy_type == "semantic":
            from .strategies.semantic import SemanticIngestionStrategy
            return SemanticIngestionStrategy()
        elif strategy_type == "structure":
            from .strategies.structure import StructureIngestionStrategy
            return StructureIngestionStrategy()
        else:
            raise ValueError(f"Unknown ingestion strategy: {strategy_type}")
