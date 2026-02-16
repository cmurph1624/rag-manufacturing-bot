# AeroStream RAG Manufacturing Bot - Application Overview

## 1. Executive Summary
This application is a Retrieval-Augmented Generation (RAG) System designed to assist "AeroStream" manufacturing technicians and support engineers. It provides instant, accurate answers to technical questions about drone maintenance, assembly procedures, and troubleshooting by retrieving information from verified Standard Operating Procedures (SOPs), Technical Notes, and "Tribal Knowledge" from internal communications.

## 2. Business Context

### 2.1 The Problem
In the high-precision drone manufacturing environment, critical information is often scattered across various formats:
*   **Formal Documentation:** PDFs of SOPs, Safety Manuals, and Maintenance Schedules.
*   **Tribal Knowledge:** Valuable troubleshooting tips and undocumented fixes shared in Slack channels or via email.
*   **Legacy Data:** Older manual versions that may still apply to legacy fleets.

Technicians often spend excessive time searching for specific values (e.g., torque settings) or debugging obscure error codes, leading to production delays and potential safety risks.

### 2.2 The Solution
The **Manufacturing Bot** serves as a centralized knowledge interface. It ingests both formal and informal documentation into a searchable vector database. Users can textually query the system to receive:
*   Precise answers (e.g., "Set torque to 2.5 Nm").
*   Source citations (e.g., "SOP-01, Page 3").
*   Safety warnings (e.g., "Do not charge above 40°C").

### 2.3 User Persona
*   **Primary User:** Assembly Line Technicians, Field Service Engineers.
*   **Goal:** Resolve technical blockers immediately without escalating to senior engineering.
*   **Key Use Cases:**
    *   Retrieving specific assembly parameters (torque, voltage, part numbers).
    *   Diagnosing error codes (LED patterns, beep codes).
    *   Accessing "field fixes" for known issues (e.g., cold weather dampener stiffness).

## 3. Technical Architecture

### 3.1 Technology Stack
*   **Language:** Python 3.10+
*   **Orchestration Framework:** [LangChain](https://www.langchain.com/)
*   **LLM Inference:** [Ollama](https://ollama.com/) (Local Inference)
    *   **Generation Model:** `llama3` (or configured via `LLM_MODEL_NAME`)
    *   **Safety Model:** `llama-guard3:1b` (1B parameter model for efficiency)
*   **Embedding Model:** `nomic-embed-text`
*   **Vector Database:**
    *   **Local:** ChromaDB (`./data/chroma_db`)
    *   **Cloud Capability:** Configuration support for Pinecone migration.
*   **Evaluation:** Ragas (Retrieval Augmented Generation Assessment)

### 3.2 System Data Flow
1.  **User Input:** The user submits a natural language query via the dashboard.
2.  **Safety Guardrail:** The input is immediately checked by `llama-guard3:1b` to detect and refuse adversarial, unsafe, or malicious prompts (e.g., "How to modify battery for explosion").
3.  **Retrieval:** Use `RetrievalFactory` to select a strategy:
    *   **Semantic:** Vector similarity search using `nomic-embed-text`.
    *   **Lexical:** Keyword matching (BM25) for specific part numbers.
    *   **Re-ranking:** Semantic search followed by a cross-encoder re-ranking step for higher precision.
4.  **Generation:** The top retrieval results are inserted into a prompt template alongside the user query. The LLM generates a response citing the provided context.
5.  **Citations:** The system parses metadata to append source references (Document Name, Page Number) to the final answer.

### 3.3 Key Components
*   **`src/rag_logic.py`**: The core application controller. Handles the end-to-end pipeline from safety check to response generation.
*   **`src/retrieval/factory.py`**: A factory pattern implementation allowing dynamic switching between Chroma and Pinecone, as well as different retrieval algorithms (Semantic vs. Lexical).
*   **`scripts/dashboard/`**: A Streamlit-based web interface for user interaction.
*   **`tests/test_set.json`**: A curated "Golden Dataset" of question-answer pairs used for automated evaluation.

## 4. Domain Specifics (AeroStream)
The application is tailored for the following proprietary products:
*   **Falcon X1 / Falcon Pro:** Commercial quadcopters used for industrial inspection.
*   **Eagle Eye V2:** The remote controller unit associated with the Falcon series.
*   **Common Issues Handled:**
    *   **"Death Wobble":** A known issue with gimbal dampeners in cold weather.
    *   **"Puffed Batteries":** Safety protocol for degraded LiPo batteries.
    *   **Connectivity:** Pairing procedures and interference management.
