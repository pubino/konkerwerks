
import logging
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnostic_list():
    client = ConcurBrowserClient()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file)
        page = context.new_page()
        try:
            page.goto(f"{client.base_url}/nui/expense")
            # Wait for any report tile
            try:
                page.wait_for_selector(".report-tile, .report-card, .sapMCard", timeout=15000)
            except:
                logger.error("No report tiles found within 15s.")
            
            client._take_screenshot(page, "diagnostic_list")
            
            # Print all text content to see what's happening
            body_text = page.inner_text("body")
            logger.info("--- PAGE TEXT START ---")
            logger.info(body_text[:2000]) # First 2k chars
            logger.info("--- PAGE TEXT END ---")
            
        finally:
            browser.close()

if __name__ == "__main__":
    diagnostic_list()
