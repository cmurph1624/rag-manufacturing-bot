from .base import LLMStrategy
from .ollama_model import OllamaLLM

class LLMFactory:
    """
    Factory to create LLM strategies.
    In the future, this can be extended to support different providers (OpenAI, Anthropic, etc.) based on configuration.
    """
    @staticmethod
    def get_llm(model_type: str = "llama") -> LLMStrategy:
        """
        Returns an instance of the requested LLM strategy.

        Args:
            model_type (str): The type of model to use (e.g., "llama", "mistral"). Defaults to "llama".

        Returns:
            LLMStrategy: An instance of a class implementing LLMStrategy.
        """
        if model_type == "llama":
            return OllamaLLM(model_name="llama3.2")
        elif model_type == "mistral":
            return OllamaLLM(model_name="mistral")
        else:
            # Fallback or allow passing raw model name to OllamaLLM?
            # For now, treat unknown as a raw model name for Ollama
            return OllamaLLM(model_name=model_type)
