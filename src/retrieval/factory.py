from langchain_core.retrievers import BaseRetriever
from langchain_ollama import OllamaEmbeddings

from src.config import VECTOR_DB, CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL
from .lexical import LexicalRetriever
from .rerank import get_rerank_retriever

# Number of chunks handed to the LLM
TOP_K = 7
# Candidates fetched before the cross-encoder narrows them down
RERANK_CANDIDATES = 20


def _get_vectorstore():
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    if VECTOR_DB == "pinecone":
        from langchain_pinecone import PineconeVectorStore
        from .pinecone_client import PINECONE_INDEX_NAME
        print(f"Using Pinecone VectorDB (Index: {PINECONE_INDEX_NAME})")
        return PineconeVectorStore(index_name=PINECONE_INDEX_NAME, embedding=embeddings)

    from langchain_chroma import Chroma
    print("Using ChromaDB (Local)")
    return Chroma(
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


class RetrievalFactory:
    """
    Factory to create LangChain Retrievers.
    """
    @staticmethod
    def get_strategy(strategy_type: str) -> BaseRetriever:
        if strategy_type == "semantic":
            return _get_vectorstore().as_retriever(search_kwargs={"k": TOP_K})
        elif strategy_type == "lexical":
            return LexicalRetriever(k=TOP_K)
        elif strategy_type == "semantic-rerank":
            base_retriever = _get_vectorstore().as_retriever(search_kwargs={"k": RERANK_CANDIDATES})
            return get_rerank_retriever(base_retriever)
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy_type}")
