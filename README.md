# SAP Concur API & Browser Automation Test Suite

This project provides a unified Python integration client and test suite to verify connectivity and support programmatically creating draft expense reports in SAP Concur.

It supports two modes of interaction:
1. **API Integration (Direct)**: Uses SAP Concur REST APIs with OAuth 2.0 Client Credentials authentication (requires API permissions and administrative licensing).
2. **Browser Automation (Playwright)**: Automates a browser session to perform UI clicks (useful if your organization doesn't have Web Services API access or if direct API keys are unavailable).

---

## 🛠️ Prerequisites

### For API-Based Access
1. **Client Web Services License**: A valid license to enable API access.
2. **App Registration**: A registered application in the SAP Concur App Center to obtain a `Client ID` and `Client Secret`.
3. **Scopes**: Your application must have the `EXPRPT` (Expense Report) scope enabled.
4. **Target User Account**: A valid SAP Concur Login ID.

### For Browser-Based Automation
1. **Login Credentials**: Standard Concur username/password or SSO login.
2. **Playwright Setup**: Playwright must be installed locally along with chromium binaries (handled automatically by `./run.sh setup`).

---

## 🚀 Getting Started

### 1. Configuration

Copy the template `.env.example` file to `.env`, and populate it with your credentials:

```bash
cp .env.example .env
```

Open `.env` and fill in the details:
```env
CONCUR_CLIENT_ID=your_actual_client_id
CONCUR_CLIENT_SECRET=your_actual_client_secret
CONCUR_USER_LOGIN_ID=target_user_email@company.com
```

### 2. Setup Local Environment

Build the Python environment, install requirements, and download Playwright chromium browser binaries:

```bash
./run.sh setup
```

---

## 📂 Run Options

### Command Table

| Run Mode | Command | Scope / Notes |
| :--- | :--- | :--- |
| **Containerized Unit Tests** | `./run.sh test-docker` | Runs mock tests in Docker (Offline, credentials not needed). |
| **Local Unit Tests** | `./run.sh test-local` | Runs mock tests locally using `.venv`. |
| **Live API Test** | `./run.sh run-live` | Tests token retrieval, report listing, and report creation. |
| **Headed Browser Login** | `./run.sh browser-login` | Boots browser window for manual login, saves authentication state. |
| **Headless Browser Creation**| `./run.sh browser-create` | Programmatically logs in using saved state and creates a draft report. |
| **Visible Browser Creation** | `./run.sh browser-create-headed` | Performs browser creation visibly on screen (useful for debugging). |
| **List Historical Reports** | `./run.sh browser-query-old [filter]` | Query and list historical reports (e.g. "Last 90 Days"). |
| **Report Details** | `./run.sh browser-report-details "Name" [filter]` | Fetch line-item details of a specific report. |
| **List Card Transactions** | `./run.sh browser-list-cards [filter]` | List credit card transactions under specific activity filters. |
| **Card Transaction Details** | `./run.sh browser-card-details "Merchant/ID" [filter]` | Fetch details for a card transaction by name or ID. |
| **Add Expense Delegate** | `./run.sh browser-add-delegate "Name" [perms...]` | Add delegate and assign permissions (prepare, submit, approve). |
| **Remove Expense Delegate** | `./run.sh browser-remove-delegate "Name"` | Remove expense delegate from settings page. |
| **Reconcile Report** | `./run.sh browser-reconcile "Name" [rules.json]` | Reconcile report transactions with rules and submit. |
| **Attach Receipt to Transaction** | `./run.sh browser-attach-receipt "Name" "Merchant" "receipt.pdf"` | Attach local receipt file directly to a transaction row in a report. |

---

## 🔍 Detailed Usage Examples & API Reference

### 1. Historical Expense Reports

Concur separates active draft reports from older, submitted, or processed reports via dropdown filters. The browser client automates navigating the reports grid, updating the view filter, and clicking individual cards to extract details.

* **List Old Reports:**
  ```bash
  # Query using the default 'Last 90 Days' filter
  ./run.sh browser-query-old
  
  # Specify a custom filter (e.g., 'All Reports')
  ./run.sh browser-query-old "All Reports"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Discovered 2 historical report(s):
    1. Old Lodging Report 2025 (Purpose: FY2025 Conference)
    2. Q1 Travel Report (Purpose: Client Visits Q1)
  ```

* **Get Report Details:**
  ```bash
  # Get line items and header details for a specific report
  ./run.sh browser-report-details "Old Lodging Report 2025" "Last 90 Days"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Details retrieved:
    Name:     Old Lodging Report 2025
    Number:   REP-100200
    Purpose:  FY2025 Conference
    Comment:  Approved & Paid
    Expenses: (2 items)
      - Date: 2026-06-12 | Type: Lodging | Amount: $150.00 | Merchant: Hilton
      - Date: 2026-06-13 | Type: Meal | Amount: $45.20 | Merchant: Italian Bistro
  ```

### 2. Credit Card Transactions

Automates listing and viewing credit card transactions inside the **Available Expenses** dashboard section. Supports selecting view activities such as "All Corporate and Personal Cards" or "All Purchasing Cards".

* **List Card Transactions:**
  ```bash
  # List corporate and personal cards (default)
  ./run.sh browser-list-cards "All Corporate and Personal Cards"
  
  # List purchasing cards
  ./run.sh browser-list-cards "All Purchasing Cards"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Discovered 1 transaction(s):
    1. Office Depot - $189.99
  ```

* **Get Transaction Details:**
  ```bash
  ./run.sh browser-card-details "Office Depot" "All Purchasing Cards"
  ```
  *Output Example:*
  ```text
  [SUCCESS] Transaction details:
    Merchant:     Office Depot
    Date:         2026-06-18
    Amount:       $189.99
    Transaction ID: TX_5002
    Card Program: Purchasing Card
  ```

### 3. Expense Delegates Settings

Automates adding and removing delegates, plus managing permissions in the profile settings (`/profile/editdelegates.asp`).

* **Add Expense Delegate:**
  Add a delegate by name or email, specifying checkboxes for permissions (`prepare`, `submit`, `approve`).
  ```bash
  # Add John Doe with Prepare and Submit permissions
  ./run.sh browser-add-delegate "John Doe" prepare submit
  
  # Add Jane Smith with Prepare and Approve permissions
  ./run.sh browser-add-delegate "Jane Smith" prepare approve
  ```

* **Remove Expense Delegate:**
  Remove a delegate by selecting their checkbox, triggering 'Delete', and saving the profiles page.
  ```bash
  ./run.sh browser-remove-delegate "John Doe"
  ```

### 4. Month-End Expense Reconciliation

Reconciliation is a critical month-end task. The client navigates inside a report, reads the merchant list, and maps matching rules to fill in Expense Types, Business Purposes, Comments, and Allocation Codes for every transaction row before submitting the report.

* **Reconcile and Submit Report:**
  ```bash
  # Reconcile using default built-in matching rules
  ./run.sh browser-reconcile "Reconciliation Report A"
  
  # Or provide a custom JSON file defining your accounting code mapping rules
  ./run.sh browser-reconcile "Reconciliation Report A" my_recon_rules.json
  ```
  
  *Example `my_recon_rules.json` file:*
  ```json
  {
    "Uber": {
      "expense_type": "Ground Transportation",
      "business_purpose": "Client travel to office",
      "comment": "Uber Ride",
      "allocation_code": "COST-CENTER-101"
    },
    "Office Depot": {
      "expense_type": "Office Supplies",
      "business_purpose": "Team whiteboard supplies",
      "comment": "Pens and notebooks",
      "allocation_code": "COST-CENTER-102"
    }
  }
  ```

### 5. Match & Attach Receipt Directly to Transaction

Matching receipt PDFs or images to individual card transactions can be automated. Playwright navigates into the expense report detail row matching your merchant name, locates the hidden file input element, and uploads the local file.

* **Attach Local Receipt to Report Expense:**
  ```bash
  ./run.sh browser-attach-receipt "Receipt Upload Report A" "Uber" "receipts/uber_ride_receipt.pdf"
  ```

---

## 🔮 Recommended Future Features & Integrations

1. **Receipt-to-Report Attachment:**
   * *Description:* Automate uploading local images/PDFs into the **Available Receipts** gallery, then attaching them to specific reports or transaction entries.
   * *Value:* Fully automates matching receipt files to credit card expenses without manual drag-and-drop.
2. **Expense Itemization Automation:**
   * *Description:* Parse lodging/hotel folios or receipt text (using OCR/LLM) and programmatically itemize room rates, room taxes, parking, and meals.
   * *Value:* Eliminates tedious manual breakdowns of hotel checkout bills.
3. **Approval workflows for Managers:**
   * *Description:* Scan pending approval reports, display total summaries, and click approve or send back to employees with custom comments.
   * *Value:* Streamlines managers' review process via CLI/Slack commands.
4. **Export to ERP/Accounting Formats:**
   * *Description:* Export queried reports and transactions directly to CSV, JSON, or standard ERP formats (SAP, NetSuite, QuickBooks).
   * *Value:* Syncs Concur expense data directly into business accounting books.

---

## 🔒 Handling Multi-Factor Authentication (MFA) & SSO in Browser Mode

Modern enterprise security often requires MFA or SSO login screens that standard automation cannot programmatically bypass. This project handles this using a **Session State Preservation** strategy:

1. Run the manual session setup:
   ```bash
   ./run.sh browser-login
   ```
2. A headed Chromium window will open. Enter your email/password, solve SSO if prompted, and complete the MFA authentication.
3. Once logged in and redirected to the SAP Concur dashboard page, return to your terminal and press **ENTER**.
4. Your authenticated session token, cookies, and local storage are saved into `concur_session.json`.
5. Subsequent automated actions will load this file and run headlessly without requiring login or prompt parameters.

---

## 📂 Project Directory Structure

```
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Service orchestration for testing
├── requirements.txt        # Third-party Python dependencies
├── .env.example            # Environment variables configuration template
├── run.sh                  # Zsh shell helper script
├── README.md               # Developer-oriented documentation
├── src/
│   ├── __init__.py
│   ├── client.py           # Core Concur API Client Wrapper
│   ├── browser_client.py   # Playwright Browser Automation Client
│   └── cli.py              # Command-Line Access Tester Script
└── tests/
    ├── __init__.py
    ├── mock_concur_server.py # Stateful local mock SAP Concur Server
    ├── test_client.py      # Unit tests using requests mocks
    └── test_browser_smoke.py # E2E local browser smoke tests
```
