"""
Hourly rain-probability checker for 92620 (Irvine, CA).
Checks the next hour's precipitation probability via Open-Meteo (no API key needed).
If it exceeds RAIN_THRESHOLD, sends an SMS via Twilio.

Credentials and config are read from environment variables (set as GitHub
Actions secrets — never hardcode them in this file):
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_FROM_NUMBER   e.g. +18668118506
  TWILIO_TO_NUMBER     e.g. +17144174325
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
RAIN_THRESHOLD = 18  # percent

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


def send_sms(probability, time_label):
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    to_number = os.environ["TWILIO_TO_NUMBER"]

    client = Client(sid, token)
    message = client.messages.create(
        body=(
            f"Rain alert for {LOCATION_LABEL}: "
            f"{probability}% chance of rain around {time_label}. "
            f"(Threshold: {RAIN_THRESHOLD}%)"
        ),
        from_=from_number,
        to=to_number,
    )
    print(f"SMS sent, SID: {message.sid}")


def main():
    time_label, probability = get_next_hour_rain_probability()
    print(f"[{datetime.now(timezone.utc).isoformat()}] "
          f"Checked {LOCATION_LABEL} for {time_label}: {probability}% rain probability")

    if probability is not None and probability > RAIN_THRESHOLD:
        send_sms(probability, time_label)
    else:
        print("Below threshold — no SMS sent.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
