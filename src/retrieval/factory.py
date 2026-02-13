import os
from langchain_core.retrievers import BaseRetriever
from langchain_chroma import Chroma
from langchain_pinecone import PineconeVectorStore
from langchain_ollama import OllamaEmbeddings
from .lexical import LexicalRetriever
from .rerank import get_rerank_retriever
from .pinecone_client import PINECONE_INDEX_NAME

class RetrievalFactory:
    """
    Factory to create LangChain Retrievers.
    """
    @staticmethod
    def get_strategy(strategy_type: str) -> BaseRetriever:
        # Initialize VectorStore (Semantic)
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        vector_db_type = os.getenv("VECTOR_DB", "chroma")
        
        if vector_db_type == "pinecone":
            print(f"Using Pinecone VectorDB (Index: {PINECONE_INDEX_NAME})")
            vectorstore = PineconeVectorStore(
                index_name=PINECONE_INDEX_NAME,
                embedding=embeddings
            )
        else:
            print("Using ChromaDB (Local)")
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
