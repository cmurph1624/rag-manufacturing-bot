from typing import List, Tuple
from sentence_transformers import CrossEncoder
from .base import RetrievalStrategy, RetrievalResult
from .semantic import SemanticRetrievalStrategy

# Global model cache to avoid reloading on every request
_reranker_model = None
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"

def get_reranker_model():
    global _reranker_model
    if _reranker_model is None:
        print(f"Loading reranker model '{RERANKER_MODEL_NAME}'... (This may take a while on first run)")
        _reranker_model = CrossEncoder(RERANKER_MODEL_NAME, max_length=512)
    return _reranker_model

class SemanticRerankingRetrievalStrategy(RetrievalStrategy):
    """
    Two-stage retrieval:
    1. Semantic Search (Retrieves N candidates, e.g., 20)
    2. Reranking using a Cross-Encoder (Selects top K, e.g., 5)
    """
    @property
    def type(self) -> str:
        return "semantic-rerank"

    def retrieve(self, query: str, n_results: int = 5) -> RetrievalResult:
        # Step 1: coarse retrieval (get more candidates than needed)
        # We fetch 4x the requested amount to give the reranker enough candidates
        initial_k = n_results * 4  
        semantic_strategy = SemanticRetrievalStrategy()
        
        # We need to manually match the return type logic if we invoke another strategy
        # But here we just use it as a helper
        initial_result = semantic_strategy.retrieve(query, n_results=initial_k)
        
        docs = initial_result.documents
        metas = initial_result.metadatas
        
        if not docs:
            return initial_result

        # Step 2: Rerank
        model = get_reranker_model()
        
        # Prepare pairs: (Query, Document_Text)
        pairs = [[query, doc] for doc in docs]
        
        # Predict scores
        scores = model.predict(pairs)
        
        # Combine docs, metas, and scores
        ranked_results: List[Tuple[float, str, dict]] = []
        for i in range(len(docs)):
            ranked_results.append((scores[i], docs[i], metas[i]))
            
        # Sort by score descending
        ranked_results.sort(key=lambda x: x[0], reverse=True)
        
        # Slice top n_results
        top_results = ranked_results[:n_results]
        
        # Unpack back into lists
        final_docs = [r[1] for r in top_results]
        final_metas = [r[2] for r in top_results]
        
        return RetrievalResult(documents=final_docs, metadatas=final_metas)
