import sys
import time
from datetime import datetime

print(f"[{datetime.now().isoformat()}] INFO: Initializing evaluation script...")

print(f"[{datetime.now().isoformat()}] INFO: Importing standard libraries...")
import json
import os
import sqlite3

# Set offline mode to prevent Hugging Face/Transformers from hanging on network calls/file locks
# This must be set before any transformers imports
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

print(f"[{datetime.now().isoformat()}] INFO: Importing external libraries (this may take a moment)...")

# Validating environment and pre-loading heavy models
# This must happen BEFORE other imports (especially ollama) to avoid lockups
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    # Force pre-load the reranker model for safety
    print(f"[{datetime.now().isoformat()}] INFO: Pre-loading reranker model (BAAI/bge-reranker-v2-m3)...")
    from src.retrieval.factory import RetrievalFactory
    RetrievalFactory.get_strategy("semantic-rerank")
    print(f"[{datetime.now().isoformat()}] INFO: Reranker model pre-loaded successfully.")
except Exception as e:
    print(f"[{datetime.now().isoformat()}] WARNING: Pre-loading reranker failed: {e}")

try:
    import ollama
    print(f"[{datetime.now().isoformat()}] INFO: 'ollama' imported successfully.")
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import 'ollama': {e}")
    sys.exit(1)

try:
    from tqdm import tqdm
    print(f"[{datetime.now().isoformat()}] INFO: 'tqdm' imported successfully.")
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import 'tqdm': {e}")
    sys.exit(1)

print(f"[{datetime.now().isoformat()}] INFO: Importing internal modules...")

# Pre-load Reranker BEFORE rag_logic/ollama to prevent deadlocks
# This ensures PyTorch initializes cleanly first


try:
    from src.rag_logic import generate_answer, GENERATION_MODEL, DEFAULT_RETRIEVAL_STRATEGY
    print(f"[{datetime.now().isoformat()}] INFO: 'rag_logic' imported successfully. Active Strategy: {DEFAULT_RETRIEVAL_STRATEGY}")
except ImportError as e:
    print(f"[{datetime.now().isoformat()}] ERROR: Failed to import 'rag_logic': {e}")
    sys.exit(1)

DB_PATH = "data/databases/evaluation_history.db"

def init_db():
    print(f"[{datetime.now().isoformat()}] INFO: Connecting to database '{DB_PATH}'...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_name TEXT NOT NULL,
            accuracy REAL NOT NULL,
            verified_accuracy REAL,
            total_questions INTEGER NOT NULL,
            avg_latency REAL,
            retrieval_type TEXT,
            ingestion_config_id INTEGER
        )
    ''')
    
    # Create run_details table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS run_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            question TEXT,
            gold_answer TEXT,
            bot_answer TEXT,
            is_correct BOOLEAN,
            verified_correct BOOLEAN,
            citation_match BOOLEAN,
            latency REAL,
            retrieval_type TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    ''')
    
    # Simple migration: check if column exists, if not add it
    cursor.execute("PRAGMA table_info(runs)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "retrieval_type" not in columns:
        print(f"[{datetime.now().isoformat()}] INFO: Migrating DB: Adding 'retrieval_type' column to runs...")
        cursor.execute("ALTER TABLE runs ADD COLUMN retrieval_type TEXT")
    
    if "ingestion_config_id" not in columns:
        print(f"[{datetime.now().isoformat()}] INFO: Migrating DB: Adding 'ingestion_config_id' column to runs...")
        cursor.execute("ALTER TABLE runs ADD COLUMN ingestion_config_id INTEGER")

    if "verified_accuracy" not in columns:
        print(f"[{datetime.now().isoformat()}] INFO: Migrating DB: Adding 'verified_accuracy' column to runs...")
        cursor.execute("ALTER TABLE runs ADD COLUMN verified_accuracy REAL")
        # Initialize verified_accuracy with accuracy for existing records
        cursor.execute("UPDATE runs SET verified_accuracy = accuracy")

    cursor.execute("PRAGMA table_info(run_details)")
    detail_columns = [info[1] for info in cursor.fetchall()]

    if "verified_correct" not in detail_columns:
        print(f"[{datetime.now().isoformat()}] INFO: Migrating DB: Adding 'verified_correct' column to run_details...")
        cursor.execute("ALTER TABLE run_details ADD COLUMN verified_correct BOOLEAN")
        # Initialize verified_correct with is_correct for existing records
        cursor.execute("UPDATE run_details SET verified_correct = is_correct")
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now().isoformat()}] INFO: Database initialized.")

