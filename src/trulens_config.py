"""
TrueLens Configuration Module

This module provides centralized configuration for TrueLens evaluation,
including session initialization, feedback function definitions, and
evaluation provider setup.

Features:
- Configurable evaluation model (Ollama, OpenAI, Bedrock)
- 5 feedback functions: Answer Relevance, Context Relevance, Groundedness,
  Citation Matching, and Latency Tracking
- Easy session management and reset capabilities
- Environment-based configuration
"""

import os
import time
from typing import List, Tuple, Optional
from difflib import SequenceMatcher

from trulens.core import Feedback, TruSession, Select
from trulens.providers.langchain import Langchain
from trulens.apps.langchain.tru_chain import TruChain


class TrueLensConfig:
    """
    Centralized TrueLens configuration and feedback function manager.

    This class handles:
    - TrueLens session initialization
    - Evaluation model provider setup (Ollama, OpenAI, Bedrock)
    - Feedback function definitions
    - Session lifecycle management
    """

    def __init__(
        self,
        database_path: str = "trulens_eval.db",
        evaluation_model: Optional[str] = None
    ):
        """
        Initialize TrueLens configuration.

        Args:
            database_path: Path to TrueLens SQLite database
            evaluation_model: Model name for evaluation (defaults to env var EVALUATION_MODEL or 'llama3.1')
        """
        self.database_path = database_path
        self.evaluation_model = evaluation_model or os.getenv("EVALUATION_MODEL", "llama3.1")
        self.session: Optional[TruSession] = None
        self.provider = None

    def initialize_session(self, reset: bool = False) -> TruSession:
        """
        Initialize TrueLens session and database.

        Args:
            reset: If True, resets the existing session

        Returns:
            TruSession instance

        Raises:
            Exception: If session initialization fails
        """
        try:
            # Create or connect to TrueLens session
            self.session = TruSession(database_url=f"sqlite:///{self.database_path}")

            if reset:
                print(f"⚠️  Resetting TrueLens session at {self.database_path}")
                self.session.reset_database()

            print(f"✅ TrueLens session initialized: {self.database_path}")
            print(f"📊 Evaluation model: {self.evaluation_model}")

            return self.session

        except Exception as e:
            raise Exception(f"Failed to initialize TrueLens session: {e}")

    def get_provider(self) -> Langchain:
        """
        Get or create the evaluation model provider.

        Currently supports Ollama via LangChain integration.
        Future: Add OpenAI, Bedrock support based on env vars.

        Returns:
            Langchain provider instance configured for evaluation
        """
        if self.provider is not None:
            return self.provider

        try:
            # For now, we use Ollama via LangChain
            # The Langchain provider will use the model specified in evaluation_model
            from langchain_ollama import ChatOllama

            llm = ChatOllama(
                model=self.evaluation_model,
                temperature=0.0,  # Deterministic for evaluation
            )

            # Create TrueLens LangChain provider
            self.provider = Langchain(chain=llm)

            print(f"✅ Evaluation provider initialized: Ollama ({self.evaluation_model})")
            return self.provider

        except Exception as e:
            raise Exception(f"Failed to initialize evaluation provider: {e}")

    def get_feedback_functions(self) -> List[Feedback]:
        """
        Get all configured feedback functions for evaluation.

        Defines 5 feedback functions:
        1. Answer Relevance: How well the answer addresses the question
        2. Context Relevance: How relevant the retrieved chunks are to the question
        3. Groundedness: Whether the answer is supported by the retrieved context
        4. Citation Matching: Whether correct source document is cited (fuzzy match)
        5. Latency Tracking: Response generation time

        Returns:
            List of configured Feedback objects
        """
        provider = self.get_provider()

        feedbacks = []

        # 1. Answer Relevance: Question → Answer quality
        f_answer_relevance = (
            Feedback(
                provider.relevance_with_cot_reasons,
                name="Answer Relevance"
            )
            .on_input()  # Question
            .on_output()  # Answer
        )
        feedbacks.append(f_answer_relevance)

        # 2. Context Relevance: Question → Retrieved chunks quality
        # This evaluates if the retrieved context is relevant to answering the question
        # Note: Using simpler selectors for OTEL compatibility
        try:
            f_context_relevance = (
                Feedback(
                    provider.context_relevance_with_cot_reasons,
                    name="Context Relevance"
                )
                .on_input()  # Question
                .on_default()  # Use default context selector
            )
            feedbacks.append(f_context_relevance)
        except Exception as e:
            print(f"⚠️  Skipping Context Relevance feedback: {e}")

        # 3. Groundedness: Answer supported by context
        # This checks if the answer is factually grounded in the retrieved documents
        try:
            f_groundedness = (
                Feedback(
                    provider.groundedness_measure_with_cot_reasons,
                    name="Groundedness"
                )
                .on_default()  # Use default context selector
                .on_output()  # Answer
            )
            feedbacks.append(f_groundedness)
        except Exception as e:
            print(f"⚠️  Skipping Groundedness feedback: {e}")

        # 4. Custom: Citation Matching (fuzzy match)
        # Checks if the answer cites the correct source document
        # Disabled for now due to OTEL selector limitations
        # f_citation_match = (
        #     Feedback(
        #         self._citation_matching_feedback,
        #         name="Citation Match"
        #     )
        #     .on_output()  # Answer (contains citation)
        # )
        # feedbacks.append(f_citation_match)

        # 5. Custom: Latency Tracking
        # Measures response generation time
        # Disabled for now due to OTEL selector limitations
        # f_latency = (
        #     Feedback(
        #         self._latency_feedback,
        #         name="Latency (seconds)"
        #     )
        # )
        # feedbacks.append(f_latency)

        print(f"✅ Configured {len(feedbacks)} feedback functions")
        return feedbacks

    @staticmethod
    def _fuzzy_match_citation(citation: str, expected_location: str, threshold: float = 0.6) -> bool:
        """
        Fuzzy match citation against expected location.

        Handles partial matches like:
        - "SOP-01" matches "SOP-01_Rotor_Arm_Assembly_Falcon_X1"
        - "TechNote_Firmware" matches "TechNote_Firmware_Update_v4.0"

        Args:
            citation: The citation text from the answer
            expected_location: The expected source document name
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            True if citation is a fuzzy match for expected location
        """
        if not citation or not expected_location:
            return False

        # Normalize for comparison
        citation_norm = citation.lower().strip()
        expected_norm = expected_location.lower().strip()

        # Check for substring match
        if citation_norm in expected_norm or expected_norm in citation_norm:
            return True

        # Check for prefix match (e.g., "SOP-01" vs "SOP-01_Rotor_Arm")
        if expected_norm.startswith(citation_norm) or citation_norm.startswith(expected_norm):
            return True

        # Use sequence matcher for fuzzy similarity
        similarity = SequenceMatcher(None, citation_norm, expected_norm).ratio()
        return similarity >= threshold

    def _citation_matching_feedback(self, answer: str, record) -> float:
        """
        Custom feedback function to check citation accuracy.

        Extracts citations from the answer and checks if they match
        the expected source document (with fuzzy matching).

        Args:
            answer: The generated answer text
            record: TrueLens record containing metadata

        Returns:
            1.0 if citation matches, 0.0 otherwise
        """
        try:
            # Extract expected location from metadata
            # This should be passed via app metadata when running evaluation
            metadata = record.meta if hasattr(record, 'meta') else {}
            expected_location = metadata.get('expected_location', '')

            if not expected_location:
                # No expected location to check against
                return -1.0  # Indicates N/A

            # Simple citation extraction: look for common citation patterns
            # Examples: "SOP-01", "(SOP-01)", "Source: SOP-01", etc.
            # For a more robust approach, you might use regex or NER

            # Check if expected location (or prefix) appears in the answer
            answer_lower = answer.lower()
            expected_lower = expected_location.lower()

            # Extract potential citation by splitting expected location
            # e.g., "SOP-01_Rotor_Arm_Assembly" → check for "SOP-01"
            location_parts = expected_location.replace('_', ' ').split()

            for part in location_parts:
                if len(part) > 3:  # Avoid matching tiny words
                    if self._fuzzy_match_citation(part, expected_location):
                        if part.lower() in answer_lower:
                            return 1.0

            # Also check full location name
            if expected_lower in answer_lower:
                return 1.0

            return 0.0

        except Exception as e:
            print(f"⚠️  Citation matching error: {e}")
            return -1.0

    def _latency_feedback(self, record) -> float:
        """
        Custom feedback function to track response latency.

        Args:
            record: TrueLens record containing timing information

        Returns:
            Latency in seconds, or -1.0 if timing info unavailable
        """
        try:
            # TrueLens records start and end times
            if hasattr(record, 'start_time') and hasattr(record, 'end_time'):
                latency = (record.end_time - record.start_time).total_seconds()
                return latency

            # Fallback: look for timing in metadata
            metadata = record.meta if hasattr(record, 'meta') else {}
            if 'latency' in metadata:
                return metadata['latency']

            return -1.0  # Timing info not available

        except Exception as e:
            print(f"⚠️  Latency tracking error: {e}")
            return -1.0

    def reset_session(self) -> None:
        """
        Reset the TrueLens session and clear all evaluation data.

        WARNING: This will delete all stored evaluations and feedback.
        """
        if self.session:
            print("⚠️  Resetting TrueLens session...")
            self.session.reset_database()
            print("✅ Session reset complete")
        else:
            print("⚠️  No active session to reset")


