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
            "Pilot_Tom: Sounds like your PID gains are too high. Try lowering the 'P' gain on the vertical axis.",
            "X1_Vet: @Pilot_Tom No, don't touch the gains! That's a classic mistake on the X1.",
            "X1_Vet: @OP, what is the temperature outside? If it's below 5°C, check your rubber gimbal dampeners.",
            "OP_Flyer: Yeah it's freezing today, about 2°C.",
            "X1_Vet: That's it. The rubber stiffens up in the cold and causes that oscillation. Warm them up in your hands for a minute before you fly, it will stop the shake.",
            "OP_Flyer: Wow, that worked instantly. Thanks."
        ]
    },
    {
        "parent_message": "I can't get the controller to pair with the Eagle Eye V2. I tried the 5-second hold like the manual says.",
        "replies": [
            "Newbie_99: Is the battery charged?",
            "OP_Flyer: Yes, fully charged. It just blinks slowly.",
            "Tech_Lead: Ignore the manual that came in the box, it's outdated for the V2 hardware.",
            "Tech_Lead: They changed the sequence. You have to hold the Power button AND the 'Return to Home' button together for 10 seconds.",
            "Tech_Lead: Keep holding until you hear a weird 'musical' beep, not the standard beep.",
            "OP_Flyer: Got the musical beep! Paired immediately. They really need to update that PDF."
        ]
    },
    {
        "parent_message": "I have a battery that is slightly puffed. Is it safe to fly for just a short test? It's barely noticeable.",
        "replies": [
            "Budget_Flyer: If it's just a little bit, maybe put it in the fridge? I've flown packs like that before.",
            "Safety_Officer: @Budget_Flyer DO NOT give that advice. That is dangerous.",
            "Safety_Officer: @OP Absolutely not. There is Zero Tolerance on puffing.",
            "Safety_Officer: Even slight swelling means internal gas buildup and chemical decomposition. It can catch fire under load.",
            "Safety_Officer: Discard it immediately. Don't risk a fire for a 5-minute flight."
        ]
    },
    {
        "parent_message": "Anyone else seeing massive video lag on the Eagle Eye V2? It's unflyable today.",
        "replies": [
            "User_Mark: Mine is fine. Maybe your tablet is too old?",
            "User_Sarah: @User_Mark No, I have the new iPad and I'm seeing it too. It stutters every 3 seconds.",
            "User_Admin: @User_Sarah @User_Mark Are you guys leaving the transmission on 'Auto'?",
            "User_Sarah: Yeah, isn't that best?",
            "User_Admin: No, that's the issue. On the V2, Auto mode hunts for channels too aggressively. You need to manually switch to a 5.8GHz channel (try Ch 150+). That fixes the lag instantly."
        ]
    },
    {
        "parent_message": "Help! My Falcon Pro is only getting like 500m range before the signal drops. Box says 5km.",
        "replies": [
            "Pilot_Dave: Send it back, sounds like a dud unit.",
            "Tech_Guru: @Pilot_Dave hold on. @OP, how are you holding the controller?",
            "OP_Flyer: Just normal, pointing the antennas right at the drone.",
            "Tech_Guru: That is your problem. This is a common mistake. Dipole antennas radiate from the sides, not the tip. You need to orient the antennas perpendicular to the drone (broadside), not point the tips at it.",
            "OP_Flyer: Wow, just tried that and signal went to 100%. Thanks!"
        ]
    },
    {
        "parent_message": "Just had a minor crash with the X1. Gimbal is totally limp. Is it dead?",
        "replies": [
            "Crash_King: RIP. That happened to me, had to buy a whole new camera unit ($400).",
            "Mod_Steve: @Crash_King you probably wasted money. @OP, don't buy anything yet.",
            "Mod_Steve: On the X1, the ribbon cable connector on the backplate is designed to pop off during impact to save the board.",
            "Mod_Steve: Take the 4 screws off the back cover and check the connector. I bet it's just unplugged.",
            "OP_Flyer: @Mod_Steve You are a lifesaver! It was just unplugged. Clicked it back in and it works perfectly."
        ]
    },
    {
        "parent_message": "The AeroStream app keeps crashing immediately on my new phone. Can't fly.",
        "replies": [
            "Android_User: Same here. Pixel 8?",
            "OP_Flyer: Yeah, Pixel 8 Pro. Android 14.",
            "Android_User: It's an Android 14 compatibility issue with the current store version.",
            "Dev_Support: We are working on a patch. For now, go to the support forum and download the Beta v4.2 APK. That version solves the Android 14 crash loop."
        ]
    },
    {
        "parent_message": "I'm at a construction site and I keep getting a 'Magnetic Interference' error. Can't arm motors.",
        "replies": [
            "Newbie: Try calibrating the compass?",
            "Site_Manager: I tried calibrating 5 times, still fails.",
            "Pro_Pilot: If you are standing near rebar or a metal structure, calibration won't work because the interference is real.",
            "Pro_Pilot: You have to switch the flight mode switch to 'Atti' (Manual). This bypasses the GPS/Compass lock and allows you to arm the motors.",
            "Pro_Pilot: Just fly it away from the metal, then switch back to GPS mode."
        ]
    },
    {
        "parent_message": "Motors are making a weird clicking sound when I spin them up. Sounds bad.",
        "replies": [
            "Mechanic_Mike: Bearings are shot. Replace them.",
            "Falcon_Fan: Wait, before you replace bearings, check for debris. The Falcon motors have strong magnets.",
            "Falcon_Fan: I had this last week, turns out it was just a tiny piece of gravel in the bell housing.",
            "Falcon_Fan: Blow it out with compressed air first. If that doesn't stop the clicking, try an ESC calibration.",
            "OP_Flyer: Used air, a ton of dust came out. Noise is gone. Thanks!"
        ]
    },
    {
        "parent_message": "Can I use the spare arms from my Falcon X1 on my new Falcon Pro? They look the same.",
        "replies": [
            "Parts_Guy: Physically, yes. They are both Part #RA-400.",
            "Parts_Guy: BUT... the motors are different.",
            "Parts_Guy: The X1 uses 800kV motors, the Pro uses 950kV. So you can use the carbon arm, but you have to swap the motor itself over.",
            "OP_Flyer: Got it. Arm is same, motor is different. I'll swap them."
        ]
    },
    {
        "parent_message": "Flying in Florida and my camera lens keeps fogging up. Ruining my shots.",
        "replies": [
            "Photo_Pro: Are you taking it from a/c straight outside?",
            "OP_Flyer: Yeah.",
            "Photo_Pro: That's condensation. Let it acclimate.",
            "Water_Boy: Also, put a silica gel packet inside the camera housing if you can fit it. ",
            "Water_Boy: AeroStream actually sells specific anti-fog inserts for the X1 camera that slide in next to the SD card slot."
        ]
    },
    {
        "parent_message": "My landing gear is stuck halfway. Won't go up or down.",
        "replies": [
            "Grease_Monkey: WD40 it.",
            "Tech_Lead: NO! Do not use WD40. It attracts dirt and turns into grinding paste.",
            "Tech_Lead: It's likely dirt in the worm gear. Clean it out with compressed air, then use a Dry PTFE Lube.",
            "Tech_Lead: If you use grease or wet oil, it will just jam again in 2 flights."
        ]
    },
    {
        "parent_message": "What is the 'compass dance' everyone talks about? My drone is drifting.",
        "replies": [
            "Dancer_01: It's just the calibration.",
            "Dancer_01: Tap 'Calibrate Compass' in the app.",
            "Dancer_01: Hold the drone flat and spin 360 degrees until the light turns green.",
            "Dancer_01: Then point the nose straight down at the ground and spin 360 degrees again.",
            "Dancer_01: Make sure you do this away from your car or keys, or it will fail."
        ]
    },
    {
        "parent_message": "My waypoint mission is crashing into trees! I set altitude to 50ft.",
        "replies": [
            "Map_Guy: 50ft relative to what?",
            "OP_Flyer: I don't know, just says 50ft.",
            "Map_Guy: Check your settings. If it's set to MSL (Mean Sea Level), 50ft might be underground if you are on a hill.",
            "Map_Guy: You need to set the altitude reference to AGL (Above Ground Level) to ensure it clears the trees relative to where you took off."
        ]
    },
    {
        "parent_message": "I can't get the battery out. The release tab is stuck solid.",
        "replies": [
            "Strong_Man: Pull harder.",
            "Safety_Sam: Don't force it, you'll snap the plastic.",
            "Safety_Sam: The latch gets jammed under pressure. Push the battery DOWN firmly into the drone first.",
            "Safety_Sam: While pushing down, pull the release tab. It should slide right out."
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