def log_to_db(accuracy, total_questions, avg_latency, model_name, retrieval_type, detailed_results=None):
    print(f"[{datetime.now().isoformat()}] INFO: Logging results to database...")
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # Get latest ingestion config
    ingestion_config_id = None
    try:
        cursor.execute("SELECT id FROM ingestion_configs ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            ingestion_config_id = result[0]
            print(f"[{datetime.now().isoformat()}] INFO: Linked to Ingestion Config ID: {ingestion_config_id}")
        else:
            print(f"[{datetime.now().isoformat()}] WARNING: No ingestion config found.")
    except Exception as e:
        # ingestion_configs table might not exist yet if check_db hasn't been run or ingest_master logic differs
        print(f"[{datetime.now().isoformat()}] WARNING: Could not fetch ingestion config (table might be missing?): {e}")

    # For new runs, verified_accuracy starts as equal to accuracy
    verified_accuracy = accuracy

    cursor.execute('''
        INSERT INTO runs (timestamp, model_name, accuracy, verified_accuracy, total_questions, avg_latency, retrieval_type, ingestion_config_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, model_name, accuracy, verified_accuracy, total_questions, avg_latency, retrieval_type, ingestion_config_id))
    
    run_id = cursor.lastrowid
    
    if detailed_results:
        print(f"[{datetime.now().isoformat()}] INFO: Logging {len(detailed_results)} detailed results for run {run_id}...")
        for res in detailed_results:
            is_correct = res['is_correct']
            # Default verified_correct to is_correct
            verified_correct = is_correct
            
            cursor.execute('''
                INSERT INTO run_details (
                    run_id, question, gold_answer, bot_answer, is_correct, verified_correct,
                    citation_match, latency, retrieval_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_id, 
                res['question'], 
                res['gold_answer'], 
                res['bot_answer'], 
                is_correct,
                verified_correct,
                res['citation_match'], 
                res['latency_seconds'], 
                res.get('retrieval_type', 'unknown')
            ))
            
    conn.commit()
    conn.close()
    print(f"[{datetime.now().isoformat()}] INFO: Run metrics and details successfully logged.")

# Configuration
TEST_SET_PATH = "test_set.json"
JUDGE_MODEL = "llama3.1"  # Using a larger model (8B) for better reasoning as a judge

def load_test_set(path):
    print(f"[{datetime.now().isoformat()}] INFO: Loading test set from '{path}'...")
    with open(path, 'r') as f:
        data = json.load(f)
    print(f"[{datetime.now().isoformat()}] INFO: Test set loaded successfully.")
    return data["qa_pairs"]

def evaluate_answer(question, bot_answer, gold_answer):
    """
    Uses an LLM to judge if the bot's answer is correct based on the gold answer.
    """
    prompt = f"""
    You are an impartial judge evaluating a chatbot's response.
    
    Question: {question}
    
    Gold Answer: {gold_answer}
    
    Bot Answer: {bot_answer}
    
    Does the Bot Answer contain the information present in the Gold Answer?
    
    Respond 'INCORRECT' if:
    - The bot says "I don't know", "I can't help", or similar.
    - The bot's answer is missing the key facts from the Gold Answer.
    - The bot's answer contradicts the Gold Answer.
    
    Respond 'CORRECT' if:
    - The bot's answer contains the core facts from the Gold Answer (even if phrased differently).
    
    Respond with ONLY 'CORRECT' or 'INCORRECT'.
    """
    
    try:
        response = ollama.chat(model=JUDGE_MODEL, messages=[
            {'role': 'user', 'content': prompt},
        ])
        judgment = response['message']['content'].strip().upper()
        if "CORRECT" in judgment and "INCORRECT" not in judgment:
            return True
        elif "INCORRECT" in judgment:
            return False
        else:
            # Fallback if the model is chatty
            return "CORRECT" in judgment
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR: Error evaluating answer: {e}")
        return False

def main():
    print(f"[{datetime.now().isoformat()}] INFO: Starting main execution...")
    qa_pairs = load_test_set(TEST_SET_PATH)
    
    print(f"[{datetime.now().isoformat()}] INFO: Loaded {len(qa_pairs)} QA pairs.")
    
    correct_count = 0
    results = []
    
    print(f"[{datetime.now().isoformat()}] INFO: Starting evaluation loop...")
    total_tests = len(qa_pairs)
    for i, item in enumerate(tqdm(qa_pairs)):
        question = item["question"]
        print(f"\n[{datetime.now().isoformat()}] INFO: [{i+1}/{total_tests}] Running test: {question}")
        gold_answer = item["answer"]
        expected_location = item.get("location", "N/A")
        
        # Get bot's answer
        start_time = time.time()
        try:
            response_data = generate_answer(question)
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] ERROR: Failed to generate answer for question '{question}': {e}")
            response_data = {"answer": f"Error: {e}", "retrieved_chunks": [], "model": "error", "retrieval_type": "error"}

        end_time = time.time()
        latency = end_time - start_time
        
        bot_answer = response_data["answer"]
        retrieved_chunks = response_data.get("retrieved_chunks", [])
        model_used = response_data.get("model", "unknown")
        retrieval_type_used = response_data.get("retrieval_type", "unknown")
        
        # Judge the answer
        print(f"[{datetime.now().isoformat()}] INFO: Judging answer...")
        is_correct = evaluate_answer(question, bot_answer, gold_answer)
        print(f"[{datetime.now().isoformat()}] INFO: Judgment: {'CORRECT' if is_correct else 'INCORRECT'}")
        
        if is_correct:
            correct_count += 1
            
        # Check citation
        citation_match = False
        if expected_location != "N/A" and expected_location in bot_answer:
            citation_match = True
        
        results.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "gold_answer": gold_answer,
            "expected_location": expected_location,
            "bot_answer": bot_answer,
            "retrieved_chunks": retrieved_chunks,
            "model_used": model_used,
            "retrieval_type": retrieval_type_used,
            "latency_seconds": latency,
            "is_correct": is_correct,
            "citation_match": citation_match
        })
        
    accuracy = (correct_count / len(qa_pairs)) * 100
    print(f"\n[{datetime.now().isoformat()}] INFO: Evaluation Complete!")
    print(f"Accuracy: {accuracy:.2f}% ({correct_count}/{len(qa_pairs)})")
    
    # Save detailed results with timestamp
    output_dir = "evaluation_results"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evaluation_results_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Create final output structure
    final_output = {
        "metadata": {
            "model": GENERATION_MODEL,
            "execution_timestamp": timestamp,
            "accuracy": f"{accuracy:.2f}%",
            "total_questions": len(qa_pairs),
            "correct_answers": correct_count
        },
        "results": results
    }

    with open(filepath, "w") as f:
        json.dump(final_output, f, indent=4)
    print(f"[{datetime.now().isoformat()}] INFO: Detailed results saved to '{filepath}'")
    
    # Log to SQLite Database
    try:
        # Since retrieval type is constant per run in this architecture, we use the last one seen or default
        # But logically should be consistent.
        final_retrieval_type = results[0]["retrieval_type"] if results else "unknown"
        log_to_db(accuracy, len(qa_pairs), latency, GENERATION_MODEL, final_retrieval_type, results)
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] WARNING: Failed to log to database: {e}")

if __name__ == "__main__":
    main()
