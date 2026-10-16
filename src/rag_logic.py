import ollama
from functools import lru_cache
from typing import Dict, Any
import time
import traceback

# LangChain Imports
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Custom Imports
from src.retrieval import RetrievalFactory
from src.llm import LLMFactory
from src.prompts.answer_prompt import SYSTEM_INSTRUCTION
from src.config import RETRIEVAL_STRATEGY, LLM_MODEL_NAME
from src.formatting import format_citations

# Configuration
GENERATION_MODEL = LLM_MODEL_NAME
DEFAULT_RETRIEVAL_STRATEGY = RETRIEVAL_STRATEGY
SAFETY_MODEL = "llama-guard3:1b"

REFUSAL_MESSAGE = "I am unable to help with this request as it has been deemed unsafe"
ERROR_MESSAGE = "Sorry, something went wrong while answering that. Please try again shortly."


@lru_cache(maxsize=None)
def _get_rag_chain(retrieval_strategy_type: str, model_name: str):
    """
    Builds the retriever + LLM chain once per (strategy, model).
    Building is expensive (the reranker loads a cross-encoder and the lexical
    retriever builds a BM25 index), so it is reused across queries.
    """
    print(f"Initializing LangChain RAG (Model: {model_name}, Strategy: {retrieval_strategy_type})...")
    llm = LLMFactory.get_llm(model_name)
    retriever = RetrievalFactory.get_strategy(retrieval_strategy_type)

    # create_stuff_documents_chain fills {context} with the retrieved chunks
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_INSTRUCTION + "\n\n{context}"),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, question_answer_chain)


def is_unsafe(user_query: str) -> bool:
    """Classifies the query with Llama Guard, which replies 'safe' or 'unsafe\\n<category>'."""
    # keep_alive=0 unloads the guard model right away so it doesn't hold VRAM
    response = ollama.chat(model=SAFETY_MODEL, messages=[
        {'role': 'user', 'content': user_query},
    ], keep_alive=0)
    verdict = response['message']['content'].strip().lower()
    if verdict.startswith("unsafe"):
        print(f"Unsafe request detected: {verdict}")
        return True
    return False


def generate_answer(
    user_query: str,
    retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY
) -> Dict[str, Any]:
    """
    Core RAG logic using LangChain.

    This function performs the following steps:
    1. Safety Check (Llama Guard via Ollama)
    2. Retrieve context and generate an answer (cached LangChain chain)
    3. Append citations for the retrieved sources

    The return format is:
    {
        "answer": str,              # Generated answer with citations
        "retrieved_chunks": list,   # List of retrieved document texts
        "model": str,               # LLM model used
        "retrieval_type": str,      # Retrieval strategy used
        "error": str                # Only present if something failed
    }
    """
    try:
        # Step A: Safety Check
        start_time = time.time()
        if is_unsafe(user_query):
            return {
                "answer": REFUSAL_MESSAGE,
                "retrieved_chunks": [],
                "model": SAFETY_MODEL,
                "retrieval_type": "blocked"
            }
        print(f"Safety check complete in {time.time() - start_time:.2f}s")

        # Step B: Retrieve + Generate
        rag_chain = _get_rag_chain(retrieval_strategy_type, GENERATION_MODEL)
        response = rag_chain.invoke({"input": user_query})

        answer = response["answer"]
        documents = response["context"]  # List of Document objects

        if not documents:
            return {
                "answer": "I couldn't find any relevant documents in the database.",
                "retrieved_chunks": [],
                "model": GENERATION_MODEL,
                "retrieval_type": retrieval_strategy_type
            }

        # Step C: Citations
        return {
            "answer": answer + format_citations(doc.metadata for doc in documents),
            "retrieved_chunks": [doc.page_content for doc in documents],
            "model": GENERATION_MODEL,
            "retrieval_type": retrieval_strategy_type
        }

    except Exception as e:
        # Details go to the server log and the "error" field, never to the end user
        print(f"Error processing request: {e}")
        traceback.print_exc()
        return {
            "answer": ERROR_MESSAGE,
            "retrieved_chunks": [],
            "model": GENERATION_MODEL,
            "retrieval_type": retrieval_strategy_type,
            "error": str(e)
        }
