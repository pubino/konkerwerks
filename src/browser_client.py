import os
import time
import logging
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ConcurBrowserClient")


class ConcurBrowserClient:
    """Browser automation client for SAP Concur using Playwright."""

    def __init__(
        self,
        session_file: str = "concur_session.json",
        base_url: str = "https://www.concursolutions.com"
    ):
        self.session_file = session_file
        self.base_url = base_url.rstrip("/")
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _take_screenshot(self, page: Any, name: str) -> str:
        """Helper to capture screenshots for debugging."""
        path = os.path.join(self.screenshot_dir, f"{name}.png")
        try:
            page.screenshot(path=path)
            logger.info(f"Captured screenshot: {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to capture screenshot {name}: {str(e)}")
            return ""

    def _wait_for_dashboard(self, page: Any) -> None:
        """Helper to wait for Concur's dynamic SPA dashboard elements to load."""
        logger.info("Waiting for Concur dashboard to render (handling loading spinners)...")
        try:
            page.wait_for_load_state("load", timeout=15000)
        except Exception:
            pass

        # Smart wait loop: wait until all Concur busy indicators (blue loading dots) disappear
        try:
            logger.info("Waiting for all Concur busy indicators to clear...")
            indicator = page.locator(".sapcnqr-busy-indicator, .spndpkg-full-page-busyIndicator-wrapper")
            start_time = time.time()
            page.wait_for_timeout(500)
            
            while time.time() - start_time < 30:
                visible_count = 0
                count = indicator.count()
                for i in range(count):
                    try:
                        if indicator.nth(i).is_visible():
                            visible_count += 1
                    except Exception:
                        continue
                if visible_count == 0:
                    break
                page.wait_for_timeout(500)
            logger.info("Concur busy indicators cleared.")
        except Exception as e:
            logger.warning(f"Proceeding after busy indicator wait timeout: {str(e)}")

        # Combined selectors representing key elements
        combined_selectors = [
            "#create-report-btn",
            "button:has-text('Create New Report')",
            "button:has-text('Create Report')",
            "button:has-text('Create Expense Report')",
            "span:has-text('Create Expense Report')",
            ".no-reports",
            ".report-card",
            ".report-tile",
            ".cnqr-report-card",
            ".sapMCard",
            "h2:has-text('Available Receipts')"
        ]
        combined_str = ", ".join(combined_selectors)

        try:
            page.locator(combined_str).first.wait_for(state="visible", timeout=15000)
            logger.info("Dashboard components loaded and visible.")
        except Exception as e:
            logger.warning(f"Proceeding after dashboard load timeout: {str(e)}")

    def run_headed_login(self) -> None:
        """
        Launches a headed browser instance to let the user log in manually
        and handle MFA/2FA or SSO. Once logged in, it saves the session state.
        """
        logger.info("Starting headed browser for login...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            logger.info(f"Navigating to login page: {self.base_url}")
            page.goto(self.base_url)

            print("\n" + "=" * 80)
            print(" ACTION REQUIRED:")
            print(" 1. In the opened browser window, log in to SAP Concur.")
            print(" 2. Complete any MFA/2FA, Single Sign-On (SSO), or Captchas if prompted.")
            print(" 3. Once you see the Concur Homepage / Dashboard (fully logged in),")
            print("    return to this terminal and press ENTER to save your session.")
            print("=" * 80 + "\n")

            input("Press ENTER here after you have logged in and see the Concur home page...")

            context.storage_state(path=self.session_file)
            logger.info(f"Session state successfully saved to {self.session_file}")
            browser.close()
            logger.info("Browser closed.")

    def create_draft_report(
        self,
        name: str,
        purpose: Optional[str] = None,
        comment: Optional[str] = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Loads the saved session and attempts to create a draft expense report.
        Captures screenshots at each step for verification and debugging.
        """
        if not os.path.exists(self.session_file):
            raise FileNotFoundError(
                f"Session file '{self.session_file}' not found. "
                "Please run login configuration first using: python3 src/cli.py --browser-login"
            )

        logger.info(f"Launching browser (headless={headless}) using session from {self.session_file}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                storage_state=self.session_file,
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            try:
                dashboard_url = f"{self.base_url}/nui/expense"
                logger.info(f"Navigating to Concur Expense page: {dashboard_url}")
                page.goto(dashboard_url, timeout=30000)
                
                # Check for login redirection
                current_url = page.url
                if "login" in current_url.lower() or "signin" in current_url.lower():
                    self._take_screenshot(page, "session_expired_error")
                    raise RuntimeError("Session appears to have expired. Please re-run '--browser-login'.")

                # Wait for SPA widgets to load
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "01_expense_dashboard")

                # Step 1: Click "Create New Report"
                logger.info("Locating 'Create New Report' button...")
                create_button = None
                selectors = [
                    # Real Concur selector strategies
                    lambda p: p.get_by_text("Create Expense Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create Expense Report", exact=False),
                    lambda p: p.locator("text=Create Expense Report"),
                    lambda p: p.locator("button:has-text('Create Expense Report')"),
                    
                    # Alternative selector fallbacks
                    lambda p: p.get_by_role("button", name="Create New Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create Report", exact=False),
                    lambda p: p.locator("button:has-text('Create New Report')"),
                    lambda p: p.locator("button:has-text('Create Report')"),
                    lambda p: p.locator("a:has-text('Create New Report')"),
                    lambda p: p.locator("a:has-text('Create Report')"),
                    lambda p: p.locator("#create-report-btn"),
                    lambda p: p.locator(".sapMBtnContent:has-text('Create New Report')")
                ]

                for idx, get_sel in enumerate(selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            create_button = loc
                            logger.info(f"Found 'Create New Report' using selector strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not create_button:
                    self._take_screenshot(page, "create_button_not_found")
                    raise RuntimeError("Could not locate 'Create New Report' button.")

                create_button.click()
                logger.info("Clicked 'Create New Report' button.")
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "02_create_report_dialog")

                # Step 2: Fill in the Report Header Form
                logger.info("Filling out the report header form...")

                # Name input selector
                name_input = page.get_by_role("textbox", name="Report Name", exact=False)
                if not name_input.is_visible(timeout=2000):
                    name_input = page.locator("#reportname, input[id*='reportname'], input[id*='ReportName'], input[name*='name']")
                
                if name_input.is_visible(timeout=2000):
                    name_input.fill(name)
                    logger.info(f"Filled Report Name: {name}")
                else:
                    raise RuntimeError("Could not find standard Report Name input field.")

                # Purpose input
                if purpose:
                    purpose_input = page.get_by_role("textbox", name="Purpose", exact=False)
                    if not purpose_input.is_visible(timeout=1000):
                        purpose_input = page.locator("#purpose, textarea[id*='purpose'], input[id*='purpose']")
                    
                    if purpose_input.is_visible(timeout=1000):
                        purpose_input.fill(purpose)
                        logger.info("Filled Purpose field.")

                # Comment input
                if comment:
                    comment_input = page.get_by_role("textbox", name="Comment", exact=False)
                    if not comment_input.is_visible(timeout=1000):
                        comment_input = page.locator("#comment, textarea[id*='comment'], input[id*='comment']")
                    
                    if comment_input.is_visible(timeout=1000):
                        comment_input.fill(comment)
                        logger.info("Filled Comment field.")

                self._take_screenshot(page, "03_filled_form")

                # Step 3: Click "Create Report" / "Next" / "Save"
                logger.info("Submitting the report form...")
                submit_button = None
                submit_selectors = [
                    lambda p: p.get_by_role("button", name="Create Report", exact=False),
                    lambda p: p.get_by_role("button", name="Create", exact=True),
                    lambda p: p.get_by_role("button", name="Next", exact=True),
                    lambda p: p.get_by_role("button", name="Save", exact=True),
                    lambda p: p.locator("#submit-report-btn"),
                    lambda p: p.locator("button:has-text('Create Report')")
                ]

                for idx, get_sel in enumerate(submit_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            submit_button = loc
                            logger.info(f"Found submit button using selector strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not submit_button:
                    self._take_screenshot(page, "submit_button_not_found")
                    raise RuntimeError("Could not locate Create/Next/Save button in report form.")

                submit_button.click()
                logger.info("Clicked form submission button.")
                page.wait_for_timeout(3000)

                self._take_screenshot(page, "04_after_creation_completed")
                logger.info("Report creation completed!")

                return {
                    "success": True,
                    "report_name": name,
                    "screenshot_folder": os.path.abspath(self.screenshot_dir),
                    "notes": "Verify details in screenshots/04_after_creation_completed.png"
                }

            except PlaywrightTimeoutError as e:
                self._take_screenshot(page, "timeout_error")
                raise RuntimeError(f"Playwright operation timed out: {str(e)}")
            except Exception as e:
                self._take_screenshot(page, "unexpected_browser_error")
                raise e
            finally:
                browser.close()

    def list_reports(self, filter_view: Optional[str] = None, headless: bool = True) -> List[Dict[str, Any]]:
        """
        [READ] Navigates to the Expense page and retrieves all visible reports.
        Optionally selects a different filter view (e.g. 'Last 90 Days', 'All Reports') first.
        """
        logger.info(f"Listing expense reports via browser (headless={headless}, filter={filter_view})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            reports = []
            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "list_reports_dashboard")

                if filter_view:
                    logger.info(f"Selecting report filter view: {filter_view}...")
                    view_btn = None
                    view_selectors = [
                        lambda p: p.locator("#report-view-select"),
                        lambda p: p.get_by_role("combobox", name="View", exact=False),
                        lambda p: p.locator("select[id*='view']"),
                        lambda p: p.locator(".sapMSelect, [class*='select']").filter(has_text="Reports").first,
                        lambda p: p.get_by_text("Active Reports", exact=True),
                        lambda p: p.locator("button:has-text('Active Reports')")
                    ]
                    for idx, get_sel in enumerate(view_selectors):
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                view_btn = loc
                                logger.info(f"Found View selector using strategy {idx+1}.")
                                break
                        except Exception:
                            continue

                    if view_btn:
                        tag_name = view_btn.evaluate("el => el.tagName.toLowerCase()")
                        if tag_name == "select":
                            view_btn.select_option(label=filter_view)
                        else:
                            view_btn.click()
                            page.wait_for_timeout(1000)
                            option = page.get_by_role("option", name=filter_view, exact=False)
                            if not option.is_visible(timeout=1000):
                                option = page.locator(f".sapMSelectListItem:has-text('{filter_view}')")
                            if not option.is_visible(timeout=1000):
                                option = page.locator(f"text={filter_view}").last
                            option.click()
                        
                        logger.info(f"Successfully selected filter view: {filter_view}")
                        page.wait_for_timeout(3000)
                        self._wait_for_dashboard(page)
                        self._take_screenshot(page, "list_reports_post_filter")

                # Handle empty state
                if page.locator(".no-reports").is_visible(timeout=2000):
                    logger.info("No reports found on dashboard.")
                    return []

                # Selector options to locate report containers (supports Mock UI and standard Concur UIs)
                card_selectors = [".report-tile", ".report-card", ".cnqr-report-card", ".sapMCard"]
                cards = None
                for selector in card_selectors:
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        cards = loc
                        logger.info(f"Found report cards using selector '{selector}'.")
                        break

                if not cards:
                    cards = page.locator(".sapMListUl .sapMLIB")
                
                count = cards.count()
                logger.info(f"Discovered {count} report item(s) on page.")

                for i in range(count):
                    card = cards.nth(i)
                    
                    # Extract Name
                    name_selectors = [
                        ".report-tile__header__text",
                        ".report-name",
                        ".cnqr-report-name",
                        ".sapMObjLTitle",
                        "h3",
                        "strong"
                    ]
                    name = "Unknown Report"
                    for ns in name_selectors:
                        sub = card.locator(ns)
                        if sub.count() > 0:
                            name = sub.first.text_content().strip()
                            break

                    # Extract Purpose / Info
                    purpose_selectors = [
                        ".report-purpose",
                        ".sapMObjLDescription",
                        "p"
                    ]
                    purpose = ""
                    for ps in purpose_selectors:
                        sub = card.locator(ps)
                        if sub.count() > 0:
                            purpose = sub.first.text_content().strip()
                            break

                    reports.append({
                        "index": i,
                        "name": name,
                        "purpose": purpose
                    })
                    logger.info(f"  Report {i+1}: {name} ({purpose})")

            except Exception as e:
                logger.error(f"Error listing reports: {str(e)}")
            finally:
                browser.close()
            return reports

    def update_report(
        self,
        old_name: str,
        new_name: str,
        new_purpose: Optional[str] = None,
        new_comment: Optional[str] = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        [UPDATE] Locates an expense report by its current name, enters edit mode,
        modifies its headers, and saves it.
        """
        logger.info(f"Updating report '{old_name}' -> '{new_name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "update_report_pre")

                # Find the card containing the old name
                card = page.locator(".report-tile, .report-card").filter(has_text=old_name)
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=old_name)
                
                if card.count() == 0:
                    raise FileNotFoundError(f"No report named '{old_name}' found to edit.")

                # Click "Edit" or open the report
                edit_btn = card.get_by_role("button", name="Edit", exact=False)
                if edit_btn.is_visible(timeout=2000):
                    edit_btn.click()
                else:
                    card.first.click()
                    page.wait_for_timeout(2000)
                    
                    # Open 'Report Details' dropdown menu
                    page.get_by_role("button", name="Report Details", exact=False).click()
                    page.wait_for_timeout(1000)
                    
                    # Locate and click 'Report Header' (or 'Edit Report Info' on legacy UIs)
                    menu_item = None
                    menu_selectors = [
                        lambda p: p.get_by_role("menuitem", name="Report Header", exact=False),
                        lambda p: p.get_by_role("menuitem", name="Edit Report Info", exact=False),
                        lambda p: p.locator("text=Report Header"),
                        lambda p: p.locator("text=Edit Report Info")
                    ]
                    for idx, get_sel in enumerate(menu_selectors):
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                menu_item = loc
                                break
                        except Exception:
                            continue

                    if not menu_item:
                        self._take_screenshot(page, "report_header_menuitem_not_found")
                        raise RuntimeError("Could not locate 'Report Header' dropdown item.")
                    
                    menu_item.click()

                page.wait_for_timeout(2000)
                self._take_screenshot(page, "update_report_dialog")

                # Refill form fields
                name_input = page.get_by_role("textbox", name="Report Name", exact=False)
                if not name_input.is_visible(timeout=2000):
                    name_input = page.locator("#reportname, input[id*='reportname'], input[id*='ReportName'], input[name*='name']")
                
                if name_input.is_visible(timeout=2000):
                    name_input.fill(new_name)
                    logger.info(f"Filled Report Name: {new_name}")
                else:
                    raise RuntimeError("Could not find standard Report Name input field.")

                if new_purpose:
                    purpose_input = page.get_by_role("textbox", name="Purpose", exact=False)
                    if not purpose_input.is_visible(timeout=2000):
                        purpose_input = page.locator("#purpose, textarea[id*='purpose'], input[id*='purpose']")
                    if purpose_input.is_visible(timeout=2000):
                        purpose_input.fill(new_purpose)
                        logger.info("Filled Purpose field.")

                if new_comment:
                    comment_input = page.get_by_role("textbox", name="Comment", exact=False)
                    if not comment_input.is_visible(timeout=2000):
                        comment_input = page.locator("#comment, textarea[id*='comment'], input[id*='comment']")
                    if comment_input.is_visible(timeout=2000):
                        comment_input.fill(new_comment)
                        logger.info("Filled Comment field.")

                self._take_screenshot(page, "update_report_form_filled")

                # Save changes
                save_btn = page.get_by_role("button", name="Save", exact=True)
                if not save_btn.is_visible(timeout=2000):
                    save_btn = page.locator("#submit-report-btn, button:has-text('Save')")
                save_btn.click()
                
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "update_report_post")
                logger.info(f"Report '{old_name}' successfully updated to '{new_name}'!")
                return {"success": True, "name": new_name}

            except Exception as e:
                self._take_screenshot(page, "update_error")
                raise e
            finally:
                browser.close()

    def delete_report(self, name: str, headless: bool = True) -> Dict[str, Any]:
        """
        [DELETE] Locates an expense report by its name, clicks delete, and confirms.
        """
        logger.info(f"Deleting report '{name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "delete_report_pre")

                # Find target report card
                card = page.locator(".report-tile, .report-card").filter(has_text=name)
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=name)

                if card.count() == 0:
                    raise FileNotFoundError(f"No report named '{name}' found to delete.")

                # Set up listener for dialog popups (like window.confirm prompt)
                page.on("dialog", lambda dialog: dialog.accept())

                # Click Delete
                delete_btn = card.get_by_role("button", name="Delete", exact=False)
                if delete_btn.is_visible(timeout=2000):
                    delete_btn.click()
                    logger.info("Clicked delete button on card.")
                else:
                    # In real Concur Fiori: open the report, click three-dot menu, click Delete Report
                    logger.info("Opening report details page to delete...")
                    card.first.click()
                    page.wait_for_timeout(3000)
                    
                    # Locate and click the '...' (More Options) button next to 'Submit Report'
                    more_btn = None
                    more_selectors = [
                        lambda p: p.get_by_role("button", name="Report Actions", exact=False),
                        lambda p: p.get_by_role("button", name="More Actions", exact=False),
                        lambda p: p.get_by_role("button", name="More Options", exact=False),
                        lambda p: p.get_by_role("button", name="More", exact=False),
                        lambda p: p.locator("button:has-text('...')"),
                        lambda p: p.locator("[class*='more']"),
                        lambda p: p.locator(".sapMBtnContent:has-text('...')")
                    ]
                    for get_sel in more_selectors:
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                more_btn = loc
                                break
                        except Exception:
                            continue
                            
                    if not more_btn:
                        self._take_screenshot(page, "more_options_button_not_found")
                        raise RuntimeError("Could not locate three-dot (More Actions) button inside report.")
                        
                    more_btn.click()
                    page.wait_for_timeout(1000)
                    self._take_screenshot(page, "more_options_menu_open")
                    
                    # Click 'Delete Report' or 'Delete'
                    delete_item = None
                    delete_item_selectors = [
                        lambda p: p.get_by_role("menuitem", name="Delete Report", exact=False),
                        lambda p: p.get_by_role("menuitem", name="Delete", exact=False),
                        lambda p: p.locator("text=Delete Report"),
                        lambda p: p.locator("text=Delete")
                    ]
                    for get_sel in delete_item_selectors:
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                delete_item = loc
                                break
                        except Exception:
                            continue
                            
                    if not delete_item:
                        raise RuntimeError("Could not locate 'Delete Report' menu item.")
                        
                    delete_item.click()
                    logger.info("Clicked 'Delete Report' menu item.")
                    
                    # Confirm popup if not handled automatically
                    try:
                        confirm_selectors = [
                            lambda p: p.get_by_role("button", name="Delete Report", exact=True),
                            lambda p: p.get_by_role("button", name="Delete", exact=True),
                            lambda p: p.get_by_role("button", name="Yes, Delete", exact=False),
                            lambda p: p.locator(".sapcnqr-button--primary:has-text('Delete Report')"),
                            lambda p: p.locator("button:has-text('Delete Report')").last
                        ]
                        confirm_btn = None
                        for get_sel in confirm_selectors:
                            try:
                                loc = get_sel(page)
                                if loc.is_visible(timeout=2000):
                                    confirm_btn = loc
                                    break
                            except Exception:
                                continue

                        if confirm_btn:
                            confirm_btn.click()
                            logger.info("Clicked confirmation button.")
                        else:
                            logger.warning("No confirmation button matched/visible.")
                    except Exception as ce:
                        logger.warning(f"Error handling confirmation: {str(ce)}")

                page.wait_for_timeout(3000)
                self._take_screenshot(page, "delete_report_post")
                logger.info(f"Report '{name}' successfully deleted!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "delete_error")
                raise e
            finally:
                browser.close()

    def list_available_receipts(self, headless: bool = True) -> List[str]:
        """
        [READ RECEIPTS] Navigates to the Expense page and lists names of available receipts.
        """
        logger.info(f"Listing available receipts via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            receipts = []
            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "list_receipts_dashboard")

                # Locate specific receipt grid items to avoid instructions and loading skeletons
                items = page.locator(".receipt-grid-item")
                count = items.count()
                
                # Fallback to general thumbnails if specific classes are not found (e.g. in mock server)
                if count == 0:
                    items = page.locator(".available-receipt-thumbnail")
                    count = items.count()

                logger.info(f"Discovered {count} available receipt card(s) on page.")

                for i in range(count):
                    item = items.nth(i)
                    
                    # Try to extract the title/name of the receipt
                    name = ""
                    name_selectors = [
                        ".receipt-grid-item__header__text.receipt-grid-item__header--bold",
                        ".receipt-grid-item__header__text",
                        ".receipt-name"
                    ]
                    for ns in name_selectors:
                        sub = item.locator(ns)
                        if sub.count() > 0:
                            name = sub.first.text_content().strip()
                            break
                    
                    if not name:
                        # Fallback to stripping the text content of the item directly
                        name = item.text_content().strip()
                        if "\n" in name:
                            name = name.split("\n")[-1].strip()

                    # Clean up layout text and skeletons
                    if name:
                        name = name.replace("\n", " ").strip()
                    
                    if (name and 
                        "loading" not in name.lower() and 
                        "drag and drop" not in name.lower() and 
                        "valid file types" not in name.lower() and
                        "available receipts" not in name.lower() and
                        "upload new receipt" not in name.lower()):
                        receipts.append(name)
                        logger.info(f"  Receipt {i+1}: {name}")

            except Exception as e:
                logger.error(f"Error listing receipts: {str(e)}")
            finally:
                browser.close()
            return list(set(receipts))

    def delete_available_receipt(self, receipt_name: str, headless: bool = True) -> Dict[str, Any]:
        """
        [DELETE RECEIPT] Navigates to the Expense page, locates the receipt thumbnail
        in the 'Available Receipts' section, opens it, clicks delete, and confirms.
        """
        logger.info(f"Deleting available receipt '{receipt_name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "delete_receipt_dashboard_pre")

                # Find the receipt thumbnail
                thumb_selectors = [
                    lambda p: p.locator(".receipt-grid-item").filter(has_text=receipt_name),
                    lambda p: p.locator(".available-receipt-thumbnail").filter(has_text=receipt_name),
                    lambda p: p.locator("[class*='receipt']").filter(has_text=receipt_name)
                ]

                thumbnail = None
                for get_sel in thumb_selectors:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            thumbnail = loc.first
                            logger.info("Found receipt thumbnail to delete.")
                            break
                    except Exception:
                        continue

                if not thumbnail:
                    raise FileNotFoundError(f"No available receipt named '{receipt_name}' found.")

                page.on("dialog", lambda dialog: dialog.accept())

                thumbnail.click()
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "delete_receipt_viewer_open")

                # Click the Delete button inside the viewer
                delete_btn = None
                delete_selectors = [
                    lambda p: p.get_by_role("button", name="Delete Receipt", exact=False),
                    lambda p: p.get_by_role("button", name="Delete", exact=False),
                    lambda p: p.locator("#delete-receipt-btn"),
                    lambda p: p.locator("button:has-text('Delete')")
                ]

                for idx, get_sel in enumerate(delete_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            delete_btn = loc
                            logger.info(f"Found receipt delete button using strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if not delete_btn:
                    raise RuntimeError("Could not locate Delete button in receipt viewer.")

                delete_btn.click()
                logger.info("Clicked delete button in receipt viewer.")
                
                try:
                    confirm_btn = page.get_by_role("button", name="Yes, Delete", exact=False)
                    if confirm_btn.is_visible(timeout=1000):
                        confirm_btn.click()
                        logger.info("Clicked confirmation confirmation button.")
                except Exception:
                    pass

                page.wait_for_timeout(3000)
                self._take_screenshot(page, "delete_receipt_post")
                logger.info(f"Receipt '{receipt_name}' successfully deleted!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "delete_receipt_error")
                raise e
            finally:
                browser.close()

    def get_report_details(self, name: str, filter_view: Optional[str] = None, headless: bool = True) -> Dict[str, Any]:
        """
        Navigates to the Expense page, locates a report by name, clicks it to open detail view,
        and extracts report metadata and line-item expenses.
        Optionally selects a different filter view (e.g. 'Last 90 Days') first.
        """
        logger.info(f"Getting details for report '{name}' via browser (headless={headless}, filter={filter_view})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "get_report_details_pre")

                if filter_view:
                    logger.info(f"Selecting report filter view: {filter_view}...")
                    view_btn = None
                    view_selectors = [
                        lambda p: p.locator("#report-view-select"),
                        lambda p: p.get_by_role("combobox", name="View", exact=False),
                        lambda p: p.locator("select[id*='view']"),
                        lambda p: p.locator(".sapMSelect, [class*='select']").filter(has_text="Reports").first,
                        lambda p: p.get_by_text("Active Reports", exact=True),
                        lambda p: p.locator("button:has-text('Active Reports')")
                    ]
                    for idx, get_sel in enumerate(view_selectors):
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                view_btn = loc
                                break
                        except Exception:
                            continue

                    if view_btn:
                        tag_name = view_btn.evaluate("el => el.tagName.toLowerCase()")
                        if tag_name == "select":
                            view_btn.select_option(label=filter_view)
                        else:
                            view_btn.click()
                            page.wait_for_timeout(1000)
                            option = page.get_by_role("option", name=filter_view, exact=False)
                            if not option.is_visible(timeout=1000):
                                option = page.locator(f".sapMSelectListItem:has-text('{filter_view}')")
                            if not option.is_visible(timeout=1000):
                                option = page.locator(f"text={filter_view}").last
                            option.click()
                        page.wait_for_timeout(3000)
                        self._wait_for_dashboard(page)
                        self._take_screenshot(page, "get_report_details_post_filter")

                # Locate the card and click it to navigate into detail view
                card = page.locator(".report-tile, .report-card").filter(has_text=name)
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=name)

                if card.count() == 0:
                    raise FileNotFoundError(f"No report named '{name}' found.")

                card.first.click()
                page.wait_for_timeout(3000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "get_report_details_open")

                # Extract Report Details Header info
                report_num = "Unknown"
                purpose = "Unknown"
                comment = "Unknown"

                # Standard Fiori selectors for report header info
                # Report Number
                selectors_num = [
                    lambda p: p.locator("#detail-report-id"),
                    lambda p: p.locator("[class*='report-number']"),
                    lambda p: p.locator("text=Report Number:").locator(".."),
                    lambda p: p.get_by_role("button", name="Report Number", exact=False)
                ]
                for get_sel in selectors_num:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            report_num = loc.first.text_content().replace("Report Number:", "").replace("Report Number", "").strip()
                            break
                    except Exception:
                        continue

                # Purpose
                selectors_purpose = [
                    lambda p: p.locator("#detail-purpose"),
                    lambda p: p.locator("text=Purpose:").locator(".."),
                    lambda p: p.locator("[class*='purpose']")
                ]
                for get_sel in selectors_purpose:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            purpose = loc.first.text_content().replace("Purpose:", "").replace("Purpose", "").strip()
                            break
                    except Exception:
                        continue

                # Comment
                selectors_comment = [
                    lambda p: p.locator("#detail-comment"),
                    lambda p: p.locator("text=Comment:").locator("..")
                ]
                for get_sel in selectors_comment:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            comment = loc.first.text_content().replace("Comment:", "").replace("Comment", "").strip()
                            break
                    except Exception:
                        continue

                # List expenses line items
                expenses = []
                expense_rows = page.locator(".detail-row, .sapMListUl .sapMLIB, [class*='expense-item'], [class*='expense-row']").all()
                logger.info(f"Discovered {len(expense_rows)} expense line item(s) inside report details.")

                for idx, row in enumerate(expense_rows):
                    try:
                        text = row.text_content().strip()
                        if text and ("lodging" in text.lower() or "meal" in text.lower() or "uber" in text.lower() or "hilton" in text.lower() or "merchant" in text.lower() or "amount" in text.lower() or "type" in text.lower()):
                            expenses.append({
                                "index": idx,
                                "raw_text": text
                            })
                    except Exception:
                        continue

                return {
                    "success": True,
                    "report_name": name,
                    "report_number": report_num,
                    "purpose": purpose,
                    "comment": comment,
                    "expenses": expenses
                }

            except Exception as e:
                self._take_screenshot(page, "get_report_details_error")
                raise e
            finally:
                browser.close()

    def list_card_transactions(self, card_type_filter: str = "All Corporate and Personal Cards", headless: bool = True) -> List[Dict[str, Any]]:
        """
        Navigates to the Expense page, locates the Available Expenses section,
        selects the card type activity view (e.g. All Corporate and Personal Cards, All Purchasing Cards),
        and lists available credit card transactions.
        """
        logger.info(f"Listing card transactions with filter '{card_type_filter}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            transactions = []
            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "list_card_transactions_pre")

                # Filter dropdown selector for available expenses/card transactions
                filter_btn = None
                filter_selectors = [
                    lambda p: p.locator("#card-view-select"),
                    lambda p: p.get_by_role("combobox", name="Activity", exact=False),
                    lambda p: p.locator("select[id*='card']"),
                    lambda p: p.locator("button:has-text('All Corporate and Personal Cards')"),
                    lambda p: p.locator("button:has-text('All Purchasing Cards')")
                ]
                for idx, get_sel in enumerate(filter_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            filter_btn = loc
                            logger.info(f"Found card filter view dropdown using strategy {idx+1}.")
                            break
                    except Exception:
                        continue

                if filter_btn:
                    tag_name = filter_btn.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "select":
                        filter_btn.select_option(label=card_type_filter)
                    else:
                        filter_btn.click()
                        page.wait_for_timeout(1000)
                        
                        # Select option
                        option = page.get_by_role("option", name=card_type_filter, exact=False)
                        if not option.is_visible(timeout=1000):
                            option = page.locator(f"text={card_type_filter}").last
                        option.click()
                    
                    logger.info(f"Selected card filter view: {card_type_filter}")
                    page.wait_for_timeout(3000)
                    self._wait_for_dashboard(page)
                    self._take_screenshot(page, "list_card_transactions_post_filter")

                # Extract list of transactions
                rows = page.locator(".card-transaction-row, .card-transaction-item, [class*='transaction'], [class*='card-view']").all()
                logger.info(f"Discovered {len(rows)} potential transaction item(s) on page.")

                for idx, row in enumerate(rows):
                    try:
                        text = row.text_content().strip()
                        # Deduplicate instructions/headers
                        if text and ("uber" in text.lower() or "office" in text.lower() or "starbucks" in text.lower() or "amount" in text.lower() or "amazon" in text.lower() or "$" in text.lower()):
                            transactions.append({
                                "index": idx,
                                "raw_text": text
                            })
                            logger.info(f"  Transaction {idx+1}: {text}")
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Error listing card transactions: {str(e)}")
            finally:
                browser.close()
            return transactions

    def get_card_transaction_details(self, merchant_or_id: str, card_type_filter: Optional[str] = None, headless: bool = True) -> Dict[str, Any]:
        """
        Navigates to the Expense page, locates the card transaction row matching merchant_or_id,
        clicks it to open the transaction details dialog, and extracts full details.
        Optionally selects a different card type filter first.
        """
        logger.info(f"Getting details for transaction matching '{merchant_or_id}' via browser (headless={headless}, filter={card_type_filter})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "get_transaction_details_pre")

                if card_type_filter:
                    logger.info(f"Selecting card filter view: {card_type_filter}...")
                    filter_btn = None
                    filter_selectors = [
                        lambda p: p.locator("#card-view-select"),
                        lambda p: p.get_by_role("combobox", name="Activity", exact=False),
                        lambda p: p.locator("select[id*='card']"),
                        lambda p: p.locator("button:has-text('All Corporate and Personal Cards')"),
                        lambda p: p.locator("button:has-text('All Purchasing Cards')")
                    ]
                    for idx, get_sel in enumerate(filter_selectors):
                        try:
                            loc = get_sel(page)
                            if loc.is_visible(timeout=2000):
                                filter_btn = loc
                                break
                        except Exception:
                            continue

                    if filter_btn:
                        tag_name = filter_btn.evaluate("el => el.tagName.toLowerCase()")
                        if tag_name == "select":
                            filter_btn.select_option(label=card_type_filter)
                        else:
                            filter_btn.click()
                            page.wait_for_timeout(1000)
                            option = page.get_by_role("option", name=card_type_filter, exact=False)
                            if not option.is_visible(timeout=1000):
                                option = page.locator(f"text={card_type_filter}").last
                            option.click()
                        page.wait_for_timeout(3000)
                        self._wait_for_dashboard(page)
                        self._take_screenshot(page, "get_transaction_details_post_filter")

                # Find the row containing merchant_or_id
                row = page.locator(".card-transaction-row, .card-transaction-item, [class*='transaction']").filter(has_text=merchant_or_id).first
                if row.count() == 0:
                    row = page.locator("*:has-text('" + merchant_or_id + "')").last

                row.click()
                page.wait_for_timeout(3000)
                self._take_screenshot(page, "get_transaction_details_open")

                # Extract details from modal
                merchant = "Unknown"
                date = "Unknown"
                amount = "Unknown"
                tx_id = "Unknown"
                card_prog = "Unknown"

                selectors_merchant = [lambda p: p.locator("#tx-merchant"), lambda p: p.locator("text=Merchant:").locator("..")]
                for get_sel in selectors_merchant:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            merchant = loc.first.text_content().replace("Merchant:", "").strip()
                            break
                    except Exception:
                        continue

                selectors_date = [lambda p: p.locator("#tx-date"), lambda p: p.locator("text=Date:").locator("..")]
                for get_sel in selectors_date:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            date = loc.first.text_content().replace("Date:", "").strip()
                            break
                    except Exception:
                        continue

                selectors_amount = [lambda p: p.locator("#tx-amount"), lambda p: p.locator("text=Amount:").locator("..")]
                for get_sel in selectors_amount:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            amount = loc.first.text_content().replace("Amount:", "").strip()
                            break
                    except Exception:
                        continue

                selectors_id = [lambda p: p.locator("#tx-id"), lambda p: p.locator("text=Transaction ID:").locator("..")]
                for get_sel in selectors_id:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            tx_id = loc.first.text_content().replace("Transaction ID:", "").strip()
                            break
                    except Exception:
                        continue

                selectors_prog = [lambda p: p.locator("#tx-program"), lambda p: p.locator("text=Card Program:").locator("..")]
                for get_sel in selectors_prog:
                    try:
                        loc = get_sel(page)
                        if loc.count() > 0:
                            card_prog = loc.first.text_content().replace("Card Program:", "").strip()
                            break
                    except Exception:
                        continue

                return {
                    "success": True,
                    "merchant": merchant,
                    "date": date,
                    "amount": amount,
                    "transaction_id": tx_id,
                    "card_program": card_prog
                }

            except Exception as e:
                self._take_screenshot(page, "get_transaction_details_error")
                raise e
            finally:
                browser.close()

    def add_expense_delegate(self, name_or_email: str, permissions: Optional[List[str]] = None, headless: bool = True) -> Dict[str, Any]:
        """
        Navigates to the Expense Delegates settings page, adds a delegate by name or email,
        sets their checkboxes based on permissions list, and saves the settings.
        """
        logger.info(f"Adding delegate '{name_or_email}' with permissions {permissions} via browser (headless={headless})...")
        if not permissions:
            permissions = ["prepare"] # Default permission

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                # Direct navigation to the edit delegates page
                delegates_url = f"{self.base_url}/profile/editdelegates.asp?ObjectType=1"
                logger.info(f"Navigating to Concur Expense Delegates: {delegates_url}")
                page.goto(delegates_url, timeout=30000)
                page.wait_for_load_state("load")
                page.wait_for_timeout(3000)
                self._take_screenshot(page, "add_delegate_pre")

                # Step 1: Click 'Add' or search delegate button
                add_btn = None
                add_selectors = [
                    lambda p: p.locator("#add-delegate-btn"),
                    lambda p: p.get_by_role("button", name="Add", exact=True),
                    lambda p: p.get_by_role("button", name="Add Delegate", exact=False),
                    lambda p: p.locator("button:has-text('Add')")
                ]
                for idx, get_sel in enumerate(add_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            add_btn = loc
                            break
                    except Exception:
                        continue

                if not add_btn:
                    raise RuntimeError("Could not locate 'Add' delegate button.")

                add_btn.click()
                page.wait_for_timeout(1000)

                # Step 2: Fill in the search input
                search_input = None
                search_selectors = [
                    lambda p: p.locator("#delegate-search-input"),
                    lambda p: p.get_by_role("textbox", name="search", exact=False),
                    lambda p: p.locator("input[placeholder*='name']"),
                    lambda p: p.locator("input[placeholder*='delegate']")
                ]
                for idx, get_sel in enumerate(search_selectors):
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            search_input = loc
                            break
                    except Exception:
                        continue

                if not search_input:
                    raise RuntimeError("Could not locate delegate search input field.")

                search_input.fill(name_or_email)
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "add_delegate_searching")

                # Click the matched suggestion item
                suggestion = None
                suggestion_selectors = [
                    lambda p: p.locator("#suggestion-john") if "john" in name_or_email.lower() else p.locator("#suggestion-jane"),
                    lambda p: p.locator(".suggestion-item").first,
                    lambda p: p.locator("[class*='suggestion']").first,
                    lambda p: page.get_by_role("listitem").first
                ]
                for get_sel in suggestion_selectors:
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            suggestion = loc
                            break
                    except Exception:
                        continue

                if not suggestion:
                    raise RuntimeError(f"Could not locate autocomplete suggestion for '{name_or_email}'.")

                suggestion.click()
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "add_delegate_added_to_table")

                # Step 3: Find delegate row and set permission checkboxes
                row = page.locator(".delegate-row, tr").filter(has_text=name_or_email).first
                if row.count() == 0:
                    row = page.locator("tr:has-text('" + name_or_email + "')").first

                if row.count() == 0:
                    raise RuntimeError(f"Could not find delegate row for '{name_or_email}' in table.")

                # Set checkboxes
                # Usually there are columns: Prepare, Submit, Approve, Receives Emails
                if "prepare" in permissions:
                    chk_prepare = row.locator(".perm-prepare, input[type='checkbox']").nth(1) # nth(0) is row selection
                    if not chk_prepare.is_checked():
                        chk_prepare.check()
                        logger.info("Checked 'Can Prepare' permission.")
                
                if "submit" in permissions:
                    chk_submit = row.locator(".perm-submit, input[type='checkbox']").nth(2)
                    if not chk_submit.is_checked():
                        chk_submit.check()
                        logger.info("Checked 'Can Submit Reports' permission.")

                if "approve" in permissions:
                    chk_approve = row.locator(".perm-approve, input[type='checkbox']").nth(3)
                    if not chk_approve.is_checked():
                        chk_approve.check()
                        logger.info("Checked 'Can Approve' permission.")

                self._take_screenshot(page, "add_delegate_permissions_checked")

                # Click Save settings button
                save_btn = None
                save_selectors = [
                    lambda p: p.locator("#save-delegates-btn"),
                    lambda p: p.get_by_role("button", name="Save", exact=True),
                    lambda p: p.locator("button:has-text('Save')")
                ]
                for get_sel in save_selectors:
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            save_btn = loc
                            break
                    except Exception:
                        continue

                if not save_btn:
                    raise RuntimeError("Could not locate Save settings button on Delegates page.")

                page.on("dialog", lambda dialog: dialog.accept())
                save_btn.click()
                page.wait_for_timeout(3000)
                self._take_screenshot(page, "add_delegate_saved")

                logger.info(f"Successfully added delegate '{name_or_email}'!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "add_delegate_error")
                raise e
            finally:
                browser.close()

    def remove_expense_delegate(self, name_or_email: str, headless: bool = True) -> Dict[str, Any]:
        """
        Navigates to the Expense Delegates settings page, locates a delegate by name or email,
        selects them, clicks the Delete button, and saves the settings.
        """
        logger.info(f"Removing delegate '{name_or_email}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                delegates_url = f"{self.base_url}/profile/editdelegates.asp?ObjectType=1"
                logger.info(f"Navigating to Concur Expense Delegates: {delegates_url}")
                page.goto(delegates_url, timeout=30000)
                page.wait_for_load_state("load")
                page.wait_for_timeout(3000)
                self._take_screenshot(page, "remove_delegate_pre")

                # Step 1: Find the delegate row
                row = page.locator(".delegate-row, tr").filter(has_text=name_or_email).first
                if row.count() == 0:
                    row = page.locator("tr:has-text('" + name_or_email + "')").first

                if row.count() == 0:
                    raise FileNotFoundError(f"No delegate named '{name_or_email}' found to remove.")

                # Step 2: Check the row selection checkbox (first column)
                select_chk = row.locator(".delegate-select-chk, input[type='checkbox']").first
                select_chk.check()
                logger.info(f"Checked delegate selection checkbox for '{name_or_email}'.")
                page.wait_for_timeout(1000)
                self._take_screenshot(page, "remove_delegate_selected")

                # Step 3: Click 'Delete' button
                delete_btn = None
                delete_selectors = [
                    lambda p: p.locator("#delete-delegate-btn"),
                    lambda p: p.get_by_role("button", name="Delete", exact=True),
                    lambda p: p.locator("button:has-text('Delete')")
                ]
                for get_sel in delete_selectors:
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            delete_btn = loc
                            break
                    except Exception:
                        continue

                if not delete_btn:
                    raise RuntimeError("Could not locate 'Delete' delegate button.")

                page.on("dialog", lambda dialog: dialog.accept())
                delete_btn.click()
                page.wait_for_timeout(2000)
                self._take_screenshot(page, "remove_delegate_clicked_delete")

                # Step 4: Click 'Save' to apply deletion
                save_btn = None
                save_selectors = [
                    lambda p: p.locator("#save-delegates-btn"),
                    lambda p: p.get_by_role("button", name="Save", exact=True),
                    lambda p: p.locator("button:has-text('Save')")
                ]
                for get_sel in save_selectors:
                    try:
                        loc = get_sel(page)
                        if loc.is_visible(timeout=2000):
                            save_btn = loc
                            break
                    except Exception:
                        continue

                if not save_btn:
                    raise RuntimeError("Could not locate Save settings button.")

                save_btn.click()
                page.wait_for_timeout(3000)
                self._take_screenshot(page, "remove_delegate_saved")

                logger.info(f"Successfully removed delegate '{name_or_email}'!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "remove_delegate_error")
                raise e
            finally:
                browser.close()

    def reconcile_report(self, report_name: str, reconciliation_rules: Dict[str, Dict[str, str]], headless: bool = True) -> Dict[str, Any]:
        """
        Automates month-end reconciliation: opens the report details view,
        iterates over all transaction rows, matches them with reconciliation rules,
        inputs Expense Type, Business Purpose, Comment, and Allocation Codes,
        saves each row, and submits the entire report when all are reconciled.
        """
        logger.info(f"Starting month-end reconciliation for report '{report_name}' via browser (headless={headless})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "reconcile_start")

                # Locate and open the report
                card = page.locator(".report-tile, .report-card").filter(has_text=report_name).first
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=report_name).first
                if card.count() == 0:
                    raise FileNotFoundError(f"Could not find report '{report_name}'.")

                card.click()
                page.wait_for_timeout(3000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "reconcile_opened_report")

                # Iterate through reconciliation rows
                rows = page.locator(".transaction-recon-row, .detail-row").all()
                logger.info(f"Discovered {len(rows)} line item(s) to reconcile.")

                for idx, row in enumerate(rows):
                    merchant_elem = row.locator(".recon-merchant, strong").first
                    if merchant_elem.count() == 0:
                        continue
                    
                    raw_text = merchant_elem.text_content().strip()
                    logger.info(f"Checking line item {idx+1}: '{raw_text}'...")

                    # Match with rule key (case insensitive)
                    matched_rule = None
                    for key, rule in reconciliation_rules.items():
                        if key.lower() in raw_text.lower():
                            matched_rule = rule
                            break

                    if not matched_rule:
                        logger.warning(f"No reconciliation rule matched for '{raw_text}'. Skipping.")
                        continue

                    logger.info(f"Reconciling item '{raw_text}' using rule: {matched_rule}")
                    
                    # Fill inputs
                    sel_type = row.locator("select.recon-type")
                    if sel_type.count() > 0:
                        sel_type.select_option(label=matched_rule.get("expense_type", ""))
                    
                    inp_purpose = row.locator("input.recon-purpose")
                    if inp_purpose.count() > 0:
                        inp_purpose.fill(matched_rule.get("business_purpose", ""))
                    
                    inp_comment = row.locator("input.recon-comment")
                    if inp_comment.count() > 0:
                        inp_comment.fill(matched_rule.get("comment", ""))
                    
                    inp_alloc = row.locator("input.recon-allocation")
                    if inp_alloc.count() > 0:
                        inp_alloc.fill(matched_rule.get("allocation_code", ""))
                    
                    # Save this transaction
                    save_btn = row.locator("button.recon-save-btn").first
                    if save_btn.count() > 0:
                        save_btn.click()
                        page.wait_for_timeout(2000)
                        logger.info("Saved transaction reconciliation fields.")

                self._take_screenshot(page, "reconcile_all_saved")

                # Click Submit Report
                submit_btn = page.locator("#submit-entire-report-btn").first
                if submit_btn.count() > 0 and submit_btn.is_enabled():
                    # Register dialog accept handler
                    page.on("dialog", lambda dialog: dialog.accept())
                    submit_btn.click()
                    page.wait_for_timeout(3000)
                    self._take_screenshot(page, "reconcile_submitted")
                    logger.info("Report successfully submitted!")
                    return {"success": True}
                else:
                    raise RuntimeError("Submit Report button is missing or not enabled. Check if all transactions are reconciled.")

            except Exception as e:
                self._take_screenshot(page, "reconcile_error")
                raise e
            finally:
                browser.close()

    def attach_receipt_to_transaction(self, report_name: str, merchant_or_id: str, receipt_file_path: str, headless: bool = True) -> Dict[str, Any]:
        """
        Navigates to the report details view, locates the transaction row matching merchant_or_id,
        and uploads a local receipt file (PDF/image) to match/associate it with the transaction.
        """
        logger.info(f"Attaching receipt '{receipt_file_path}' to transaction matching '{merchant_or_id}' in report '{report_name}'...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file, viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                page.goto(f"{self.base_url}/nui/expense", timeout=30000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "attach_receipt_start")

                # Locate and open the report
                card = page.locator(".report-tile, .report-card").filter(has_text=report_name).first
                if card.count() == 0:
                    card = page.locator(".sapMCard, .sapMLIB").filter(has_text=report_name).first
                if card.count() == 0:
                    raise FileNotFoundError(f"Could not find report '{report_name}'.")

                card.click()
                page.wait_for_timeout(3000)
                self._wait_for_dashboard(page)
                self._take_screenshot(page, "attach_receipt_report_opened")

                # Find the transaction row matching merchant_or_id
                row = page.locator(".transaction-recon-row, .detail-row").filter(has_text=merchant_or_id).first
                if row.count() == 0:
                    raise FileNotFoundError(f"Could not find transaction matching '{merchant_or_id}'.")

                # Locate file input element and upload the file
                input_file = row.locator("input.recon-receipt-file")
                if input_file.count() == 0:
                    raise RuntimeError("Could not find file input for receipt upload.")

                input_file.set_input_files(receipt_file_path)
                page.wait_for_timeout(3000)

                self._take_screenshot(page, "attach_receipt_completed")
                logger.info(f"Successfully attached receipt '{receipt_file_path}' to transaction!")
                return {"success": True}

            except Exception as e:
                self._take_screenshot(page, "attach_receipt_error")
                raise e
            finally:
                browser.close()
