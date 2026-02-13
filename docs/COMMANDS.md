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

## Evaluation

### Quick Test Evaluation (5 questions)
```bash
./scripts/run_evaluation.sh --test
```

### Full Evaluation (50 questions)
```bash
./scripts/run_evaluation.sh
```

### Custom Evaluation
```bash
# Specify number of questions
python3 scripts/evaluation/evaluate_trulens.py --limit 20

# Specify model and retrieval strategy
python3 scripts/evaluation/evaluate_trulens.py \
  --model llama3.2 \
  --retrieval semantic-rerank \
  --limit 10

# Custom app ID for tracking
python3 scripts/evaluation/evaluate_trulens.py --app-id "test_run_v1"
```

### Change LLM Model
You can specify the LLM model using the `LLM_MODEL_NAME` environment variable or via command line.

```bash
# Via environment variable
LLM_MODEL_NAME=mistral python3 scripts/evaluation/evaluate_trulens.py --limit 10

# Via command line flag
python3 scripts/evaluation/evaluate_trulens.py --model mistral --limit 10
```

---

## Dashboard

### Launch TruLens Dashboard
```bash
./scripts/dashboard/start_dashboard.sh
```

Or directly:
```bash
python3 scripts/dashboard/start_dashboard.py
```

The dashboard will be available at `http://localhost:8501`

---

## Analysis Scripts

### Analyze Performance
```bash
python3 scripts/evaluation/analyze_performance.py
```

### Analyze TruLens Results
```bash
python3 scripts/evaluation/analyze_trulens_results.py
```

### Compare Systems
```bash
python3 scripts/evaluation/compare_systems.py
```

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
python3 src/bot.py
```

---

## Testing

### Test Basic RAG
```bash
python3 tests/test_langchain_rag.py
```

### Test TruLens Instrumentation
```bash
python3 tests/test_trulens_instrumentation.py
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
python3 scripts/evaluation/evaluate_trulens.py \
  --retrieval semantic \
  --app-id "test_semantic" \
  --limit 20

# Test semantic with reranking
python3 scripts/evaluation/evaluate_trulens.py \
  --retrieval semantic-rerank \
  --app-id "test_rerank" \
  --limit 20

# Compare in dashboard
./scripts/dashboard/start_dashboard.sh
```
