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
        """
        Splits text into semantic units (sentences or structural blocks).
        Uses improved regex to avoid splitting on:
        - Numbered lists (1., 2.)
        - Part numbers/Measurements (2.5, #RA-400)
        - Common abbreviations
        """
        # Regex explanation:
        # (?<!\d\.) : Negative lookbehind - not preceded by a digit AND dot (protects 1., 2.5.)
        # (?<=[.?!]): Positive lookbehind - must be preceded by sentence terminator
        # \s+      : One or more whitespaces
        # This preserves "1. Item" but splits "Sentence. Next"
        sentences = re.split(r'(?<!\d\.)(?<=[.?!])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _classify_chunk(self, text):
        """Helper to identify the structural type of a text chunk."""
        text = text.strip()
        if not text: return "empty"
        
        # Header detection:
        # 1. Ends with colon (e.g., "Required Tools:")
        # 2. Short and all caps (e.g., "INTRODUCTION")
        # 3. Starts with "Step" followed by number (e.g., "Step 1")
        if text.endswith(":") or (text.isupper() and len(text) < 60) or re.match(r'^Step\s+\d+', text, re.IGNORECASE):
            return "header"
            
        # List Item detection:
        # 1. Numbered lists: "1.", "1)", "1-"
        # 2. Bullets: "●", "-", "*", "•"
        if re.match(r'^(\d+[\.\)\-]|\.|[•\-\*])\s', text):
            return "list_item"
            
        # Table detection (heuristic):
        # Contains pipe separators or looks tabular
        if "|" in text and len(text.split("|")) > 2:
            return "table_row"
            
        return "text"

    def combine_sentences(self, sentences, embeddings, threshold, min_chunk_size=100):
        """
        Combines sentences into chunks based on structure and semantic similarity.
        Respects:
        - Minimum chunk size
        - Section boundaries (Headers, Lists)
        """
        if not sentences:
            return []

        chunks = []
        current_chunk = [sentences[0]]
        current_chunk_size = len(sentences[0])
        
        # Calculate cosine distances between adjacent sentences
        distances = []
        if len(embeddings) > 1:
            # Batch calculate similarities for efficiency if possible, 
            # here we loop as in original code but could be optimized.
            # Convert to numpy for faster ops if needed, but list grouping is fine for now.
            for i in range(len(embeddings) - 1):
                sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
                distances.append(1 - sim)
        else:
            distances = []

        for i in range(len(distances)):
            dist = distances[i]
            next_sent = sentences[i+1]
            next_type = self._classify_chunk(next_sent)
            current_sent = sentences[i]
            current_type = self._classify_chunk(current_sent)
            
            # --- Logic for Grouping ---
            
            # 1. Force Break: If next item is a Header, almost always start new chunk
            # (unless current chunk is very small)
            is_header_break = (next_type == "header")
            
            # 2. Force Group: 
            # - If current is Header, always keep next with it (Context)
            # - If both are Table Rows, keep together
            # - If both are List Items of same style (heuristic), prefer keeping together
            # - If next is very short (< 30 chars), prefer keeping with previous
            is_forced_group = (
                (current_type == "header") or 
                (current_type == "table_row" and next_type == "table_row") or
                (len(next_sent) < 50 and next_type == "text") # Keep short/fragments together
            )
            
            # 3. Size Constraint
            is_under_size = (current_chunk_size < min_chunk_size)
            
            # Decision
            should_split = False
            
            if is_header_break and not is_under_size:
                should_split = True
            elif is_forced_group:
                should_split = False
            elif is_under_size:
                should_split = False # Keep growing to meet min size
            elif dist > threshold:
                should_split = True # Semantic shift detected
            
            # Execute
            if should_split:
                chunks.append(" ".join(current_chunk))
                current_chunk = [next_sent]
                current_chunk_size = len(next_sent)
            else:
                current_chunk.append(next_sent)
                current_chunk_size += len(next_sent) + 1 # +1 for space
        
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
