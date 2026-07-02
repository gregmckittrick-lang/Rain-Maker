"""
Hourly rain-probability checker for 92620 (Irvine, CA).
Checks the next hour's precipitation probability via Open-Meteo (no API key needed).
If it exceeds RAIN_THRESHOLD, sends a WhatsApp message via Twilio's WhatsApp Sandbox.

Credentials and config are read from environment variables (set as GitHub
Actions secrets — never hardcode them in this file):
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_FROM_NUMBER   Twilio's sandbox number, e.g. +14155238886
                       (NOT prefixed with "whatsapp:" — the code adds that)
  TWILIO_TO_NUMBER     your WhatsApp number, e.g. +17144174325
                       (NOT prefixed with "whatsapp:" — the code adds that)

Note: to receive messages, your phone must first join the Twilio Sandbox by
sending the join code (from the Twilio Console → Messaging → Try it out →
Send a WhatsApp message) to the sandbox number via WhatsApp. This only needs
to be done once, though sandbox sessions can expire after long inactivity —
see the README.
"""

import os
import sys
from datetime import datetime, timezone

import requests
from twilio.rest import Client

# ---- Config ----
LATITUDE = 33.7090
LONGITUDE = -117.7590
LOCATION_LABEL = "92620 (Irvine, CA)"
RAIN_THRESHOLD = -1  # percent

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    "&hourly=precipitation_probability"
    "&timezone=America/Los_Angeles"
    "&forecast_days=1"
)


def get_next_hour_rain_probability():
    resp = requests.get(OPEN_METEO_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    times = data["hourly"]["time"]
    probs = data["hourly"]["precipitation_probability"]

    now = datetime.now().astimezone()
    now_naive_str = now.strftime("%Y-%m-%dT%H:00")

    # Find the current/next hour slot in the returned series
    if now_naive_str in times:
        idx = times.index(now_naive_str)
    else:
        # Fallback: first slot at or after now
        idx = 0
        for i, t in enumerate(times):
            if t >= now_naive_str:
                idx = i
                break

    return times[idx], probs[idx]


def send_whatsapp(probability, time_label):
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    to_number = os.environ["TWILIO_TO_NUMBER"]

    # WhatsApp Sandbox requires the "whatsapp:" prefix on both numbers.
    # Numbers are stored bare in secrets so they're easy to reuse elsewhere;
    # the prefix is added here.
    from_whatsapp = f"whatsapp:{from_number}"
    to_whatsapp = f"whatsapp:{to_number}"

    client = Client(sid, token)
    message = client.messages.create(
        body=(
            f"Rain alert for {LOCATION_LABEL}: "
            f"{probability}% chance of rain around {time_label}. "
            f"(Threshold: {RAIN_THRESHOLD}%)"
        ),
        from_=from_whatsapp,
        to=to_whatsapp,
    )
    print(f"WhatsApp message sent, SID: {message.sid}")


def main():
    time_label, probability = get_next_hour_rain_probability()
    print(f"[{datetime.now(timezone.utc).isoformat()}] "
          f"Checked {LOCATION_LABEL} for {time_label}: {probability}% rain probability")

    if probability is not None and probability > RAIN_THRESHOLD:
        send_whatsapp(probability, time_label)
    else:
        print("Below threshold — no WhatsApp message sent.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
