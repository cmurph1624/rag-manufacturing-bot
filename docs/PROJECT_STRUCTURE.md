# Project Structure Documentation

## Overview

This document describes the organization of the RAG Manufacturing Bot codebase after the February 2026 reorganization.

## Directory Structure

```
rag-manufacturing-bot/
├── .env                    # Environment variables (gitignored)
├── .env.example           # Template for environment configuration
├── .gitignore            # Git ignore patterns
├── README.md             # Project overview and quick start guide
├── requirements.txt      # Python dependencies
│
├── src/                  # Core application code
│   ├── bot.py           # Main Slack bot application
│   ├── rag_logic.py     # RAG pipeline with TruLens instrumentation
│   ├── trulens_config.py # TruLens configuration and feedback functions
│   │
│   ├── llm/             # LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py      # Base LLM strategy interface
│   │   ├── factory.py   # LLM factory for creating model instances
│   │   └── ollama_model.py # Ollama implementation
│   │
│   ├── retrieval/       # Retrieval strategies
│   │   ├── __init__.py
│   │   ├── base.py      # Base retrieval interface
│   │   ├── factory.py   # Retrieval factory
│   │   ├── semantic.py  # Semantic search using embeddings
│   │   ├── lexical.py   # Lexical/BM25 search
│   │   └── rerank.py    # Reranking with BGE-reranker
│   │
│   ├── ingest/          # Document ingestion
│   │   ├── __init__.py
│   │   ├── base.py      # Base ingestion interface
│   │   ├── factory.py   # Ingestion factory
│   │   ├── loaders.py   # Document loaders (PDF, JSON, Slack)
│   │   └── strategies/
│   │       ├── __init__.py
│   │       ├── standard.py  # Standard chunking strategy
│   │       └── semantic.py  # Semantic chunking strategy
│   │
│   └── prompts/         # Prompt templates
│       ├── __init__.py
│       └── answer_prompt.py # Answer generation prompts
│
├── scripts/             # Executable scripts
│   ├── run_evaluation.sh # Main evaluation runner wrapper
│   │
│   ├── ingest/          # Data ingestion scripts
│   │   ├── ingest_master.py # Master ingestion script
│   │   └── seed_slack.py    # Slack data seeding utility
│   │
│   ├── evaluation/      # Evaluation and analysis
│   │   ├── evaluate_trulens.py      # TruLens evaluation runner
│   │   ├── eval_rag_bot.py          # Legacy evaluation script
│   │   ├── analyze_performance.py   # Performance analysis
│   │   ├── analyze_trulens_results.py # TruLens results analyzer
│   │   └── compare_systems.py       # System comparison tool
│   │
│   ├── database/        # Database utilities
│   │   ├── check_db.py     # Database inspection
│   │   ├── verify_db.py    # Database verification
│   │   └── migrate_results.py # Results migration
│   │
│   └── dashboard/       # Dashboard scripts
│       ├── start_dashboard.py  # Dashboard launcher
│       └── start_dashboard.sh  # Dashboard shell wrapper
│
├── tests/               # Test files
│   ├── test_langchain_rag.py          # Basic RAG tests
│   ├── test_trulens_instrumentation.py # TruLens integration tests
│   ├── test_trulens_setup.py          # TruLens setup tests
│   ├── test.json                       # Test dataset (minimal)
│   ├── test_quick.json                 # Quick test dataset
│   └── test_set.json                   # Full test dataset (50 Q&A pairs)
│
├── data/                # Data files (gitignored)
│   ├── pdfs/           # PDF documents for ingestion
│   ├── chroma_db/      # ChromaDB vector store
│   ├── databases/      # SQLite databases
│   │   ├── trulens_eval.db       # TruLens evaluation results
│   │   ├── default.sqlite         # Default database
│   │   └── evaluation_history.db  # Legacy evaluation history
│   └── logs/           # Application logs
│
├── docs/                # Documentation
│   ├── README.md                      # Copy of main README
│   ├── PROJECT_STRUCTURE.md           # This file
│   ├── COMMANDS.md                    # Command reference
│   ├── TECHNICAL_SUMMARY.md           # Technical architecture
│   ├── TRULENS_QUICKSTART.md         # TruLens quick start guide
│   ├── TRULENS_EVALUATION_SUMMARY.md # TruLens evaluation guide
│   ├── TRULENS_MIGRATION_PLAN.md     # TruLens migration details
│   ├── MIGRATION_COMPLETE.md          # Migration completion notes
│   └── ProjectSummary.md              # Original project summary
│
└── archive/             # Historical files
    ├── README.md        # Archive documentation
    └── evaluation_results_old/  # Old evaluation results

```

## Import Paths

After the reorganization, all imports from core modules should use the `src.` prefix:

```python
# Correct imports
from src.rag_logic import generate_answer
from src.llm import LLMFactory
from src.retrieval import RetrievalFactory
from src.ingest import IngestionFactory
from src.trulens_config import initialize_trulens

# Incorrect (old style - will not work)
from rag_logic import generate_answer
from llm import LLMFactory
```

## Configuration Paths

Key configuration paths have been updated:

| Configuration | Old Path | New Path |
|--------------|----------|----------|
| PDF Documents | `data_pdfs/` | `data/pdfs/` |
| ChromaDB | `chroma_db/` | `data/chroma_db/` |
| TruLens DB | `trulens_eval.db` | `data/databases/trulens_eval.db` |
| Evaluation DB | `evaluation_history.db` | `data/databases/evaluation_history.db` |
| Application Logs | `logs/` | `data/logs/` |

## Running Scripts

All scripts should be run from the project root directory:

```bash
# Ingestion
python scripts/ingest/ingest_master.py --strategy semantic

# Evaluation
./scripts/run_evaluation.sh --test
python scripts/evaluation/evaluate_trulens.py --limit 10

# Dashboard
./scripts/dashboard/start_dashboard.sh

# Bot
python src/bot.py

# Tests
python tests/test_langchain_rag.py
```

## Benefits of New Structure

1. **Clear Separation**: Core code (`src/`), scripts, tests, data, and docs are clearly separated
2. **Scalability**: Easy to add new modules within each category
3. **Discoverability**: Logical grouping makes it easier to find files
4. **Clean Root**: Only essential files at root level
5. **Standard Layout**: Follows Python project best practices
6. **Better Git**: Data files properly organized and gitignored

## Migration Notes

- All Python imports updated to use `src.` prefix
- Shell scripts updated to reference new paths
- Database paths updated in configuration files
- README.md updated with new structure
- `.gitignore` updated for new data/ directory layout
- No breaking changes to functionality - only file locations changed

## Next Steps for New Developers

1. Read `README.md` for quick start guide
2. Review `docs/TECHNICAL_SUMMARY.md` for architecture overview
3. See `docs/COMMANDS.md` for common commands
4. Check `docs/TRULENS_QUICKSTART.md` for evaluation workflow
5. Explore `src/` for core implementation
6. Run tests in `tests/` to verify setup

## Maintenance

When adding new files:
- Core logic → `src/`
- Executable scripts → `scripts/` (with appropriate subdirectory)
- Tests → `tests/`
- Documentation → `docs/`
- Data files → `data/` (and add to `.gitignore` if needed)
