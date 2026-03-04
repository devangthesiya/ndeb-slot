"""
NDEB Slot Tracker
Continuously monitors the NDEB portal for open exam registration slots
and logs when Canadian slots are found.
"""

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import config
from logger import log


def create_driver() -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver."""
    options = Options()
    if config.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-application-cache")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def login(driver: webdriver.Chrome):
    """Navigate to NDEB portal and log in."""
    log("Navigating to NDEB login page...")
    driver.get(config.NDEB_LOGIN_URL)
    time.sleep(4)

    wait = WebDriverWait(driver, 20)

    # Find username field
    username_field = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='username'], input[placeholder*='mail'], input[placeholder*='Username']"))
    )
    username_field.clear()
    username_field.send_keys(config.NDEB_USERNAME)

    # Find password field
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_field.clear()
    password_field.send_keys(config.NDEB_PASSWORD)

    # Find and click login button
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.loginButton, button.slds-button")
    login_btn.send_keys(Keys.ENTER)
    time.sleep(3)
    log("Login submitted")


def click_next_button(driver: webdriver.Chrome, timeout: int = 30):
    """Wait for and click the 'Next' button in the registration flow."""
    wait = WebDriverWait(driver, timeout)
    next_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH,
            "//button[contains(text(),'Next') or contains(text(),'next')]"
            " | //lightning-button//button"))
    )
    next_btn.click()
    time.sleep(2)


def check_for_slots(driver: webdriver.Chrome) -> list[str]:
    """
    Navigate the registration flow and check for available slots.
    Returns a list of location names with availability (excluding filtered locations).
    """
    wait = WebDriverWait(driver, 30)

    # Step 1: Click the first "Next" / flow navigation button to proceed
    log("Clicking through registration flow...")
    try:
        flow_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "flowruntime-navigation-bar button, "
                "footer button.slds-button_brand, "
                "button.slds-button_brand"))
        )
        flow_btn.click()
        time.sleep(3)
    except Exception:
        log("Could not find initial flow button — trying alternative selectors")
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.text.strip().lower() in ("next", "start", "begin", "continue"):
                    btn.click()
                    time.sleep(3)
                    break
        except Exception as e:
            log(f"Failed to proceed through flow: {e}")
            return []

    # Step 2: Check if we landed on a page with a table of locations
    # or if it says "Finish" (meaning no slots available)
    time.sleep(3)

    # Check for "Finish" button which means no new slots
    try:
        finish_buttons = driver.find_elements(By.XPATH,
            "//button[normalize-space(text())='Finish']")
        if finish_buttons:
            log("'Finish' button found — no slots available")
            return []
    except Exception:
        pass

    # Step 3: Try to select a registration option (checkbox) and proceed
    try:
        checkbox = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,
                "lightning-primitive-cell-checkbox span.slds-checkbox_faux, "
                "input[type='checkbox'], "
                "td lightning-primitive-cell-checkbox"))
        )
        checkbox.click()
        time.sleep(1)

        # Click Next after selecting
        next_buttons = driver.find_elements(By.CSS_SELECTOR,
            "flowruntime-navigation-bar button")
        for btn in next_buttons:
            if btn.text.strip().lower() in ("next",):
                btn.click()
                time.sleep(3)
                break
    except Exception:
        log("No checkbox/registration option found at this step")

    # Step 4: Check for the "Finish" button again
    try:
        finish_buttons = driver.find_elements(By.XPATH,
            "//button[normalize-space(text())='Finish']")
        if finish_buttons:
            log("'Finish' button found after selection — no location slots")
            return []
    except Exception:
        pass

    # Step 5: Scrape the location table for available slots
    found_locations = []
    try:
        # Look for table rows containing location data
        rows = driver.find_elements(By.CSS_SELECTOR,
            "flowruntime-datatable table tbody tr, "
            "lightning-datatable table tbody tr, "
            "table.slds-table tbody tr")

        if not rows:
            # Try broader search
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")

        for row in rows:
            try:
                # Get the location text from the first cell
                cells = row.find_elements(By.CSS_SELECTOR,
                    "th lightning-formatted-rich-text, "
                    "td lightning-formatted-rich-text, "
                    "th, td")
                if not cells:
                    continue

                location_text = cells[0].text.strip()
                if not location_text:
                    continue

                # Check if this location should be excluded
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

    except Exception as e:
        log(f"Error reading location table: {e}")

    return found_locations


def run_check_cycle(driver: webdriver.Chrome):
    """Run a single check cycle: login → navigate → check slots."""
    try:
        login(driver)
        locations = check_for_slots(driver)

        if locations:
            log(f"*** SLOTS AVAILABLE at {len(locations)} location(s)! ***")
            for loc in locations:
                log(f"  >>> {loc}")
        else:
            log("No slots available")

    except Exception as e:
        log(f"Error during check cycle: {e}")


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
