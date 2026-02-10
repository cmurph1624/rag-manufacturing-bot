import ollama
from dotenv import load_dotenv
from typing import Dict, Any
import os
import time

# LangChain Imports
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# Custom Imports
from retrieval import RetrievalFactory
from llm import LLMFactory

# Load environment variables
load_dotenv()

# Configuration
GENERATION_MODEL = os.getenv("LLM_MODEL_NAME", "llama")
DEFAULT_RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "semantic")

def generate_answer(user_query: str, retrieval_strategy_type: str = DEFAULT_RETRIEVAL_STRATEGY) -> Dict[str, Any]:
    """
    Core RAG logic using LangChain.
    1. Safety Check (Raw Ollama Call)
    2. Build RAG Chain (Retriever + LLM)
    3. Invoke Chain
    4. Format Response with Citations
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
                 "retrieval_type": "blocked"
             }


        # Step B: Build LangChain RAG Pipeline
        print(f"Initializing LangChain RAG (Model: {GENERATION_MODEL}, Strategy: {retrieval_strategy_type})...")
        
        # 1. Get Components
        llm = LLMFactory.get_llm(GENERATION_MODEL)
        retriever = RetrievalFactory.get_strategy(retrieval_strategy_type)
        
        # 2. define Prompt
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
        
        # Step C: Invoke Chain
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
                 "model": GENERATION_MODEL,
                 "retrieval_type": retrieval_strategy_type
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
            "retrieval_type": retrieval_strategy_type # passing string name back
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
            "error": str(e)
        }
