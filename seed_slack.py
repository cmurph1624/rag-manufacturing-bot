import os
import time
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables
load_dotenv()

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CHANNEL_ID = "aerostream-support"  # Paste your channel ID here

import ssl

# Initialize WebClient
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)

# Data Structure
conversations = [
    {
        "parent_message": "Has anyone seen the Falcon X1 shake violently when descending quickly? It looks like a death wobble.",
        "replies": [
            "I saw that last week. It's not a gain setting issue.",
            "Check the rubber dampeners on the gimbal. If they get too cold (below 5°C), they stiffen up and cause that shake. Warm them up in your hands before flight."
        ]
    },
    {
        "parent_message": "I can't get the controller to pair with the Eagle Eye V2. I tried the 5-second hold.",
        "replies": [
            "The manual is outdated for the V2. You actually have to hold the power button AND the 'Return to Home' button together for 10 seconds.",
            "You'll hear a 'musical' beep when it works."
        ]
    },
    {
        "parent_message": "I have a battery that is slightly puffed. Is it safe to fly for just a short test?",
        "replies": [
            "Absolutely not. Zero tolerance on puffing. Even slight swelling means internal gas buildup. Discard it immediately.",
            "Don't risk a fire for a 5-minute flight."
        ]
    }
]

def seed_slack():
    if not SLACK_BOT_TOKEN:
        print("Error: SLACK_BOT_TOKEN not found in .env file.")
        return

    print(f"Starting to seed channel {CHANNEL_ID}...")

    for i, conv in enumerate(conversations, 1):
        try:
            # Post parent message
            parent_response = client.chat_postMessage(
                channel=CHANNEL_ID,
                text=conv["parent_message"]
            )
            parent_ts = parent_response["ts"]
            print(f"Posted conversation {i} parent message...")
            
            time.sleep(1)

            # Post replies
            for reply in conv["replies"]:
                client.chat_postMessage(
                    channel=CHANNEL_ID,
                    text=reply,
                    thread_ts=parent_ts
                )
                time.sleep(1)
            
            print(f"Finished posting replies for conversation {i}.")
            time.sleep(1)

        except SlackApiError as e:
            print(f"Error posting message: {e}")

    print("Seeding complete!")

if __name__ == "__main__":
    seed_slack()
