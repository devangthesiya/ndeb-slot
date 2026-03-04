# NDEB Slot Tracker - Usage Guide

Monitors the [National Dental Examining Board of Canada (NDEB)](https://ndeb-bned.ca/) for exam registration availability. Sends alerts when slots open up.

## Two Modes

### 1. Public Page Checker (no login needed)
Scrapes the public [exam dates page](https://ndeb-bned.ca/examination-dates-and-locations/) and reports which exams have registration **OPEN**, **CLOSED**, or **UPCOMING**.

```bash
source venv/bin/activate
python3 public_checker.py
```

**What it shows:** exam type (NDECC, AFK, ACJ, Virtual OSCE), exam date, registration deadline, and status.

**Limitation:** Does not show specific locations with available slots — only whether registration is open or closed for each exam.

### 2. Portal Slot Checker (login required)
Logs into the NDEB portal via Selenium, navigates the registration flow, and checks for specific **location-level slot availability** (e.g., Ottawa, Toronto).

```bash
source venv/bin/activate
python3 slot_checker.py
```

**What it shows:** which specific exam locations have open slots, filtering out excluded US cities.

**Requires:** NDEB account credentials in `.env` and a Chrome profile to bypass reCAPTCHA (see setup below).

## Setup

### Prerequisites
- Python 3.10+
- Google Chrome installed

### Install
```bash
git clone git@github.com:devangthesiya/ndeb-slot.git
cd ndeb-slot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure
```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required for portal checker (slot_checker.py)
NDEB_USERNAME=your_email@example.com
NDEB_PASSWORD=your_password

# Chrome profile to skip reCAPTCHA (find yours with the command below)
# ls ~/Library/Application\ Support/Google/Chrome/ | grep Profile
CHROME_PROFILE=Profile 1

# Check interval in seconds (default: 30)
CHECK_INTERVAL_SECONDS=30

# Run Chrome without a visible window (default: false)
HEADLESS_MODE=false

# US cities to exclude from slot results (comma-separated)
EXCLUDED_LOCATIONS=New York,Los Angeles,Washington,Pennsylvania,Michigan
```

### Chrome Profile (for portal checker)

The NDEB login has reCAPTCHA. Using your real Chrome profile (where you're already logged in) helps bypass it.

1. Find your Chrome profiles:
   ```bash
   # macOS
   ls ~/Library/Application\ Support/Google/Chrome/ | grep Profile

   # Windows
   dir "%LOCALAPPDATA%\Google\Chrome\User Data" | findstr Profile

   # Linux
   ls ~/.config/google-chrome/ | grep -i profile
   ```

2. Set `CHROME_PROFILE` in `.env` to your profile name (e.g., `Profile 1`)

3. **Important:** Close Chrome completely before running the script — Chrome locks its profile folder.

## Logs

All output is logged to `logs/slot_tracker.log` with timestamps.

## Project Structure

```
├── .env.example        # Configuration template
├── config.py           # Settings loaded from .env
├── logger.py           # Timestamped console + file logging
├── public_checker.py   # Public page scraper (no login)
├── slot_checker.py     # Portal login + slot checker
└── requirements.txt    # Python dependencies
```

## Exam Types Tracked

| Exam | Full Name |
|------|-----------|
| NDECC | National Dental Examining Board Comprehensive Clinical |
| AFK | Assessment of Fundamental Knowledge |
| ACJ | Assessment of Clinical Judgement |
| Virtual OSCE | Virtual Objective Structured Clinical Examination |

## Inspired By

[farkoo/National-Dental-Examining-Board-of-Canada-Robot](https://github.com/farkoo/National-Dental-Examining-Board-of-Canada-Robot) — original C# implementation.
