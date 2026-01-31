import ollama
from .base import RetrievalStrategy, RetrievalResult, get_chroma_collection, EMBEDDING_MODEL

class SemanticRetrievalStrategy(RetrievalStrategy):
    """
    Retrieves documents using vector similarity search via ChromaDB.
    """
    @property
    def type(self) -> str:
        return "semantic"

    def retrieve(self, query: str, n_results: int = 7) -> RetrievalResult:
        # Generate embedding for the query
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=query)
        query_embedding = response.get("embedding")

        if not query_embedding:
            print("Error: Failed to generate embedding for search.")
            return RetrievalResult(documents=[], metadatas=[])

        # Query ChromaDB
        col = get_chroma_collection()
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # Chroma returns lists of lists (one per query)
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []

        return RetrievalResult(documents=documents, metadatas=metadatas)
