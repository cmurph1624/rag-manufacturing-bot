# RAG Manufacturing Bot

This project establishes a Retrieval-Augmented Generation (RAG) bot that answers questions based on:
1.  **PDF Documents** (stored in `data_pdfs/`)
2.  **Slack History** (ingested from a specific channel)

It uses **Slack Bolt** for the bot interface, **ChromaDB** for vector storage, and **Ollama** for embeddings and generation.

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
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
```

## Files Description

-   **`bot.py`**: The main Slack bot application.
    -   Listens for `@App mentions`.
    -   Queries ChromaDB for relevant context.
    -   Generates answers using Llama 3.2 via Ollama.
    -   Cites sources (PDF filename + page, or Slack thread).

-   **`ingest_pdfs.py`**: Ingests PDF files.
    -   Reads all PDFs from `data_pdfs/`.
    -   Chunks text (500 chars, 50 overlap).
    -   Generates embeddings and stores them in ChromaDB (`aerostream_docs`).

-   **`ingest_slack.py`**: Ingests Slack channel history.
    -   Fetches history from the configured channel.
    -   Merges thread replies into single documents.
    -   Embeds and stores them in ChromaDB.
    -   *Note: Requires `CHANNEL_ID` to be set or correctly resolved.*

-   **`seed_slack.py`**: (Utility) Helper script to seed a Slack channel with mock data for testing.

-   **`check_db.py`**: (Utility) Simple script to verify the count of documents in ChromaDB and check for Slack entries.

## Usage

1.  **Start Ollama**:
    ```bash
    ollama serve
    ```

2.  **Ingest Data**:
    ```bash
    # Ingest PDFs
    python ingest_pdfs.py

    # Ingest Slack History
    python ingest_slack.py
    ```

3.  **Run the Bot**:
    ```bash
    python bot.py
    ```

## Troubleshooting

-   **SSL Errors**: The scripts use `certifi` to handle SSL context for Slack clients.
-   **Channel Not Found**: Ensure the correct Channel ID is used in `ingest_slack.py` if name resolution fails.
