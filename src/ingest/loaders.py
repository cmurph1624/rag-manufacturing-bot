import os
import re
import json
import ssl
import certifi
import pdfplumber
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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
        print(f"Error reading PDF {file_path}: {e}", flush=True)
    return text_data

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
        print(f"Error reading JSON {file_path}: {e}", flush=True)
    return chunks_data

def get_slack_client():
    token = os.getenv("SLACK_BOT_TOKEN")
    if token:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        return WebClient(token=token, ssl=ssl_context)
    return None

def resolve_channel_id(client, channel):
    """Accepts a channel ID (C.../G...) or a channel name and returns the ID."""
    if re.fullmatch(r"[CG][A-Z0-9]{8,}", channel):
        return channel
    name = channel.lstrip("#")
    # SlackResponse is iterable over pages, following next_cursor automatically
    for page in client.conversations_list(types="public_channel,private_channel", limit=200):
        for ch in page["channels"]:
            if ch["name"] == name:
                return ch["id"]
    return None

def fetch_slack_history(client, channel_id):
    """Yields (thread_text, ts) for every message in the channel, including thread replies."""
    if not client or not channel_id:
        print("Skipping Slack ingestion (Token or Channel ID missing).", flush=True)
        return

    print(f"Connecting to Slack Channel: {channel_id}...", flush=True)

    try:
        resolved = resolve_channel_id(client, channel_id)
        if not resolved:
            print(f"Slack channel '{channel_id}' not found (is the bot a member?).", flush=True)
            return
        channel_id = resolved

        messages = []
        for page in client.conversations_history(channel=channel_id, limit=200):
            messages.extend(page["messages"])
        print(f"Found {len(messages)} messages in Slack.", flush=True)

        for msg in messages:
            text = msg.get("text", "")
            ts = msg.get("ts")
            if not text: continue

            combined_text = f"Q: {text}"

            # If it's a thread parent, fetch replies
            if msg.get("thread_ts") == ts:
                try:
                    replies = []
                    for page in client.conversations_replies(channel=channel_id, ts=ts, limit=200):
                        replies.extend(page["messages"])
                    # Skip the first one (it's the parent we already have)
                    for reply in replies[1:]:
                        combined_text += f"\n A: {reply.get('text', '')}"
                except SlackApiError as e:
                    print(f"Error fetching replies for thread {ts}: {e}", flush=True)

            yield combined_text, ts

    except SlackApiError as e:
        print(f"Slack API Error: {e}", flush=True)
