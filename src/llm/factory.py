from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel

class LLMFactory:
    """
    Factory to create LangChain Chat Models.
    """
    @staticmethod
    def get_llm(model_type: str = "llama") -> BaseChatModel:
        """
        Returns a LangChain Chat Model instance.
        """
        if model_type == "llama":
            return ChatOllama(model="llama3.2")
        elif model_type == "mistral":
            return ChatOllama(model="mistral")
        else:
            return ChatOllama(model=model_type)
