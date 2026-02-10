"""
Compare TrueLens and Old Evaluation System Results
"""

import sqlite3
import json
from collections import defaultdict
from typing import Dict, Any, List


def analyze_trulens_data() -> Dict[str, Any]:
    """Analyze latest TrueLens evaluation run."""
    conn = sqlite3.connect("trulens_eval.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest app
    cursor.execute("""
        SELECT app_id, app_name, app_json
        FROM trulens_apps
        ORDER BY app_id DESC
        LIMIT 1
    """)

    app_row = cursor.fetchone()
    if not app_row:
        print("⚠️  No apps found in TrueLens database")
        return {}

    app_id = app_row["app_id"]
    app_name = app_row["app_name"]

    print(f"\n{'='*60}")
    print(f"TrueLens Analysis")
    print(f"{'='*60}")
    print(f"App ID: {app_id}")
    print(f"App Name: {app_name}")

    # Get all records for this app
    cursor.execute("""
        SELECT record_id, input, output, ts, cost_json, perf_json, record_json
        FROM trulens_records
        WHERE app_id = ?
        ORDER BY ts
    """, (app_id,))

    records = cursor.fetchall()
    print(f"Total Records: {len(records)}")

    if not records:
        return {}

    # Parse records
    latencies = []
    categories = defaultdict(int)
    citation_matches = 0

    for record in records:
        # Parse perf_json for latency
        perf = json.loads(record["perf_json"]) if record["perf_json"] else {}
        if "latency" in perf:
            latencies.append(perf["latency"])

        # Parse record_json for metadata
        record_data = json.loads(record["record_json"]) if record["record_json"] else {}
        meta = record_data.get("meta", {})

        category = meta.get("category", "Unknown")
        categories[category] += 1

        # Check citation (simple check in output)
        output = record["output"] or ""
        expected_location = meta.get("expected_location", "")
        if expected_location and expected_location.lower() in output.lower():
            citation_matches += 1

    # Get feedback scores
    cursor.execute("""
        SELECT f.name, f.result
        FROM trulens_feedbacks f
        JOIN trulens_records r ON f.record_id = r.record_id
        WHERE r.app_id = ? AND f.result IS NOT NULL
    """, (app_id,))

    feedbacks = cursor.fetchall()
    feedback_scores = defaultdict(list)
    for fb in feedbacks:
        if fb["result"] is not None and fb["result"] >= 0:
            feedback_scores[fb["name"]].append(fb["result"])

    conn.close()

    # Calculate statistics
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    citation_rate = (citation_matches / len(records) * 100) if records else 0

    avg_feedback_scores = {}
    for name, scores in feedback_scores.items():
        if scores:
            avg_feedback_scores[name] = sum(scores) / len(scores)

    print(f"\n{'─'*60}")
    print(f"Metrics")
    print(f"{'─'*60}")
    print(f"Average Latency: {avg_latency:.2f}s")
    print(f"Citation Match Rate: {citation_matches}/{len(records)} ({citation_rate:.1f}%)")

    if avg_feedback_scores:
        print(f"\nFeedback Scores:")
        for name, score in avg_feedback_scores.items():
            print(f"  {name}: {score:.3f}")
    else:
        print(f"\n⚠️  No feedback scores computed (async evaluation may still be running)")

    print(f"\nCategory Breakdown:")
    for category, count in categories.items():
        print(f"  {category}: {count}")

    return {
        "app_name": app_name,
        "total_records": len(records),
        "avg_latency": avg_latency,
        "citation_rate": citation_rate,
        "feedback_scores": avg_feedback_scores,
        "categories": dict(categories)
    }


def analyze_old_system() -> Dict[str, Any]:
    """Analyze latest run from old evaluation system."""
    conn = sqlite3.connect("evaluation_history.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest run
    cursor.execute("""
        SELECT id, timestamp, model_name, accuracy, total_questions, avg_latency, retrieval_type
        FROM runs
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    run_row = cursor.fetchone()
    if not run_row:
        print("\n⚠️  No runs found in old evaluation database")
        return {}

    run_id = run_row["id"]

    print(f"\n{'='*60}")
    print(f"Old System Analysis")
    print(f"{'='*60}")
    print(f"Run ID: {run_id}")
    print(f"Timestamp: {run_row['timestamp']}")
    print(f"Model: {run_row['model_name']}")
    print(f"Retrieval: {run_row['retrieval_type']}")

    # Get run details
    cursor.execute("""
        SELECT question, gold_answer, bot_answer, is_correct, citation_match, latency
        FROM run_details
        WHERE run_id = ?
    """, (run_id,))

    details = cursor.fetchall()
    print(f"Total Questions: {len(details)}")

    conn.close()

    if not details:
        return {}

    # Calculate statistics
    correct = sum(1 for d in details if d["is_correct"])
    accuracy = (correct / len(details) * 100) if details else 0

    citations = sum(1 for d in details if d["citation_match"])
    citation_rate = (citations / len(details) * 100) if details else 0

    latencies = [d["latency"] for d in details if d["latency"]]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print(f"\n{'─'*60}")
    print(f"Metrics")
    print(f"{'─'*60}")
    print(f"Accuracy: {correct}/{len(details)} ({accuracy:.1f}%)")
    print(f"Citation Match Rate: {citations}/{len(details)} ({citation_rate:.1f}%)")
    print(f"Average Latency: {avg_latency:.2f}s")

    return {
        "run_id": run_id,
        "total_questions": len(details),
        "accuracy": accuracy,
        "citation_rate": citation_rate,
        "avg_latency": avg_latency,
        "model": run_row["model_name"],
        "retrieval_type": run_row["retrieval_type"]
    }


def compare_systems(trulens_data: Dict[str, Any], old_data: Dict[str, Any]) -> None:
    """Compare the two systems side by side."""
    print(f"\n{'='*60}")
    print(f"SYSTEM COMPARISON")
    print(f"{'='*60}")

    if not trulens_data and not old_data:
        print("⚠️  No data available for comparison")
        return

    print(f"\n{'─'*60}")
    print(f"Dataset Size")
    print(f"{'─'*60}")
    print(f"TrueLens: {trulens_data.get('total_records', 'N/A')} records")
    print(f"Old System: {old_data.get('total_questions', 'N/A')} questions")

    print(f"\n{'─'*60}")
    print(f"Performance Metrics")
    print(f"{'─'*60}")

    # Latency comparison
    trulens_latency = trulens_data.get("avg_latency", 0)
    old_latency = old_data.get("avg_latency", 0)

    print(f"\nAverage Latency:")
    print(f"  TrueLens: {trulens_latency:.2f}s")
    print(f"  Old System: {old_latency:.2f}s")

    if trulens_latency and old_latency:
        diff = trulens_latency - old_latency
        pct_diff = (diff / old_latency * 100)
        print(f"  Difference: {diff:+.2f}s ({pct_diff:+.1f}%)")

    # Citation comparison
    trulens_citation = trulens_data.get("citation_rate", 0)
    old_citation = old_data.get("citation_rate", 0)

    print(f"\nCitation Match Rate:")
    print(f"  TrueLens: {trulens_citation:.1f}%")
    print(f"  Old System: {old_citation:.1f}%")

    if trulens_citation and old_citation:
        diff = trulens_citation - old_citation
        print(f"  Difference: {diff:+.1f} percentage points")

    # Accuracy (old system only)
    if "accuracy" in old_data:
        print(f"\nAccuracy (Old System LLM Judge):")
        print(f"  {old_data['accuracy']:.1f}%")

    # Feedback scores (TrueLens only)
    if trulens_data.get("feedback_scores"):
        print(f"\nTrueLens Feedback Scores (0-1 scale):")
        for name, score in trulens_data["feedback_scores"].items():
            print(f"  {name}: {score:.3f}")

    print(f"\n{'─'*60}")
    print(f"Key Observations")
    print(f"{'─'*60}")

    observations = []

    # Latency comparison
    if trulens_latency and old_latency:
        if trulens_latency > old_latency * 1.1:
            observations.append(f"⚠️  TrueLens is {pct_diff:.1f}% slower - likely due to instrumentation overhead")
        elif trulens_latency < old_latency * 0.9:
            observations.append(f"✅ TrueLens is {abs(pct_diff):.1f}% faster")
        else:
            observations.append(f"✅ Latency is comparable between systems ({abs(pct_diff):.1f}% difference)")

    # Citation comparison
    if trulens_citation and old_citation:
        if abs(trulens_citation - old_citation) < 5:
            observations.append(f"✅ Citation rates are consistent ({trulens_citation:.1f}% vs {old_citation:.1f}%)")
        elif trulens_citation > old_citation:
            observations.append(f"📈 TrueLens has better citation rate (+{diff:.1f} points)")
        else:
            observations.append(f"📉 TrueLens has lower citation rate ({diff:.1f} points)")

    # Feedback availability
    if not trulens_data.get("feedback_scores"):
        observations.append(f"ℹ️  TrueLens feedback scores not yet available (async computation)")

    for obs in observations:
        print(f"{obs}")

    print(f"\n{'─'*60}")
    print(f"Interpretation Guide")
    print(f"{'─'*60}")
    print("""
The old system used a binary LLM judge (correct/incorrect) with citation checking.
TrueLens provides more granular feedback with multiple metrics:

- Answer Relevance (0-1): How well the answer addresses the question
- Context Relevance (0-1): Quality of retrieved context
- Groundedness (0-1): Whether answer is supported by context

Recommended TrueLens thresholds for "good" performance:
- Answer Relevance > 0.70
- Context Relevance > 0.60
- Groundedness > 0.70

Note: Citation match rate in TrueLens is computed via simple string matching,
      while the old system used more sophisticated LLM-based verification.
    """)


def main():
    """Main comparison function."""
    print(f"{'='*60}")
    print("TrueLens vs Old System Comparison")
    print(f"{'='*60}")

    trulens_data = analyze_trulens_data()
    old_data = analyze_old_system()

    compare_systems(trulens_data, old_data)

    print(f"\n{'='*60}")
    print("Analysis Complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
