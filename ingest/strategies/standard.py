import os
import shutil
from ..base import (
    IngestionStrategy, get_chroma_collection, get_embedding, log_ingestion_config,
    PDF_FOLDER, DB_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
)
from ..loaders import process_pdf, process_json, get_slack_client, fetch_slack_history

class StandardIngestionStrategy(IngestionStrategy):
    """
    Standard ingestion strategy:
    - Fixed-size chunking with overlap.
    - Processes PDFs, JSONs, and Slack history.
    """
    @property
    def type(self) -> str:
        return "standard"

    def chunk_text(self, text, chunk_size, overlap):
        """Splits text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)
        return chunks

    def ingest(self, reset: bool = False, **kwargs):
        chunk_size = kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE)
        overlap = kwargs.get("overlap", DEFAULT_OVERLAP)

        # Handle Reset
        if reset:
            if os.path.exists(DB_PATH):
                print(f"Resetting database: Removing {DB_PATH}...", flush=True)
                shutil.rmtree(DB_PATH)
            else:
                print("Database path not found, nothing to reset.", flush=True)
        
        # Log Logic
        config = {"chunk_size": chunk_size, "overlap": overlap}
        log_ingestion_config(self.type, config)
        
        print(f"Starting ingestion (Standard) with Chunk Size: {chunk_size}, Overlap: {overlap}", flush=True)

        collection = get_chroma_collection()
        
        # 1. Process Local Files (PDFs and JSONs)
        if os.path.exists(PDF_FOLDER):
            files = os.listdir(PDF_FOLDER)
            print(f"Found {len(files)} files in {PDF_FOLDER}", flush=True)
            
            for filename in files:
                file_path = os.path.join(PDF_FOLDER, filename)
                
                # PDF Processing
                if filename.endswith(".pdf"):
                    print(f"Processing PDF: {filename}...", flush=True) 
                    pages = process_pdf(file_path)
                    for page_text, page_num in pages:
                        print(f"  - Page {page_num}", flush=True)
                        text_chunks = self.chunk_text(page_text, chunk_size, overlap)
                        for i, chunk in enumerate(text_chunks):
                            embedding = get_embedding(chunk)
                            if embedding:
                                collection.upsert(
                                    ids=[f"{filename}_p{page_num}_c{i}"],
                                    documents=[chunk],
                                    embeddings=[embedding],
                                    metadatas=[{"source": filename, "page": page_num, "type": "manual"}]
                                )

                # JSON Processing
                elif filename.endswith(".json"):
                    # print(f"Processing JSON: {filename}...")
                    json_chunks = process_json(file_path)
                    for text, thread_id in json_chunks:
                        embedding = get_embedding(text)
                        if embedding:
                            collection.upsert(
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
                embedding = get_embedding(combined_text)
                if embedding:
                    collection.upsert(
                        ids=[f"slack_{ts}"],
                        embeddings=[embedding],
                        metadatas=[{"source": "Slack API", "timestamp": ts, "type": "tribal_knowledge"}],
                        documents=[combined_text]
                    )
                    print(f"Ingested Slack Thread: {combined_text[:40]}...", flush=True)

        print(f"--- Ingestion Complete ({self.type}) ---", flush=True)
