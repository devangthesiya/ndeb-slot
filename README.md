# NDEB Slot Tracker

Automated bot that monitors the [National Dental Examining Board of Canada (NDEB)](https://ndeb-bned.ca/) for exam registration slot availability. Get notified the moment a slot opens up.

## What It Does

- Checks NDEB exam registration status every 30 seconds (configurable)
- Tracks all exam types: **NDECC**, **AFK**, **ACJ**, **Virtual OSCE**
- Filters out US-only locations (configurable)
- Logs every check with timestamps
- Uses [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) to bypass bot detection and reCAPTCHA

## Two Modes

| Mode | Script | Login Required | What It Shows |
|------|--------|---------------|---------------|
| **Public** | `public_checker.py` | No | Registration open/closed/upcoming per exam + dates + deadlines |
| **Portal** | `slot_checker.py` | Yes | Specific locations with available slots (Ottawa, Toronto, etc.) |

## Quick Start

```bash
# Clone
git clone git@github.com:devangthesiya/ndeb-slot.git
cd ndeb-slot

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials (see Configuration below)

# Run public checker (no login needed)
python3 public_checker.py

# Run portal checker (needs NDEB credentials)
python3 slot_checker.py
```

## Configuration

Edit `.env` after copying from `.env.example`:

```env
# NDEB portal credentials (required for slot_checker.py)
NDEB_USERNAME=your_email@example.com
NDEB_PASSWORD=your_password

# Your Chrome profile name — helps bypass reCAPTCHA
# Find yours: ls ~/Library/Application\ Support/Google/Chrome/ | grep Profile
CHROME_PROFILE=Profile 1

# How often to check (seconds)
CHECK_INTERVAL_SECONDS=30

# Run Chrome without visible window
HEADLESS_MODE=false

# US cities to exclude from results (comma-separated)
EXCLUDED_LOCATIONS=New York,Los Angeles,Washington,Pennsylvania,Michigan
```

### Chrome Profile Setup

The NDEB login page has reCAPTCHA. Using your real Chrome profile (where you may already be logged in) combined with `undetected-chromedriver` helps bypass it.

1. Find your Chrome profile:
   ```bash
   # macOS
   ls ~/Library/Application\ Support/Google/Chrome/ | grep Profile

   # Windows
   dir "%LOCALAPPDATA%\Google\Chrome\User Data" | findstr Profile

   # Linux
   ls ~/.config/google-chrome/ | grep -i profile
   ```
2. Set `CHROME_PROFILE=Profile 1` (or whichever is yours) in `.env`
3. **Close Chrome completely** before running — Chrome locks its profile folder

## Sample Output

### Public Checker
```
[2026-03-04 20:12:33] *** 2 EXAM(S) WITH REGISTRATION OPEN ***
[2026-03-04 20:12:33]   >>> [OPEN    ] Assessment of Clinical Judgement (ACJ)  |  Exam: 5 May, 2026  |  Deadline: 01 April, 2026
[2026-03-04 20:12:33]   >>> [OPEN    ] Assessment of Fundamental Knowledge (AFK)  |  Exam: 14 August, 2026  |  Deadline: 09 June, 2026
[2026-03-04 20:12:33]   --- [CLOSED  ] NDECC  |  Exam: 5 January - 12 March 2026
[2026-03-04 20:12:33]   ... [UPCOMING] Virtual OSCE  |  Exam: 27 May, 2026  |  Opens: 10 MARCH, 2026
[2026-03-04 20:12:33] Summary: 2 open, 12 upcoming, 3 closed
```

### Portal Checker
```
[2026-03-04 20:15:00] *** SLOTS AVAILABLE at 2 location(s)! ***
[2026-03-04 20:15:00]   >>> Ottawa, ON
[2026-03-04 20:15:00]   >>> Toronto, ON
```

## Project Structure

```
├── .env.example        # Configuration template
├── config.py           # Settings loaded from .env
├── logger.py           # Timestamped console + file logging
├── public_checker.py   # Public page scraper (no login)
├── slot_checker.py     # Portal checker with undetected-chromedriver
├── requirements.txt    # Python dependencies
├── USAGE.md            # Detailed usage guide
└── logs/               # Auto-created log directory
    └── slot_tracker.log
```

## Tech Stack

- **Python 3.10+**
- **Selenium** — browser automation
- **undetected-chromedriver** — bot detection / reCAPTCHA bypass
- **webdriver-manager** — auto-manages ChromeDriver binary

## Inspired By

[farkoo/National-Dental-Examining-Board-of-Canada-Robot](https://github.com/farkoo/National-Dental-Examining-Board-of-Canada-Robot) — original C# + Selenium implementation.

## License

MIT
