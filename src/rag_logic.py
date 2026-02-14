import ollama
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
import os
import time

# LangChain Imports
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# TrueLens Imports
from trulens.apps.langchain.tru_chain import TruChain
from trulens.core import Feedback

# Custom Imports
from src.retrieval import RetrievalFactory
from src.llm import LLMFactory
from src.trulens_config import initialize_trulens

# Load environment variables
load_dotenv()

# Configuration
GENERATION_MODEL = os.getenv("LLM_MODEL_NAME", "llama")
DEFAULT_RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "semantic")

# TrueLens global state (initialized when needed)
_TRULENS_SESSION = None
_TRULENS_FEEDBACKS = None
_TRU_CHAIN_REFS = [] # Store references to prevent GC


def _initialize_trulens_if_needed(database_path: str = "data/databases/trulens_eval.db") -> None:
    """
    Initialize TrueLens session and feedback functions if not already initialized.

    This function is called automatically when TrueLens tracking is enabled.
    It initializes the global TrueLens state only once per session.

    Args:
        database_path: Path to TrueLens SQLite database
    """
    global _TRULENS_SESSION, _TRULENS_FEEDBACKS

    if _TRULENS_SESSION is None or _TRULENS_FEEDBACKS is None:
        print("🔄 Initializing TrueLens for the first time...")
        _TRULENS_SESSION, _TRULENS_FEEDBACKS = initialize_trulens(
            database_path=database_path,
            reset=False
        )
        print("✅ TrueLens initialized successfully")


