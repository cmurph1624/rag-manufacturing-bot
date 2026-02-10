from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMStrategy(ABC):
    """
    Abstract base class for LLM strategies.
    """
    @abstractmethod
    def generate_response(self, system_instruction: str, user_prompt: str) -> str:
        """
        Generates a response from the LLM.

        Args:
            system_instruction (str): The system instruction/prompt.
            user_prompt (str): The user's prompt.

        Returns:
            str: The generated response.
        """
        pass
