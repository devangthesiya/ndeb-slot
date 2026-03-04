"""
NDEB Slot Tracker
Continuously monitors the NDEB portal for open exam registration slots
and logs when Canadian slots are found.

Uses cookie-based session reuse — you log in manually once, then the
script reuses cookies for all subsequent checks (no reCAPTCHA needed).
"""

import json
import os
import sys
import time

import undetected_chromedriver as uc

import config
from logger import log

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.json")


def create_driver() -> uc.Chrome:
    """Create and return an undetected Chrome WebDriver."""
    options = uc.ChromeOptions()
    if config.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-application-cache")

    driver = uc.Chrome(options=options, version_main=145)
    driver.implicitly_wait(5)
    log("Browser launched (undetected-chromedriver)")
    return driver


# ---------------------------------------------------------------------------
# Shadow DOM helpers
# ---------------------------------------------------------------------------

def _shadow_find(driver, selector):
    """Find an element inside Shadow DOM using JS deep traversal."""
    return driver.execute_script(f'''
        function deepQuery(root, sel) {{
            let result = root.querySelector(sel);
            if (result) return result;
            for (let child of root.querySelectorAll("*")) {{
                if (child.shadowRoot) {{
                    result = deepQuery(child.shadowRoot, sel);
                    if (result) return result;
                }}
            }}
            return null;
        }}
        return deepQuery(document, '{selector}');
    ''')


def _shadow_find_all(driver, selector):
    """Find ALL matching elements inside Shadow DOM using JS deep traversal."""
    return driver.execute_script(f'''
        function deepQueryAll(root, sel) {{
            let results = Array.from(root.querySelectorAll(sel));
            for (let child of root.querySelectorAll("*")) {{
                if (child.shadowRoot) {{
                    results = results.concat(deepQueryAll(child.shadowRoot, sel));
                }}
            }}
            return results;
        }}
        return deepQueryAll(document, '{selector}');
    ''')


def _debug_page(driver, label=""):
    """Save a screenshot and log visible button text for debugging."""
    try:
        fname = f"debug_{label}_{int(time.time())}.png"
        driver.save_screenshot(fname)
        log(f"Screenshot saved: {fname}")
    except Exception as e:
        log(f"Screenshot failed: {e}")

    try:
        buttons = _shadow_find_all(driver, "button")
        btn_texts = [b.text.strip() for b in buttons if b.text.strip()]
        if btn_texts:
            log(f"Visible buttons: {btn_texts}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Cookie-based login
# ---------------------------------------------------------------------------

def save_cookies(driver):
    """Save browser cookies to a JSON file."""
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)
    log(f"Cookies saved ({len(cookies)} cookies)")


