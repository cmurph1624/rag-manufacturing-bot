from .base import RetrievalStrategy, RetrievalResult, get_chroma_collection

class LexicalRetrievalStrategy(RetrievalStrategy):
    """
    Retrieves documents using lexical search (keyword matching) via ChromaDB's valid metadata or document filters.
    Note: ChromaDB's document search is limited. We use $contains on document content.
    """
    @property
    def type(self) -> str:
        return "lexical"

    def retrieve(self, query: str, n_results: int = 7) -> RetrievalResult:
        col = get_chroma_collection()
        
        # Use ChromaDB's 'where_document' with $contains operator for substring match
        results = col.get(
            where_document={"$contains": query},
            limit=n_results,
            include=["documents", "metadatas"]
        )

        # Chroma's 'get' returns lists directly (not lists of lists like 'query')
        documents = results["documents"] if results["documents"] else []
        metadatas = results["metadatas"] if results["metadatas"] else []

        return RetrievalResult(documents=documents, metadatas=metadatas)
