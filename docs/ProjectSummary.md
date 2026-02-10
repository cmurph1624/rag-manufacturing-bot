# Project Summary: AI-Powered Manufacturing Support Bot

**Goal:** Create a Retrieval-Augmented Generation (RAG) tool that answers support questions using both *official documentation* (PDFs) and *tribal knowledge* (Slack history).

## 1. The Problem
Manufacturing teams often face two challenges:
* **Fragmented Data:** Answers are split between official Standard Operating Procedures (SOPs) and informal chats.
* **Lost "Tribal Knowledge":** Critical fixes (e.g., "warm up the dampeners") are shared in Slack threads but never make it into the manual, leaving new technicians in the dark.

## 2. The Solution Architecture
We built a local, privacy-first PoC using the following stack:
* **Interface:** **Slack** (via Socket Mode for secure, firewall-friendly connection).
* **Brain (LLM):** **Ollama** running locally (using `llama3.2` for reasoning and `nomic-embed-text` for search).
* **Memory (Vector DB):** **ChromaDB** (stores data as mathematical "embeddings" for semantic search).
* **Coding Assistant:** **Antigravity** (used to generate 100% of the Python code).

## 3. Development Lifecycle

### Phase 1: Infrastructure & Connection
* **Objective:** Establish a secure link between local Python scripts and the Slack workspace.
* **Action:** Configured a Slack App with **Socket Mode** to bypass the need for public web servers.
* **Result:** The bot could "hear" mentions (`@ManufacturingHelpBot`) and respond with a basic "Hello."

### Phase 2: Ingesting "Official" Knowledge (PDFs)
* **Objective:** Teach the bot to read complex manufacturing documents.
* **Action:** Created synthetic documents for "AeroStream Drones" (Assembly Instructions, Error Codes, Safety Sheets).
* **Challenge:** The bot initially failed to find specific torque settings because the relevant text was split across different "chunks."
* **Solution:** We increased the retrieval window (`n_results=7`) to ensure the bot read enough context to connect "Step 2" (Loctite) with "Step 4" (Torque 2.5 Nm).

### Phase 3: Ingesting "Tribal" Knowledge (Slack History)
* **Objective:** Capture informal fixes that don't exist in manuals.
* **Action:** Seeded the Slack channel with realistic conversations (e.g., fixing a "Death Wobble" by warming up rubber dampeners). We then built a script to scrape, thread, and ingest these conversations into the same database as the PDFs.
* **Challenge:** The bot crashed because it tried to cite "Page Numbers" for Slack threads (which don't have pages).
* **Solution:** We implemented adaptive citation logic:
    * *If PDF:* Cite **Filename + Page Number**.
    * *If Slack:* Cite **"Slack Thread" + Date/Timestamp**.

## 4. Key Outcomes & Business Value
* **Dual-Source Intelligence:** The bot successfully answers questions using *either* source.
    * *Q: "What is the torque setting?"* -> **A: "2.5 Nm"** (Source: SOP PDF).
    * *Q: "How do I fix the death wobble?"* -> **A: "Warm the dampeners"** (Source: Slack Thread).
* **Conflict Resolution:** When the manual was outdated (e.g., pairing the V2 controller), the bot prioritized the newer advice found in the Slack chat history.
* **Data Privacy:** The entire solution runs locally, meaning no proprietary manufacturing data leaves the secure environment.

