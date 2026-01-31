import os
import json
import ssl
import certifi
import chromadb
import pdfplumber
import ollama
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# --- Configuration ---
load_dotenv()

PDF_FOLDER = "data_pdfs"
DB_PATH = "chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"

# Slack Config
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Chunking Settings
CHUNK_SIZE = 1000
OVERLAP = 200

def get_embedding(text):
    """Generates an embedding vector using Ollama."""
    try:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return []

def chunk_text(text, chunk_size, overlap):
    """Splits text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

# --- PDF Handler ---
def process_pdf(file_path):
    """Extracts text from PDF using pdfplumber (better for tables)."""
    text_data = [] 
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_data.append((page_text, i + 1))
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text_data

# --- JSON Handler (Local Files) ---
def process_json(file_path):
    """Extracts Q&A pairs from local JSON conversation logs."""
    chunks_data = []
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        if isinstance(data, list):
            for i, item in enumerate(data):
                parent = item.get("parent_message", "")
                replies = " ".join(item.get("replies", []))
                full_text = f"Question/Issue: {parent}\nAnswer/Reply: {replies}"
                chunks_data.append((full_text, f"json_thread_{i}"))
    except Exception as e:
        print(f"Error reading JSON {file_path}: {e}")
    return chunks_data

# --- Slack Handler (Live API) ---
def ingest_slack_history(client, channel_id, collection):
    """Fetches threads from Slack and indexes them."""
    if not client or not channel_id:
        print("Skipping Slack ingestion (Token or Channel ID missing).")
        return

    print(f"Connecting to Slack Channel: {channel_id}...")
    
    # Resolve Channel Name to ID if necessary
    if not channel_id.startswith("C"):
        try:
            response = client.conversations_list(types="public_channel,private_channel")
            for channel in response["channels"]:
                if channel["name"] == channel_id:
                    channel_id = channel["id"]
                    break
        except SlackApiError as e:
            print(f"Error listing Slack channels: {e}")
            return

    try:
        # Fetch history
        result = client.conversations_history(channel=channel_id)
        messages = result["messages"]
        print(f"Found {len(messages)} messages in Slack.")

        for msg in messages:
            text = msg.get("text", "")
            ts = msg.get("ts")
            if not text: continue

            combined_text = f"Q: {text}"

            # If it's a thread, fetch replies
            if "thread_ts" in msg and msg["thread_ts"] == ts:
                try:
                    replies_result = client.conversations_replies(channel=channel_id, ts=ts)
                    replies = replies_result["messages"]
                    # Skip the first one (it's the parent we already have)
                    for reply in replies[1:]:
                        combined_text += f"\n A: {reply.get('text', '')}"
                except SlackApiError as e:
                    print(f"Error fetching replies for thread {ts}: {e}")

            # Embed and Upsert
            embedding = get_embedding(combined_text)
            if embedding:
                collection.upsert(
                    ids=[f"slack_{ts}"],
                    embeddings=[embedding],
                    metadatas=[{"source": "Slack API", "timestamp": ts, "type": "tribal_knowledge"}],
                    documents=[combined_text]
                )
                print(f"Ingested Slack Thread: {combined_text[:40]}...")

    except SlackApiError as e:
        print(f"Slack API Error: {e}")

# --- Main Execution ---
def main():
    # 1. Setup Database
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Setup Slack Client
    slack_client = None
    if SLACK_BOT_TOKEN:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        slack_client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)

    # 3. Process Local Files (PDFs and JSONs)
    if os.path.exists(PDF_FOLDER):
        for filename in os.listdir(PDF_FOLDER):
            file_path = os.path.join(PDF_FOLDER, filename)
            
            # PDF Processing
            if filename.endswith(".pdf"):
                print(f"Processing PDF: {filename}...")
                pages = process_pdf(file_path)
                for page_text, page_num in pages:
                    text_chunks = chunk_text(page_text, CHUNK_SIZE, OVERLAP)
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
                print(f"Processing JSON: {filename}...")
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

    # 4. Process Live Slack Data
    if slack_client:
        ingest_slack_history(slack_client, SLACK_CHANNEL_ID, collection)

    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()