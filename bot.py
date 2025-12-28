import os
import slack_bolt
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import chromadb
import ollama

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = "./chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"
GENERATION_MODEL = "llama3.2"

# Initialize ChromaDB Client
print(f"Connecting to ChromaDB at '{DB_PATH}'...")
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_collection(name=COLLECTION_NAME)

# Create SSL context using certifi
import ssl
import certifi
from slack_sdk import WebClient

ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"), ssl=ssl_context)

# Initialize Slack App with custom WebClient
app = App(client=client)

@app.event("app_mention")
def handle_app_mention(event, say):
    """
    Event listener for app_mention.
    1. Acknowledge.
    2. Search ChromaDB.
    3. Generate answer using Ollama.
    4. Reply with answer and citations.
    """
    user_query = event.get("text")
    channel_id = event.get("channel")
    thread_ts = event.get("ts") # Reply in thread

    print(f"Received query: {user_query}")

    # Step A: Acknowledge
    say(f"Thinking...", thread_ts=thread_ts)

    try:
        # Step B: Search
        # Generate embedding for the query
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=user_query)
        query_embedding = response.get("embedding")

        if not query_embedding:
            say("Error: Failed to generate embedding for search.", thread_ts=thread_ts)
            return

        # Query ChromaDB (Get top 7 results)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=7
        )

        documents = results["documents"][0] # list of strings

        print("\n--- DEBUG: Retrieved Context ---")
        for doc in documents:
            print(doc[:200] + "...") # Print first 200 chars
        print("--------------------------------\n")
        metadatas = results["metadatas"][0] # list of dicts

        if not documents:
            say("I couldn't find any relevant documents in the database.", thread_ts=thread_ts)
            return

        # Combine documents into context text
        context_text = "\n\n---\n\n".join(documents)

        # Step C: Construct Prompt
        # We'll use the chat API, mapping requirements to roles.
        system_instruction = (
            "You are a helpful manufacturing support assistant. "
            "Answer the question using ONLY the following context. "
            "If you don't know, say you don't know."
        )
        
        user_prompt_content = f"Context:\n{context_text}\n\nQuestion: {user_query}"

        # Step D: Generate
        print("Sending prompt to Ollama...")
        response = ollama.chat(model=GENERATION_MODEL, messages=[
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': user_prompt_content},
        ])

        answer = response['message']['content']

        # Step F: Citations
        citations = []
        seen_sources = set()
        for meta in metadatas:
            source = meta.get("source", "Unknown")
            page = meta.get("page_number", "Unknown")
            # Create a unique key to avoid duplicate citations if chunks are from same page
            citation_key = f"{source}:{page}"
            if citation_key not in seen_sources:
                citations.append(f"• {source} (Page {page})")
                seen_sources.add(citation_key)
        
        citation_text = "\n\n*References:*\n" + "\n".join(citations)
        
        final_response = f"{answer}{citation_text}"

        # Step E: Reply
        say(final_response, thread_ts=thread_ts)

    except Exception as e:
        print(f"Error processing request: {e}")
        say(f"Sorry, I encountered an error: {str(e)}", thread_ts=thread_ts)

if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        print("Error: SLACK_APP_TOKEN not found.")
    else:
        print("Starting Socket Mode Bot...")
        handler = SocketModeHandler(app, app_token)
        handler.start()
