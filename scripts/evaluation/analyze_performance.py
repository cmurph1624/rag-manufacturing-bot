"""
Performance Analysis for RAG Evaluation

Analyzes timing data from evaluation runs to identify performance bottlenecks.
"""

import re
import statistics
from typing import List, Dict, Any
from datetime import datetime


def parse_timing_data(log_file: str) -> List[Dict[str, Any]]:
    """
    Parse timing information from evaluation log output.

    Args:
        log_file: Path to log output file

    Returns:
        List of timing records
    """
    timing_pattern = r'\[(.*?)\] INFO: ✓ Completed in ([\d.]+)s \(Citation: ([✓✗])\)'

    timings = []
    with open(log_file, 'r') as f:
        for line in f:
            match = re.search(timing_pattern, line)
            if match:
                timestamp_str = match.group(1)
                duration = float(match.group(2))
                citation_match = match.group(3) == '✓'

                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    timings.append({
                        'timestamp': timestamp,
                        'duration': duration,
                        'citation_match': citation_match
                    })
                except:
                    pass

    return timings


def analyze_timings(timings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze timing data and identify performance characteristics.

    Args:
        timings: List of timing records

    Returns:
        Analysis results
    """
    if not timings:
        return {}

    durations = [t['duration'] for t in timings]

    # Basic statistics
    total_time = sum(durations)
    avg_time = statistics.mean(durations)
    median_time = statistics.median(durations)
    std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
    min_time = min(durations)
    max_time = max(durations)

    # Identify outliers (> 2 standard deviations from mean)
    threshold = avg_time + (2 * std_dev)
    outliers = [t for t in timings if t['duration'] > threshold]

    # Calculate percentiles
    p50 = statistics.median(durations)
    p95 = sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations)
    p99 = sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)

    # Time range analysis
    if len(timings) > 1:
        start_time = timings[0]['timestamp']
        end_time = timings[-1]['timestamp']
        wall_clock_time = (end_time - start_time).total_seconds()
    else:
        wall_clock_time = durations[0] if durations else 0

    # Citation match analysis
    citation_matches = sum(1 for t in timings if t['citation_match'])
    citation_rate = (citation_matches / len(timings) * 100) if timings else 0

    # Performance categories
    fast = sum(1 for d in durations if d < 30)
    medium = sum(1 for d in durations if 30 <= d < 60)
    slow = sum(1 for d in durations if d >= 60)

    return {
        'count': len(timings),
        'total_time': total_time,
        'wall_clock_time': wall_clock_time,
        'avg_time': avg_time,
        'median_time': median_time,
        'std_dev': std_dev,
        'min_time': min_time,
        'max_time': max_time,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'outliers': len(outliers),
        'citation_rate': citation_rate,
        'performance_distribution': {
            'fast (<30s)': fast,
            'medium (30-60s)': medium,
            'slow (>=60s)': slow
        },
        'outlier_records': outliers[:5]  # Show top 5 outliers
    }


def print_analysis(analysis: Dict[str, Any]) -> None:
    """Print formatted analysis results."""
    print(f"\n{'='*60}")
    print("PERFORMANCE ANALYSIS")
    print(f"{'='*60}")

    print(f"\nTotal Questions: {analysis['count']}")
    print(f"Wall Clock Time: {analysis['wall_clock_time']:.1f}s ({analysis['wall_clock_time']/60:.1f} minutes)")
    print(f"Total Processing Time: {analysis['total_time']:.1f}s")

    print(f"\n{'─'*60}")
    print("TIMING STATISTICS")
    print(f"{'─'*60}")
    print(f"Average: {analysis['avg_time']:.2f}s")
    print(f"Median: {analysis['median_time']:.2f}s")
    print(f"Std Dev: {analysis['std_dev']:.2f}s")
    print(f"Min: {analysis['min_time']:.2f}s")
    print(f"Max: {analysis['max_time']:.2f}s")

    print(f"\n{'─'*60}")
    print("PERCENTILES")
    print(f"{'─'*60}")
    print(f"P50 (Median): {analysis['p50']:.2f}s")
    print(f"P95: {analysis['p95']:.2f}s")
    print(f"P99: {analysis['p99']:.2f}s")

    print(f"\n{'─'*60}")
    print("PERFORMANCE DISTRIBUTION")
    print(f"{'─'*60}")
    for category, count in analysis['performance_distribution'].items():
        pct = (count / analysis['count'] * 100) if analysis['count'] > 0 else 0
        print(f"{category}: {count} ({pct:.1f}%)")

    print(f"\n{'─'*60}")
    print("QUALITY METRICS")
    print(f"{'─'*60}")
    print(f"Citation Match Rate: {analysis['citation_rate']:.1f}%")

    if analysis['outliers'] > 0:
        print(f"\n{'─'*60}")
        print(f"OUTLIERS (>{analysis['avg_time'] + 2*analysis['std_dev']:.1f}s)")
        print(f"{'─'*60}")
        print(f"Total Outliers: {analysis['outliers']}")
        if analysis['outlier_records']:
            print("\nTop Outlier Durations:")
            for i, outlier in enumerate(analysis['outlier_records'], 1):
                print(f"  {i}. {outlier['duration']:.2f}s at {outlier['timestamp'].strftime('%H:%M:%S')}")

    print(f"\n{'─'*60}")
    print("PERFORMANCE ASSESSMENT")
    print(f"{'─'*60}")

    # Performance assessment
    if analysis['avg_time'] < 30:
        assessment = "EXCELLENT - Very fast response times"
    elif analysis['avg_time'] < 45:
        assessment = "GOOD - Acceptable response times"
    elif analysis['avg_time'] < 60:
        assessment = "MODERATE - Could be improved"
    else:
        assessment = "SLOW - Performance optimization recommended"

    print(f"Overall: {assessment}")

    # Identify bottlenecks
    print(f"\n{'─'*60}")
    print("POTENTIAL BOTTLENECKS")
    print(f"{'─'*60}")

    bottlenecks = []

    if analysis['avg_time'] > 50:
        bottlenecks.append("• Average response time >50s - investigate LLM latency")

    if analysis['std_dev'] > 20:
        bottlenecks.append("• High variance - inconsistent performance, check resource contention")

    if analysis['max_time'] > 90:
        bottlenecks.append(f"• Max time {analysis['max_time']:.1f}s - investigate timeout cases")

    slow_pct = analysis['performance_distribution']['slow (>=60s)'] / analysis['count'] * 100
    if slow_pct > 30:
        bottlenecks.append(f"• {slow_pct:.1f}% of queries are slow (>=60s)")

    if bottlenecks:
        for bottleneck in bottlenecks:
            print(bottleneck)
    else:
        print("✅ No major bottlenecks detected")

    print(f"\n{'─'*60}")
    print("OPTIMIZATION RECOMMENDATIONS")
    print(f"{'─'*60}")

    if analysis['avg_time'] > 50:
        print("""
1. LLM Performance:
   - Consider using a faster model variant
   - Reduce context window size if possible
   - Enable model caching if available
   - Check if Ollama is using GPU acceleration

2. Retrieval Performance:
   - Profile vector search latency
   - Consider reducing top_k (currently retrieving many chunks)
   - Optimize reranking if enabled

3. System Resources:
   - Monitor CPU/GPU usage during evaluation
   - Check for memory swapping
   - Ensure Ollama has adequate resources
        """)
    else:
        print("✅ Current performance is acceptable")
        print("   Consider these optimizations only if needed:")
        print("   - Batch processing for multiple queries")
        print("   - Parallel evaluation with multiple workers")
        print("   - Caching frequently accessed documents")


def main():
    """Main analysis function."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_performance.py <log_file>")
        print("\nExample:")
        print("  python analyze_performance.py /tmp/eval_output.log")
        sys.exit(1)

    log_file = sys.argv[1]

    print(f"Parsing timing data from: {log_file}")
    timings = parse_timing_data(log_file)

    if not timings:
        print("❌ No timing data found in log file")
        sys.exit(1)

    print(f"✅ Found {len(timings)} timing records")

    analysis = analyze_timings(timings)
    print_analysis(analysis)

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
