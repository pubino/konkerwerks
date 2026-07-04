
import logging
import os
import json
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_report_rows():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    
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
            
            # Use our new aggressive dismissal
            client._dismiss_modals(page)
            
            # Locate rows exactly like get_report_details
            row_selectors = [
                ".detail-row", ".sapMListUl .sapMLIB", "[class*='expense-item']", 
                "[class*='expense-row']", ".sapMCustomListItem", "[role='row']",
                "[role='listitem']", ".sapMTable tr", "tr.sapMLIB"
            ]
            all_rows = page.locator(", ".join(row_selectors)).all()
            logger.info(f"Total potential rows: {len(all_rows)}")
            
            valid_rows_data = []
            for idx, r in enumerate(all_rows):
                text = r.text_content() or ""
                normalized = " ".join(text.split()).strip()
                
                # Apply current filtering logic
                is_valid = True
                if len(normalized) < 15: is_valid = False
                lower_text = normalized.lower()
                if "expense type" in lower_text and "vendor details" in lower_text: is_valid = False
                if "select all rows" in lower_text: is_valid = False
                
                if is_valid:
                    valid_rows_data.append({
                        "original_index": idx,
                        "text": normalized[:100]
                    })
            
            logger.info(f"Discovered {len(valid_rows_data)} valid rows.")
            for i, data in enumerate(valid_rows_data):
                logger.info(f"Valid Row {i+1} (Orig {data['original_index']}): {data['text']}")

        except Exception as e:
            logger.error(f"Debug failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_report_rows()