def load_cookies(driver):
    """Load cookies from file into the browser session."""
    if not os.path.exists(COOKIES_FILE):
        return False

    with open(COOKIES_FILE) as f:
        cookies = json.load(f)

    # Navigate to the domain first so cookies can be set
    driver.get("https://ndeb-bned.my.site.com/s/")
    time.sleep(3)

    for cookie in cookies:
        # Remove problematic fields that can cause errors
        cookie.pop("sameSite", None)
        cookie.pop("storeId", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass

    log(f"Loaded {len(cookies)} cookies from file")
    return True


def is_logged_in(driver):
    """Check if we're on a logged-in page (not the login page)."""
    url = driver.current_url.lower()
    if "/s/login" in url:
        return False
    # Check for login form in shadow DOM
    login_btn = _shadow_find(driver, "button.login-button")
    if login_btn:
        return False
    return True


def manual_login(driver):
    """Open the login page and wait for the user to log in manually.

    The user solves reCAPTCHA and logs in themselves. Once logged in,
    cookies are saved for future reuse.
    """
    log("=" * 50)
    log("MANUAL LOGIN REQUIRED")
    log("A browser window will open. Please:")
    log("  1. Solve the reCAPTCHA (click 'I'm not a robot')")
    log("  2. Enter your credentials and click Login")
    log("  3. Wait until the portal loads")
    log("The script will detect when you're logged in.")
    log("=" * 50)

    driver.get(config.NDEB_LOGIN_URL)

    # Poll until user completes login (max 5 minutes)
    timeout = 300
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        try:
            url = driver.current_url.lower()
            if "/s/login" not in url and "ndeb" in url:
                # Double-check we're really past login
                time.sleep(3)
                if is_logged_in(driver):
                    log("Login detected! Saving cookies...")
                    save_cookies(driver)
                    return True
        except Exception:
            pass

    log("Login timed out after 5 minutes")
    return False


def login_with_cookies(driver):
    """Try to log in using saved cookies. Returns True if successful."""
    if not os.path.exists(COOKIES_FILE):
        return False

    log("Attempting login with saved cookies...")
    load_cookies(driver)

    # Navigate to the registrations page
    registrations_url = (
        "https://ndeb-bned.my.site.com/s/registrations"
        "?language=en_CA&tabset-603fc=696fb"
    )
    driver.get(registrations_url)
    time.sleep(8)

    if is_logged_in(driver):
        log("Cookie login successful!")
        return True

    log("Cookies expired or invalid")
    return False


# ---------------------------------------------------------------------------
# Slot checking
# ---------------------------------------------------------------------------

def check_for_slots(driver: uc.Chrome) -> list[str]:
    """
    Navigate the registration flow and check for available slots.
    All element lookups use Shadow DOM traversal since the NDEB portal
    is Salesforce LWC-based with nested shadow roots.
    """
    _debug_page(driver, "post_login")

    # Step 1: Click flow navigation button (Next/Start/Continue)
    log("Looking for flow navigation buttons in Shadow DOM...")
    time.sleep(3)

    clicked = False
    for selector in [
        "flowruntime-navigation-bar button",
        "button.slds-button_brand",
        "lightning-button button",
        "button.slds-button",
    ]:
        buttons = _shadow_find_all(driver, selector)
        for btn in buttons:
            try:
                txt = btn.text.strip().lower()
                if txt in ("next", "start", "begin", "continue", "register"):
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    log(f"Clicked flow button: '{btn.text.strip()}'")
                    clicked = True
                    break
            except Exception:
                continue
        if clicked:
            break

    if not clicked:
        # Fallback: click any button with action-like text
        all_buttons = _shadow_find_all(driver, "button")
        for btn in all_buttons:
            try:
                txt = btn.text.strip().lower()
                if txt in ("next", "start", "begin", "continue", "register"):
                    driver.execute_script("arguments[0].click();", btn)
                    log(f"Clicked fallback button: '{btn.text.strip()}'")
                    clicked = True
                    break
            except Exception:
                continue

    if not clicked:
        log("Could not find any flow navigation button")
        _debug_page(driver, "no_flow_btn")
        return []

    time.sleep(5)
    _debug_page(driver, "after_flow_click")

    # Step 2: Check for "Finish" button (means no slots)
    finish_buttons = _shadow_find_all(driver, "button")
    for btn in finish_buttons:
        try:
            if btn.text.strip().lower() == "finish":
                log("'Finish' button found — no slots available")
                return []
        except Exception:
            continue

    # Step 3: Try to select a registration option (checkbox) and proceed
    checkbox_clicked = False
    for selector in [
        "lightning-primitive-cell-checkbox span.slds-checkbox_faux",
        "input[type='checkbox']",
        "span.slds-checkbox_faux",
        "lightning-input input[type='checkbox']",
    ]:
        el = _shadow_find(driver, selector)
        if el:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", el)
                log("Selected registration checkbox")
                checkbox_clicked = True
                break
            except Exception:
                continue

    if checkbox_clicked:
        time.sleep(2)
        next_buttons = _shadow_find_all(driver, "button")
        for btn in next_buttons:
            try:
                if btn.text.strip().lower() == "next":
                    driver.execute_script("arguments[0].click();", btn)
                    log("Clicked 'Next' after checkbox selection")
                    time.sleep(5)
                    break
            except Exception:
                continue
        _debug_page(driver, "after_checkbox_next")
    else:
        log("No checkbox found at this step (may not be needed)")

    # Step 4: Check for "Finish" again
    finish_buttons = _shadow_find_all(driver, "button")
    for btn in finish_buttons:
        try:
            if btn.text.strip().lower() == "finish":
                log("'Finish' button found after selection — no location slots")
                return []
        except Exception:
            continue

    # Step 5: Scrape location table for available slots
    found_locations = []
    _debug_page(driver, "before_table_scrape")

    rows = _shadow_find_all(driver, "table tbody tr")
    if not rows:
        rows = _shadow_find_all(driver, "tr")
    if not rows:
        rows = _shadow_find_all(driver, "lightning-datatable tr")

    log(f"Found {len(rows)} table rows")

    for row in rows:
        try:
            cells = driver.execute_script("""
                var row = arguments[0];
                var cells = row.querySelectorAll('th, td');
                var texts = [];
                for (var i = 0; i < cells.length; i++) {
                    texts.push(cells[i].innerText.trim());
                }
                return texts;
            """, row)

            if not cells or not cells[0]:
                continue

            location_text = cells[0]

            if location_text.lower() in ("location", "city", "site", "exam site", ""):
                continue

            is_excluded = any(
                excluded.lower() in location_text.lower()
                for excluded in config.EXCLUDED_LOCATIONS
            )

            if is_excluded:
                log(f"  Skipping excluded location: {location_text}")
            else:
                log(f"  SLOT FOUND: {location_text}")
                found_locations.append(location_text)

        except Exception:
            continue

    if not rows:
        log("No table rows found — page might need different parsing")
        try:
            body_text = driver.execute_script("return document.body.innerText;")
            if body_text:
                log(f"Page text preview: {body_text[:500]}")
        except Exception:
            pass

    return found_locations


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_check_cycle(driver: uc.Chrome):
    """Run a single check cycle: login with cookies → check slots."""
    # Try cookie login first
    if not login_with_cookies(driver):
        # Cookies missing or expired — need manual login
        if not manual_login(driver):
            log("Manual login failed — skipping this cycle")
            return

    locations = check_for_slots(driver)

    if locations:
        log(f"*** SLOTS AVAILABLE at {len(locations)} location(s)! ***")
        for loc in locations:
            log(f"  >>> {loc}")
    else:
        log("No slots available")


def main():
    if not config.NDEB_USERNAME or not config.NDEB_PASSWORD:
        print("ERROR: NDEB_USERNAME and NDEB_PASSWORD must be set in .env file")
        print("Copy .env.example to .env and fill in your credentials:")
        print("  cp .env.example .env")
        sys.exit(1)

    log("=" * 50)
    log("NDEB Slot Tracker Started")
    log(f"Check interval: {config.CHECK_INTERVAL}s")
    log(f"Headless mode: {config.HEADLESS}")
    log(f"Excluded locations: {config.EXCLUDED_LOCATIONS}")
    if os.path.exists(COOKIES_FILE):
        log("Saved cookies found — will try cookie login first")
    else:
        log("No saved cookies — manual login will be required on first run")
    log("=" * 50)

    while True:
        driver = None
        try:
            driver = create_driver()
            run_check_cycle(driver)
        except Exception as e:
            log(f"Fatal error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        log(f"Waiting {config.CHECK_INTERVAL}s before next check...")
        time.sleep(config.CHECK_INTERVAL)


if __name__ == "__main__":
    main()
