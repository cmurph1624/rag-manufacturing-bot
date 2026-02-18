from typing import List
import os
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import numpy as np

class LexicalRetriever(BaseRetriever):
    """
    Retrieves documents using BM25 lexical search.
    Works with both ChromaDB and Pinecone by building an in-memory BM25 index.
    """
    k: int = 7
    _bm25_index = None
    _doc_ids = None
    _documents = None
    _metadatas = None

    def _build_index_from_chroma(self):
        """Build BM25 index from ChromaDB."""
        from .base import get_chroma_collection

        col = get_chroma_collection()
        all_docs = col.get(include=["documents", "metadatas"])

        if not all_docs["documents"]:
            print("Warning: No documents found in ChromaDB for BM25 indexing")
            return None, None, None, None

        return (
            all_docs["ids"],
            all_docs["documents"],
            all_docs["metadatas"],
            all_docs["documents"]
        )

    def _build_index_from_pinecone(self):
        """Build BM25 index from Pinecone using query-based sampling."""
        from .pinecone_client import get_pinecone_index
        import random

        index = get_pinecone_index()
        stats = index.describe_index_stats()
        total_vectors = stats.total_vector_count

        print(f"Fetching vectors from Pinecone for BM25 indexing (total: {total_vectors})...")

        all_ids = []
        all_texts = []
        all_metadatas = []

        try:
            # Use query() with diverse random vectors to sample the index
            # This is the most reliable method across Pinecone versions
            print("  Using query() to sample documents...")

            dimension = stats.dimension
            queries_to_make = min(20, (total_vectors // 50) + 1)  # Adaptive based on size

            for i in range(queries_to_make):
                # Create random query vector to get diverse results
                if i == 0:
                    # First query: zero vector
                    query_vector = [0.0] * dimension
                else:
                    # Subsequent queries: random vectors for diversity
                    query_vector = [random.uniform(-1, 1) for _ in range(dimension)]

                # Query Pinecone
                results = index.query(
                    vector=query_vector,
                    top_k=min(100, total_vectors),
                    include_metadata=True
                )

                # Extract documents
                for match in results.get('matches', []):
                    vec_id = match['id']

                    # Deduplicate
                    if vec_id in all_ids:
                        continue

                    all_ids.append(vec_id)

                    # Extract text from metadata
                    metadata = match.get('metadata', {})
                    text = metadata.get('text', '')

                    if not text:
                        # Fallback: Check alternative field names
                        text = metadata.get('page_content', metadata.get('content', ''))

                    all_texts.append(text)
                    all_metadatas.append(metadata)

                print(f"  Progress: {len(all_ids)} documents fetched ({i+1}/{queries_to_make} queries)")

                # Stop if we've sampled enough documents (cap at 2000 for performance)
                if len(all_ids) >= min(2000, total_vectors):
                    print(f"  Reached {len(all_ids)} documents, stopping")
                    break

        except Exception as e:
            print(f"  ✗ Error fetching from Pinecone: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None

        if not all_texts:
            print("  ✗ Warning: No documents found in Pinecone")
            return None, None, None, None

        # Check if texts are empty
        non_empty_count = sum(1 for text in all_texts if text.strip())
        if non_empty_count == 0:
            print(f"  ✗ Warning: All {len(all_texts)} documents have empty text!")
            print(f"  Check that 'text' field exists in Pinecone metadata")
            return None, None, None, None

        print(f"  ✓ Built BM25 index with {len(all_texts)} documents ({non_empty_count} non-empty)")
        return all_ids, all_texts, all_metadatas, all_texts

    def _build_index(self):
        """Build BM25 index from the configured vector database."""
        if self._bm25_index is not None:
            return  # Already built

        vector_db_type = os.getenv("VECTOR_DB", "chroma")

        if vector_db_type == "pinecone":
            doc_ids, documents, metadatas, corpus = self._build_index_from_pinecone()
        else:
            doc_ids, documents, metadatas, corpus = self._build_index_from_chroma()

        if not corpus:
            self._bm25_index = None
            return

        self._doc_ids = doc_ids
        self._documents = documents
        self._metadatas = metadatas

        # Tokenize documents (simple whitespace + lowercase)
        tokenized_corpus = [doc.lower().split() for doc in corpus]

        # Build BM25 index
        self._bm25_index = BM25Okapi(tokenized_corpus)
        print(f"BM25 index built successfully with {len(corpus)} documents")

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Retrieve documents using BM25."""
        # Build index if not already built
        self._build_index()

        if self._bm25_index is None or not self._documents:
            print("Warning: BM25 index is empty, returning no results")
            return []

        # Tokenize query
        tokenized_query = query.lower().split()

        # Get BM25 scores
        scores = self._bm25_index.get_scores(tokenized_query)

        # Get top-k indices
        top_k_idx = np.argsort(scores)[::-1][:self.k]

        # Filter out zero scores (no matches)
        top_k_idx = [idx for idx in top_k_idx if scores[idx] > 0]

        if not top_k_idx:
            print(f"Warning: No BM25 matches found for query: {query}")
            return []

        # Create LangChain Documents
        langchain_docs = []
        for idx in top_k_idx:
            doc = Document(
                page_content=self._documents[idx],
                metadata=self._metadatas[idx] if self._metadatas else {}
            )
            langchain_docs.append(doc)

        print(f"BM25 found {len(langchain_docs)} matches")
        return langchain_docs
