"""
TrueLens-based RAG Evaluation Runner

This script evaluates the RAG system using TrueLens instrumentation and feedback functions.
It loads a test set of Q&A pairs, runs them through the instrumented RAG pipeline,
and stores all evaluation results in the TrueLens database.

Features:
- Loads test set from test_set.json (50 QA pairs)
- Uses TrueLens feedback functions for automatic evaluation
- Tracks metadata: category, expected_location, gold_answer
- Measures latency and retrieval performance
- Supports multiple models and retrieval strategies
- Command-line arguments for flexible testing
- Progress tracking with tqdm
- Graceful error handling

Usage:
    # Run full evaluation with defaults
    python evaluate_trulens.py

    # Test with subset of questions
    python evaluate_trulens.py --limit 5

    # Use specific model and retrieval strategy
    python evaluate_trulens.py --model llama3.2 --retrieval semantic-rerank

    # Custom app identifier
    python evaluate_trulens.py --app-id eval_production_2025

Author: RAG Manufacturing Bot Team
"""

import sys
import time
import json
import os
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

print(f"[{datetime.now().isoformat()}] INFO: Initializing TrueLens evaluation script...")

# Set offline mode to prevent Hugging Face/Transformers from hanging
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get project root (scripts/evaluation -> scripts -> root)
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

print(f"[{datetime.now().isoformat()}] INFO: Importing libraries...")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import dotenv: {e}")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import tqdm: {e}")
    sys.exit(1)

try:
    from trulens.core import TruSession
    from trulens.dashboard import run_dashboard
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import TrueLens: {e}")
    print("Please install: pip install trulens trulens-providers-langchain")
    sys.exit(1)

try:
    from src.rag_logic import generate_answer
    from src.trulens_config import initialize_trulens
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import internal modules: {e}")
    sys.exit(1)

# Configuration
# Configuration
TEST_SET_PATH = os.path.join(project_root, "tests", "test_set.json")
DEFAULT_DATABASE_PATH = os.path.join(project_root, "data", "databases", "trulens_eval.db")


