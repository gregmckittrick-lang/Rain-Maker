
"""
Hourly rain-probability checker for 92620 (Irvine, CA).
Checks the current hour's precipitation probability via the National
Weather Service API (api.weather.gov — free, no API key needed, uses NOAA's
own forecast grids). Also checks the latest observation from the nearest
weather station to catch rain that's already happening but wasn't in the
forecast (e.g. drizzle a model missed).
If either signal exceeds/matches RAIN_THRESHOLD, sends a WhatsApp message
via Twilio's WhatsApp Sandbox.
 
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
RAIN_THRESHOLD = 8  # percent
 
# NWS requires a descriptive User-Agent identifying the app (no key needed).
NWS_HEADERS = {
    "User-Agent": "(Rain-Maker personal alert script, github.com/gregmckittrick-lang/Rain-Maker)",
    "Accept": "application/geo+json",
}
 
# Words in a station's current-conditions description that mean it's
# actively raining/drizzling right now, even if the hourly forecast missed it.
RAIN_KEYWORDS = ("rain", "drizzle", "shower", "thunderstorm")
 
 
def get_forecast_hourly_url():
    """Look up the NWS grid endpoint for our lat/lon, once."""
    resp = requests.get(
        f"https://api.weather.gov/points/{LATITUDE},{LONGITUDE}",
        headers=NWS_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    props = resp.json()["properties"]
    return props["forecastHourly"], props["observationStations"]
 
 
def get_current_hour_rain_probability(forecast_hourly_url):
    resp = requests.get(forecast_hourly_url, headers=NWS_HEADERS, timeout=15)
    resp.raise_for_status()
    periods = resp.json()["properties"]["periods"]
 
    # First period is always the current/next hour.
    period = periods[0]
    prob = period.get("probabilityOfPrecipitation", {}).get("value")
    return period["startTime"], (prob if prob is not None else 0), period.get("shortForecast", "")
 
 
def get_current_observation(observation_stations_url):
    """Check the nearest station's latest observation for rain happening
    right now (catches drizzle the hourly forecast model missed)."""
    stations_resp = requests.get(observation_stations_url, headers=NWS_HEADERS, timeout=15)
    stations_resp.raise_for_status()
    features = stations_resp.json().get("features", [])
    if not features:
        return None
 
    station_id = features[0]["properties"]["stationIdentifier"]
    obs_resp = requests.get(
        f"https://api.weather.gov/stations/{station_id}/observations/latest",
        headers=NWS_HEADERS,
        timeout=15,
    )
    obs_resp.raise_for_status()
    return obs_resp.json()["properties"].get("textDescription", "") or ""
 
 
def send_whatsapp(reason_text):
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
        body=f"Rain alert for {LOCATION_LABEL}: {reason_text}",
        from_=from_whatsapp,
        to=to_whatsapp,
    )
    print(f"WhatsApp message sent, SID: {message.sid}")
 
 
def main():
    forecast_hourly_url, observation_stations_url = get_forecast_hourly_url()
 
    time_label, probability, short_forecast = get_current_hour_rain_probability(forecast_hourly_url)
    print(f"[{datetime.now(timezone.utc).isoformat()}] "
          f"Checked {LOCATION_LABEL} for {time_label}: "
          f"{probability}% rain probability ({short_forecast})")
 
    current_conditions = get_current_observation(observation_stations_url) or ""
    print(f"Current station observation: {current_conditions or 'unavailable'}")
    is_raining_now = any(word in current_conditions.lower() for word in RAIN_KEYWORDS)
 
    if probability > RAIN_THRESHOLD:
        send_whatsapp(
            f"{probability}% chance of rain around {time_label} "
            f"({short_forecast}). (Threshold: {RAIN_THRESHOLD}%)"
        )
    elif is_raining_now:
        send_whatsapp(
            f"it looks like it's currently {current_conditions.lower()} "
            f"at the nearest station, even though the forecast probability "
            f"was only {probability}%."
        )
    else:
        print("Below threshold and no rain currently reported — no WhatsApp message sent.")
 
 
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
