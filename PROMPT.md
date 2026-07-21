This project implements read operations of reports and allocations using Playwright against SAP Concur.

The following is the result of an update-transaction subcommand and then an inspection of the modified record with the report-details subcommand.

Task is complete when the updated transaction reports success and the report-details reflects the change accurately (with the inverse being true; a failure to update should then have report-details return something other than the requested update).

➜  ccworks git:(main) ✗ ./ccworks update-transaction "Statement Report 06/16 - 07/31" 1 --type "Software (OIT use only)"
- Updating 1 transaction(s) in report 'Statement Report 06/16 - 07/31'...2026-07-03 21:21:40,241 - ERROR -   [1] Failed to update expense type: Locator.input_value: Error: Node is not an <input>, <textarea> or <select> element
Call log:
  - waiting for locator("#sapcnqr-layout-side-panel-elements, .sapcnqr-layout-side-panel__elements, .ere__dynamic-main-content").filter(visible=True).first.locator("input[id*='type']:not([id*='header']), [data-nuiexp*='type']:not([data-nuiexp*='header']), .sapMInputBaseInner[id*='type']:not([id*='header']), select[id*='type']").first

{                                                                        
  "success": true,
  "report_name": "Statement Report 06/16 - 07/31",
  "results": [
    {
      "index": 1,
      "success": true,
      "partial_success": false,
      "validation_error": null
    }
  ],
  "comment": null
}
➜  ccworks git:(main) ✗ ./ccworks report-details "Statement Report 06/16 - 07/31" --deep
| Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:22:54,713 - WARNING -   Transaction list not immediately visible after back/cancel: Page.wait_for_selector: Timeout 20000ms exceeded.
Call log:
  - waiting for locator(".detail-row, .sapMListUl .sapMLIB, [class*='expense-item'], [class*='expense-row'], .sapMCustomListItem, [role='row'], [role='listitem'], .sapMTable tr, tr.sapMLIB") to be visible

/ Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:22:56,717 - ERROR -   List still not found. Attempting to scroll.
| Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:22:57,723 - WARNING -   Transaction 2 not found in current view. Skipping.
| Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:23:17,725 - WARNING -   Transaction list not immediately visible after back/cancel: Page.wait_for_selector: Timeout 20000ms exceeded.
Call log:
  - waiting for locator(".detail-row, .sapMListUl .sapMLIB, [class*='expense-item'], [class*='expense-row'], .sapMCustomListItem, [role='row'], [role='listitem'], .sapMTable tr, tr.sapMLIB") to be visible

| Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:23:19,729 - ERROR -   List still not found. Attempting to scroll.
\ Fetching details for 'Statement Report 06/16 - 07/31'...2026-07-03 21:23:20,736 - WARNING -   Transaction 3 not found in current view. Skipping.
{                                                         
  "success": true,
  "report_name": "Statement Report 06/16 - 07/31",
  "report_number": "HXRLMW",
  "purpose": "Unknown",
  "comment": "Unknown",
  "expenses": [
    {
      "index": 1,
      "date": "06/30/2026",
      "expense_type": "Computer Peripherals (OIT use only)",
      "vendor": "ANTHROPIC* CLAUDE TEAM",
      "amount": "$400.00",
      "business_purpose": "",
      "comment": "",
      "raw_text": "Select expense, Computer Peripherals (OIT use only), $400.00, date, 06/30/2026 06/30/2026Computer Peripherals (OIT use only)ANTHROPIC* CLAUDE TEAMDepartmental Purchasing Card$400.00"
    },
    {
      "index": 2,
      "date": "06/22/2026",
      "expense_type": "Software (OIT use only)",
      "vendor": "APPLE.COM/BILL",
      "amount": "$2.99",
      "business_purpose": "",
      "comment": "",
      "raw_text": "Select expense, Software (OIT use only), $2.99, date, 06/22/2026 06/22/2026Software (OIT use only)APPLE.COM/BILLDepartmental Purchasing Card$2.99"
    },
    {
      "index": 3,
      "date": "06/20/2026",
      "expense_type": "Software (OIT use only)",
      "vendor": "GODADDY#4117118402",
      "amount": "$185.52",
      "business_purpose": "",
      "comment": "",
      "raw_text": "Select expense, Software (OIT use only), $185.52, date, 06/20/2026 06/20/2026Software (OIT use only)GODADDY#4117118402Departmental Purchasing Card$185.52"
    }
  ]
}