def load_test_set(path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load test set from JSON file.

    Args:
        path: Path to test_set.json
        limit: Optional limit on number of questions to load

    Returns:
        List of Q&A pair dictionaries

    Raises:
        FileNotFoundError: If test set file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    print(f"[{datetime.now().isoformat()}] INFO: Loading test set from '{path}'...")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Test set not found at: {path}")

    with open(path, 'r') as f:
        data = json.load(f)

    qa_pairs = data.get("qa_pairs", [])

    if limit and limit > 0:
        qa_pairs = qa_pairs[:limit]
        print(f"[{datetime.now().isoformat()}] INFO: Limited to first {limit} questions")

    print(f"[{datetime.now().isoformat()}] INFO: Loaded {len(qa_pairs)} Q&A pairs")
    return qa_pairs


def extract_citation_from_answer(answer: str) -> Optional[str]:
    """
    Extract citation from answer text.

    Looks for common citation patterns in the answer:
    - References section at the end
    - Inline citations like (SOP-01)

    Args:
        answer: The generated answer text

    Returns:
        Extracted citation string or None
    """
    if not answer:
        return None

    # Look for References section
    if "*References:*" in answer:
        # Extract everything after References
        ref_section = answer.split("*References:*")[1].strip()
        # Get first line (first citation)
        lines = ref_section.split("\n")
        if lines:
            first_citation = lines[0].strip()
            # Extract source name (before " (Page")
            if " (Page" in first_citation:
                return first_citation.split(" (Page")[0].replace("•", "").strip()

    return None


def check_citation_match(answer: str, expected_location: str) -> bool:
    """
    Check if answer contains correct citation.

    Uses fuzzy matching to handle partial matches:
    - "SOP-01" matches "SOP-01_Rotor_Arm_Assembly_Falcon_X1"
    - Case-insensitive matching

    Args:
        answer: The generated answer with citations
        expected_location: Expected source document name

    Returns:
        True if citation matches expected location
    """
    if not answer or not expected_location or expected_location == "N/A":
        return False

    answer_lower = answer.lower()
    expected_lower = expected_location.lower()

    # Direct substring match
    if expected_lower in answer_lower:
        return True

    # Check for prefix match (e.g., "SOP-01" in "SOP-01_Rotor_Arm")
    # Split on underscore and check each part
    parts = expected_location.split("_")
    for part in parts:
        if len(part) > 3:  # Avoid matching tiny words
            if part.lower() in answer_lower:
                return True

    return False


def run_evaluation(
    qa_pairs: List[Dict[str, Any]],
    model_name: str,
    retrieval_strategy: str,
    app_id: str,
    database_path: str = DEFAULT_DATABASE_PATH
) -> Dict[str, Any]:
    """
    Run evaluation on all Q&A pairs with TrueLens instrumentation.

    For each question:
    1. Call generate_answer() with TrueLens enabled
    2. Track metadata (category, expected_location, gold_answer)
    3. Measure latency
    4. Check citation accuracy
    5. Store in TrueLens database

    Args:
        qa_pairs: List of Q&A dictionaries from test set
        model_name: LLM model to use for generation
        retrieval_strategy: Retrieval strategy (semantic, lexical, etc.)
        app_id: Unique identifier for this evaluation run
        database_path: Path to TrueLens database

    Returns:
        Dictionary containing evaluation results and statistics
    """
    print(f"\n{'='*60}")
    print(f"Starting TrueLens Evaluation")
    print(f"{'='*60}")
    print(f"App ID: {app_id}")
    print(f"Model: {model_name}")
    print(f"Retrieval Strategy: {retrieval_strategy}")
    print(f"Total Questions: {len(qa_pairs)}")
    print(f"Database: {database_path}")
    print(f"{'='*60}\n")

    # Initialize TrueLens
    print(f"[{datetime.now().isoformat()}] INFO: Initializing TrueLens...")
    session, feedbacks = initialize_trulens(
        database_path=database_path,
        reset=False
    )
    print(f"[{datetime.now().isoformat()}] INFO: TrueLens initialized with {len(feedbacks)} feedback functions")

    # Track results
    results = []
    latencies = []
    citation_matches = 0
    category_stats = defaultdict(lambda: {"total": 0, "errors": 0})
    errors = []

    # Progress bar
    print(f"\n[{datetime.now().isoformat()}] INFO: Starting evaluation loop...\n")

    for i, item in enumerate(tqdm(qa_pairs, desc="Evaluating", unit="question")):
        question = item["question"]
        gold_answer = item["answer"]
        expected_location = item.get("location", "N/A")
        category = item.get("category", "Unknown")

        # Update category stats
        category_stats[category]["total"] += 1

        # Prepare metadata for TrueLens
        metadata = {
            "question_id": i,
            "category": category,
            "expected_location": expected_location,
            "gold_answer": gold_answer,
            "retrieval_strategy": retrieval_strategy,
            "model": model_name
        }

        print(f"\n[{datetime.now().isoformat()}] INFO: [{i+1}/{len(qa_pairs)}] Processing: {question[:80]}...")

        # Run RAG with TrueLens instrumentation
        start_time = time.time()
        try:
            response_data = generate_answer(
                user_query=question,
                retrieval_strategy_type=retrieval_strategy,
                enable_trulens=True,
                app_id=app_id,
                metadata=metadata
            )

            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)

            bot_answer = response_data.get("answer", "")
            retrieved_chunks = response_data.get("retrieved_chunks", [])

            # Check citation
            citation_match = check_citation_match(bot_answer, expected_location)
            if citation_match:
                citation_matches += 1

            print(f"[{datetime.now().isoformat()}] INFO: ✓ Completed in {latency:.2f}s (Citation: {'✓' if citation_match else '✗'})")

            # Store result
            results.append({
                "question_id": i,
                "question": question,
                "gold_answer": gold_answer,
                "bot_answer": bot_answer,
                "expected_location": expected_location,
                "category": category,
                "latency_seconds": latency,
                "citation_match": citation_match,
                "retrieved_chunks_count": len(retrieved_chunks),
                "model": model_name,
                "retrieval_strategy": retrieval_strategy,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            end_time = time.time()
            latency = end_time - start_time
            latencies.append(latency)

            error_msg = str(e)
            print(f"[{datetime.now().isoformat()}] ERROR: Failed on question {i+1}: {error_msg}")

            category_stats[category]["errors"] += 1
            errors.append({
                "question_id": i,
                "question": question,
                "error": error_msg,
                "category": category
            })

            # Store error result (still track it)
            results.append({
                "question_id": i,
                "question": question,
                "gold_answer": gold_answer,
                "bot_answer": f"ERROR: {error_msg}",
                "expected_location": expected_location,
                "category": category,
                "latency_seconds": latency,
                "citation_match": False,
                "retrieved_chunks_count": 0,
                "model": model_name,
                "retrieval_strategy": retrieval_strategy,
                "timestamp": datetime.now().isoformat(),
                "error": error_msg
            })

    # Calculate statistics
    total_questions = len(qa_pairs)
    successful_questions = total_questions - len(errors)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    citation_rate = (citation_matches / total_questions * 100) if total_questions > 0 else 0
    success_rate = (successful_questions / total_questions * 100) if total_questions > 0 else 0

    # Compile summary
    summary = {
        "app_id": app_id,
        "model": model_name,
        "retrieval_strategy": retrieval_strategy,
        "timestamp": datetime.now().isoformat(),
        "total_questions": total_questions,
        "successful_questions": successful_questions,
        "failed_questions": len(errors),
        "success_rate": success_rate,
        "avg_latency_seconds": avg_latency,
        "citation_matches": citation_matches,
        "citation_match_rate": citation_rate,
        "category_breakdown": dict(category_stats),
        "errors": errors,
        "database_path": database_path
    }

    return {
        "summary": summary,
        "results": results
    }


def print_summary(summary: Dict[str, Any]) -> None:
    """
    Print evaluation summary statistics to console.

    Args:
        summary: Summary dictionary from run_evaluation
    """
    print(f"\n\n{'='*60}")
    print(f"📊 EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"App ID: {summary['app_id']}")
    print(f"Model: {summary['model']}")
    print(f"Retrieval Strategy: {summary['retrieval_strategy']}")
    print(f"Timestamp: {summary['timestamp']}")
    print(f"\n{'─'*60}")
    print(f"📈 PERFORMANCE METRICS")
    print(f"{'─'*60}")
    print(f"Total Questions: {summary['total_questions']}")
    print(f"Successful: {summary['successful_questions']} ({summary['success_rate']:.1f}%)")
    print(f"Failed: {summary['failed_questions']}")
    print(f"Average Latency: {summary['avg_latency_seconds']:.2f}s")
    print(f"Citation Match Rate: {summary['citation_matches']}/{summary['total_questions']} ({summary['citation_match_rate']:.1f}%)")

    print(f"\n{'─'*60}")
    print(f"📂 BREAKDOWN BY CATEGORY")
    print(f"{'─'*60}")
    for category, stats in summary['category_breakdown'].items():
        error_rate = (stats['errors'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{category}:")
        print(f"  Total: {stats['total']}")
        print(f"  Errors: {stats['errors']} ({error_rate:.1f}%)")

    if summary['errors']:
        print(f"\n{'─'*60}")
        print(f"⚠️  ERRORS ({len(summary['errors'])})")
        print(f"{'─'*60}")
        for error in summary['errors'][:5]:  # Show first 5 errors
            print(f"  Q{error['question_id']+1} [{error['category']}]: {error['error'][:80]}")
        if len(summary['errors']) > 5:
            print(f"  ... and {len(summary['errors']) - 5} more errors")

    print(f"\n{'─'*60}")
    print(f"💾 TrueLens Database: {summary['database_path']}")
    print(f"{'─'*60}")
    print(f"\n✅ Evaluation complete! Results stored in TrueLens database.")
    print(f"📊 View dashboard: python -m trulens.dashboard")
    print(f"\nℹ️  TrueLens feedback functions will run asynchronously.")
    print(f"   Check the dashboard for detailed scores (Answer Relevance, Context Relevance, Groundedness).")
    print(f"{'='*60}\n")


def save_results_to_json(evaluation_data: Dict[str, Any], output_dir: str = "evaluation_results") -> str:
    """
    Save evaluation results to JSON file for reference.

    Args:
        evaluation_data: Full evaluation data with summary and results
        output_dir: Directory to save results

    Returns:
        Path to saved JSON file
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trulens_eval_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(evaluation_data, f, indent=2)

    print(f"[{datetime.now().isoformat()}] INFO: Results also saved to '{filepath}'")
    return filepath


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run RAG evaluation with TrueLens instrumentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full evaluation
  python evaluate_trulens.py

  # Test with first 5 questions
  python evaluate_trulens.py --limit 5

  # Use specific model and retrieval strategy
  python evaluate_trulens.py --model llama3.2 --retrieval semantic-rerank

  # Custom app ID
  python evaluate_trulens.py --app-id eval_production_2025
        """
    )

    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LLM_MODEL_NAME", "llama"),
        help="LLM model to use (default: from LLM_MODEL_NAME env var or 'llama')"
    )

    parser.add_argument(
        "--retrieval",
        type=str,
        default=os.getenv("RETRIEVAL_STRATEGY", "semantic"),
        choices=["semantic", "lexical", "semantic-rerank"],
        help="Retrieval strategy (default: from RETRIEVAL_STRATEGY env var or 'semantic')"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (default: all 50)"
    )

    parser.add_argument(
        "--app-id",
        type=str,
        default=None,
        help="Custom app identifier for TrueLens (default: auto-generated)"
    )

    parser.add_argument(
        "--database",
        type=str,
        default=DEFAULT_DATABASE_PATH,
        help=f"Path to TrueLens database (default: {DEFAULT_DATABASE_PATH})"
    )

    parser.add_argument(
        "--test-set",
        type=str,
        default=TEST_SET_PATH,
        help=f"Path to test set JSON file (default: {TEST_SET_PATH})"
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    print(f"[{datetime.now().isoformat()}] INFO: Starting TrueLens evaluation runner...")

    # Parse arguments
    args = parse_args()

    # Generate app ID if not provided
    if args.app_id is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.app_id = f"eval_{args.retrieval}_{args.model}_{timestamp}"

    # Set environment variables for RAG system
    os.environ["LLM_MODEL_NAME"] = args.model
    os.environ["RETRIEVAL_STRATEGY"] = args.retrieval

    print(f"\n[{datetime.now().isoformat()}] INFO: Configuration:")
    print(f"  Model: {args.model}")
    print(f"  Retrieval: {args.retrieval}")
    print(f"  Limit: {args.limit if args.limit else 'None (all questions)'}")
    print(f"  App ID: {args.app_id}")
    print(f"  Database: {args.database}")
    print(f"  Test Set: {args.test_set}\n")

    try:
        # Load test set
        qa_pairs = load_test_set(args.test_set, limit=args.limit)

        # Run evaluation
        evaluation_data = run_evaluation(
            qa_pairs=qa_pairs,
            model_name=args.model,
            retrieval_strategy=args.retrieval,
            app_id=args.app_id,
            database_path=args.database
        )

        # Print summary
        print_summary(evaluation_data["summary"])

        # Save results to JSON
        save_results_to_json(evaluation_data)

        print(f"[{datetime.now().isoformat()}] INFO: Evaluation completed successfully!")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().isoformat()}] WARNING: Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[{datetime.now().isoformat()}] ERROR: Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
