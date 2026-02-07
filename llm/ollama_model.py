import ollama
from .base import LLMStrategy

class OllamaLLM(LLMStrategy):
    """
    Ollama implementation of LLMStrategy.
    """
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name

    def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        """
        Generates a response using Ollama.
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': user_prompt},
            ])
            return response['message']['content']
        except Exception as e:
            # Re-raise or handle as appropriate. Here we allow the caller to handle it
            raise e
