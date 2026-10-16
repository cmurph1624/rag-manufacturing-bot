"""
Shared access to the vector store used by both ingestion and retrieval.
Backed by local ChromaDB by default, or Pinecone when VECTOR_DB=pinecone.
"""
from typing import Any, Dict, List

from src.config import VECTOR_DB, CHROMA_PATH, COLLECTION_NAME

# Lazy loaded so importing this module doesn't require a running database
_collection = None


def _chroma_client():
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_chroma_collection():
    global _collection
    if _collection is None:
        print(f"Connecting to ChromaDB at '{CHROMA_PATH}'...", flush=True)
        _collection = _chroma_client().get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def reset_chroma_collection() -> None:
    """Drops the collection through Chroma's API (safe even if a client is already open)."""
    global _collection
    try:
        _chroma_client().delete_collection(name=COLLECTION_NAME)
        print(f"Reset: deleted collection '{COLLECTION_NAME}'.", flush=True)
    except Exception:
        print("Reset: collection not found, nothing to reset.", flush=True)
    _collection = None


def upsert(
    ids: List[str],
    documents: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 100,
) -> None:
    """Writes chunks to whichever vector store is configured."""
    if VECTOR_DB == "pinecone":
        from src.retrieval.pinecone_client import get_pinecone_index
        index = get_pinecone_index(create_if_missing=True)

        # Pinecone only stores vectors + metadata, so the chunk text goes in metadata
        vectors = [
            (doc_id, embedding, {**metadata, "text": document})
            for doc_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas)
        ]
        for start in range(0, len(vectors), batch_size):
            index.upsert(vectors=vectors[start:start + batch_size])
    else:
        get_chroma_collection().upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
