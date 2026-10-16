from src.formatting import format_citations, strip_mentions


class TestStripMentions:
    def test_removes_bot_mention(self):
        assert strip_mentions("<@U012ABCDEF> Which Loctite for the rotor arm?") == "Which Loctite for the rotor arm?"

    def test_removes_labelled_mention(self):
        assert strip_mentions("<@U012ABCDEF|aerobot> hi") == "hi"

    def test_mention_only_becomes_empty(self):
        assert strip_mentions("<@U012ABCDEF>") == ""

    def test_none_is_safe(self):
        assert strip_mentions(None) == ""


class TestFormatCitations:
    def test_cites_source_and_page(self):
        text = format_citations([{"source": "SOP-01.pdf", "page": 2}])
        assert text == "\n\n*References:*\n• SOP-01.pdf (Page 2)"

    def test_deduplicates_same_page(self):
        text = format_citations([
            {"source": "SOP-01.pdf", "page": 2},
            {"source": "SOP-01.pdf", "page": 2},
            {"source": "SOP-01.pdf", "page": 3},
        ])
        assert text.count("SOP-01.pdf (Page 2)") == 1
        assert "SOP-01.pdf (Page 3)" in text

    def test_pageless_sources_cited_by_name(self):
        # Slack threads have no page; JSON conversations use page 0
        text = format_citations([{"source": "Slack API"}, {"source": "threads.json", "page": 0}])
        assert "• Slack API" in text
        assert "• threads.json" in text
        assert "Page" not in text

    def test_pinecone_float_pages(self):
        assert "(Page 3)" in format_citations([{"source": "a.pdf", "page": 3.0}])

    def test_no_documents(self):
        assert format_citations([]) == ""
