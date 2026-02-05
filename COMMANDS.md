# Project Commands Cheat Sheet

## Ingestion (`ingest_master.py`)

### 1. Standard Ingestion (Fixed Chunking)
The default ingestion method. Splits text into fixed-size chunks with overlap.

```bash
# Default (Chunk Size: 1000, Overlap: 200)
python3 ingest_master.py --reset --strategy standard

# Custom Chunk Size and Overlap
python3 ingest_master.py --reset --strategy standard --chunk_size 500 --overlap 50
```

### 2. Semantic Ingestion (Smart Chunking)
Splits text based on semantic similarity of sentences using cosine distance.

```bash
# Default (Threshold: 0.4)
python3 ingest_master.py --reset --strategy semantic

# Custom Threshold (Lower = stricter/smaller chunks, Higher = looser/larger chunks)
python3 ingest_master.py --reset --strategy semantic --semantic_threshold 0.3
```

### Flags
-   `--reset`: Wipes the existing ChromaDB database before starting ingestion.
-   `--strategy`: `standard` or `semantic`.

---

## Evaluation (`evaluate.py`)

Runs the RAG evaluation suite against the test set.

```bash
# Run evaluation
python3 evaluate.py

# Run with specific retrieval strategy (if implemented in evaluate.py args)
# Currently evaluate.py typically uses the logic defined in rag_logic.py
```

---

## Dashboard (`dashboard.py`)

Launches the Streamlit dashboard to view evaluation results and history.

```bash
streamlit run dashboard.py
```
