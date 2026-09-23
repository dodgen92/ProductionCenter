import os
import json
import time
import subprocess
from threading import Thread
from Pokemon.pokerip import catch_pokemon

import requests

from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_OAUTH_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN")
BROADCASTER_USER_ID = os.getenv("BROADCASTER_USER_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET = os.getenv("SECRET")

app = Flask(__name__)


# -----------------------------
# Camera Filter
# -----------------------------

def run_camera_filter():
    subprocess.run(["python", "CameraFilters/Filter.py"])
    time.sleep(180)
    subprocess.run(["python", "CameraFilters/clearfilter.py"])

# -----------------------------
# EventSub Webhook
# -----------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Twitch verification challenge
    if "challenge" in data:
        return data["challenge"], 200

    if request.headers.get("Twitch-Eventsub-Message-Type") == "notification":
        event = data.get("event", {})

        print("EventSub event received:")
        print(json.dumps(event, indent=2))

        reward_title = event.get("reward", {}).get("title", "")
        username = event.get("user_name", "").lower()

        if reward_title == "Add Camera Filter":
            print("📸 Camera Filter redeemed!")
            Thread(target=run_camera_filter, daemon=True).start()

        elif reward_title == "Rip a Vintage Pokemon Card":
            Thread(
                target=catch_pokemon,
                args=(username,),
                daemon=True
            ).start()

    return jsonify({"message": "Event received"}), 200


# -----------------------------
# Subscribe to EventSub
# -----------------------------

def subscribe_to_channel_points():
    url = "https://api.twitch.tv/helix/eventsub/subscriptions"

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {TWITCH_OAUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "type": "channel.channel_points_custom_reward_redemption.add",
        "version": "1",
        "condition": {
            "broadcaster_user_id": BROADCASTER_USER_ID
        },
        "transport": {
            "method": "webhook",
            "callback": WEBHOOK_URL,
            "secret": SECRET
        }
    }

    print("Sending EventSub subscription request...")

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 202]:
        print("✅ EventSub subscription successful!")
    else:
        print("❌ EventSub subscription failed:")
        print(response.status_code)
        print(response.text)


# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    print("Starting Production Center server...")

    subscribe_to_channel_points()

    app.run(
        port=5000,
        debug=False,
        use_reloader=False
    )