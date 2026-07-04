
import logging
import os
import json
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def audit_all_rows():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.wait_for_selector(".report-tile, .report-card", timeout=30000)
            
            report_card = page.locator(f"text='{report_name}'").first
            report_card.click()
            page.wait_for_timeout(5000)
            client._dismiss_modals(page)
            
            # Find all rows
            rows = page.locator("table tbody tr, [role='row']").all()
            logger.info(f"Found {len(rows)} potential rows.")
            
            for i, row in enumerate(rows):
                text = row.inner_text().replace("\n", " | ")
                if not text.strip() or "Select expense" not in text:
                    continue
                    
                # Try to select it
                logger.info(f"Testing row {i}: {text[:100]}...")
                cb = row.locator(".sapMCb, [type='checkbox']").first
                if cb.count() > 0:
                    cb.click(force=True)
                    page.wait_for_timeout(2000)
                    
                    edit_btn = page.locator("button:has-text('Edit'), .sapMBtn:has-text('Edit')").filter(has_text="Edit").first
                    is_enabled = edit_btn.is_enabled() if edit_btn.count() > 0 else False
                    
                    results.append({
                        "row_index": i,
                        "text": text,
                        "edit_enabled": is_enabled
                    })
                    
                    # Deselect
                    cb.click(force=True)
                    page.wait_for_timeout(500)
            
            print(json.dumps(results, indent=2))

        except Exception as e:
            logger.error(f"Audit failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    audit_all_rows()
