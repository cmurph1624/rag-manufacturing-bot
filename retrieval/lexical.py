from typing import List, Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from .base import get_chroma_collection

class LexicalRetriever(BaseRetriever):
    """
    Retrieves documents using lexical search (keyword matching) via ChromaDB's valid metadata or document filters.
    """
    k: int = 7

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        col = get_chroma_collection()
        
        # Use ChromaDB's 'where_document' with $contains operator for substring match
        results = col.get(
            where_document={"$contains": query},
            limit=self.k,
            include=["documents", "metadatas"]
        )

        documents = results["documents"] if results["documents"] else []
        metadatas = results["metadatas"] if results["metadatas"] else []

        langchain_docs = []
        for i in range(len(documents)):
             # Ensure metadata is a dict
             meta = metadatas[i] if metadatas and i < len(metadatas) else {}
             langchain_docs.append(Document(page_content=documents[i], metadata=meta))
        
        return langchain_docs
