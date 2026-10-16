import re
from typing import List

from ..base import IngestionStrategy

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

    def get_config(self, **kwargs):
        return {
            "max_size": kwargs.get("max_size", 1500),
            "min_size": kwargs.get("min_size", 200),
        }

    def chunk_pdf(self, filename, pages, config):
        # Combine pages so sections that cross a page break stay together
        full_text = ""
        page_map = []  # (char_start, char_end, page_num)
        for page_text, page_num in pages:
            start = len(full_text)
            full_text += page_text + "\n"
            page_map.append((start, start + len(page_text), page_num))

        structural_chunks = self.chunk_by_structure(full_text, max_size=config["max_size"], min_size=config["min_size"])

        # Chunks are contiguous, in-order substrings of full_text, so searching forward
        # from the previous chunk finds each one's true position even if text repeats
        cursor = 0
        for i, chunk in enumerate(structural_chunks):
            position = full_text.find(chunk, cursor)
            source_page = 0
            if position != -1:
                cursor = position + len(chunk)
                for start, end, page_num in page_map:
                    if start <= position <= end:
                        source_page = page_num
                        break

            yield f"{filename}_struct_{i}", chunk, {"source": filename, "page": source_page, "type": "structure"}
