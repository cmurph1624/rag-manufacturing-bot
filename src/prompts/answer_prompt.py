SYSTEM_INSTRUCTION = (
    "You are a helpful manufacturing support assistant. "
    "Answer the question using ONLY the following context. "
    "If you don't know, say you don't know."
)

def format_user_prompt(context_text: str, user_query: str) -> str:
    return f"Context:\n{context_text}\n\nQuestion: {user_query}"
