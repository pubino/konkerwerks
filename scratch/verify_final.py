
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

def verify_report():
    client = ConcurBrowserClient()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file)
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.locator("text='Statement Report 06/16 - 07/31'").first.click()
            page.wait_for_timeout(5000)
            
            # Use nuclear dismissal
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"]').forEach(el => el.remove())")
            
            # Scan rows
            rows = page.locator("tr").all()
            for r in rows:
                text = r.inner_text()
                if "Select expense" in text and ("APPLE" in text or "GODADDY" in text):
                    print(f"ROW: {text.replace('\\n', ' ')}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_report()
