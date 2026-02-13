# TruLens Quickstart Guide

This guide will help you get started with evaluating your RAG system using TruLens.

## Table of Contents

1. [What is TruLens?](#what-is-trulens)
2. [Quick Start](#quick-start)
3. [Understanding Feedback Functions](#understanding-feedback-functions)
4. [Running Evaluations](#running-evaluations)
5. [Using the Dashboard](#using-the-dashboard)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)

## What is TruLens?

TruLens is an industry-standard framework for evaluating and monitoring LLM applications. It provides:

- **Automatic Instrumentation**: Traces all components of your RAG pipeline
- **Feedback Functions**: Pre-built evaluators for common metrics
- **Interactive Dashboard**: Rich visualizations and analytics
- **Persistent Storage**: All evaluations stored in a SQLite database

### Why TruLens for RAG?

TruLens specializes in three critical RAG evaluation dimensions:

1. **Answer Relevance**: Does the answer address the user's question?
2. **Context Relevance**: Are the retrieved documents relevant to the question?
3. **Groundedness**: Is the answer supported by the retrieved context?

## Quick Start

### 1. Install Dependencies

Ensure you have TruLens installed:

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
# Edit .env with your settings (especially SLACK tokens if needed)
```

### 3. Run Your First Evaluation

Start with a small test:

```bash
./scripts/run_evaluation.sh --test
```

Or directly:

```bash
python3 scripts/evaluation/evaluate_trulens.py --limit 5
```

This will:
- Load 5 test questions
- Run them through your RAG system
- Evaluate with TruLens feedback functions
- Save results to `data/databases/trulens_eval.db`

### 4. View Results

Launch the dashboard:

```bash
./scripts/dashboard/start_dashboard.sh
```

Open your browser to `http://localhost:8501`

## Understanding Feedback Functions

TruLens evaluates your RAG system on three dimensions:

### 1. Answer Relevance (0.0 - 1.0)

**What it measures**: How well the generated answer addresses the user's question.

**Evaluation method**: LLM-based assessment comparing question and answer.

**Score interpretation**:
- **0.9-1.0**: Excellent - Answer directly and completely addresses the question
- **0.7-0.9**: Good - Answer is relevant with minor gaps
- **0.5-0.7**: Fair - Answer is partially relevant
- **< 0.5**: Poor - Answer doesn't address the question

**Example**:
```
Question: "What is the recommended torque for wing bolts?"
Answer: "Wing bolts should be torqued to 45 ft-lbs according to section 3.2"
Score: 0.95 (Excellent - direct answer with citation)

Answer: "Torque specifications vary by component. See the manual."
Score: 0.4 (Poor - too vague, doesn't answer the question)
```

### 2. Context Relevance (0.0 - 1.0)

**What it measures**: How relevant the retrieved documents are to the question.

**Evaluation method**: LLM-based assessment of each retrieved chunk's relevance.

**Score interpretation**:
- **0.9-1.0**: Excellent - All retrieved chunks are highly relevant
- **0.7-0.9**: Good - Most chunks are relevant
- **0.5-0.7**: Fair - Some relevant chunks mixed with noise
- **< 0.5**: Poor - Retrieved context is mostly irrelevant

**Example**:
```
Question: "How do I troubleshoot engine startup issues?"
Retrieved chunks:
  1. "Engine startup troubleshooting guide..." (Relevant ✓)
  2. "Starter motor specifications..." (Relevant ✓)
  3. "Annual maintenance schedule..." (Less relevant ✗)
Score: 0.67 (Fair - 2/3 chunks relevant)
```

### 3. Groundedness (0.0 - 1.0)

**What it measures**: Whether the answer's claims are supported by the retrieved context.

**Evaluation method**: Checks if each statement in the answer can be verified in the context.

**Score interpretation**:
- **0.9-1.0**: Excellent - All claims are grounded in context
- **0.7-0.9**: Good - Most claims are supported
- **0.5-0.7**: Fair - Some unsupported claims
- **< 0.5**: Poor - Answer makes claims not found in context (hallucination)

**Example**:
```
Context: "The recommended interval for oil changes is 50 hours."
Answer: "Change oil every 50 hours as specified in the manual."
Score: 1.0 (Perfect - fully grounded)

Answer: "Change oil every 50 hours and replace the filter every 100 hours."
Score: 0.5 (Fair - filter info not in context)
```

## Running Evaluations

### Basic Evaluation

Run with default settings (50 questions):

```bash
./scripts/run_evaluation.sh
```

Or directly:

```bash
python3 scripts/evaluation/evaluate_trulens.py
```

### Limited Test Run

Test with fewer questions:

```bash
./scripts/run_evaluation.sh --test
```

Or:

```bash
python3 scripts/evaluation/evaluate_trulens.py --limit 10
```

### Custom Configuration

Specify model and retrieval strategy:

```bash
python3 scripts/evaluation/evaluate_trulens.py \
  --model llama3.2 \
  --retrieval semantic-rerank \
  --limit 20
```

### Custom App Identifier

Use a specific app ID to organize evaluations:

```bash
python3 scripts/evaluation/evaluate_trulens.py --app-id "production_eval_v2"
```

### Available Options

```bash
python3 scripts/evaluation/evaluate_trulens.py --help
```

**Common options**:
- `--limit N`: Evaluate only N questions (default: 50)
- `--model MODEL`: LLM model to use (default: from .env or llama3.2)
- `--retrieval STRATEGY`: semantic, lexical, or semantic-rerank
- `--app-id ID`: Custom identifier for this evaluation run
- `--skip-feedback`: Skip feedback function evaluation (faster)

## Using the Dashboard

### Launching the Dashboard

```bash
./scripts/dashboard/start_dashboard.sh
```

Or directly:

```bash
python3 scripts/dashboard/start_dashboard.py
```

The dashboard opens at `http://localhost:8501`

### Dashboard Features

#### 1. Leaderboard View

**What it shows**: Comparison of all evaluation runs

**Key metrics**:
- Average feedback scores (Answer Relevance, Context Relevance, Groundedness)
- Number of records
- Timestamp
- Configuration details

**Use cases**:
- Compare different models
- Compare retrieval strategies
- Track improvements over time

#### 2. Evaluations Page

**What it shows**: Detailed results for each evaluation run

**Features**:
- Filter by app ID, model, retrieval strategy
- View individual question-answer pairs
- See retrieved context for each question
- Drill down into feedback scores

**Use cases**:
- Debug specific failures
- Understand why certain questions score poorly
- Verify context retrieval quality

#### 3. Individual Record View

**What it shows**: Complete details for a single question-answer interaction

**Information displayed**:
- Input question
- Retrieved context chunks
- Generated answer
- Feedback scores with explanations
- Execution trace

**Use cases**:
- Deep dive into specific issues
- Understand retrieval behavior
- Verify grounding of answers

#### 4. Filtering and Search

**Available filters**:
- **App ID**: Filter by evaluation run
- **Tags**: Filter by metadata (category, model, etc.)
- **Date Range**: Filter by evaluation date
- **Score Ranges**: Filter by feedback scores

**Use cases**:
- Find low-scoring questions
- Compare specific categories
- Analyze specific time periods

### Managing Evaluations

#### Deleting Runs

From the dashboard:
1. Navigate to the evaluation you want to delete
2. Click "Delete Run" button
3. Confirm deletion

**Note**: This permanently deletes the evaluation and all associated records.

#### Exporting Results

Results are automatically exported to JSON:

```bash
ls evaluation_results/
# trulens_eval_20260210_095549.json
# trulens_eval_20260210_102613.json
```

Each file contains:
- Summary statistics
- All question-answer pairs
- Feedback scores
- Configuration details

## Advanced Usage

### Analyzing Results Programmatically

#### Compare Performance

```bash
python3 scripts/evaluation/analyze_performance.py
```

This script analyzes:
- Score distributions
- Category-wise performance
- Model comparisons
- Retrieval strategy effectiveness

#### Detailed TruLens Analysis

```bash
python3 scripts/evaluation/analyze_trulens_results.py
```

This provides:
- Statistical analysis of feedback scores
- Correlations between metrics
- Failure pattern analysis
- Recommendations for improvement

#### Compare Old vs New Systems

```bash
python3 scripts/evaluation/compare_systems.py
```

Compares:
- Legacy evaluation system results
- TruLens evaluation results
- Migration validation

### Custom Feedback Functions

The system uses LangChain-based feedback providers. To add custom feedback:

1. Edit `src/trulens_config.py`
2. Add your custom feedback function
3. Register it in `get_feedback_functions()`

Example:

```python
def custom_citation_feedback(question, answer, context):
    """Check if answer includes proper citations."""
    # Your evaluation logic here
    return score  # 0.0 - 1.0

# Register in get_feedback_functions()
```

### Batch Evaluation

Run multiple configurations in sequence:

```bash
# Create a script
cat > batch_eval.sh << 'EOF'
#!/bin/bash
for model in llama3.2 mistral; do
  for strategy in semantic lexical semantic-rerank; do
    python3 scripts/evaluation/evaluate_trulens.py \
      --model $model \
      --retrieval $strategy \
      --app-id "batch_${model}_${strategy}" \
      --limit 20
  done
done
EOF

chmod +x batch_eval.sh
./batch_eval.sh
```

### Integration with CI/CD

Run evaluations in your CI pipeline:

```yaml
# .github/workflows/evaluate.yml
name: RAG Evaluation
on: [push]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run evaluation
        run: |
          pip install -r requirements.txt
          python3 scripts/evaluation/evaluate_trulens.py --limit 10
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: evaluation-results
          path: evaluation_results/
```

## Troubleshooting

### Common Issues

#### 1. Database Locked Error

**Symptom**: `database is locked` error when running evaluations

**Solution**:
```bash
# Close the dashboard first
# Then run evaluation
python3 scripts/evaluation/evaluate_trulens.py --limit 5
```

#### 2. Feedback Function Errors

**Symptom**: Errors during feedback evaluation, but results still saved

**Explanation**: TruLens runs feedback functions asynchronously. Errors don't stop evaluation.

**Solution**:
- Check the error details in the console output
- Verify your LLM is running (e.g., `ollama serve`)
- Check model availability: `ollama list`

#### 3. Missing Results in Dashboard

**Symptom**: Dashboard shows no results after evaluation

**Solution**:
```bash
# Verify database exists
ls -lh data/databases/trulens_eval.db

# Check database contents
python3 -c "from trulens.core import TruSession; session = TruSession(database_url='sqlite:///data/databases/trulens_eval.db'); print(len(session.get_apps()))"

# Restart dashboard
./scripts/dashboard/start_dashboard.sh
```

#### 4. Slow Evaluation

**Symptom**: Evaluation takes a long time

**Causes & Solutions**:
- **Too many questions**: Use `--limit` to reduce
- **Slow LLM**: Use a faster model or enable GPU
- **Feedback overhead**: Use `--skip-feedback` for testing
- **Reranking overhead**: Try `semantic` instead of `semantic-rerank`

#### 5. Import Errors

**Symptom**: `ModuleNotFoundError` for TruLens or dependencies

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import trulens; print(trulens.__version__)"
```

### Getting Help

1. **Check Logs**: Evaluation script prints detailed logs
2. **Console Output**: Look for error messages and warnings
3. **Database Inspection**: Query `trulens_eval.db` directly
4. **TruLens Docs**: https://www.trulens.org/
5. **Project Issues**: See `TRULENS_MIGRATION_PLAN.md` for known issues

### Debug Mode

Enable verbose logging:

```bash
export TRULENS_LOG_LEVEL=DEBUG
python3 scripts/evaluation/evaluate_trulens.py --limit 5
```

### Resetting Everything

If you need to start fresh:

```bash
# Backup current database
cp data/databases/trulens_eval.db data/databases/trulens_eval_backup.db

# Delete database
rm data/databases/trulens_eval.db

# Run fresh evaluation
python3 scripts/evaluation/evaluate_trulens.py --limit 5
```

## Best Practices

### 1. Start Small

Always test with `--limit 5` before running full evaluations.

### 2. Use Meaningful App IDs

Name your evaluations descriptively:
- `eval_production_v1`
- `test_new_reranker`
- `baseline_llama32`

### 3. Regular Monitoring

Run evaluations regularly to catch regressions:
```bash
# Weekly baseline
python3 scripts/evaluation/evaluate_trulens.py --app-id "weekly_baseline_$(date +%Y%m%d)"
```

### 4. Compare Configurations

When testing changes, run before/after evaluations:
```bash
python3 scripts/evaluation/evaluate_trulens.py --app-id "before_change"
# Make your changes
python3 scripts/evaluation/evaluate_trulens.py --app-id "after_change"
```

### 5. Archive Important Results

Export and save critical evaluations:
```bash
cp evaluation_results/trulens_eval_*.json archive/important_eval.json
```

## Next Steps

- **Read**: `TRULENS_MIGRATION_PLAN.md` for implementation details
- **Explore**: `src/trulens_config.py` to understand feedback functions
- **Customize**: Add your own feedback functions
- **Optimize**: Use analysis scripts to improve your RAG system
- **Monitor**: Set up regular evaluation runs

## Additional Resources

- **TruLens Documentation**: https://www.trulens.org/
- **LangChain Documentation**: https://python.langchain.com/
- **RAG Best Practices**: See `README.md` for overall system documentation
- **Migration Details**: See `TRULENS_MIGRATION_PLAN.md`
- **Legacy System**: See `archive/README.md` for old evaluation system
