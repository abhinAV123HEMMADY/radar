"""Visits the deployed Radar app with a real headless browser to keep it warm.

Streamlit Community Cloud puts free-tier apps to sleep after ~12 hours of no
real visits, and a plain HTTP GET/uptime-monitor ping does NOT prevent this —
it returns 200 with a static HTML shell without ever booting the Python app.
Only an actual browser visit counts, which is why this uses Playwright instead
of curl. Run on a schedule via .github/workflows/keep-alive.yml.
"""
import sys

from playwright.sync_api import sync_playwright

URL = "https://io7hxxdsqhswhud9lngnwm.streamlit.app"
WAKE_UP_PHRASES = ["get this app back up", "wake up", "yes, get this app back up"]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        for phrase in WAKE_UP_PHRASES:
            locator = page.get_by_text(phrase, exact=False)
            try:
                if locator.count() > 0:
                    locator.first.click()
                    print(f"Clicked wake-up control matching '{phrase}'")
                    page.wait_for_timeout(15000)
                    break
            except Exception as exc:
                print(f"Wake-up click attempt failed for '{phrase}': {exc}", file=sys.stderr)

        page.wait_for_timeout(5000)
        print(f"Visited {URL} — page title: {page.title()!r}")
        browser.close()


if __name__ == "__main__":
    main()
