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
│   ├── rag_logic.py       # Core RAG pipeline (LangChain)
│   ├── llm/               # LLM abstractions and factory
│   ├── retrieval/         # Retrieval strategies (semantic, lexical, rerank)
│   ├── ingest/            # Document ingestion strategies
│   └── prompts/           # Prompt templates
├── scripts/               # Executable scripts
│   ├── ingest/           # Data ingestion scripts
│   ├── evaluation/       # Evaluation and analysis scripts
│   └── database/         # Database utilities
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


```

See `.env.example` for a complete template with all available options.

## Key Components

-   **`src/bot.py`**: The main Slack bot application that listens for mentions and generates answers.
-   **`src/rag_logic.py`**: Core RAG pipeline using LangChain.
-   **`scripts/ingest/ingest_master.py`**: Master ingestion script supporting multiple strategies.

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



## Project Structure

```
rag-manufacturing-bot/
├── bot.py                      # Main Slack bot application
├── rag_logic.py                # Core RAG logic (LangChain-based)
├── ingest_master.py            # Data ingestion orchestrator
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
└── evaluation_results/         # Historical evaluation exports
```



## Troubleshooting

-   **SSL Errors**: The scripts use `certifi` to handle SSL context for Slack clients.
-   **Channel Not Found**: Ensure the correct Channel ID is used in `ingest_slack.py` if name resolution fails.

