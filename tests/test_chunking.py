import pytest

from src.ingest.strategies.standard import StandardIngestionStrategy
from src.ingest.strategies.semantic import SemanticIngestionStrategy, cosine_distance
from src.ingest.strategies.structure import StructureIngestionStrategy


class TestStandardChunking:
    strategy = StandardIngestionStrategy()

    def test_chunks_overlap(self):
        chunks = self.strategy.chunk_text("abcdefghij", chunk_size=4, overlap=2)
        assert chunks == ["abcd", "cdef", "efgh", "ghij"]

    def test_short_text_is_one_chunk(self):
        assert self.strategy.chunk_text("abc", chunk_size=10, overlap=2) == ["abc"]

    def test_no_redundant_tail_chunk(self):
        # The last window already reaches the end, so no trailing chunk of pure overlap
        chunks = self.strategy.chunk_text("a" * 1000, chunk_size=1000, overlap=200)
        assert chunks == ["a" * 1000]

    @pytest.mark.parametrize("chunk_size, overlap", [(100, 100), (100, 150), (0, 0), (100, -1)])
    def test_rejects_settings_that_would_never_advance(self, chunk_size, overlap):
        with pytest.raises(ValueError):
            self.strategy.chunk_text("some text", chunk_size=chunk_size, overlap=overlap)

    def test_chunk_pdf_ids_and_metadata(self):
        chunks = list(self.strategy.chunk_pdf("SOP.pdf", [("x" * 15, 3)], {"chunk_size": 10, "overlap": 0}))
        assert [c[0] for c in chunks] == ["SOP.pdf_p3_c0", "SOP.pdf_p3_c1"]
        assert chunks[0][2] == {"source": "SOP.pdf", "page": 3, "type": "manual"}


class TestSemanticChunking:
    strategy = SemanticIngestionStrategy()

    def test_does_not_split_numbered_lists(self):
        sentences = self.strategy.split_sentences("Required Tools: 1. 3mm Hex Key 2. Loctite 243. Done here.")
        assert "1. 3mm Hex Key 2. Loctite 243." in " ".join(sentences)
        assert "1." not in sentences

    def test_splits_ordinary_sentences(self):
        assert self.strategy.split_sentences("First one. Second one? Third!") == ["First one.", "Second one?", "Third!"]

    def test_keeps_decimal_measurements(self):
        assert self.strategy.split_sentences("Torque to 2.5 Nm. Then wait.") == ["Torque to 2.5 Nm.", "Then wait."]

    def test_classify_chunk(self):
        assert self.strategy._classify_chunk("Required Tools:") == "header"
        assert self.strategy._classify_chunk("Step 3 Attach the arm") == "header"
        assert self.strategy._classify_chunk("1. Remove the screws") == "list_item"
        assert self.strategy._classify_chunk("a | b | c") == "table_row"
        assert self.strategy._classify_chunk("Just a sentence.") == "text"

    def test_semantic_shift_starts_new_chunk(self):
        long_a = "The rotor arm is secured with four M3 screws and threadlocker. " * 3
        long_b = "Batteries must never be charged above forty degrees Celsius. " * 3
        chunks = self.strategy.combine_sentences([long_a, long_b], [[1.0, 0.0], [0.0, 1.0]], threshold=0.4)
        assert len(chunks) == 2

    def test_similar_sentences_stay_together(self):
        long_a = "The rotor arm is secured with four M3 screws and threadlocker. " * 3
        long_b = "Each screw on the rotor arm is torqued to the specified value. " * 3
        chunks = self.strategy.combine_sentences([long_a, long_b], [[1.0, 0.0], [0.9, 0.1]], threshold=0.4)
        assert len(chunks) == 1

    def test_cosine_distance(self):
        assert cosine_distance([1, 0], [1, 0]) == pytest.approx(0.0)
        assert cosine_distance([1, 0], [0, 1]) == pytest.approx(1.0)
        # Failed embeddings fall back to zero vectors; treat them as unrelated, not NaN
        assert cosine_distance([0, 0], [1, 0]) == 1.0


class TestStructureChunking:
    strategy = StructureIngestionStrategy()

    def test_splits_on_section_headers(self):
        text = "\n".join([
            "1. Scope",
            "This SOP covers rotor arm assembly for the Falcon X1. " * 5,
            "2. Required Tools",
            "3mm Hex Key and Loctite 243 are required for this procedure. " * 5,
        ])
        chunks = self.strategy.chunk_by_structure(text, max_size=1500, min_size=200)
        assert len(chunks) == 2
        assert chunks[0].startswith("1. Scope")
        assert chunks[1].startswith("2. Required Tools")

    def test_merges_small_fragments(self):
        chunks = self.strategy.chunk_by_structure("short line\nanother short line", max_size=1500, min_size=200)
        assert chunks == ["short line\nanother short line"]

    def test_respects_max_size(self):
        text = "\n".join(["word " * 20] * 50)
        chunks = self.strategy.chunk_by_structure(text, max_size=500, min_size=100)
        assert all(len(c) <= 500 for c in chunks)

    def test_page_attribution_across_pages(self):
        pages = [
            ("1. Scope\n" + "Scope text for the procedure. " * 10, 1),
            ("2. Procedure\n" + "Procedure text for the assembly. " * 10, 2),
        ]
        chunks = list(self.strategy.chunk_pdf("SOP.pdf", pages, {"max_size": 1500, "min_size": 100}))
        assert [c[2]["page"] for c in chunks] == [1, 2]

    def test_repeated_text_maps_to_correct_page(self):
        # Identical sections on two pages: each chunk must map to its own page, not the first match
        section = "1. Safety\n" + "Wear eye protection at all times. " * 10
        pages = [(section, 1), (section, 2)]
        chunks = list(self.strategy.chunk_pdf("SOP.pdf", pages, {"max_size": 1500, "min_size": 100}))
        assert [c[2]["page"] for c in chunks] == [1, 2]
