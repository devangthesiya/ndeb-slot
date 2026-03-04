import os
from dotenv import load_dotenv

load_dotenv()


# NDEB credentials
NDEB_USERNAME = os.getenv("NDEB_USERNAME", "")
NDEB_PASSWORD = os.getenv("NDEB_PASSWORD", "")

# NDEB portal URL (login → redirects to registrations tab)
NDEB_LOGIN_URL = (
    "https://ndeb-bned.my.site.com/s/login/"
    "?language=en_CA"
    "&startURL=%2Fs%2Fregistrations%3Flanguage%3Den_CA%26tabset-603fc%3D696fb"
)

# Public NDEB page (no login required)
NDEB_PUBLIC_URL = "https://ndeb-bned.ca/examination-dates-and-locations/"

# Chrome profile — use your real browser profile to skip reCAPTCHA
# Set to your Chrome profile folder, e.g. "Profile 1", "Profile 2", "Default"
CHROME_PROFILE = os.getenv("CHROME_PROFILE", "")
CHROME_USER_DATA_DIR = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome"
)

# Checker behaviour
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
HEADLESS = os.getenv("HEADLESS_MODE", "false").lower() == "true"

# Locations to skip (US cities the original code filtered out)
EXCLUDED_LOCATIONS = [
    loc.strip()
    for loc in os.getenv(
        "EXCLUDED_LOCATIONS",
        "New York,Los Angeles,Washington,Pennsylvania,Michigan",
    ).split(",")
]
