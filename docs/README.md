# RAG Manufacturing Bot

This project establishes a Retrieval-Augmented Generation (RAG) bot that answers questions based on:
1.  **PDF Documents** (stored in `data/pdfs/`)
2.  **Slack History** (ingested from a specific channel)

It uses **Slack Bolt** for the bot interface, **ChromaDB** for vector storage, and **Ollama** for embeddings and generation.

## Project Structure

```
rag-manufacturing-bot/
├── src/                    # Core application code
│   ├── bot.py             # Main Slack bot application
│   ├── rag_logic.py       # RAG pipeline with TruLens instrumentation
│   ├── trulens_config.py  # TruLens configuration
│   ├── llm/               # LLM abstractions and factory
│   ├── retrieval/         # Retrieval strategies (semantic, lexical, rerank)
│   ├── ingest/            # Document ingestion strategies
│   └── prompts/           # Prompt templates
├── scripts/               # Executable scripts
│   ├── ingest/           # Data ingestion scripts
│   ├── evaluation/       # Evaluation and analysis scripts
│   ├── database/         # Database utilities
│   └── dashboard/        # Dashboard launcher scripts
├── tests/                # Test files and test datasets
├── data/                 # Data files (gitignored)
│   ├── pdfs/            # PDF documents for ingestion
│   ├── chroma_db/       # Vector database
│   ├── databases/       # SQLite databases
│   └── logs/            # Application logs
├── docs/                 # Documentation
└── archive/             # Historical files
```

## Prerequisites

