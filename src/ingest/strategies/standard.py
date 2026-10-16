from ..base import IngestionStrategy, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP

class StandardIngestionStrategy(IngestionStrategy):
    """
    Standard ingestion strategy:
    - Fixed-size chunking with overlap, per page.
    """
    @property
    def type(self) -> str:
        return "standard"

    def get_config(self, **kwargs):
        return {
            "chunk_size": kwargs.get("chunk_size", DEFAULT_CHUNK_SIZE),
            "overlap": kwargs.get("overlap", DEFAULT_OVERLAP),
        }

    def chunk_text(self, text, chunk_size, overlap):
        """Splits text into overlapping chunks."""
        if chunk_size <= 0 or not 0 <= overlap < chunk_size:
            raise ValueError(f"Need chunk_size > 0 and 0 <= overlap < chunk_size (got {chunk_size}, {overlap})")

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break  # Last chunk already reaches the end; don't emit a tail that is pure overlap
            start += (chunk_size - overlap)
        return chunks

    def chunk_pdf(self, filename, pages, config):
        for page_text, page_num in pages:
            for i, chunk in enumerate(self.chunk_text(page_text, config["chunk_size"], config["overlap"])):
                yield f"{filename}_p{page_num}_c{i}", chunk, {"source": filename, "page": page_num, "type": "manual"}
