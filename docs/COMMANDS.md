# Project Commands Cheat Sheet

## Ingestion

### 1. Standard Ingestion (Fixed Chunking)
The default ingestion method. Splits text into fixed-size chunks with overlap.

```bash
# Default (Chunk Size: 1000, Overlap: 200)
python3 scripts/ingest/ingest_master.py --reset --strategy standard

# Custom Chunk Size and Overlap
python3 scripts/ingest/ingest_master.py --reset --strategy standard --chunk_size 500 --overlap 50
```

### 2. Semantic Ingestion (Smart Chunking)
Splits text based on semantic similarity of sentences using cosine distance.

```bash
# Default (Threshold: 0.4)
python3 scripts/ingest/ingest_master.py --reset --strategy semantic

# Custom Threshold (Lower = stricter/smaller chunks, Higher = looser/larger chunks)
python3 scripts/ingest/ingest_master.py --reset --strategy semantic --semantic_threshold 0.3
```

### Flags
-   `--reset`: Wipes the existing ChromaDB database before starting ingestion.
-   `--strategy`: `standard` or `semantic`.

**Note**: Place your PDF files in `data/pdfs/` before running ingestion.

---

## Evaluation (Ragas)

We use Ragas for evaluation (Faithfulness, Answer Relevancy, Context Precision/Recall).

### 1. Quick Test
Runs evaluation on a small subset (5 questions) to verify the pipeline.

```bash
./scripts/run_evaluation.sh --test
```

### 2. Full Evaluation
Runs evaluation on the entire dataset.

```bash
./scripts/run_evaluation.sh
```

### 3. Custom Evaluation
Use the helper script `run_evaluation.sh` with flags or call the Python script directly.

```bash
# Limit to 10 questions
./scripts/run_evaluation.sh --limit 10

# Filter by Category
./scripts/run_evaluation.sh --category "Adversarial"

# Filter by Test ID
./scripts/run_evaluation.sh --id 1

# Specify Run Name (for tracking in Dashboard/CSVs)
./scripts/run_evaluation.sh --name "experiment_v1"
```

### 4. Change Model or Retrieval Strategy
You can override the generation model and retrieval strategy using flags.

```bash
# Use Mistral model
./scripts/run_evaluation.sh --model mistral --limit 10

# Use Semantic Reranking retrieval
./scripts/run_evaluation.sh --retrieval semantic-rerank --limit 10
```

---

## Dashboard

Launch the Ragas Dashboard (Streamlit) to visualize results.

```bash
./scripts/dashboard/start_dashboard.sh
```

Or directly:
```bash
python3 scripts/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`.

---

## Database Utilities

### Check Database
```bash
python3 scripts/database/check_db.py
```

### Verify Database
```bash
python3 scripts/database/verify_db.py
```

---

## Slack Bot

Starts the Slack bot in Socket Mode.

**Prerequisites:**
Ensure you have the following environment variables in your `.env` file:
- `SLACK_BOT_TOKEN`: The Bot User OAuth Token (starts with `xoxb-`)
- `SLACK_APP_TOKEN`: The App-Level Token (starts with `xapp-`)

```bash
# Start the bot
python3 -m src.bot
```

---

## Testing

### Test Basic RAG
```bash
python3 tests/test_langchain_rag.py
```

---

## Common Workflows

### Complete Setup and Test
```bash
# 1. Start Ollama
ollama serve

# 2. Ingest documents
python3 scripts/ingest/ingest_master.py --reset --strategy semantic

# 3. Run quick test
./scripts/run_evaluation.sh --test

# 4. View results
./scripts/dashboard/start_dashboard.sh
```

### Compare Retrieval Strategies
```bash
# Test semantic retrieval
./scripts/run_evaluation.sh \
  --retrieval semantic \
  --name "semantic_baseline" \
  --limit 20

# Test semantic with reranking
./scripts/run_evaluation.sh \
  --retrieval semantic-rerank \
  --name "rerank_experiment" \
  --limit 20

# Compare in dashboard
./scripts/dashboard/start_dashboard.sh
```
