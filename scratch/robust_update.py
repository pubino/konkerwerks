
import os
import json
import time
import logging
import re
from typing import List, Dict, Optional, Any, Union
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class RobustConcurClient:
    def __init__(self, session_file="concur_session.json", base_url="https://www.concursolutions.com"):
        self.session_file = session_file
        self.base_url = base_url

    def _dismiss_modals(self, page):
        """Nuclear modal dismissal."""
        page.evaluate('''
            document.querySelectorAll("[data-nuiexp='timelineModal'], .sapcnqr-dialog, [role='dialog']").forEach(el => el.remove());
            document.querySelectorAll(".sapMDialog, .sapMMessageToast").forEach(el => el.remove());
            document.body.classList.remove("sapMDialog-Open");
        ''')
        page.wait_for_timeout(1000)

    def _get_valid_rows(self, page):
        """Finds all rows that are actually clickable expenses."""
        all_rows = page.locator("tr, [role='row']").all()
        valid = []
        for r in all_rows:
            try:
                text = r.inner_text()
                if "Select expense" in text and len(text) > 20:
                    valid.append(r)
            except:
                continue
        return valid

    def update_transaction(self, report_name, indices, expense_type=None, justification=None):
        indices = [indices] if isinstance(indices, int) else indices
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=self.session_file)
            page = context.new_page()
            
            try:
                page.goto(f"{self.base_url}/nui/expense")
                page.wait_for_selector(".report-tile, .report-card")
                
                # Open report
                page.locator(f"text='{report_name}'").first.click()
                page.wait_for_timeout(5000)
                self._dismiss_modals(page)
                
                results = []
                for idx in indices:
                    logger.info(f"Updating index {idx}...")
                    rows = self._get_valid_rows(page)
                    if idx > len(rows):
                        results.append({"index": idx, "success": False, "error": "Index out of range"})
                        continue
                    
                    row = rows[idx-1]
                    # Select and Edit
                    cb = row.locator(".sapMCb").first
                    cb.click(force=True)
                    page.wait_for_timeout(1000)
                    
                    edit_btn = page.locator("button:has-text('Edit')").filter(visible=True).first
                    if not edit_btn.is_enabled():
                        # Try re-clicking
                        row.click(force=True)
                        page.wait_for_timeout(1000)
                    
                    if not edit_btn.is_enabled():
                        results.append({"index": idx, "success": False, "error": "Edit button disabled"})
                        continue
                        
                    edit_btn.click()
                    page.wait_for_timeout(3000)
                    self._dismiss_modals(page)
                    
                    # Fill Type
                    if expense_type:
                        type_inp = page.locator("input[id*='type'], [data-nuiexp*='type']").first
                        type_inp.fill(expense_type)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(1000)
                    
                    # Fill Justification (into Business Purpose and Comment)
                    if justification:
                        for field in ["purpose", "comment"]:
                            inp = page.locator(f"input[id*='{field}'], textarea[id*='{field}']").first
                            if inp.count() > 0:
                                inp.fill(justification)
                    
                    # Save
                    save_btn = page.locator("button:has-text('Save')").filter(visible=True).first
                    save_btn.click()
                    page.wait_for_timeout(3000)
                    self._dismiss_modals(page)
                    results.append({"index": idx, "success": True})
                
                return results
            finally:
                browser.close()

if __name__ == "__main__":
    import sys
    client = RobustConcurClient()
    # Run the specific update needed
    res = client.update_transaction("Statement Report 06/16 - 07/31", [2, 3], 
                                     expense_type="Software (OIT use only)", 
                                     justification="Required by bs37. Software used for research.")
    print(json.dumps(res, indent=2))
