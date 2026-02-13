from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from .base import RetrievalStrategy, RetrievalResult # Keep imports if needed by other files, but we are changing the usage

def get_rerank_retriever(base_retriever):
    """
    Returns a ContextualCompressionRetriever that uses a CrossEncoder to rerank results.
    """
    model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
    compressor = CrossEncoderReranker(model=model, top_n=5)
    return ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=base_retriever
    )
