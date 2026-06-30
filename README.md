# Hourly Rain Alert (92620 → SMS)

Checks the rain probability for ZIP 92620 (Irvine, CA) every hour and texts
714-417-4325 if it's above 20%. Runs for free on GitHub Actions — no server
needed.

## Setup (5–10 minutes)

### 1. Create a new GitHub repo
- Go to github.com → New repository (e.g. `rain-alert`, can be private)
- Upload these three files, keeping the folder structure:
  - `check_rain.py`
  - `requirements.txt`
  - `.github/workflows/check-rain.yml`

### 2. Add your Twilio credentials as repo secrets
In your new repo: **Settings → Secrets and variables → Actions → New repository secret**

Add four secrets:
| Name | Value |
|---|---|
| `TWILIO_ACCOUNT_SID` | your Account SID |
| `TWILIO_AUTH_TOKEN` | your Auth Token |
| `TWILIO_FROM_NUMBER` | your Twilio number, e.g. `+18668118506` |
| `TWILIO_TO_NUMBER` | `+17144174325` |

Secrets are encrypted and never appear in logs — this is the standard, safe
way to hold credentials for an automation like this (much better than
putting them in the script itself).

### 3. Done — it runs automatically
The workflow fires every hour on its own (`cron: "0 * * * *"`). You can also
trigger a run manually any time: go to the **Actions** tab → "Hourly Rain
Check" → **Run workflow**, to confirm it's working without waiting for the
next hour.

### 4. (Important) Verify your phone with Twilio
Since this is a Twilio trial account, it can only text numbers you've
verified in the Twilio console (**Phone Numbers → Verified Caller IDs**).
Make sure 714-417-4325 is added there, or the SMS send will fail silently.

## Notes
- Threshold and location are set at the top of `check_rain.py`
  (`RAIN_THRESHOLD = 20`, `LATITUDE`/`LONGITUDE` for 92620). Change either
  any time.
- Weather data comes from Open-Meteo, which is free and needs no API key.
- Since you pasted the Twilio Auth Token in chat earlier, it's worth
  regenerating it once in the Twilio console and updating the
  `TWILIO_AUTH_TOKEN` secret — one click, good hygiene.
