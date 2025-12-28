import os
import chromadb
import ollama
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Configuration
CHANNEL_ID = "C0A669KHBPT"
# Load environment variables
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN not found in .env file.")

# Initialize Slack Client
import ssl
import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)

# Initialize ChromaDB Client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="aerostream_docs")

def ingest_slack_history():
    # Resolve Channel ID if name provided
    # We must access the global CHANNEL_ID or pass it as argument. Since it's global, we can use it but updating it requires 'global' keyword if we assign to it.
    global CHANNEL_ID
    if not CHANNEL_ID.startswith("C"):
        try:
            print(f"Resolving channel ID for '{CHANNEL_ID}'...")
            response = client.conversations_list(types="public_channel,private_channel")
            found = False
            for channel in response["channels"]:
                if channel["name"] == CHANNEL_ID:
                    CHANNEL_ID = channel["id"]
                    found = True
                    print(f"Found channel ID: {CHANNEL_ID}")
                    break
            if not found:
                 raise ValueError(f"Could not find channel with name '{CHANNEL_ID}'")
        except SlackApiError as e:
            print(f"Error listing channels: {e}")
            exit(1)

    try:
        # Fetch conversation history
        result = client.conversations_history(channel=CHANNEL_ID)
        messages = result["messages"]

        print(f"Found {len(messages)} messages in channel {CHANNEL_ID}.")

        for msg in messages:
            # Skip subtype messages (like 'channel_join') if necessary, keeping it simple for now as requested
            text = msg.get("text", "")
            ts = msg.get("ts")
            
            if not text:
                continue

            combined_text = f"Q: {text}"
            
            # Check for thread
            if "thread_ts" in msg and msg["thread_ts"] == ts:
                # It's a parent message of a thread (or just a message, but logic checks if it has replies)
                # Note: conversations_history returns the parent message. 
                # If it has a thread_ts, we should check reply_count to be sure, or just fetch replies.
                # However, conversations_replies includes the parent message as the first message.
                
                try:
                    replies_result = client.conversations_replies(channel=CHANNEL_ID, ts=ts)
                    replies = replies_result["messages"]
                    
                    # The first message in replies is the parent, which we already have in 'text'
                    # But the user asked to merge: 'Q: [Parent text] \n A: [Reply 1] \n A: [Reply 2]'
                    # So let's iterate from the second message onwards for replies
                    
                    for reply in replies[1:]:
                         reply_text = reply.get("text", "")
                         combined_text += f"\n A: {reply_text}"
                         
                except SlackApiError as e:
                    print(f"Error fetching replies for {ts}: {e}")

            # Generate embedding
            # using nomic-embed-text as requested
            try:
                response = ollama.embeddings(model='nomic-embed-text', prompt=combined_text)
                embedding = response["embedding"]
                
                # Upsert to Chroma
                collection.upsert(
                    ids=[ts],
                    embeddings=[embedding],
                    metadatas=[{"source": "Slack Thread", "timestamp": ts}],
                    documents=[combined_text]
                )
                
                print(f"Ingested thread regarding: {combined_text[:50]}...")
            
            except Exception as e:
                print(f"Error generating embedding or upserting for {ts}: {e}")

    except SlackApiError as e:
        print(f"Error fetching conversation history: {e}")

if __name__ == "__main__":
    ingest_slack_history()
