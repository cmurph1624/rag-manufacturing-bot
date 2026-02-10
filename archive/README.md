# Archived Evaluation System

This directory contains the legacy evaluation system that was replaced by TrueLens in February 2026.

## Archived Files

### `dashboard_old.py`
The original Gradio-based dashboard for viewing evaluation results. This provided a web interface for:
- Viewing evaluation history
- Comparing different RAG configurations
- Visualizing performance metrics
- Managing evaluation runs

**Replaced by:** TrueLens Dashboard (accessed via `start_dashboard.py`)

### `evaluation_history_old.db`
SQLite database containing all evaluation results from the legacy system. This stored:
- Evaluation run metadata
- Question/answer pairs
- Performance metrics (correctness, relevance, etc.)
- Configuration details

**Replaced by:** `trulens_eval.db` in the project root

### `evaluation_results_old/`
Directory containing JSON exports of evaluation results from the legacy system.
- Contains timestamped evaluation result files
- Each file represents a single evaluation run
- Useful for historical analysis and comparison

**Replaced by:** TrueLens stores results in its database and provides export capabilities

## Why These Files Were Archived

The evaluation system was migrated to TrueLens for the following reasons:

1. **Industry Standard**: TrueLens is a widely-adopted framework for RAG evaluation
2. **Better Instrumentation**: Automatic tracing and feedback collection
3. **Advanced Analytics**: Built-in dashboards with comprehensive visualizations
4. **Feedback Functions**: Pre-built evaluation metrics (faithfulness, answer relevance, context relevance)
5. **Scalability**: Better performance for large-scale evaluations
6. **Active Development**: Maintained by TruEra with regular updates

## Accessing Old Results

If you need to access results from the old system:

1. **View in Dashboard**: Run the old dashboard (not recommended)
   ```bash
   python archive/dashboard_old.py
   ```

2. **Query Database**: Access the SQLite database directly
   ```bash
   sqlite3 archive/evaluation_history_old.db
   ```

3. **Read JSON Files**: Open the JSON files in `evaluation_results_old/`
   ```bash
   cat archive/evaluation_results_old/evaluation_results_*.json | jq
   ```

## Migration Notes

- All evaluation logic has been rewritten to use TrueLens
- The new system is located in `evaluate_trulens.py`
- Dashboard access is through `start_dashboard.py`
- See `TRULENS_QUICKSTART.md` for usage instructions
- See `TRULENS_MIGRATION_PLAN.md` for complete migration details

## Cleanup

These files are kept for historical reference and can be deleted after:
- Verifying all needed results have been migrated or documented
- Confirming the new TrueLens system meets all requirements
- Archiving any critical evaluation data to long-term storage

Recommended retention: 3-6 months after migration (until ~May 2026)
