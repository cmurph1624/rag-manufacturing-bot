import ollama
from dotenv import load_dotenv
from typing import Dict, Any
from retrieval import RetrievalFactory

# Load environment variables
load_dotenv()

# Configuration
GENERATION_MODEL = "llama3.2"
DEFAULT_RETRIEVAL_STRATEGY = "semantic"

def generate_answer(user_query: str, retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY) -> Dict[str, Any]:
    """
    Core RAG logic using the Strategy Pattern for retrieval.
    1. Retrieve context using selected strategy
    2. Generate answer with Ollama
    3. Format with citations
    """
    try:
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
                 "model": GENERATION_MODEL
            }

        # Combine documents into context text
        context_text = "\n\n---\n\n".join(documents)

        # Step C: Construct Prompt
        system_instruction = (
            "You are a helpful manufacturing support assistant. "
            "Answer the question using ONLY the following context. "
            "If you don't know, say you don't know."
        )
        
        user_prompt_content = f"Context:\n{context_text}\n\nQuestion: {user_query}"

        # Step D: Generate
        print("Sending prompt to Ollama...")
        response = ollama.chat(model=GENERATION_MODEL, messages=[
            {'role': 'system', 'content': system_instruction},
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
