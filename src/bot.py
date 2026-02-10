import os
import json
import time
import uuid
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import ssl
import certifi
from slack_sdk import WebClient
# Import the separated logic
from src.rag_logic import generate_answer

# Load environment variables
load_dotenv()

# Create SSL context using certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"), ssl=ssl_context)

# Initialize Slack App with custom WebClient

app = App(client=client)

# Logging Configuration
LOGS_DIR = "data/logs"
os.makedirs(LOGS_DIR, exist_ok=True)

def log_interaction(query, response_data, latency):
    """
    Logs the interaction details to a JSON file.
    """
    timestamp = datetime.now().isoformat()
    interaction_id = str(uuid.uuid4())
    
    log_entry = {
        "timestamp": timestamp,
        "interaction_id": interaction_id,
        "query": query,
        "response": response_data.get("answer"),
        "retrieved_chunks": response_data.get("retrieved_chunks", []),
        "model": response_data.get("model", "unknown"),
        "latency_seconds": latency
    }
    
    filename = f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{interaction_id}.json"
    filepath = os.path.join(LOGS_DIR, filename)
    
    try:
        with open(filepath, "w") as f:
            json.dump(log_entry, f, indent=4)
        print(f"Logged interaction to {filepath}")
    except Exception as e:
        print(f"Failed to log interaction: {e}")

@app.event("app_mention")
def handle_app_mention(event, say):
    """
    Event listener for app_mention.
    """
    user_query = event.get("text")
    channel_id = event.get("channel")
    thread_ts = event.get("ts") # Reply in thread

    print(f"Received query: {user_query}")

    # Step A: Acknowledge
    say(f"Thinking...", thread_ts=thread_ts)

    # Call the core logic with timing
    start_time = time.time()
    response_data = generate_answer(user_query)
    end_time = time.time()
    latency = end_time - start_time

    # Log the interaction
    log_interaction(user_query, response_data, latency)

    final_response = response_data["answer"]

    # Step E: Reply
    say(final_response, thread_ts=thread_ts)

if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        print("Error: SLACK_APP_TOKEN not found.")
    else:
        print("Starting Socket Mode Bot...")
        handler = SocketModeHandler(app, app_token)
        handler.start()