-   Python 3.10+
-   [Ollama](https://ollama.ai/) installed and running (`ollama serve`)
-   Ollama models pulled:
    -   `nomic-embed-text` (for embeddings)
    -   `llama3.2` (for generation)
-   Slack App configured with Socket Mode and appropriate scopes.

## Environment Variables

Create a `.env` file with the following:

```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token

# LLM Configuration (optional - defaults shown)
GENERATION_MODEL=llama3.2        # Model for answer generation
EMBEDDING_MODEL=nomic-embed-text # Model for embeddings
RERANK_MODEL=bge-reranker-v2-m3  # Model for reranking (optional)

# TruLens Configuration (optional)
TRULENS_DATABASE_URL=sqlite:///data/databases/trulens_eval.db
TRULENS_LOG_LEVEL=INFO
```

See `.env.example` for a complete template with all available options.

## Key Components

-   **`src/bot.py`**: The main Slack bot application that listens for mentions and generates answers.
-   **`src/rag_logic.py`**: Core RAG pipeline with optional TruLens instrumentation for evaluation.
-   **`scripts/ingest/ingest_master.py`**: Master ingestion script supporting multiple strategies.
-   **`scripts/evaluation/evaluate_trulens.py`**: TruLens-based evaluation runner.
-   **`scripts/dashboard/start_dashboard.py`**: TruLens dashboard launcher for viewing results.

## Usage

1.  **Start Ollama**:
    ```bash
    ollama serve
    ```

2.  **Ingest Data**:
    ```bash
    # Place PDF files in data/pdfs/ directory

    # Ingest with standard chunking strategy
    python scripts/ingest/ingest_master.py --strategy standard

    # Or use semantic chunking
    python scripts/ingest/ingest_master.py --strategy semantic
    ```

3.  **Run the Bot**:
    ```bash
    python src/bot.py
    ```

## Evaluation with TruLens

This project uses **TruLens** for comprehensive RAG evaluation, tracking answer relevance, context relevance, and groundedness.

### Running Evaluations

1.  **Run a small test evaluation** (5 questions):
    ```bash
    ./scripts/run_evaluation.sh --test
    ```

2.  **Run full evaluation** (50 questions):
    ```bash
    ./scripts/run_evaluation.sh
    ```

3.  **View results in the dashboard**:
    ```bash
    ./scripts/dashboard/start_dashboard.sh
    ```

4.  **Customize evaluation settings**:
    ```bash
    # Use specific model and retrieval strategy
    python3 evaluate_trulens.py --model llama3.2 --retrieval semantic-rerank

    # Custom app identifier
    python3 evaluate_trulens.py --app-id eval_production_2025
    ```

### Viewing the Dashboard

Launch the TruLens dashboard to view evaluation results:

```bash
# Option 1: Use the helper script (recommended)
./start_dashboard.sh

# Option 2: Run the Python launcher directly
python3 start_dashboard.py
```

The dashboard will open at `http://localhost:8501` and provides:
- **Leaderboard**: Compare different evaluation runs
- **Feedback Scores**: Answer Relevance, Context Relevance, Groundedness
- **Individual Records**: Drill down into each question-answer pair
- **Metadata Filters**: Filter by category, model, retrieval strategy

### Interpreting Feedback Scores

TruLens evaluates three key dimensions (scores 0.0-1.0):

1.  **Answer Relevance**: How well the answer addresses the question
    - **High (>0.8)**: Answer directly answers the question
    - **Medium (0.5-0.8)**: Partially relevant but may be incomplete
    - **Low (<0.5)**: Answer is off-topic or doesn't address the question

2.  **Context Relevance**: How relevant retrieved chunks are to the question
    - **High (>0.8)**: Retrieved documents are highly relevant
    - **Medium (0.5-0.8)**: Some relevant context, but may include noise
    - **Low (<0.5)**: Retrieved context is mostly irrelevant

3.  **Groundedness**: Whether the answer is supported by retrieved context
    - **High (>0.8)**: Answer is fully grounded in provided context
    - **Medium (0.5-0.8)**: Partially grounded, some unsupported claims
    - **Low (<0.5)**: Answer makes claims not found in context

### Filtering and Analysis

Use the dashboard to filter results by:
- **Category**: Work_Instructions, Safety, Troubleshooting, Slack_QA
- **Model**: mistral, llama3.2, etc.
- **Retrieval Strategy**: semantic, lexical, semantic-rerank
- **App ID**: Specific evaluation run identifier

### Evaluation Results Storage

- **Database**: `trulens_eval.db` (SQLite) - Persistent storage for all evaluations
- **JSON Reports**: `evaluation_results/trulens_eval_YYYYMMDD_HHMMSS.json` - Per-run summaries

### Advanced Features

**Analyzing Results**:
```bash
# Compare different system configurations
python analyze_performance.py

# Analyze TruLens results with detailed statistics
python analyze_trulens_results.py

# Compare old vs new evaluation systems
python compare_systems.py
```

**Managing Evaluations**:
- Delete runs via the dashboard UI (click "Delete Run" button)
- Export results to JSON for sharing or archiving
- Filter and search across all evaluation history

**Custom Feedback Functions**:
The evaluation system uses LangChain-based feedback providers for:
- Answer relevance (LLM-based evaluation)
- Context relevance (LLM-based evaluation)
- Groundedness (checks if answer is supported by context)

For more details, see `TRULENS_QUICKSTART.md`.

## Project Structure

```
rag-manufacturing-bot/
├── bot.py                      # Main Slack bot application
├── rag_logic.py                # Core RAG logic (LangChain-based)
├── ingest_master.py            # Data ingestion orchestrator
├── evaluate_trulens.py         # TruLens evaluation system
├── start_dashboard.py          # Dashboard launcher
├── trulens_config.py           # TruLens configuration and feedback
├── data_pdfs/                  # PDF documents for ingestion
├── ingestion/                  # Ingestion strategies
│   ├── standard_ingestion.py  # Standard chunking strategy
│   └── semantic_ingestion.py  # Semantic chunking strategy
├── retrieval/                  # Retrieval components
│   ├── lexical.py             # BM25 lexical search
│   └── rerank.py              # Reranking logic
├── archive/                    # Archived old evaluation system
│   ├── README.md              # Archive documentation
│   ├── dashboard_old.py       # Legacy dashboard
│   ├── evaluation_history_old.db
│   └── evaluation_results_old/
└── evaluation_results/         # TruLens evaluation exports
```

## Migration Notes

This project recently migrated from a custom evaluation system to TruLens (February 2026). The old system has been archived in `archive/` for reference. Key improvements:

- **Standardized Framework**: Industry-standard evaluation with TruLens
- **Better Instrumentation**: Automatic tracing and feedback collection
- **Advanced Analytics**: Comprehensive dashboards and visualizations
- **LangChain Integration**: Modern RAG implementation using LangChain

For migration details, see `TRULENS_MIGRATION_PLAN.md` and `archive/README.md`.

## Troubleshooting

-   **SSL Errors**: The scripts use `certifi` to handle SSL context for Slack clients.
-   **Channel Not Found**: Ensure the correct Channel ID is used in `ingest_slack.py` if name resolution fails.
-   **TruLens Feedback Errors**: Background feedback evaluation may show errors but doesn't affect main evaluation. Results are still recorded to the database.
