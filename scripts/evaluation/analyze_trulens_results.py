"""
Analyze TrueLens Evaluation Results

This script connects to the TrueLens database, extracts evaluation metrics,
and compares them with the old evaluation system.

Usage:
    python analyze_trulens_results.py
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Database paths
# Database paths
TRULENS_DB = "data/databases/trulens_eval.db"
OLD_DB = "data/databases/evaluation_history.db"


def connect_to_db(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite database."""
    try:
        conn = sqlite3.Connection(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except Exception as e:
        print(f"Error connecting to {db_path}: {e}")
        raise


def get_trulens_apps(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all TrueLens apps/evaluation runs."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT app_name, app_version FROM apps ORDER BY app_name DESC")

    apps = []
    for row in cursor.fetchall():
        apps.append({
            "app_name": row["app_name"],
            "app_version": row["app_version"]
        })

    return apps


def get_trulens_records(conn: sqlite3.Connection, app_name: str = None) -> List[Dict[str, Any]]:
    """Get all records from TrueLens database."""
    cursor = conn.cursor()

    if app_name:
        cursor.execute("""
            SELECT
                record_id,
                app_id,
                input,
                output,
                tags,
                meta,
                ts,
                cost_json,
                latency
            FROM records
            WHERE app_id = (SELECT app_id FROM apps WHERE app_name = ? LIMIT 1)
            ORDER BY ts DESC
        """, (app_name,))
    else:
        cursor.execute("""
            SELECT
                record_id,
                app_id,
                input,
                output,
                tags,
                meta,
                ts,
                cost_json,
                latency
            FROM records
            ORDER BY ts DESC
        """)

    records = []
    for row in cursor.fetchall():
        records.append({
            "record_id": row["record_id"],
            "app_id": row["app_id"],
            "input": row["input"],
            "output": row["output"],
            "tags": row["tags"],
            "meta": row["meta"],
            "timestamp": row["ts"],
            "cost": row["cost_json"],
            "latency": row["latency"]
        })

    return records


def get_truelens_feedbacks(conn: sqlite3.Connection, record_id: str = None) -> List[Dict[str, Any]]:
    """Get feedback scores from TrueLens database."""
    cursor = conn.cursor()

    if record_id:
        cursor.execute("""
            SELECT
                feedback_result_id,
                record_id,
                feedback_definition_id,
                result,
                name,
                calls_json
            FROM feedback_results
            WHERE record_id = ?
        """, (record_id,))
    else:
        cursor.execute("""
            SELECT
                feedback_result_id,
                record_id,
                feedback_definition_id,
                result,
                name,
                calls_json
            FROM feedback_results
        """)

    feedbacks = []
    for row in cursor.fetchall():
        feedbacks.append({
            "feedback_result_id": row["feedback_result_id"],
            "record_id": row["record_id"],
            "feedback_definition_id": row["feedback_definition_id"],
            "name": row["name"],
            "result": row["result"],
            "calls_json": row["calls_json"]
        })

    return feedbacks


def analyze_trulens_run(conn: sqlite3.Connection, app_name: str = None) -> Dict[str, Any]:
    """Analyze a TrueLens evaluation run."""
    records = get_trulens_records(conn, app_name)

    print(f"\n{'='*60}")
    print(f"TrueLens Analysis: {app_name or 'Latest Run'}")
    print(f"{'='*60}")
    print(f"Total Records: {len(records)}")

    if len(records) == 0:
        print("⚠️  No records found in TrueLens database")
        return {}

    # Aggregate feedback scores
    feedback_scores = defaultdict(list)
    records_with_metadata = []

    for record in records:
        # Get feedbacks for this record
        feedbacks = get_truelens_feedbacks(conn, record["record_id"])

        record_feedbacks = {}
        for fb in feedbacks:
            if fb["result"] is not None and fb["name"]:
                feedback_scores[fb["name"]].append(fb["result"])
                record_feedbacks[fb["name"]] = fb["result"]

        # Parse metadata
        meta = json.loads(record["meta"]) if record["meta"] else {}

        records_with_metadata.append({
            "record_id": record["record_id"],
            "input": record["input"],
            "output": record["output"],
            "latency": record["latency"],
            "category": meta.get("category", "Unknown"),
            "expected_location": meta.get("expected_location", "N/A"),
            "feedbacks": record_feedbacks
        })

    # Calculate average scores
    print(f"\n{'─'*60}")
    print(f"Feedback Scores (Average)")
    print(f"{'─'*60}")

    avg_scores = {}
    for fb_name, scores in feedback_scores.items():
        valid_scores = [s for s in scores if s is not None and s >= 0]
        if valid_scores:
            avg = sum(valid_scores) / len(valid_scores)
            avg_scores[fb_name] = avg
            print(f"{fb_name}: {avg:.3f} ({len(valid_scores)}/{len(scores)} valid)")
        else:
            print(f"{fb_name}: No valid scores")

    # Calculate latency statistics
    latencies = [r["latency"] for r in records if r["latency"] is not None]
    if latencies:
        print(f"\n{'─'*60}")
        print(f"Latency Statistics")
        print(f"{'─'*60}")
        print(f"Average: {sum(latencies)/len(latencies):.2f}s")
        print(f"Min: {min(latencies):.2f}s")
        print(f"Max: {max(latencies):.2f}s")

    # Breakdown by category
    category_stats = defaultdict(lambda: {"total": 0, "feedbacks": defaultdict(list)})
    for record in records_with_metadata:
        category = record["category"]
        category_stats[category]["total"] += 1

        for fb_name, score in record["feedbacks"].items():
            if score is not None and score >= 0:
                category_stats[category]["feedbacks"][fb_name].append(score)

    print(f"\n{'─'*60}")
    print(f"Breakdown by Category")
    print(f"{'─'*60}")
    for category, stats in category_stats.items():
        print(f"\n{category}:")
        print(f"  Total: {stats['total']}")
        for fb_name, scores in stats["feedbacks"].items():
            if scores:
                avg = sum(scores) / len(scores)
                print(f"  {fb_name}: {avg:.3f}")

    return {
        "app_name": app_name,
        "total_records": len(records),
        "avg_scores": avg_scores,
        "latency_stats": {
            "avg": sum(latencies)/len(latencies) if latencies else 0,
            "min": min(latencies) if latencies else 0,
            "max": max(latencies) if latencies else 0
        },
        "category_stats": dict(category_stats),
        "records": records_with_metadata
    }


def get_old_system_run(conn: sqlite3.Connection, limit: int = 1) -> List[Dict[str, Any]]:
    """Get recent run from old evaluation system."""
    cursor = conn.cursor()

    # Get distinct run IDs
    cursor.execute("""
        SELECT DISTINCT run_id, timestamp
        FROM evaluation_results
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    runs = cursor.fetchall()

    if not runs:
        print("⚠️  No runs found in old evaluation database")
        return []

    results = []
    for run_row in runs:
        run_id = run_row["run_id"]

        # Get all records for this run
        cursor.execute("""
            SELECT
                question_id,
                question,
                gold_answer,
                bot_answer,
                judge_score,
                judge_reasoning,
                expected_location,
                citation_match,
                category,
                latency_seconds,
                model,
                retrieval_strategy
            FROM evaluation_results
            WHERE run_id = ?
            ORDER BY question_id
        """, (run_id,))

        records = []
        for row in cursor.fetchall():
            records.append({
                "question_id": row["question_id"],
                "question": row["question"],
                "gold_answer": row["gold_answer"],
                "bot_answer": row["bot_answer"],
                "judge_score": row["judge_score"],
                "judge_reasoning": row["judge_reasoning"],
                "expected_location": row["expected_location"],
                "citation_match": row["citation_match"],
                "category": row["category"],
                "latency_seconds": row["latency_seconds"],
                "model": row["model"],
                "retrieval_strategy": row["retrieval_strategy"]
            })

        results.append({
            "run_id": run_id,
            "timestamp": run_row["timestamp"],
            "records": records
        })

    return results


def analyze_old_system(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Analyze the most recent run from the old evaluation system."""
    runs = get_old_system_run(conn, limit=1)

    if not runs:
        return {}

    run = runs[0]
    records = run["records"]

    print(f"\n{'='*60}")
    print(f"Old System Analysis")
    print(f"{'='*60}")
    print(f"Run ID: {run['run_id']}")
    print(f"Timestamp: {run['timestamp']}")
    print(f"Total Records: {len(records)}")

    # Calculate average judge score
    judge_scores = [r["judge_score"] for r in records if r["judge_score"] is not None]
    avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else 0

    # Calculate citation match rate
    citation_matches = sum(1 for r in records if r["citation_match"])
    citation_rate = (citation_matches / len(records) * 100) if records else 0

    # Calculate latency
    latencies = [r["latency_seconds"] for r in records if r["latency_seconds"] is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print(f"\n{'─'*60}")
    print(f"Metrics")
    print(f"{'─'*60}")
    print(f"Average Judge Score: {avg_judge_score:.3f} (scale: 0-5)")
    print(f"Citation Match Rate: {citation_matches}/{len(records)} ({citation_rate:.1f}%)")
    print(f"Average Latency: {avg_latency:.2f}s")

    # Breakdown by category
    category_stats = defaultdict(lambda: {"total": 0, "judge_scores": [], "citations": 0})
    for record in records:
        category = record["category"]
        category_stats[category]["total"] += 1
        if record["judge_score"] is not None:
            category_stats[category]["judge_scores"].append(record["judge_score"])
        if record["citation_match"]:
            category_stats[category]["citations"] += 1

    print(f"\n{'─'*60}")
    print(f"Breakdown by Category")
    print(f"{'─'*60}")
    for category, stats in category_stats.items():
        print(f"\n{category}:")
        print(f"  Total: {stats['total']}")
        if stats["judge_scores"]:
            avg = sum(stats["judge_scores"]) / len(stats["judge_scores"])
            print(f"  Avg Judge Score: {avg:.3f}")
        citation_rate = (stats["citations"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  Citation Rate: {stats['citations']}/{stats['total']} ({citation_rate:.1f}%)")

    return {
        "run_id": run["run_id"],
        "timestamp": run["timestamp"],
        "total_records": len(records),
        "avg_judge_score": avg_judge_score,
        "citation_match_rate": citation_rate,
        "avg_latency": avg_latency,
        "category_stats": dict(category_stats),
        "records": records
    }


def compare_systems(trulens_data: Dict[str, Any], old_data: Dict[str, Any]) -> None:
    """Compare TrueLens and old evaluation system results."""
    print(f"\n{'='*60}")
    print(f"SYSTEM COMPARISON")
    print(f"{'='*60}")

    if not trulens_data or not old_data:
        print("⚠️  Insufficient data for comparison")
        return

    print(f"\n{'─'*60}")
    print(f"Dataset Size")
    print(f"{'─'*60}")
    print(f"TrueLens: {trulens_data.get('total_records', 0)} records")
    print(f"Old System: {old_data.get('total_records', 0)} records")

    print(f"\n{'─'*60}")
    print(f"Performance Metrics")
    print(f"{'─'*60}")

    # Compare latency
    trulens_latency = trulens_data.get("latency_stats", {}).get("avg", 0)
    old_latency = old_data.get("avg_latency", 0)
    print(f"Average Latency:")
    print(f"  TrueLens: {trulens_latency:.2f}s")
    print(f"  Old System: {old_latency:.2f}s")
    if trulens_latency and old_latency:
        diff = ((trulens_latency - old_latency) / old_latency * 100)
        print(f"  Difference: {diff:+.1f}%")

    print(f"\n{'─'*60}")
    print(f"Evaluation Metrics")
    print(f"{'─'*60}")
    print(f"Old System Judge Score (0-5 scale): {old_data.get('avg_judge_score', 0):.3f}")
    print(f"\nTrueLens Feedback Scores (0-1 scale):")
    for fb_name, score in trulens_data.get("avg_scores", {}).items():
        print(f"  {fb_name}: {score:.3f}")

    print(f"\n{'─'*60}")
    print(f"Interpretation Guide")
    print(f"{'─'*60}")
    print("""
The old system used a single LLM judge with a 0-5 scale.
TrueLens uses multiple feedback functions with 0-1 scales:

- Answer Relevance: How well the answer addresses the question (0-1)
- Context Relevance: How relevant retrieved chunks are (0-1)
- Groundedness: Whether answer is supported by context (0-1)

Converting scales for comparison:
- Old Judge Score 4.0/5 ≈ 0.80 in TrueLens
- Old Judge Score 3.5/5 ≈ 0.70 in TrueLens
- Old Judge Score 3.0/5 ≈ 0.60 in TrueLens

Recommended TrueLens thresholds:
- Answer Relevance > 0.70: Good answer quality
- Context Relevance > 0.60: Relevant retrieval
- Groundedness > 0.70: Well-grounded answer
    """)


def main():
    """Main analysis function."""
    print(f"{'='*60}")
    print("TrueLens vs Old System Comparison")
    print(f"{'='*60}\n")

    try:
        # Analyze TrueLens
        print("Connecting to TrueLens database...")
        trulens_conn = connect_to_db(TRULENS_DB)

        # Get list of apps
        apps = get_trulens_apps(trulens_conn)
        print(f"\nFound {len(apps)} TrueLens app(s)")

        if apps:
            # Analyze most recent app
            latest_app = apps[0]["app_name"]
            print(f"Analyzing latest app: {latest_app}")
            trulens_data = analyze_trulens_run(trulens_conn, latest_app)
        else:
            trulens_data = analyze_trulens_run(trulens_conn)

        trulens_conn.close()

    except Exception as e:
        print(f"⚠️  Error analyzing TrueLens: {e}")
        trulens_data = {}

    try:
        # Analyze old system
        print(f"\n\nConnecting to old evaluation database...")
        old_conn = connect_to_db(OLD_DB)
        old_data = analyze_old_system(old_conn)
        old_conn.close()

    except Exception as e:
        print(f"⚠️  Error analyzing old system: {e}")
        old_data = {}

    # Compare systems
    compare_systems(trulens_data, old_data)

    print(f"\n{'='*60}")
    print("Analysis Complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
