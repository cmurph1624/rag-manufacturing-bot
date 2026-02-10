from langchain_core.retrievers import BaseRetriever
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from .lexical import LexicalRetriever
from .rerank import get_rerank_retriever

class RetrievalFactory:
    """
    Factory to create LangChain Retrievers.
    """
    @staticmethod
    def get_strategy(strategy_type: str) -> BaseRetriever:
        # Initialize VectorStore (Semantic)
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma(
            persist_directory="./data/chroma_db",
            collection_name="aerostream_docs",
            embedding_function=embeddings
        )
        
        if strategy_type == "semantic":
            return vectorstore.as_retriever(search_kwargs={"k": 7})
        elif strategy_type == "lexical":
            return LexicalRetriever(k=7)
        elif strategy_type == "semantic-rerank":
            # Fetch more candidates for reranking (e.g., 20)
            base_retriever = vectorstore.as_retriever(search_kwargs={"k": 20})
            return get_rerank_retriever(base_retriever)
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy_type}")
