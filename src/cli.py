#!/usr/bin/env python3
import os
import sys
import argparse
import json
import threading
import itertools
import time
import logging
import signal
from datetime import datetime
from dotenv import load_dotenv

# Configure signal handling for graceful exit
def signal_handler(sig, frame):
    logging.info(f"Signal {sig} received. Cleaning up and exiting...")
    sys.exit(0)

signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Add current directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.client import ConcurClient, ConcurError
from src.browser_client import ConcurBrowserClient, ConcurSessionExpiredError


class Spinner:
    """A simple terminal spinner for long-running tasks."""
    def __init__(self, message="In progress...", delay=0.1):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.message = message
        self.running = False
        self.thread = None

    def spin(self):
        while self.running:
            sys.stderr.write(f"\r{next(self.spinner)} {self.message}")
            sys.stderr.flush()
            time.sleep(self.delay)
        sys.stderr.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stderr.flush()

    def __enter__(self):
        self.running = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.running = False
        if self.thread:
            self.thread.join()


def run_tests():
    # Load .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="SAP Concur API & Browser Access Tool")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed log messages on stderr")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format (default: json for queries)")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

    # Command: api-test
    subparsers.add_parser("api-test", help="Run the API client test suite")

    # Command: login
    subparsers.add_parser("login", help="Launch a headed browser for manual authentication and save session state")

    # Command: check-session
    subparsers.add_parser("check-session", help="Check whether the currently saved browser session state is valid and active")

    # Command: query
    subparsers.add_parser("query", help="Query and list current reports and available receipts via browser automation")

    # Command: create-report
    p_create = subparsers.add_parser("create-report", help="Create a draft expense report using browser automation")
    p_create.add_argument("--name", type=str, help="Name of report to create")
    p_create.add_argument("--purpose", type=str, help="Business purpose of report to create")
    p_create.add_argument("--comment", type=str, help="Additional comment for report to create")
    p_create.add_argument("--headed", action="store_true", help="Run browser visibly (headed) rather than headlessly")

    # Command: delete-report
    p_del = subparsers.add_parser("delete-report", help="Delete an expense report by name using browser automation")
    p_del.add_argument("report_name", type=str, help="Name of report to delete")

    # Command: delete-all-reports
    subparsers.add_parser("delete-all-reports", help="Delete all draft expense reports via browser")

    # Command: delete-all-receipts
    subparsers.add_parser("delete-all-receipts", help="Delete all available receipts via browser")

    # Command: nuke
    subparsers.add_parser("nuke", help="Delete all draft expense reports AND all available receipts via browser")

    # Command: list-old-reports
    p_list_old = subparsers.add_parser("list-old-reports", help="Query and list historical/old expense reports")
    p_list_old.add_argument("--filter-view", type=str, default="Last 90 Days", help="Dropdown filter (default: 'Last 90 Days')")

    # Command: report-details
    p_rep_det = subparsers.add_parser("report-details", help="Get detailed view of an expense report by name")
    p_rep_det.add_argument("report_name", type=str, help="Name of the expense report")
    p_rep_det.add_argument("--filter-view", type=str, help="Dropdown filter to look inside (default: current view)")

    # Command: list-cards
    p_list_cards = subparsers.add_parser("list-cards", help="Query and list credit card transactions")
    p_list_cards.add_argument("--filter-view", type=str, default="All Corporate and Personal Cards", help="Dropdown filter (default: 'All Corporate and Personal Cards')")
 
    # Command: allocations
    p_alloc = subparsers.add_parser("allocations", help="Query allocation details (cost centers) for a report")
    p_alloc.add_argument("report_name", type=str, help="Name of the expense report")
    p_alloc.add_argument("--filter-view", type=str, help="Dropdown filter to look inside")

    # Command: card-details
    p_card_det = subparsers.add_parser("card-details", help="Get detailed view of a card transaction by merchant or ID")
    p_card_det.add_argument("merchant_or_id", type=str, help="Merchant name or transaction ID")
    p_card_det.add_argument("--filter-view", type=str, default="All Corporate and Personal Cards", help="Filter view for cards (default: 'All Corporate and Personal Cards')")

    # Command: add-delegate
    p_add_del = subparsers.add_parser("add-delegate", help="Add a new expense delegate by name or email")
    p_add_del.add_argument("name_or_email", type=str, help="Name or email of delegate")
    p_add_del.add_argument("--delegate-perms", nargs="+", default=["prepare"], help="Permissions: prepare, submit, approve")

    # Command: remove-delegate
    p_rem_del = subparsers.add_parser("remove-delegate", help="Remove an expense delegate by name or email")
    p_rem_del.add_argument("name_or_email", type=str, help="Name or email of delegate")

    # Command: reconcile
    p_recon = subparsers.add_parser("reconcile", help="Reconcile transactions of an expense report by name")
    p_recon.add_argument("report_name", type=str, help="Name of draft report to reconcile")
    p_recon.add_argument("--reconcile-rules", type=str, help="Path to a JSON file containing reconciliation rules")
    p_recon.add_argument("--submit", action="store_true", help="Submit the report after reconciling (default: False, review-only)")

    # Command: attach-receipt
    p_attach = subparsers.add_parser("attach-receipt", help="Attach a receipt file to a transaction in a report")
    p_attach.add_argument("report_name", type=str, help="Name of report containing the transaction")
    p_attach.add_argument("--merchant", type=str, required=True, help="Merchant name or transaction ID to match receipt against")
    p_attach.add_argument("--receipt-path", type=str, required=True, help="Local file path of the receipt")

    args = parser.parse_args()

    # Configure logging based on verbosity
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True
    )
    # Ensure all loggers use stderr and respect the level
    for name in logging.root.manager.loggerDict:
        l = logging.getLogger(name)
        l.setLevel(log_level)
        l.propagate = True

    def output_result(data, text_summary=None):
        if args.output == "json":
            print(json.dumps(data, indent=2))
        elif text_summary:
            print(text_summary)
        else:
            print(json.dumps(data, indent=2))

    # ----------------------------------------------------
    # Flow A: Live API Client Tester
    # ----------------------------------------------------
    if args.command == "api-test":
        client_id = os.getenv("CONCUR_CLIENT_ID")
        client_secret = os.getenv("CONCUR_CLIENT_SECRET")
        token_url = os.getenv("CONCUR_TOKEN_URL", "https://us.api.concursolutions.com/oauth2/v0/token")
        base_url = os.getenv("CONCUR_BASE_URL", "https://us.api.concursolutions.com")
        user_login_id = os.getenv("CONCUR_USER_LOGIN_ID")

        if args.output == "text":
            print("=" * 60)
            print("           SAP Concur API Access Tester Script")
            print("=" * 60)

        missing_vars = []
        if not client_id or client_id == "your_client_id_here":
            missing_vars.append("CONCUR_CLIENT_ID")
        if not client_secret or client_secret == "your_client_secret_here":
            missing_vars.append("CONCUR_CLIENT_SECRET")
        if not user_login_id or user_login_id == "user@example.com":
            missing_vars.append("CONCUR_USER_LOGIN_ID")

        if missing_vars:
            if args.output == "text":
                print("\n[!] Configuration Missing.")
                print("Please configure your credentials in the '.env' file.")
                print("Required variables missing:")
                for var in missing_vars:
                    print(f"  - {var}")
                print("\nYou can copy '.env.example' to '.env' and update it:")
                print("  cp .env.example .env")
                print("=" * 60)
            else:
                print(json.dumps({"status": "error", "missing_vars": missing_vars}))
            sys.exit(1)

        if args.output == "text":
            print(f"[*] Base URL:  {base_url}")
            print(f"[*] Token URL: {token_url}")
            print(f"[*] Test User: {user_login_id}")
            print(f"[*] Client ID: {client_id[:6]}... (truncated)")
            print("-" * 60)

        try:
            client = ConcurClient(
                client_id=client_id,
                client_secret=client_secret,
                token_url=token_url,
                base_url=base_url
            )

            if args.output == "text": print("\n[Phase 1] Attempting authentication...")
            token = client.get_token()
            if args.output == "text":
                print("[SUCCESS] Authentication succeeded!")
                print(f"          Access token acquired (starts with: '{token[:12]}...')")

            if args.output == "text": print("\n[Phase 2] Attempting to list existing reports...")
            reports = client.list_reports(user_login_id=user_login_id, limit=5)
            if args.output == "text":
                print("[SUCCESS] Successfully connected to report list API!")
                print(f"          Retrieved {len(reports)} recent report(s):")
                for idx, report in enumerate(reports, 1):
                    report_name_val = report.get("Name", "Unnamed Report")
                    report_id = report.get("ReportID") or report.get("ID") or "N/A"
                    report_status = report.get("ReportStatus") or report.get("ApprovalStatus") or "N/A"
                    total = report.get("Total", 0.0)
                    currency = report.get("CurrencyCode", "")
                    print(f"            {idx}. [{report_id}] {report_name_val} - Status: {report_status} ({total} {currency})")

            if args.output == "text": print("\n[Phase 3] Attempting to create draft report...")
            report_name_val = f"API Test Draft {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            purpose = "Validating programmatic creation of draft reports"
            comment = "Created automatically via SAP Concur Python API Access Tester"

            created_report = client.create_draft_report(
                user_login_id=user_login_id,
                name=report_name_val,
                purpose=purpose,
                comment=comment
            )

            if args.output == "text":
                print("[SUCCESS] Programmatic report creation succeeded!")
                print(f"          New Report Name: {created_report.get('Name')}")
                print(f"          Report ID:       {created_report.get('ReportID') or created_report.get('ID')}")
                print(f"          Status:          {created_report.get('ReportStatus', 'Draft / Not Submitted')}")
                print("-" * 60)
                print("\n[SUMMARY] All API tests passed! You have full read/write access.")
            else:
                print(json.dumps({
                    "status": "success",
                    "reports_retrieved": len(reports),
                    "created_report": created_report
                }, indent=2))

        except ConcurError as e:
            if args.output == "text":
                print(f"\n[ERROR] An API error occurred during testing: {str(e)}")
            else:
                print(json.dumps({"status": "error", "type": "ConcurError", "message": str(e)}))
            sys.exit(1)
        except Exception as e:
            if args.output == "text":
                print(f"\n[UNEXPECTED ERROR] An unexpected error occurred: {str(e)}")
            else:
                print(json.dumps({"status": "error", "type": "UnexpectedError", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow B: Browser Manual Login Session Save
    # ----------------------------------------------------
    elif args.command == "login":
        if args.output == "text":
            print("=" * 60)
            print("       SAP Concur Browser Authentication Session Setup")
            print("=" * 60)
        
        try:
            browser_client = ConcurBrowserClient()
            browser_client.run_headed_login()
            
            result = {"status": "success", "message": "Manual login setup complete."}
            summary = "\n[SUCCESS] Setup complete. You can now run browser-based automations.\nTo run the draft creator, use: python3 src/cli.py create-report"
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to run manual login setup: {str(e)}")
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow B.2: Browser Check Session Validity
    # ----------------------------------------------------
    elif args.command == "check-session":
        if args.output == "text":
            print("=" * 60)
            print("     SAP Concur Browser Session Status Check")
            print("=" * 60)
        try:
            with Spinner("Checking browser session..."):
                browser_client = ConcurBrowserClient()
                result = browser_client.check_session_validity(headless=True)
            
            if result.get("authenticated"):
                summary = f"\n[SUCCESS] Authentication is active and valid!\nDetail: {result.get('reason')}\n" + "=" * 60
                output_result(result, summary)
            else:
                summary = f"\n[EXPIRED/NOT FOUND] Authentication is NOT valid.\nDetail: {result.get('reason')}\n" + "=" * 60
                output_result(result, summary)
                sys.exit(2)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to execute session status check: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow C: Browser Query (List Reports + List Receipts)
    # ----------------------------------------------------
    elif args.command == "query":
        if args.output == "text":
            print("=" * 60)
            print("     SAP Concur Browser-Based Expense & Receipt Query")
            print("=" * 60)
        
        try:
            with Spinner("Querying reports and receipts..."):
                browser_client = ConcurBrowserClient()
                reports = browser_client.list_reports(headless=True)
                receipts = browser_client.list_available_receipts(headless=True)
            
            result = {
                "reports": reports,
                "receipts": receipts
            }
            
            summary = "\n[*] Querying active expense reports...\n"
            summary += f"[SUCCESS] Discovered {len(reports)} expense report(s):\n"
            for idx, r in enumerate(reports, 1):
                summary += f"  {idx}. {r.get('name')} (Purpose: {r.get('purpose', 'None')})\n"
            
            summary += "\n[*] Querying available receipts gallery...\n"
            summary += f"[SUCCESS] Discovered {len(receipts)} uploaded receipt(s):\n"
            for idx, name in enumerate(receipts, 1):
                summary += f"  {idx}. {name}\n"
            summary += "\n" + "=" * 60

            output_result(result, summary)
        except ConcurSessionExpiredError as e:
            print(json.dumps({"status": "error", "message": str(e)}))
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Browser query failed: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow D: Browser Draft Report Creation (Headless/Headed)
    # ----------------------------------------------------
    elif args.command == "create-report":
        if args.output == "text":
            print("=" * 60)
            print("     SAP Concur Browser-Based Draft Report Creation")
            print("=" * 60)
        
        headless = not args.headed
        report_name_val = args.name or f"Browser Test Draft {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        purpose = args.purpose or "Validating browser-based creation of draft reports"
        comment = args.comment or "Created automatically via SAP Concur Python Playwright Tester"

        try:
            with Spinner(f"Creating report '{report_name_val}'..."):
                browser_client = ConcurBrowserClient()
                result = browser_client.create_draft_report(
                    name=report_name_val,
                    purpose=purpose,
                    comment=comment,
                    headless=headless
                )
            
            summary = "\n[SUCCESS] Browser automation completed successfully!\n"
            summary += f"          Report Created: {result.get('report_name')}\n"
            summary += f"          Screenshots folder: {result.get('screenshot_folder')}\n"
            summary += f"          Notes:          {result.get('notes')}\n" + "=" * 60
            
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Browser automation failed: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow E: Browser Delete Report
    # ----------------------------------------------------
    elif args.command == "delete-report":
        report_name_val = args.report_name
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Browser-Based Delete Report: '{report_name_val}'")
            print("=" * 60)
        
        try:
            with Spinner(f"Deleting report '{report_name_val}'..."):
                browser_client = ConcurBrowserClient()
                browser_client.delete_report(name=report_name_val, headless=True)
            
            result = {"status": "success", "report_name": report_name_val}
            summary = f"\n[SUCCESS] Successfully deleted report: '{report_name_val}'\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to delete report: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow F: Delete All Reports
    # ----------------------------------------------------
    elif args.command == "delete-all-reports":
        if args.output == "text":
            print("=" * 60)
            print("   SAP Concur Browser-Based Delete All Reports")
            print("=" * 60)
        try:
            with Spinner("Deleting all reports..."):
                browser_client = ConcurBrowserClient()
                reports = browser_client.list_reports(headless=True)
                for r in reports:
                    name = r.get("name")
                    browser_client.delete_report(name=name, headless=True)
            
            result = {"status": "success", "count": len(reports)}
            summary = f"\n[SUCCESS] All {len(reports)} reports deleted.\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to delete all reports: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow G: Delete All Receipts
    # ----------------------------------------------------
    elif args.command == "delete-all-receipts":
        if args.output == "text":
            print("=" * 60)
            print("   SAP Concur Browser-Based Delete All Receipts")
            print("=" * 60)
        try:
            with Spinner("Deleting all receipts..."):
                browser_client = ConcurBrowserClient()
                receipts = browser_client.list_available_receipts(headless=True)
                for r_name in receipts:
                    browser_client.delete_available_receipt(receipt_name=r_name, headless=True)
            
            result = {"status": "success", "count": len(receipts)}
            summary = f"\n[SUCCESS] All {len(receipts)} available receipts deleted.\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to delete all receipts: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow H: Delete All Reports AND Receipts (Nuke)
    # ----------------------------------------------------
    elif args.command == "nuke":
        if args.output == "text":
            print("=" * 60)
            print("   SAP Concur Browser-Based Nuke (Delete All Reports & Receipts)")
            print("=" * 60)
        try:
            with Spinner("Nuking all reports and receipts..."):
                browser_client = ConcurBrowserClient()
                reports = browser_client.list_reports(headless=True)
                for r in reports:
                    browser_client.delete_report(name=r.get("name"), headless=True)
                receipts = browser_client.list_available_receipts(headless=True)
                for r_name in receipts:
                    browser_client.delete_available_receipt(receipt_name=r_name, headless=True)
            
            result = {"status": "success", "reports_deleted": len(reports), "receipts_deleted": len(receipts)}
            summary = f"\n[SUCCESS] All {len(reports)} reports and {len(receipts)} receipts deleted.\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to delete all items: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow I: Query Historical (Old) Reports
    # ----------------------------------------------------
    elif args.command == "list-old-reports":
        filter_val = args.filter_view
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Browser-Based Historical Reports (Filter: {filter_val})")
            print("=" * 60)
        try:
            with Spinner(f"Querying historical reports ({filter_val})..."):
                browser_client = ConcurBrowserClient()
                reports = browser_client.list_reports(filter_view=filter_val, headless=True)
            
            summary = f"[SUCCESS] Discovered {len(reports)} historical report(s):\n"
            for idx, r in enumerate(reports, 1):
                summary += f"  {idx}. {r.get('name')} (Purpose: {r.get('purpose', 'None')})\n"
            summary += "=" * 60
            
            output_result(reports, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Historical reports query failed: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow J: Report Details of a Report
    # ----------------------------------------------------
    elif args.command == "report-details":
        report_name_val = args.report_name
        filter_val = args.filter_view
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Report Details: '{report_name_val}'")
            print("=" * 60)
        try:
            with Spinner(f"Fetching details for '{report_name_val}'..."):
                browser_client = ConcurBrowserClient()
                details = browser_client.get_report_details(name=report_name_val, filter_view=filter_val, headless=True)
            
            summary = "[SUCCESS] Details retrieved:\n"
            summary += f"  Name:     {details.get('report_name')}\n"
            summary += f"  Number:   {details.get('report_number')}\n"
            summary += f"  Purpose:  {details.get('purpose')}\n"
            summary += f"  Comment:  {details.get('comment')}\n"
            summary += f"  Expenses: ({len(details.get('expenses'))} items)\n"
            for item in details.get('expenses'):
                summary += f"    - {item.get('raw_text')}\n"
            summary += "=" * 60
            
            output_result(details, summary)
        except ConcurSessionExpiredError as e:
            print(json.dumps({"status": "error", "message": str(e)}))
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to get report details: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)
 
    # ----------------------------------------------------
    # Flow J2: Report Allocations
    # ----------------------------------------------------
    elif args.command == "allocations":
        try:
            with Spinner(f"Fetching allocations for '{args.report_name}'..."):
                browser_client = ConcurBrowserClient()
                data = browser_client.get_report_allocations(args.report_name, filter_view=args.filter_view, headless=True)
                print(json.dumps(data, indent=2))
        except ConcurSessionExpiredError as e:
            print(json.dumps({"status": "error", "message": str(e)}))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}))

    # ----------------------------------------------------
    # Flow K: List Card Transactions
    # ----------------------------------------------------
    elif args.command == "list-cards":
        filter_val = args.filter_view
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Card Transactions (Filter: {filter_val})")
            print("=" * 60)
        try:
            with Spinner(f"Querying card transactions ({filter_val})..."):
                browser_client = ConcurBrowserClient()
                txs = browser_client.list_card_transactions(card_type_filter=filter_val, headless=True)
            
            summary = f"[SUCCESS] Discovered {len(txs)} transaction(s):\n"
            for idx, t in enumerate(txs, 1):
                summary += f"  {idx}. {t.get('raw_text')}\n"
            summary += "=" * 60
            
            output_result(txs, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Listing card transactions failed: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow L: Get Card Transaction Details
    # ----------------------------------------------------
    elif args.command == "card-details":
        tx_id = args.merchant_or_id
        filter_val = args.filter_view
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Card Transaction Details: '{tx_id}'")
            print("=" * 60)
        try:
            with Spinner(f"Fetching transaction details for '{tx_id}'..."):
                browser_client = ConcurBrowserClient()
                details = browser_client.get_card_transaction_details(merchant_or_id=tx_id, card_type_filter=filter_val, headless=True)
            
            summary = "[SUCCESS] Transaction details:\n"
            summary += f"  Merchant:     {details.get('merchant')}\n"
            summary += f"  Date:         {details.get('date')}\n"
            summary += f"  Amount:       {details.get('amount')}\n"
            summary += f"  ID:           {details.get('transaction_id')}\n"
            summary += f"  Card Program: {details.get('card_program')}\n"
            summary += "=" * 60
            
            output_result(details, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to get transaction details: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow M: Add Delegate
    # ----------------------------------------------------
    elif args.command == "add-delegate":
        name = args.name_or_email
        perms = args.delegate_perms
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Add Expense Delegate: '{name}'")
            print(f"     Permissions: {perms}")
            print("=" * 60)
        try:
            with Spinner(f"Adding delegate '{name}'..."):
                browser_client = ConcurBrowserClient()
                browser_client.add_expense_delegate(name_or_email=name, permissions=perms, headless=True)
            
            result = {"status": "success", "name": name, "permissions": perms}
            summary = f"\n[SUCCESS] Delegate '{name}' added successfully!\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to add delegate: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow N: Remove Delegate
    # ----------------------------------------------------
    elif args.command == "remove-delegate":
        name = args.name_or_email
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Remove Expense Delegate: '{name}'")
            print("=" * 60)
        try:
            with Spinner(f"Removing delegate '{name}'..."):
                browser_client = ConcurBrowserClient()
                browser_client.remove_expense_delegate(name_or_email=name, headless=True)
            
            result = {"status": "success", "name": name}
            summary = f"\n[SUCCESS] Delegate '{name}' removed successfully!\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to remove delegate: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow O: Reconcile Report Transactions
    # ----------------------------------------------------
    elif args.command == "reconcile":
        report_name_val = args.report_name
        rules_path = args.reconcile_rules
        
        reconciliation_rules = {
            "Uber": {
                "expense_type": "Ground Transportation",
                "business_purpose": "Client dinner ride",
                "comment": "Uber Ride",
                "allocation_code": "COST-01"
            },
            "Office Depot": {
                "expense_type": "Office Supplies",
                "business_purpose": "Team materials",
                "comment": "Pens and notebooks",
                "allocation_code": "COST-02"
            }
        }
        
        if rules_path:
            try:
                with open(rules_path, "r") as f:
                    reconciliation_rules = json.load(f)
            except Exception as e:
                if args.output == "text":
                    print(f"[ERROR] Failed to load reconciliation rules JSON from '{rules_path}': {str(e)}")
                else:
                    print(json.dumps({"status": "error", "message": f"Failed to load rules: {str(e)}"}))
                sys.exit(1)
                
        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Report Reconciliation: '{report_name_val}'")
            print("=" * 60)
        try:
            with Spinner(f"Reconciling report '{report_name_val}'..."):
                browser_client = ConcurBrowserClient()
                res = browser_client.reconcile_report(
                    report_name=report_name_val,
                    reconciliation_rules=reconciliation_rules,
                    headless=True,
                    submit=args.submit
                )
            
            if args.submit:
                summary = f"\n[SUCCESS] Report '{report_name_val}' reconciled and submitted successfully!\n" + "=" * 60
            else:
                summary = f"\n[SUCCESS] Report '{report_name_val}' reconciled successfully! (Draft mode, not submitted)\n" + "=" * 60
            
            output_result(res, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Reconciliation failed: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)

    # ----------------------------------------------------
    # Flow P: Attach Receipt to Transaction
    # ----------------------------------------------------
    elif args.command == "attach-receipt":
        report_name_val = args.report_name
        merchant = args.merchant
        receipt_path = args.receipt_path

        if args.output == "text":
            print("=" * 60)
            print(f"     SAP Concur Attach Receipt: '{receipt_path}' to '{merchant}' in '{report_name_val}'")
            print("=" * 60)
        try:
            with Spinner(f"Attaching receipt to '{merchant}'..."):
                browser_client = ConcurBrowserClient()
                browser_client.attach_receipt_to_transaction(
                    report_name=report_name_val,
                    merchant_or_id=merchant,
                    receipt_file_path=receipt_path,
                    headless=True
                )
            
            result = {"status": "success", "merchant": merchant, "receipt": receipt_path}
            summary = f"\n[SUCCESS] Receipt '{receipt_path}' attached successfully!\n" + "=" * 60
            output_result(result, summary)
        except Exception as e:
            if args.output == "text":
                print(f"\n[ERROR] Failed to attach receipt: {str(e)}\n" + "=" * 60)
            else:
                print(json.dumps({"status": "error", "message": str(e)}))
            sys.exit(1)


if __name__ == "__main__":
    run_tests()
