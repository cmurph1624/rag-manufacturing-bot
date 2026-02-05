import ollama
from dotenv import load_dotenv
from typing import Dict, Any
from retrieval import RetrievalFactory

# Load environment variables
load_dotenv()

# Configuration
import os

# Configuration
GENERATION_MODEL = "llama3.2"
DEFAULT_RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "semantic")

def generate_answer(user_query: str, retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY) -> Dict[str, Any]:
    """
    Core RAG logic using the Strategy Pattern for retrieval.
    1. Retrieve context using selected strategy
    2. Generate answer with Ollama
    3. Format with citations
    """
    try:
        # Step A: Safety Check
        print("Checking safety with Llama Guard (1B)...")
        import time
        start_time = time.time()
        
        # Use local 1B model which is faster/lighter
        # keep_alive=0 ensures we don't hog VRAM if not needed, though 1B is small.
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
                 "retrieval_type": "blocked"
             }


        # Step B: Search (using Strategy)
        strategy = RetrievalFactory.get_strategy(retrieval_strategy_type)
        retrieval_result = strategy.retrieve(user_query)
        
        documents = retrieval_result.documents
        metadatas = retrieval_result.metadatas

        print(f"\n--- DEBUG: Retrieved Context for '{user_query}' [{retrieval_strategy_type}] ---")
        for doc in documents:
            print(doc[:200] + "...") # Print first 200 chars
        print("--------------------------------\n")

        if not documents:
            return {
                 "answer": "I couldn't find any relevant documents in the database.",
                 "retrieved_chunks": [],
                 "model": GENERATION_MODEL,
                 "retrieval_type": retrieval_strategy_type
            }

        # Combine documents into context text
        context_text = "\n\n---\n\n".join(documents)

        # Step C: Construct Prompt
        from prompts.answer_prompt import SYSTEM_INSTRUCTION, format_user_prompt
        
        user_prompt_content = format_user_prompt(context_text, user_query)

        # Step D: Generate
        print("Sending prompt to Ollama...")
        response = ollama.chat(model=GENERATION_MODEL, messages=[
            {'role': 'system', 'content': SYSTEM_INSTRUCTION},
            {'role': 'user', 'content': user_prompt_content},
        ])

        answer = response['message']['content']

        # Step F: Citations
        citations = []
        seen_sources = set()
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
            "retrieved_chunks": documents,
            "model": GENERATION_MODEL,
            "retrieval_type": strategy.type
        }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "retrieved_chunks": [],
            "model": GENERATION_MODEL,
            "retrieval_type": retrieval_strategy_type,
            "error": str(e)
        }
