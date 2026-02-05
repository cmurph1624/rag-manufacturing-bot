from abc import ABC, abstractmethod
import os
import chromadb
import ollama
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PDF_FOLDER = "data_pdfs"
DB_PATH = "chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"

# Defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

# Globals (Lazy loaded)
chroma_client = None
collection = None

def get_chroma_collection():
    global chroma_client, collection
    if collection is None:
        print(f"Connecting to ChromaDB at '{DB_PATH}'...", flush=True)
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    return collection

def get_embedding(text):
    """Generates an embedding vector using Ollama."""
    try:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return []

def log_ingestion_config(strategy_type: str, config: dict):
    """Logs ingestion config to database using a JSON column."""
    try:
        conn = sqlite3.connect("evaluation_history.db")
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
        
        # Check columns for schema migrations
        cursor.execute("PRAGMA table_info(ingestion_configs)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Migration: Add ingestion_type
        if "ingestion_type" not in columns:
            print("Migrating DB: Adding ingestion_type column...", flush=True)
            cursor.execute("ALTER TABLE ingestion_configs ADD COLUMN ingestion_type TEXT")

        # Migration: Add configuration_json
        if "configuration_json" not in columns:
             print("Migrating DB: Adding configuration_json column...", flush=True)
             cursor.execute("ALTER TABLE ingestion_configs ADD COLUMN configuration_json TEXT")

        # Map some standard fields for backward compatibility if present in config
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
    Different implementations can be swapped out (e.g., Standard, Semantic Chunking).
    """
    @property
    @abstractmethod
    def type(self) -> str:
        """Returns the unique identifier for this ingestion strategy type."""
        pass

    @abstractmethod
    def ingest(self, reset: bool = False, **kwargs):
        """
        Performs the ingestion process.
        """
        pass
