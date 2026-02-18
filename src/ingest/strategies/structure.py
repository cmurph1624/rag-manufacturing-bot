import os
import re
import shutil
from typing import List, Dict, Any, Tuple

from ..base import (
    IngestionStrategy, get_chroma_collection, get_embedding, log_ingestion_config,
    PDF_FOLDER, DB_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
)
from ..loaders import process_pdf, process_json, get_slack_client, fetch_slack_history

class StructureIngestionStrategy(IngestionStrategy):
    """
    Structure-based ingestion strategy:
    - Chunks based on document structure (headers, sections, steps).
    - Preserves semantic tables and lists.
    - Falls back to standard chunking for non-structural content.
    """
    @property
    def type(self) -> str:
        return "structure"

    def _is_header(self, line: str) -> bool:
        """Detects if a line is a section header."""
        # Major numbered sections (e.g., "1. Introduction", "2. Scope")
        if re.match(r'^\d+\.\s+[A-Z]', line):
            return True
        
        # Specific keywords
        keywords = [
            "Scope", "Required Tools", "Installation Steps", "Procedure", 
            "Safety", "Introduction", "Summary", "Prerequisites", "Troubleshooting"
        ]
        if any(keyword in line for keyword in keywords):
            # Check if it looks like a header (short-ish, maybe capitalized)
            if len(line.split()) < 10: 
                return True
                
        return False

    def _is_step(self, line: str) -> bool:
        """Detects if a line is a step boundary."""
        # Bullet points, "Step N", or numbered lists
        return bool(re.match(r'^(●|-|\*)\s', line) or 
                    re.match(r'^Step\s+\d+[:.]', line, re.IGNORECASE) or
                    re.match(r'^\d+\.\s', line))

    def _is_table_row(self, line: str) -> bool:
        """Detects if a line looks like a table row."""
        # Check for multiple column-like gaps or explicit pipes
        return "   " in line.strip() or "|" in line

    def chunk_by_structure(self, text: str, max_size: int = 1500, min_size: int = 200) -> List[str]:
        """
        Chunks text based on logical sections.
        """
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, line in enumerate(lines):
            line_len = len(line) + 1 # +1 for newline
            is_header_line = self._is_header(line)
            is_step_line = self._is_step(line)
            is_table_row = self._is_table_row(line)
            
            # Logic to force a split
            should_split = False
            
            # 1. New Section Header found AND we have substantial content
            if is_header_line and current_length >= min_size:
                should_split = True
            
            # 2. Step boundary found AND we are getting full (proactive split)
            # This helps keep steps distinct rather than splitting inside a step description later
            elif is_step_line and current_length > max_size * 0.75:
                should_split = True
                
            # 3. Hard Limit: Identifying we WILL exceed max_size
            # If we don't split now, we'll overflow.
            # We prefer to split on steps/headers, but if we have to, we have to.
            elif current_length + line_len > max_size:
                # Exception: If it's a table row, try to keep it together (allow up to 1.5x max_size)
                if is_table_row and current_length < max_size * 1.5:
                    should_split = False
                else:
                    should_split = True

            if should_split and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
                
            current_chunk.append(line)
            current_length += line_len
            
        # Flush remaining
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        # Post-processing: Intelligent Merge
        final_chunks = []
        buffer_chunk = ""
        
        for chunk in chunks:
            chunk_len = len(chunk)
            buffer_len = len(buffer_chunk)
            
            # Decide whether to merge 'chunk' into 'buffer_chunk'
            should_merge = False
            
            if buffer_len + chunk_len < max_size:
                if buffer_len < min_size:
                    # Always merge if the previous chunk was too small
                    should_merge = True
                else:
                    # Both are decent size. Merge logic:
                    # Don't merge if the new chunk is a Major Heading
                    first_line = chunk.split('\n')[0]
                    if self._is_header(first_line):
                        should_merge = False # Keep major sections distinct
                    else:
                        should_merge = True # Merge continuity, lists, etc.
            
            if should_merge:
                buffer_chunk += ("\n" + chunk) if buffer_chunk else chunk
            else:
                if buffer_chunk:
                    final_chunks.append(buffer_chunk)
                buffer_chunk = chunk
        
        if buffer_chunk:
            final_chunks.append(buffer_chunk)
            
        return final_chunks

    def ingest(self, reset: bool = False, **kwargs):
        chunk_size_param = kwargs.get("chunk_size", 1000) # Unused usually but good to log
        # Params from kwargs or defaults
        max_chunk = kwargs.get("max_size", 1500)
        min_chunk = kwargs.get("min_size", 200)

        # Handle Reset
        if reset:
            if os.path.exists(DB_PATH):
                print(f"Resetting database: Removing {DB_PATH}...", flush=True)
                shutil.rmtree(DB_PATH)
            else:
                print("Database path not found, nothing to reset.", flush=True)
        
        # Log Logic
        config = {"strategy": "structure", "max_size": max_chunk, "min_size": min_chunk}
        log_ingestion_config(self.type, config)
        
        print(f"Starting ingestion (Structure) with Max Size: {max_chunk}, Min Size: {min_chunk}", flush=True)

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
                    
                    # Combine pages to maintain cross-page structure
                    full_text = ""
                    page_map = [] # (char_start, char_end, page_num)
                    current_idx = 0
                    
                    for page_text, page_num in pages:
                        # Clean up page headers/footers slightly if possible? 
                        # For now, just append.
                        page_len = len(page_text)
                        full_text += page_text + "\n"
                        page_map.append((current_idx, current_idx + page_len, page_num))
                        current_idx += page_len + 1
                    
                    structural_chunks = self.chunk_by_structure(full_text, max_size=max_chunk, min_size=min_chunk)
                    
                    for i, chunk in enumerate(structural_chunks):
                        # Find source page(s)
                        # We'll map the chunk's start to a page
                        chunk_start_in_full = full_text.find(chunk) # Approximate check
                        # Better way: track indices in chunk_by_structure, but finding valid substring is okay for now
                        # If finding fails (duplicates), we might get wrong page, but text context is unique enough usually
                        
                        source_page = 0
                        # Simple lookup: which page range contains chunk_start_in_full
                        if chunk_start_in_full != -1:
                            for start, end, p_num in page_map:
                                if start <= chunk_start_in_full <= end:
                                    source_page = p_num
                                    break
                                    
                        embedding = get_embedding(chunk)
                        if embedding:
                            collection.upsert(
                                ids=[f"{filename}_struct_{i}"],
                                documents=[chunk],
                                embeddings=[embedding],
                                metadatas=[{"source": filename, "page": source_page, "type": "structure"}]
                            )

                # JSON Processing (Keep existing logic)
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

        # 2. Process Live Slack Data (Keep existing logic)
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
                    
        print(f"--- Ingestion Complete ({self.type}) ---", flush=True)