def get_instrumented_rag_chain(
    retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY,
    app_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TruChain:
    """
    Create a TrueLens-instrumented RAG chain for evaluation.

    This function builds a LangChain RAG pipeline and wraps it with TruChain
    to enable automatic tracking of:
    - Input queries
    - Retrieved contexts
    - Generated answers
    - Model and retrieval strategy used
    - Latencies and timestamps

    Args:
        retrieval_strategy_type: Retrieval strategy to use (e.g., "semantic", "lexical")
        app_id: Unique identifier for this evaluation run (e.g., "eval_run_20250210_1430")
        metadata: Additional metadata to attach to the evaluation record
                 (e.g., {"expected_location": "SOP-01_Rotor_Arm"})

    Returns:
        TruChain: Instrumented RAG chain ready for evaluation

    Example:
        >>> chain = get_instrumented_rag_chain(
        ...     retrieval_strategy_type="semantic",
        ...     app_id="eval_semantic_2025",
        ...     metadata={"expected_location": "SOP-01"}
        ... )
        >>> result = chain.invoke({"input": "What is the assembly process?"})
    """
    # Initialize TrueLens if needed
    _initialize_trulens_if_needed()

    # Build the RAG chain components
    llm = LLMFactory.get_llm(GENERATION_MODEL)
    retriever = RetrievalFactory.get_strategy(retrieval_strategy_type)

    # Define prompt template
    system_prompt = (
        "You are a helpful manufacturing support assistant. "
        "Answer the question using ONLY the following context. "
        "If you don't know, say you don't know."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # Create chains
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    # Wrap with TruChain for instrumentation
    app_id = app_id or f"rag_bot_{retrieval_strategy_type}_{int(time.time())}"

    tru_chain = TruChain(
        app=rag_chain,
        app_name=app_id,
        feedbacks=_TRULENS_FEEDBACKS,
        metadata=metadata or {}
    )

    print(f"✅ Created instrumented RAG chain: {app_id}")
    return tru_chain


def generate_answer(
    user_query: str,
    retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY,
    enable_trulens: bool = False,
    app_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Core RAG logic using LangChain with optional TrueLens instrumentation.

    This function performs the following steps:
    1. Safety Check (Raw Ollama Call with Llama Guard)
    2. Build RAG Chain (Retriever + LLM)
    3. Invoke Chain (with or without TrueLens tracking)
    4. Format Response with Citations

    The return format is ALWAYS consistent regardless of TrueLens being enabled:
    {
        "answer": str,              # Generated answer with citations
        "retrieved_chunks": list,   # List of retrieved document texts
        "model": str,               # LLM model used
        "retrieval_type": str       # Retrieval strategy used
    }

    Args:
        user_query: The user's question/query
        retrieval_strategy_type: Retrieval strategy to use (default: from env var)
        enable_trulens: If True, wraps chain with TrueLens for evaluation tracking
        app_id: Unique identifier for TrueLens tracking (only used if enable_trulens=True)
        metadata: Additional metadata for TrueLens (e.g., {"expected_location": "SOP-01"})

    Returns:
        Dict with keys: answer, retrieved_chunks, model, retrieval_type

    Example (Normal Usage):
        >>> result = generate_answer("What is the assembly process?")
        >>> print(result["answer"])

    Example (With TrueLens Evaluation):
        >>> result = generate_answer(
        ...     "What is the assembly process?",
        ...     enable_trulens=True,
        ...     app_id="eval_run_20250210",
        ...     metadata={"expected_location": "SOP-01"}
        ... )
    """
    try:
        # Step A: Safety Check
        print("Checking safety with Llama Guard (1B)...")
        start_time = time.time()
        
        # Use local 1B model which is faster/lighter
        # keep_alive=0 ensures we don't hog VRAM if not needed
        safety_response = ollama.chat(model='llama-guard3:1b', messages=[
            {'role': 'user', 'content': user_query},
        ], keep_alive=0)
        
        print(f"Safety check complete in {time.time() - start_time:.2f}s")
        
        # Check if response indicates unsafe content
        if 'unsafe' in safety_response['message']['content'].strip().lower():
             print(f"Unsafe request detected: {safety_response['message']['content']}")
             return {
                 "answer": "I am unable to help with this request as it has been deemed unsafe",
                 "retrieved_chunks": [],
                 "model": "llama-guard3:1b",
                 "retrieval_type": "blocked",
                 "trulens_record_id": None
             }


        # Step B: Build LangChain RAG Pipeline
        print(f"Initializing LangChain RAG (Model: {GENERATION_MODEL}, Strategy: {retrieval_strategy_type})...")

        # Step C: Invoke Chain (with or without TrueLens)
        if enable_trulens:
            print("🔍 TrueLens tracking ENABLED")

            # Initialize TrueLens if not already done
            _initialize_trulens_if_needed()

            # Get instrumented chain
            tru_chain = get_instrumented_rag_chain(
                retrieval_strategy_type=retrieval_strategy_type,
                app_id=app_id,
                metadata=metadata
            )

            # Keep strong reference to prevent GC of the chain object
            # This is critical because TruLens feedback runs in a background thread
            # and holds a weak reference to the app.
            _TRU_CHAIN_REFS.append(tru_chain)

            # Invoke with TrueLens context (automatically records to database)
            print(f"Invoking instrumented chain for query: '{user_query}'...")
            with tru_chain as recording:
                response = tru_chain.app.invoke({"input": user_query})
            
            # Get the record ID for feedback retrieval
            record = recording.get()
            trulens_record_id = record.record_id if record else None
            print(f"✅ TrueLens recording completed (Record ID: {trulens_record_id})")
        else:
            # Normal execution without TrueLens
            trulens_record_id = None
            # 1. Get Components
            llm = LLMFactory.get_llm(GENERATION_MODEL)
            retriever = RetrievalFactory.get_strategy(retrieval_strategy_type)

            # 2. Define Prompt
            system_prompt = (
                "You are a helpful manufacturing support assistant. "
                "Answer the question using ONLY the following context. "
                "If you don't know, say you don't know."
                "\n\n"
                "{context}"
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])

            # 3. Create Chains
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)

            # 4. Invoke Chain
            print(f"Invoking chain for query: '{user_query}'...")
            response = rag_chain.invoke({"input": user_query})
        
        answer = response["answer"]
        documents = response["context"] # List of Document objects

        # Step D: Citations and Formatting
        # Re-convert documents to string list for compatibility with existing return format
        doc_texts = [doc.page_content for doc in documents]
        
        print(f"\n--- DEBUG: Retrieved Context (LangChain) ---")
        for d in doc_texts:
            print(d[:200] + "...")
        print("--------------------------------\n")
        
        if not documents:
             return {
                 "answer": "I couldn't find any relevant documents in the database.",
                 "retrieved_chunks": [],
                 "retrieval_type": retrieval_strategy_type,
                 "trulens_record_id": None
            }

        citations = []
        seen_sources = set()
        metadatas = [doc.metadata for doc in documents] # Extract metadata
        
        for meta in metadatas:
            source = meta.get("source", "Unknown")
            page = meta.get("page_number", "Unknown")
            citation_key = f"{source}:{page}"
            if citation_key not in seen_sources:
                citations.append(f"• {source} (Page {page})")
                seen_sources.add(citation_key)
        
        citation_text = "\n\n*References:*\n" + "\n".join(citations)
        final_answer = f"{answer}{citation_text}"
        
        return {
            "answer": final_answer,
            "retrieved_chunks": doc_texts,
            "model": GENERATION_MODEL,
            "retrieval_type": retrieval_strategy_type,
            "trulens_record_id": trulens_record_id
        }

    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "retrieved_chunks": [],
            "model": GENERATION_MODEL,
            "retrieval_type": retrieval_strategy_type,
            "retrieval_type": retrieval_strategy_type,
            "error": str(e),
            "trulens_record_id": None
        }
