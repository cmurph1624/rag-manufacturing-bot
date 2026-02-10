from src.rag_logic import generate_answer
import sys

try:
    print("Testing generate_answer with 'semantic' strategy...")
    result = generate_answer("What is the safety protocol?", retrieval_strategy_type="semantic")
    print("\nResult Keys:", result.keys())
    print("Answer Preview:", result["answer"][:100])
    print("Num Chunks:", len(result["retrieved_chunks"]))
    
    if "error" in result:
        print("ERROR FOUND:", result["error"])
        sys.exit(1)
        
    print("\nSUCCESS: Basic RAG call worked.")
except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
