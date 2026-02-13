import os
import shutil
import re
import numpy as np
import sklearn
from sklearn.metrics.pairwise import cosine_similarity
from ..base import (
    IngestionStrategy, get_chroma_collection, get_embedding, log_ingestion_config,
    PDF_FOLDER, DB_PATH
)
from ..loaders import process_pdf, process_json, get_slack_client, fetch_slack_history

def upsert_to_db(ids, documents, embeddings, metadatas):
    """
    Helper to upsert to either Chroma or Pinecone based on env var.
    """
    vector_db_type = os.getenv("VECTOR_DB", "chroma")
    
    if vector_db_type == "pinecone":
        try:
            from ...retrieval.pinecone_client import get_pinecone_index
            index = get_pinecone_index(create_if_missing=True)
            
            vectors = []
            for i, doc_id in enumerate(ids):
                metadata = metadatas[i].copy()
                metadata["text"] = documents[i] # Important: Store text in metadata for Pinecone
                vectors.append((doc_id, embeddings[i], metadata))
            
            # Upsert in batches of 100 to avoid limits
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                index.upsert(vectors=batch)
                print(f"    - Upserted batch of {len(batch)} to Pinecone.", flush=True)

        except ImportError:
            print("Error: Pinecone client not found. Please install pinecone-client.")
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")
            
    else:
        # Default to Chroma
        collection = get_chroma_collection()
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

class SemanticIngestionStrategy(IngestionStrategy):
    """
    Semantic ingestion strategy:
    - Splits text into sentences.
    - Groups sentences based on cosine similarity of their embeddings.
    """
    @property
    def type(self) -> str:
        return "semantic"

    def split_sentences(self, text):
        # Basic sentence splitting (improved regex)
        sentences = re.split(r'(?<=[.?!])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def combine_sentences(self, sentences, embeddings, threshold, buffer_size=1):
        """
        Combines sentences into chunks based on semantic similarity.
        """
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        
        # Calculate cosine distances between adjacent sentences
        distances = []
        for i in range(len(embeddings) - 1):
             # Cosine similarity is 1.0 for identical, -1.0 for opposite.
             # Distance = 1 - Similarity.
             sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
             dist = 1 - sim
             distances.append(dist)

        # We can use percentile as threshold if threshold implies percentile
        # But for now, let's treat the incoming threshold as a specific distance value (e.g. 0.3)
        # Higher distance = less similar. Break if distance > threshold.
        
        start_idx = 0
        
        # Simple loop to create chunks
        current_chunk = [sentences[0]]
        
        for i in range(len(distances)):
            dist = distances[i]
            
            if dist > threshold:
                # Semantic shift detected, finalize current chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i+1]]
            else:
                # Similar enough, continue chunk
                current_chunk.append(sentences[i+1])
        
        # Append the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    def ingest(self, reset: bool = False, **kwargs):
        threshold = kwargs.get("semantic_threshold", 0.4) # Default threshold for distance (0.0=same, 1.0=unrelated)
        
         # Handle Reset
        if reset:
            if os.path.exists(DB_PATH):
                print(f"Resetting database: Removing {DB_PATH}...", flush=True)
                shutil.rmtree(DB_PATH)
            else:
                print("Database path not found, nothing to reset.", flush=True)

        config = {"semantic_threshold": threshold}
        log_ingestion_config(self.type, config)
        
        print(f"Starting ingestion (Semantic) with Threshold: {threshold}", flush=True)
        collection = get_chroma_collection()

        # 1. Process Local Files (PDFs and JSONs)
        if os.path.exists(PDF_FOLDER):
            files = os.listdir(PDF_FOLDER)
            for filename in files:
                file_path = os.path.join(PDF_FOLDER, filename)
                
                # PDF Processing
                if filename.endswith(".pdf"):
                    print(f"Processing PDF: {filename}...", flush=True) 
                    pages = process_pdf(file_path)
                    for page_text, page_num in pages:
                        # Split sentences
                        sentences = self.split_sentences(page_text)
                        
                        if not sentences: continue

                        # Embed ALL sentences (Expensive!)
                        # Batching this would be better but get_embedding is single item for now
                        # We will accept the slowness for this proof of concept
                        print(f"  - Embedding {len(sentences)} sentences on Page {page_num}...", flush=True)
                        embeddings = []
                        for s in sentences:
                            e = get_embedding(s)
                            if not e:
                                # Fallback zero vector or skip
                                print("Warning: Empty embedding for sentence.")
                                e = [0.0] * 768 # Assuming 768 dim, kinda risky.
                            embeddings.append(e)
                        
                        # Chunk
                        text_chunks = self.combine_sentences(sentences, embeddings, threshold)
                        print(f"  - Created {len(text_chunks)} chunks for Page {page_num}", flush=True)

                        for i, chunk in enumerate(text_chunks):
                             embedding = get_embedding(chunk) # Re-embed the FULL chunk
                             if embedding:
                                upsert_to_db(
                                    ids=[f"{filename}_p{page_num}_c{i}"],
                                    documents=[chunk],
                                    embeddings=[embedding],
                                    metadatas=[{"source": filename, "page": page_num, "type": "manual"}]
                                )

                # JSON Processing (Similar logic, or keep as whole threads?)
                elif filename.endswith(".json"):
                     # Existing logic was to treat whole thread as one chunk.
                     # Semantic chunking on conversation structure is tricky. 
                     # Let's keep the existing logic for JSONs for now as it makes sense for Q&A pairs to stay together.
                     json_chunks = process_json(file_path)
                     for text, thread_id in json_chunks:
                        embedding = get_embedding(text)
                        if embedding:
                            upsert_to_db(
                                ids=[f"{filename}_{thread_id}"],
                                documents=[text],
                                embeddings=[embedding],
                                metadatas=[{"source": filename, "page": 0, "type": "conversation"}]
                            )

        # 2. Process Live Slack Data
        slack_client = get_slack_client()
        slack_channel_id = os.getenv("SLACK_CHANNEL_ID")
        
        if slack_client and slack_channel_id:
            for combined_text, ts in fetch_slack_history(slack_client, slack_channel_id):
                # For Slack, threads are "natural" semantic units. 
                # We could split them, but context (Q&A) is best kept together.
                # So we treat the whole thread as a chunk.
                embedding = get_embedding(combined_text)
                if embedding:
                    upsert_to_db(
                        ids=[f"slack_{ts}"],
                        embeddings=[embedding],
                        metadatas=[{"source": "Slack API", "timestamp": ts, "type": "tribal_knowledge"}],
                        documents=[combined_text]
                    )
                    print(f"Ingested Slack Thread: {combined_text[:40]}...", flush=True)

        print(f"--- Ingestion Complete ({self.type}) ---", flush=True)
