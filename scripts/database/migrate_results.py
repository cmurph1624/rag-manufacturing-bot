import json
import sqlite3
import os
import glob
from datetime import datetime

DB_PATH = "evaluation_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Ensure tables exist (copying schema from evaluate.py just in case)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_name TEXT NOT NULL,
            accuracy REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            avg_latency REAL,
            retrieval_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS run_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            question TEXT,
            gold_answer TEXT,
            bot_answer TEXT,
            is_correct BOOLEAN,
            citation_match BOOLEAN,
            latency REAL,
            retrieval_type TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_existing_runs():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp FROM runs")
    runs = cursor.fetchall()
    conn.close()
    return runs

def parse_timestamp(ts_str):
    """
    Attempts to parse timestamps from various formats.
    JSON filename: YYYYMMDD_HHMMSS
    DB timestamp: ISO format usually
    """
    try:
        return datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
    except ValueError:
        pass
    
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        pass
        
    return None

def migrate():
    print("Starting migration...")
    init_db()
    
    # Get all JSON files
    json_files = glob.glob("evaluation_results/evaluation_results_*.json")
    print(f"Found {len(json_files)} JSON result files.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    migrated_count = 0
    
    for json_file in json_files:
        with open(json_file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Skipping corrupt file: {json_file}")
                continue
            
        if isinstance(data, list):
            # Legacy format: just a list of results
            results = data
            metadata = {}
            if results and isinstance(results[0], dict):
                 # Try to grab timestamp from first result
                 first_ts = results[0].get("timestamp")
                 if first_ts:
                     metadata["execution_timestamp"] = first_ts
        else: 
            metadata = data.get("metadata", {})
            results = data.get("results", [])
        
        # Try to find a matching run in DB based on timestamp
        # The filename timestamp is usually the execution timestamp
        file_ts_str = metadata.get("execution_timestamp")
        if not file_ts_str:
             # Fallback: extract from filename
             filename = os.path.basename(json_file)
             file_ts_str = filename.replace("evaluation_results_", "").replace(".json", "")
        
        # Convert file timestamp to object for comparison (approximate)
        # The DB might have stored it slightly differently or with different precision
        # Since we don't have a perfect ID link, we'll try to match closely or blindly insert if we trust the user wants history.
        # Actually, simpler approach: Check if we have a run with this exact timestamp (converted to iso) or similar.
        # BUT, `evaluate.py` log_to_db uses `datetime.now().isoformat()` which might differ by milliseconds 
        # from the timestamp generated for the filename a few lines later.
        
        # Let's look for runs created within a small window or just assume we are backfilling EVERYTHING that doesn't have details?
        # A safer bet for this specific task (backfilling old runs not in DB or adding details to runs in DB):
        
        # Strategy:
        # 1. Provide a "force" option? No.
        # 2. Look for a run in DB with similar timestamp (+- 2 seconds).
        # 3. If found, check if it has details. If no details, insert them.
        # 4. If run NOT found, insert the RUN and then the DETAILS.
        
        dt_file = parse_timestamp(file_ts_str)
        if not dt_file:
            print(f"Could not parse timestamp for {json_file}, skipping.")
            continue
            
        # Check DB for run
        # Convert DB timestamps to objects
        cursor.execute("SELECT id, timestamp FROM runs")
        db_runs = cursor.fetchall()
        
        matching_run_id = None
        for run_id, run_ts in db_runs:
            dt_run = parse_timestamp(run_ts)
            if not dt_run: continue
            
            # Difference in seconds
            diff = abs((dt_run - dt_file).total_seconds())
            if diff < 5: # 5 second tolerance
                matching_run_id = run_id
                break
        
        if matching_run_id:
            # Check if details exist
            cursor.execute("SELECT count(*) FROM run_details WHERE run_id=?", (matching_run_id,))
            details_count = cursor.fetchone()[0]
            if details_count > 0:
                print(f"Skipping {json_file}: Run {matching_run_id} already has details.")
                continue
            else:
                print(f"Backfilling details for existing run {matching_run_id} from {json_file}")
        else:
            print(f"Creating new run entry and details for {json_file}")
            # Insert Run
            # Helper to parse accuracy string "52.00%" -> 52.0
            acc_str = metadata.get("accuracy", "0").replace("%","")
            try:
                acc = float(acc_str)
            except:
                acc = 0.0
            
            # Latency average calc if missing
            if "avg_latency" not in metadata:
                 latencies = [r.get("latency_seconds", 0) for r in results]
                 avg_latency = sum(latencies) / len(latencies) if latencies else 0
            else:
                 avg_latency = metadata["avg_latency"]

            # Infer retrieval type from first result
            retrieval_type = "unknown"
            if results:
                retrieval_type = results[0].get("retrieval_type", "unknown")

            cursor.execute('''
                INSERT INTO runs (timestamp, model_name, accuracy, total_questions, avg_latency, retrieval_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                dt_file.isoformat(), 
                metadata.get("model", "unknown"),
                acc,
                len(results),
                avg_latency,
                retrieval_type
            ))
            matching_run_id = cursor.lastrowid

        # Insert Details
        for res in results:
            cursor.execute('''
                INSERT INTO run_details (
                    run_id, question, gold_answer, bot_answer, is_correct, 
                    citation_match, latency, retrieval_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                matching_run_id, 
                res['question'], 
                res['gold_answer'], 
                res['bot_answer'], 
                res['is_correct'], 
                res.get('citation_match', False), 
                res.get('latency_seconds', 0.0), 
                res.get('retrieval_type', 'unknown')
            ))
        migrated_count += 1

    conn.commit()
    conn.close()
    print(f"Migration complete. Processed {migrated_count} files.")

if __name__ == "__main__":
    migrate()
