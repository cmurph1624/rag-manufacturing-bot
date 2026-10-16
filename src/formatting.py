"""
Small, dependency-free helpers for turning RAG output into Slack messages.
"""
import re
from typing import Any, Dict, Iterable

# Slack renders mentions as <@U123ABC> (optionally <@U123ABC|name>)
_MENTION_PATTERN = re.compile(r"<@[A-Z0-9]+(\|[^>]*)?>")


def strip_mentions(text: str) -> str:
    """Removes Slack user mentions (e.g. the bot's own @-mention) from a message."""
    return _MENTION_PATTERN.sub("", text or "").strip()


def format_citations(metadatas: Iterable[Dict[str, Any]]) -> str:
    """
    Builds a de-duplicated reference list from retrieved chunk metadata.
    Chunks without a page (Slack threads, JSON conversations) are cited by source only.
    """
    lines = []
    seen = set()
    for meta in metadatas:
        source = meta.get("source", "Unknown")
        page = meta.get("page")
        # Pinecone returns numeric metadata as floats (3 -> 3.0)
        if isinstance(page, float) and page.is_integer():
            page = int(page)

        label = f"{source} (Page {page})" if page else source
        if label not in seen:
            seen.add(label)
            lines.append(f"• {label}")

    if not lines:
        return ""
    return "\n\n*References:*\n" + "\n".join(lines)
