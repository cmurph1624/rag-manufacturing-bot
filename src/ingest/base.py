from abc import ABC, abstractmethod
import os
import ollama
import sqlite3
import json
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List, Tuple

from src.config import EMBEDDING_MODEL, VECTOR_DB
from src.vectorstore import upsert, reset_chroma_collection
from .loaders import process_pdf, process_json, get_slack_client, fetch_slack_history

# Configuration
PDF_FOLDER = "data/pdfs"
INGESTION_LOG_DB = "data/databases/evaluation_history.db"

# Defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

# (chunk_id, text, metadata)
Chunk = Tuple[str, str, Dict[str, Any]]


def get_embedding(text):
    """Generates an embedding vector using Ollama. Returns [] on failure."""
    try:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}", flush=True)
        return []

def reset_vector_store():
    """Clears previously ingested chunks so a run starts from an empty store."""
    if VECTOR_DB == "pinecone":
        print("Warning: --reset only clears the local ChromaDB. "
              "Delete Pinecone vectors from the Pinecone console if needed.", flush=True)
        return

    reset_chroma_collection()

def log_ingestion_config(strategy_type: str, config: dict):
    """Logs ingestion config to database using a JSON column."""
    try:
        os.makedirs(os.path.dirname(INGESTION_LOG_DB), exist_ok=True)
        conn = sqlite3.connect(INGESTION_LOG_DB)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingestion_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                chunk_size INTEGER,
                overlap INTEGER,
                embedding_model TEXT NOT NULL,
                ingestion_type TEXT,
                configuration_json TEXT
            )
        ''')

        # Migrate tables created before these columns existed
        cursor.execute("PRAGMA table_info(ingestion_configs)")
        columns = [info[1] for info in cursor.fetchall()]
        for column in ("ingestion_type", "configuration_json"):
            if column not in columns:
                print(f"Migrating DB: Adding {column} column...", flush=True)
                cursor.execute(f"ALTER TABLE ingestion_configs ADD COLUMN {column} TEXT")

        # Default to 0 if not present to satisfy potential NOT NULL constraints from old schema
        chunk_size = config.get("chunk_size", 0)
        overlap = config.get("overlap", 0)

        cursor.execute('''
            INSERT INTO ingestion_configs (timestamp, chunk_size, overlap, embedding_model, ingestion_type, configuration_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), chunk_size, overlap, EMBEDDING_MODEL, strategy_type, json.dumps(config)))

        conn.commit()
        conn.close()
        print(f"Logged ingestion config: Type={strategy_type}, Config={config}", flush=True)

    except Exception as e:
        print(f"Warning: Failed to log ingestion config to database: {e}", flush=True)


class IngestionStrategy(ABC):
    """
    Abstract base class for ingestion strategies.

    The pipeline (reset, PDFs, JSON conversation logs, live Slack history, embedding
    and storage) is shared; strategies only decide how a PDF is split into chunks.
    """
    @property
    @abstractmethod
    def type(self) -> str:
        """Returns the unique identifier for this ingestion strategy type."""
        pass

    @abstractmethod
    def get_config(self, **kwargs) -> Dict[str, Any]:
        """Returns the parameters this strategy uses, picked out of the CLI kwargs."""
        pass

    @abstractmethod
    def chunk_pdf(self, filename: str, pages: List[Tuple[str, int]], config: Dict[str, Any]) -> Iterable[Chunk]:
        """Splits a PDF's (page_text, page_number) pairs into chunks."""
        pass

    def ingest(self, reset: bool = False, **kwargs):
        """
        Performs the ingestion process.
        """
        if reset:
            reset_vector_store()

        config = self.get_config(**kwargs)
        log_ingestion_config(self.type, config)
        print(f"Starting ingestion ({self.type}) with {config}", flush=True)

        stored = skipped = 0
        for chunks in self._iter_sources(config):
            s, k = self._store(chunks)
            stored += s
            skipped += k

        print(f"--- Ingestion Complete ({self.type}): {stored} chunks stored, {skipped} skipped ---", flush=True)
        if skipped:
            print("Warning: skipped chunks failed to embed. Is Ollama running with "
                  f"'{EMBEDDING_MODEL}' pulled?", flush=True)

    def _iter_sources(self, config: Dict[str, Any]) -> Iterator[List[Chunk]]:
        """Yields one list of chunks per source (PDF file, JSON file, Slack channel)."""
        # 1. Process Local Files (PDFs and JSONs)
        if os.path.exists(PDF_FOLDER):
            files = sorted(os.listdir(PDF_FOLDER))
            print(f"Found {len(files)} files in {PDF_FOLDER}", flush=True)

            for filename in files:
                file_path = os.path.join(PDF_FOLDER, filename)

                if filename.endswith(".pdf"):
                    print(f"Processing PDF: {filename}...", flush=True)
                    yield list(self.chunk_pdf(filename, process_pdf(file_path), config))

                elif filename.endswith(".json"):
                    # Each Q&A thread stays whole: question and answer are only useful together
                    yield [
                        (f"{filename}_{thread_id}", text, {"source": filename, "page": 0, "type": "conversation"})
                        for text, thread_id in process_json(file_path)
                    ]

        # 2. Process Live Slack Data (threads are kept whole, like JSON conversations)
        slack_client = get_slack_client()
        slack_channel_id = os.getenv("SLACK_CHANNEL_ID")

        if slack_client and slack_channel_id:
            yield [
                (f"slack_{ts}", text, {"source": "Slack API", "timestamp": ts, "type": "tribal_knowledge"})
                for text, ts in fetch_slack_history(slack_client, slack_channel_id)
            ]

    def _store(self, chunks: List[Chunk]) -> Tuple[int, int]:
        """Embeds and upserts chunks. Returns (stored, skipped)."""
        ids, documents, embeddings, metadatas = [], [], [], []
        for chunk_id, text, metadata in chunks:
            embedding = get_embedding(text)
            if not embedding:
                continue
            ids.append(chunk_id)
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append(metadata)

        if ids:
            upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(ids), len(chunks) - len(ids)
