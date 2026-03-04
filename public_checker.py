"""
NDEB Public Page Slot Checker
Monitors the public NDEB exam dates page (no login required).
Checks registration status (open/closed/upcoming) for each exam.
"""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

import config
from logger import log


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def check_public_page(driver: webdriver.Chrome) -> list[dict]:
    """Scrape the public NDEB exam dates page for structured exam info."""
    log(f"Checking: {config.NDEB_PUBLIC_URL}")
    driver.get(config.NDEB_PUBLIC_URL)
    time.sleep(8)

    results = []
    exam_boxes = driver.find_elements(By.CSS_SELECTOR, "article.exam_box")

    for box in exam_boxes:
        try:
            exam_name = box.find_element(By.CSS_SELECTOR, "h3.exam_title").text.strip()
        except Exception:
            exam_name = "Unknown"

        try:
            exam_date = box.find_element(By.CSS_SELECTOR, "span.exam_date").text.strip()
            # Remove the "EXAM DATE\n" prefix
            exam_date = exam_date.replace("EXAM DATE\n", "").replace("EXAM DATE", "").strip()
        except Exception:
            exam_date = ""

        try:
            reg_deadline = box.find_element(By.CSS_SELECTOR, "span.exam_reg_date").text.strip()
            reg_deadline = reg_deadline.replace("REGISTRATION DEADLINE\n", "").replace("REGISTRATION DEADLINE", "").strip()
        except Exception:
            reg_deadline = ""

        try:
            status_el = box.find_element(By.CSS_SELECTOR, "span.exam-status")
            status_text = status_el.text.strip()
        except Exception:
            status_text = ""

        # Determine status
        css_classes = box.get_attribute("class") or ""
        if "registration-close" in css_classes:
            status = "CLOSED"
        elif "REGISTRATION IS OPEN" in status_text:
            status = "OPEN"
        elif "REGISTRATION OPEN DATE" in status_text:
            status = "UPCOMING"
        else:
            status = "UNKNOWN"

        results.append({
            "exam": exam_name,
            "date": exam_date,
            "deadline": reg_deadline,
            "status": status,
            "status_detail": status_text,
        })

    return results


STATUS_ICONS = {"OPEN": ">>>", "CLOSED": "---", "UPCOMING": "...", "UNKNOWN": "???"}


def print_results(results: list[dict]):
    """Log results in a clean, readable format."""
    open_exams = [r for r in results if r["status"] == "OPEN"]
    upcoming = [r for r in results if r["status"] == "UPCOMING"]
    closed = [r for r in results if r["status"] == "CLOSED"]

    if open_exams:
        log(f"*** {len(open_exams)} EXAM(S) WITH REGISTRATION OPEN ***")

    for r in results:
        icon = STATUS_ICONS.get(r["status"], "   ")
        line = f"  {icon} [{r['status']:8s}] {r['exam']}"
        if r["date"]:
            line += f"  |  Exam: {r['date']}"
        if r["deadline"]:
            line += f"  |  Deadline: {r['deadline']}"
        if r["status"] == "UPCOMING" and "OPEN DATE" in r["status_detail"]:
            opens_on = r["status_detail"].replace("REGISTRATION OPEN DATE:", "").strip()
            line += f"  |  Opens: {opens_on}"
        log(line)

    log(f"Summary: {len(open_exams)} open, {len(upcoming)} upcoming, {len(closed)} closed")


def main():
    log("=" * 60)
    log("NDEB Public Page Checker (no login required)")
    log(f"Check interval: {config.CHECK_INTERVAL}s")
    log("=" * 60)

    while True:
        driver = None
        try:
            driver = create_driver()
            results = check_public_page(driver)
            print_results(results)
        except Exception as e:
            log(f"Error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        log(f"Next check in {config.CHECK_INTERVAL}s...")
        time.sleep(config.CHECK_INTERVAL)


if __name__ == "__main__":
    main()
