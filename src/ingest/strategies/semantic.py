import re
import numpy as np
from ..base import IngestionStrategy, get_embedding

# Embedding size of nomic-embed-text, used as a neutral fallback when a sentence fails to embed
EMBEDDING_DIM = 768


def cosine_distance(a, b) -> float:
    """1 - cosine similarity. Zero vectors are treated as unrelated (distance 1.0)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 1.0
    return 1.0 - float(np.dot(a, b) / norm)

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
        
        # Cosine distances between adjacent sentences
        distances = [cosine_distance(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)]

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

    def get_config(self, **kwargs):
        # Cosine distance threshold (0.0 = same meaning, 1.0 = unrelated)
        return {"semantic_threshold": kwargs.get("semantic_threshold", 0.4)}

    def chunk_pdf(self, filename, pages, config):
        for page_text, page_num in pages:
            sentences = self.split_sentences(page_text)
            if not sentences:
                continue

            # Embedding every sentence is slow, but it is what lets us find semantic shifts
            print(f"  - Embedding {len(sentences)} sentences on Page {page_num}...", flush=True)
            embeddings = []
            for sentence in sentences:
                embedding = get_embedding(sentence)
                if not embedding:
                    print("Warning: Empty embedding for sentence.", flush=True)
                    embedding = [0.0] * EMBEDDING_DIM
                embeddings.append(embedding)

            text_chunks = self.combine_sentences(sentences, embeddings, config["semantic_threshold"])
            print(f"  - Created {len(text_chunks)} chunks for Page {page_num}", flush=True)

            for i, chunk in enumerate(text_chunks):
                # The chunk itself is re-embedded as a whole when it is stored
                yield f"{filename}_p{page_num}_c{i}", chunk, {"source": filename, "page": page_num, "type": "manual"}
