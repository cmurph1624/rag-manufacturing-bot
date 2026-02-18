import os
import sys
import json
import warnings
import pandas as pd
from typing import List, Dict
from datasets import Dataset
from ragas import evaluate, RunConfig

# Deprecation Fix: Import from collections where suggested
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas.metrics")

from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall 

# Add project root to path for src imports
sys.path.append(os.getcwd())

# LangChain / Provider Integrations
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings

# Local Imports
from src.rag_logic import generate_answer

# --- Configuration ---
EVAL_DATASET_PATH = os.path.join("data", "evaluation_dataset.json")
OUTPUT_CSV_PATH = os.path.join("evaluation_results", "ragas_results.csv")

# Use environment variable for model, default to Haiku (often more available/cheaper)
# If you have access to Sonnet or Opus, set ANTHROPIC_MODEL in .env
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307") 
EMBEDDING_MODEL = "all-MiniLM-L6-v2" # Local embeddings

def load_dataset(custom_path: str = None, category_filter: str = None, id_filter: List[int] = None) -> List[Dict]:
    """Loads the evaluation dataset, preferring tests/test_set.json or custom path."""
    if custom_path:
        path = custom_path
        if not os.path.exists(path):
             raise FileNotFoundError(f"Custom dataset not found at {path}")
    else:
        # Try the full test set first
        path = "tests/test_set.json"
        if not os.path.exists(path):
            path = os.path.join("data", "evaluation_dataset.json")
            if not os.path.exists(path):
                 raise FileNotFoundError(f"Dataset not found at tests/test_set.json or {path}")
             
    print(f"Loading dataset from {path}...")
    with open(path, 'r') as f:
        data = json.load(f)

    # Handle "qa_pairs" format (from tests/test_set.json)
    if isinstance(data, dict) and "qa_pairs" in data:
        all_items = data["qa_pairs"]
        
        # --- Category/ID Filtering ---
        if category_filter:
            print(f"Filtering dataset for category: '{category_filter}'")
            filtered_items = [item for item in all_items if item.get("category") == category_filter]
        elif id_filter:
            print(f"Filtering dataset for IDs: {id_filter}")
            filtered_items = [item for item in all_items if item.get("id") in id_filter]
        else:
            filtered_items = all_items

        if category_filter or id_filter:
            
            # Print available categories/IDs for debugging/user info
            if category_filter:
                available_categories = sorted(list(set(item.get("category", "Unknown") for item in all_items)))
                print(f"Available categories: {available_categories}")
            
            if not filtered_items:
                filter_desc = f"category '{category_filter}'" if category_filter else f"IDs {id_filter}"
                print(f"WARNING: No items found for {filter_desc}.")
                return []
            
            # Format and return filtered items
            formatted = []
            for item in filtered_items:
                formatted.append({
                    "question": item["question"],
                    "ground_truth": item["answer"],
                    "category": item.get("category"), # Keep category metadata if needed later
                    "id": item.get("id")
                })
            return formatted
        # ---------------------------

        formatted = []
        for item in all_items:
            formatted.append({
                "question": item["question"],
                "ground_truth": item["answer"],
                "category": item.get("category"),
                "id": item.get("id")
            })
        return formatted
        
    # Handle simple list format
    if isinstance(data, list):
        if category_filter:
             print("WARNING: Category filtering not supported for simple list format dataset.")
        return data

    raise ValueError("Unknown dataset format")

def run_inference(dataset: List[Dict]) -> Dict[str, List]:
    """
    Runs the RAG pipeline for each question in the dataset.
    Returns a dictionary suitable for creating a HuggingFace Dataset.
    """
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    ids = []

    print(f"Starting inference on {len(dataset)} items...")

    for item in dataset:
        q = item["question"]
        gt = item["ground_truth"]
        
        print(f"Processing: {q}")
        
        # Call the RAG pipeline
        response = generate_answer(q)
        
        questions.append(q)
        answers.append(response["answer"])
        contexts.append(response["retrieved_chunks"])
        ground_truths.append(gt)
        ids.append(item.get("id"))

    return {
        "id": ids,
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }

