
from playwright.sync_api import sync_playwright
from browser_client import ConcurBrowserClient
import json

def verify_all_fields():
    client = ConcurBrowserClient()
    report_name = "Statement Report 06/16 - 07/31"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=client.session_file, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            page.goto(f"{client.base_url}/nui/expense")
            page.locator(f"text='{report_name}'").first.click()
            page.wait_for_timeout(5000)
            
            # Dismiss all modals
            page.evaluate("document.querySelectorAll('.sapMDialog, [role=\"dialog\"], [data-nuiexp=\"timelineModal\"]').forEach(el => el.remove())")
            
            # 1. Check Header
            page.locator("button:has-text('Report Details')").first.click()
            page.wait_for_timeout(1000)
            page.locator("text='Report Header'").first.click()
            page.wait_for_timeout(2000)
            
            header_purpose = page.locator("input[id*='purpose']").first.input_value()
            header_comment = page.locator("textarea[id*='comment']").first.input_value()
            print(f"HEADER: Purpose='{header_purpose}', Comment='{header_comment}'")
            
            page.locator("button:has-text('Cancel')").first.click()
            page.wait_for_timeout(1000)
            
            # 2. Check Deep Fields for Index 2 and 3
            all_rows = page.locator("tr").all()
            valid_rows = [r for r in all_rows if "Select expense" in r.inner_text()]
            
            for i in [1, 2]: # Index 2 and 3 (0-based 1 and 2)
                row = valid_rows[i]
                row.locator(".sapMCb").first.click(force=True)
                page.locator("button:has-text('Edit')").first.click()
                page.wait_for_timeout(3000)
                
                type_val = page.locator("input[id*='type']").first.input_value()
                purpose_val = page.locator("input[id*='purpose']").first.input_value()
                comment_val = page.locator("textarea[id*='comment']").first.input_value()
                
                print(f"EXPENSE {i+1}: Type='{type_val}', Purpose='{purpose_val}', Comment='{comment_val}'")
                
                page.locator("button:has-text('Cancel')").first.click()
                page.wait_for_timeout(1000)
                
        except Exception as e:
            print(f"Verification failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_all_fields()
