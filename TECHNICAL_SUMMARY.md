# Technical Summary: AI-Powered Manufacturing Support Bot

## Overview
The application is a **Retrieval-Augmented Generation (RAG)** system designed to answer manufacturing support questions. It creates a unified knowledge base by ingesting both official documentation (PDFs) and informal "tribal knowledge" (Slack conversation history) and exposes this intelligence via a Slack Bot interface.

The system runs entirely **locally** to ensure data privacy, utilizing local LLM inference and a local vector database.

## System Architecture

### 1. Core Stack
*   **Language:** Python 3.10+
*   **Interface:** Slack Bot (Socket Mode)
*   **LLM Provider:** Ollama (Local Inference)
*   **Vector Database:** ChromaDB (Local Persistence)
*   **Orchestration:** Custom Python Scripts

### 2. AI Models (via Ollama)
*   **Generation Model:** `llama3.2`
    *   Selected for its balance of reasoning capability and speed for real-time chat.
*   **Embedding Model:** `nomic-embed-text`
    *   Used to convert text chunks into vector embeddings for semantic search.
*   **Evaluation Judge:** `llama3.1`
    *   A larger model (8B) used in the evaluation pipeline to judge the correctness of the bot's answers against a gold standard.

### 3. Data Storage & Schema
*   **Database:** ChromaDB
*   **Storage Location:** `./chroma_db` (Persistent on disk)
*   **Collection Name:** `aerostream_docs`
*   **Data Structure:**
    *   **Document:** The raw text chunk (e.g., a paragraph from a PDF or a merged Slack thread).
    *   **Embedding:** High-dimensional vector representation of the document.
    *   **Metadata:**
        *   `source`: Filename (e.g., `manual_v1.pdf`) or `Slack Thread`.
        *   `timestamp` / `page`: Location identifier.
        *   `type`: `manual` (PDF) or `tribal_knowledge` (Slack).
        *   `id`: Unique ID (e.g., `filename_p1_c0` or `slack_123456.789`).

## Key Components

### A. Data Ingestion Pipeline
The system supports multiple data sources, processed by dedicated scripts:

1.  **PDF Ingestion (`ingest_pdfs.py`, `ingest_master.py`)**
    *   **Library:** `pdfplumber` (optimized for extraction, including tables).
    *   **Process:**
        1.  Extracts text page-by-page.
        2.  Chunks text into segments (default `1000` characters) with overlap (`200` characters) to preserve context.
        3.  Generates embeddings via `ollama`.
        4.  Upserts to ChromaDB.

2.  **Slack Ingestion (`ingest_slack.py`)**
    *   **Library:** `slack_sdk`
    *   **Process:**
        1.  Fetches channel history using `conversations_history`.
        2.  Identifies threads and fetches replies using `conversations_replies`.
        3.  **Merging Strategy:** Combines the parent question and all replies into a single "Document" to maintain semantic continuity.
        4.  Generates embeddings and upserts to ChromaDB.

### B. RAG Execution Loop (`rag_logic.py`)
This module handles the real-time query processing:
1.  **Receive Query:** User asks a question in Slack.
2.  **Embed:** The query is converted to a vector using `nomic-embed-text`.
3.  **Retrieve:** ChromaDB is queried for the **Top 7** most similar chunks (`n_results=7`).
4.  **Prompt Construction:** A system prompt is combined with the retrieved chunks (Context) and the user's question.
    *   *System Prompt:* "You are a helpful manufacturing support assistant. Answer the question using ONLY the following context..."
5.  **Generate:** The prompt is sent to `llama3.2` via `ollama.chat`.
6.  **Cite:** The system appends source citations (e.g., "*References: Manual A (Page 2)*") based on the metadata of the retrieved chunks.

### C. Slack Interface (`bot.py`)
*   **Framework:** Slack Bolt / WebClient.
*   **Connection Mode:** **Socket Mode**.
    *   Uses an App Level Token (`xapp-...`) to establish a WebSocket connection.
    *   Bypasses the need for a public IP or firewall changes (ideal for secure manufacturing environments).
    *   Listens for App Mentions (`@ManufacturingHelpBot`).

### D. Evaluation Framework (`evaluate.py`)
*   **Methodology:** Automated ensuring using an "LLM-as-a-Judge".
*   **Test Data:** `test_set.json` containing pairs of Questions and Gold Answers.
*   **Process:**
    1.  Bot generates an answer for a test question.
    2.  Judge Model (`llama3.1`) compares the Bot Answer vs. Gold Answer.
    3.  Judge determines if the answer is `CORRECT` or `INCORRECT` based on factual accuracy.
*   **Metrics:** Accuracy percentage, Latency, and Citation correctness.

## Configuration & Dependencies

### Environment Variables (`.env`)
*   `SLACK_BOT_TOKEN`: OAuth token for sending messages.
*   `SLACK_APP_TOKEN`: App-level token for Socket Mode.
*   `SLACK_CHANNEL_ID`: Target channel for ingestion.

### Key Python Libraries
*   `chromadb`: Vector database client.
*   `ollama`: Client for interacting with local Ollama instance.
*   `slack_sdk`: Official Slack API client.
*   `pdfplumber`: Robust PDF text extraction.
*   `python-dotenv`: Environment variable management.
*   `tqdm`: Progress bars for ingestion/evaluation.
