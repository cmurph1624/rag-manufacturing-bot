import os
import chromadb
import ollama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = "./chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"
GENERATION_MODEL = "llama3.2"

# Globals (Lazy loaded)
chroma_client = None
collection = None

def get_chroma_collection():
    global chroma_client, collection
    if collection is None:
        print(f"Connecting to ChromaDB at '{DB_PATH}'...")
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    return collection

from typing import Dict, Any

def generate_answer(user_query: str) -> Dict[str, Any]:
    """
    Core RAG logic:
    1. Embed query
    2. Search ChromaDB
    3. Generate answer with Ollama
    4. Format with citations
    """
    try:
        # Step B: Search
        # Generate embedding for the query
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=user_query)
        query_embedding = response.get("embedding")

        if not query_embedding:
            return "Error: Failed to generate embedding for search."

        # Query ChromaDB (Get top 7 results)
        col = get_chroma_collection()
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=7
        )

        documents = results["documents"][0] # list of strings

        print(f"\n--- DEBUG: Retrieved Context for '{user_query}' ---")
        for doc in documents:
            print(doc[:200] + "...") # Print first 200 chars
        print("--------------------------------\n")
        metadatas = results["metadatas"][0] # list of dicts

        if not documents:
            return "I couldn't find any relevant documents in the database."

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
        # Note: ollama.chat might assume a running server.
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
        }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "retrieved_chunks": [],
            "model": GENERATION_MODEL,
            "error": str(e)
        }