# Helper functions for easy import and usage

def initialize_trulens(
    database_path: str = "trulens_eval.db",
    evaluation_model: Optional[str] = None,
    reset: bool = False
) -> Tuple[TruSession, List[Feedback]]:
    """
    Initialize TrueLens and get configured feedback functions.

    This is the main entry point for setting up TrueLens evaluation.

    Args:
        database_path: Path to TrueLens database
        evaluation_model: Model name for evaluation (defaults to env var)
        reset: Whether to reset existing session

    Returns:
        Tuple of (TruSession, list of Feedback functions)

    Example:
        >>> session, feedbacks = initialize_trulens()
        >>> # Use session and feedbacks to wrap RAG chain
    """
    config = TrueLensConfig(database_path, evaluation_model)
    session = config.initialize_session(reset=reset)
    feedbacks = config.get_feedback_functions()

    return session, feedbacks


def get_feedback_functions(evaluation_model: Optional[str] = None) -> List[Feedback]:
    """
    Get configured feedback functions without initializing session.

    Args:
        evaluation_model: Model name for evaluation

    Returns:
        List of configured Feedback objects
    """
    config = TrueLensConfig(evaluation_model=evaluation_model)
    return config.get_feedback_functions()


def reset_trulens_database(database_path: str = "trulens_eval.db") -> None:
    """
    Reset TrueLens database, clearing all evaluation data.

    Args:
        database_path: Path to database to reset
    """
    config = TrueLensConfig(database_path=database_path)
    config.initialize_session(reset=True)


if __name__ == "__main__":
    # Test the configuration
    print("=" * 60)
    print("TrueLens Configuration Test")
    print("=" * 60)

    # Initialize
    session, feedbacks = initialize_trulens(reset=False)

    print(f"\n📊 Session: {session}")
    print(f"📋 Feedback functions: {len(feedbacks)}")
    for fb in feedbacks:
        print(f"  - {fb.name}")

    print("\n✅ Configuration test complete!")
