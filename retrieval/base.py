from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
import chromadb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration (Shared)
DB_PATH = "./chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"

# Globals (Lazy loaded)
chroma_client = None
collection = None

def get_chroma_collection():
    global chroma_client, collection
    if collection is None:
        print(f"Connecting to ChromaDB at '{DB_PATH}'...")
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    return collection

@dataclass
class RetrievalResult:
    documents: List[str]
    metadatas: List[Dict[str, Any]]

class RetrievalStrategy(ABC):
    """
    Abstract base class for retrieval strategies.
    Different implementations can be swapped out (e.g., Semantic, Lexical).
    """
    @property
    @abstractmethod
    def type(self) -> str:
        """Returns the unique identifier for this retrieval strategy type."""
        pass

    @abstractmethod
    def retrieve(self, query: str, n_results: int = 7) -> RetrievalResult:
        pass