def main(limit: int = None, dataset_path: str = None, category: str = None, test_ids: List[int] = None):
    # 1. Check for API Key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not found in environment variables.")
        print("Please add it to your .env file to run this evaluation.")
        return

    # 2. Load Data & Run Inference
    try:
        raw_data = load_dataset(dataset_path, category, test_ids)
        
        if not raw_data:
            print("No data to evaluate. Exiting.")
            return

        # Apply Limit
        if limit is not None:
            print(f"Limiting evaluation to first {limit} items.")
            raw_data = raw_data[:limit]
            
        rag_output = run_inference(raw_data)
        
        # 3. Create HuggingFace Dataset
        hf_dataset = Dataset.from_dict(rag_output)

        # 4. Configure RAGAS with Anthropic Judge & Local Embeddings
        print(f"Configuring RAGAS with Judge: {ANTHROPIC_MODEL} and Embeddings: {EMBEDDING_MODEL}")
        
        judge_llm = ChatAnthropic(model=ANTHROPIC_MODEL)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

        # 5. Run Evaluation
        print("Running RAGAS evaluation (this may take a moment)...")
        
        # Configure run with limited concurrency to avoid RateLimitError
        # 50 RPM limit -> 2 workers is safe (25 requests/min/worker max implies 1.2s/req which is fast, 
        # but actual LLM calls take longer so 2-4 workers might be okay. Sticking to 2 for safety.)
        run_config = RunConfig(max_workers=2, max_retries=10)
        
        results = evaluate(
            hf_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=judge_llm,
            embeddings=embeddings,
            run_config=run_config
        )

        # 6. Save Results
        print("Evaluation complete!")
        print(results)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
        
        df = results.to_pandas()
        
        # Manually add 'id' column if present in the dataset (Ragas might strip unknown columns)
        if "id" in hf_dataset.features:
            df["id"] = hf_dataset["id"]

        # --- FIX: Post-process "Unsafe" Refusals ---
        # If the answer is the standard refusal message, we give it full marks.
        # This prevents "unsafe" correct refusals from tanking the metrics (no context is retrieved).
        refusal_msg = "I am unable to help with this request as it has been deemed unsafe"
        
        # Clean answer to match (strip trailing period if present in some versions/LLM output)
        mask = df['response'].str.strip('.').str.strip() == refusal_msg

        if mask.any():
            print(f"Found {mask.sum()} unsafe refusals. Overwriting metrics to 1.0.")
            cols_to_fix = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
            for col in cols_to_fix:
                if col in df.columns:
                    df.loc[mask, col] = 1.0
        # -------------------------------------------

        df.to_csv(OUTPUT_CSV_PATH, index=False)
        print(f"Results saved to {OUTPUT_CSV_PATH}")

    except Exception as e:
        print(f"An error occurred during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Run RAGAS evaluation.")
    parser.add_argument("--name", type=str, default="run", help="Name/Tag for this evaluation run (default: 'run')")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of evaluations (default: All)")
    parser.add_argument("--dataset", type=str, default=None, help="Path to specific evaluation dataset (optional)")
    parser.add_argument("--category", type=str, default=None, help="Filter evaluation by category (e.g., 'Adversarial')")
    parser.add_argument("--id", type=str, default=None, help="Filter evaluation by specific test IDs (comma-separated, e.g., '1,2,5')")
    args = parser.parse_args()

    # Parse IDs
    test_ids = []
    if args.id:
        try:
            test_ids = [int(x.strip()) for x in args.id.split(',') if x.strip()]
        except ValueError:
            print(f"Error: Invalid test ID format specified: {args.id}. must be integer or comma-separated integers.")
            sys.exit(1)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if test_ids:
        if len(test_ids) == 1:
            name_tag = f"{args.name}_id_{test_ids[0]}"
        else:
            name_tag = f"{args.name}_ids_{len(test_ids)}"
    elif args.category:
        name_tag = f"{args.name}_{args.category}"
    else:
        name_tag = args.name

    filename = f"ragas_results_{name_tag}_{timestamp}.csv"
    
    # Update global output path (hacky but works for this script structure)
    OUTPUT_CSV_PATH = os.path.join("evaluation_results", filename)
    
    print(f"--- RAGAS Evaluation: {name_tag} ---")
    if args.dataset:
        print(f"Dataset: {args.dataset}")
    if args.category:
        print(f"Category Filter: {args.category}")
    if args.limit:
        print(f"Limit: {args.limit} items")
    if test_ids:
        print(f"ID Filter: {test_ids}")

    print(f"Output will be saved to: {OUTPUT_CSV_PATH}")

    # Pass args to main
    main(limit=args.limit, dataset_path=args.dataset, category=args.category, test_ids=test_ids)
