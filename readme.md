# Auntie Som API Testing Submission

This fork audits the supplied Flask API using **45 Bruno requests in nine isolated scenarios**. The backend is unchanged. The tests assert the intended contract and preserve failures that expose defects.

## Verified results

The native collection completed **149 checks: 128 passed and 21 failed**. These failures represent backend defects, not an expectation that the deliberately broken API should pass every check. The three main findings are incorrect pricing, overselling, and an incorrect missing-order status. Additional findings concern invalid quantities.

- Native collection: [`bruno/`](bruno/)
- Importable Bruno Collection JSON: [`exports/Auntie-Som-Lab.json`](exports/Auntie-Som-Lab.json)
- Human-readable execution evidence: [`reports/audit-results.md`](reports/audit-results.md)
- Sanitized response and assertion evidence: [`reports/audit-results.json`](reports/audit-results.json)
- Export verification: [`reports/export-verification.json`](reports/export-verification.json)
- Reimported execution evidence: [`reports/reimport-results.json`](reports/reimport-results.json)

## Setup and automatic execution

Prerequisites: Python 3.10+, Node.js 22+, npm, Git, and Bruno Desktop if using the graphical client. Tested with Python 3.14.7, Node.js 22.14.0, Flask 3.1.3, and Bruno CLI 4.2.1. The official Bruno Desktop 4.2.1 portable Windows build was downloaded locally; see the export note below.

From the repository root, run these PowerShell commands:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
npm.cmd test
```

`npm test` starts the unchanged API on port 5000, waits for the initial menu inventory, runs one scenario, stops its owned server process tree, and repeats with a fresh API for each remaining scenario. It does not stop an unrelated server already using port 5000. Disable any independently running API before starting the runner.

The expected exit code against the supplied backend is **1**, indicating genuine failed assertions. Exit **2** indicates setup or execution failure. Requests continue after failed assertions; there is no `--bail`. The runner checks that each scenario actually executed all its request files with tests and no transport/script errors. An HTTP 500 response is still tested and recorded as an API defect.

Run a single scenario with:

```powershell
python scripts/run_lab.py --scenario 04-overstock
```

A single-scenario run overwrites the summary reports; run the full suite again before publishing results. Individual raw CLI reports are in ignored `reports/raw/`. They can contain ephemeral tokens and must not be committed. Published reports omit authorization headers and redact tokens; `local.bru` is restored to an empty token after every scenario, including failed runs.

## Bruno Desktop and manual CLI execution

Copy `bruno/environments/local.example.bru` to `bruno/environments/local.bru`, open the `bruno` folder in Bruno Desktop, and select the **local** environment. Its variables are `baseUrl=http://localhost:5000`, `username=student`, `password=hungry`, and an initially empty `accessToken`. These credentials are public course fixtures.

Login post-response scripts use `bru.setEnvVar('accessToken', ...)`, and order requests use `Bearer {{accessToken}}`. Bruno 4 persists environment writes, so the active local environment is ignored by Git. Runtime variables hold menu snapshots, expected totals, order IDs, and created-order responses. Order IDs are captured before pricing assertions run.

For each folder in the following order, start a fresh API using the command below, run **that folder only** using Bruno's folder runner, then stop the API with Ctrl+C before starting the next folder. Running the entire collection against one server instance does not isolate inventory.

```powershell
.\.venv\Scripts\python.exe -m flask --app auntie-som-noodle-api/app.py run --host 127.0.0.1 --port 5000 --no-debugger --no-reload
```

| Order / folder | Requests | Coverage |
| --- | ---: | --- |
| `01-contract-and-auth` | 10 | Menu schema, correct/incorrect login, missing/invalid token, unknown item, missing order, unchanged stock after rejection |
| `02-valid-order-and-price` | 5 | Create order, calculated total, response chaining, retrieve matching order, stock decrement |
| `03-exhausted-stock` | 6 | Buy the last fried rice, reject a second purchase, preserve exhausted inventory |
| `04-overstock` | 4 | Reject quantity 3 when stock is 2; preserve stock and prohibit negative inventory |
| `05-zero-quantity` | 4 | Reject quantity 0 and preserve stock |
| `06-negative-quantity` | 4 | Reject quantity -1 and preserve stock |
| `07-missing-quantity` | 4 | Reject an omitted quantity gracefully and preserve stock |
| `08-fractional-quantity` | 4 | Reject quantity 1.5 and preserve stock |
| `09-string-quantity` | 4 | Reject quantity `"one"` gracefully and preserve stock |

For manual CLI use, while a fresh API is running, change into `bruno` and run:

```powershell
..\node_modules\.bin\bru.cmd run 04-overstock --env local --reporter-json ..\reports\raw\manual-overstock.json --reporter-skip-all-headers
```

Create `reports/raw` first if needed. Restart the API and run Login again for every scenario. Copy the example environment over `local.bru` after finishing to clear the persisted token. Prefer `npm test` for automatic reset and cleanup.

## Three main bug reports

### BUG-01: Every order is undercharged by 5

- **Test:** `02-valid-order-and-price / Create valid order`, check `BUG-01 Total equals menu price times quantity`; repeated on `Retrieve created order`.
- **Reproduce:** Start a fresh API, log in, read `/menu`, then submit `POST /orders` with `{"itemId":1,"quantity":1}` and the valid token. Retrieve the returned order ID.
- **Expected:** Tom Yum's menu price is 50, so both responses should show `totalPrice: 50`.
- **Observed:** Both responses show `totalPrice: 45`. Both pricing assertions fail; creation/retrieval schema, ID chaining, and stock checks pass.
- **Impact:** Every accepted order loses 5 in revenue. The backend computes `(price * quantity) - 5` without a documented discount.

### BUG-02: An order can exceed available stock

- **Tests:** `04-overstock / Reject excess quantity` and `Inventory after rejection`.
- **Reproduce:** With fresh Tom Yum stock of 2, log in and submit `{"itemId":1,"quantity":3}`, then read `/menu`.
- **Expected:** HTTP 400 with a JSON error; stock stays 2.
- **Observed:** HTTP 200 creates an order, and stock becomes -1. The status, error-body, unchanged-stock, and nonnegative-inventory checks fail.
- **Impact:** The stall accepts orders it cannot fulfill. The backend checks only whether current stock is positive, rather than whether it covers the requested quantity.

### BUG-03: Missing orders return a success status

- **Test:** `01-contract-and-auth / Missing order`, check `HTTP status is 404`.
- **Reproduce:** Request `GET /orders/ORD-does-not-exist` against a fresh server.
- **Expected:** HTTP 404 with `{"error":"Order not found"}`.
- **Observed:** The error body is present, but the status is HTTP 200.
- **Impact:** Clients and monitoring that depend on status codes can treat missing resources as successful lookups.

## Additional findings and contract assumptions

| Payload | Observed behavior |
| --- | --- |
| `quantity: 0` | HTTP 200 creates an order with total -5; stock remains 2 |
| `quantity: -1` | HTTP 200 creates an order with total -55; stock increases to 3 |
| Missing `quantity` | HTTP 500 HTML response instead of a structured client error |
| `quantity: 1.5` | HTTP 200 creates an order with total 70; stock becomes 0.5 |
| `quantity: "one"` | HTTP 500 HTML response instead of a structured client error |

For invalid quantities, the test accepts either HTTP 400 or 422 with a JSON error because the activity does not define an exact validation-error code. Positive order totals are calculated from the live menu, assuming no discount because none is specified by the business rules. The original README's example total of 45 conflicts with the menu price of 50; the test deliberately exposes that discrepancy instead of treating the example as an undocumented discount. Successful order creation expects HTTP 200 as documented by this API, rather than imposing a generic HTTP 201 convention.

The `GET /orders/<id>` endpoint has no documented authentication requirement, and the supplied API has one account with no roles or ownership model. Multi-user IDOR, admin permissions, token expiry, and the slides' separate checkout/concurrency examples are outside this submission. Response time is observed by Bruno but has no invented pass/fail SLA.

## JSON export and verification

The JSON uses native **Bruno Collection** format, not a CLI results JSON or a Postman conversion. It includes all nine folders, 45 requests, post-response scripts, tests, and the sanitized local environment.

Bruno Desktop 4.2.1's portable build did not expose a usable window on this machine; an initial launch also logged a failure loading its bundled `web/index.html`. Therefore the export was created with the official pinned Bruno parser and validated using Bruno's collection schema, then reimported with the collection importer shipped in its CLI. No GUI export or GUI reimport is claimed.

```powershell
node scripts/verify-export.cjs --write
npm.cmd run verify:export
```

The verification compares every parsed request, body, header, script, assertion, sequence, and environment variable before and after reimport. It also verifies that the exported token is empty. A temporary native collection is created under ignored `.local/` for execution.

The reimported collection was also executed against nine fresh API instances: **45 requests, 149 checks, 128 passed, 21 failed**, matching every native request status and test outcome. This archived comparison is checked by `npm run verify:export`.

On a machine where Bruno Desktop opens normally, use the collection's **Share -> Export -> Bruno Collection** option to export JSON, then **Import Collection -> Bruno Collection** to reopen it in a different directory. Keep generated tokens empty when exporting.

## Submission

Repository: https://github.com/chayathorn-nk/api-testing-course

Submit this fork's link to the instructor through Discord DM. The native collection, JSON export, README, and sanitized evidence are the submission artifacts. Installation folders, active tokens, virtual environments, raw reports, and downloaded tools are ignored.

The work follows the [original lab](https://github.com/foname/api-testing-course) and the supplied lecture PDF: pages 26-39 cover environments, assertions, chaining, and reviewing generated scripts; page 60 requires three documented bugs and a JSON collection.

---

## Original course instructions

# 🍜 API Testing Lab: Auntie Som’s Noodle Stall

> **Objective:** Prove that Nephew Lek’s "it works on my machine" attitude is a recipe for disaster.

---

## 📖 The Backstory

Auntie Som runs a **legendary noodle stall**. Her Tom Yum is world-class, her customers are loyal, and her business is booming.  

Recently, her nephew **Lek** (who just finished a 2-week coding bootcamp) decided to "digitize" the business. He built a backend API to handle online orders. Auntie Som is thrilled, but the code… well, Lek says:  

> *"It’s fine lah Auntie! I tested it once with my own phone. No need for professional testing!"*

**You are the Last Line of Defense.**  
Before Auntie Som launches this app to 1,000+ hungry customers, you must audit the system, find the logic flaws, and automate the validation using **Bruno**.

---

## 🎯 Learning Objectives

By the end of this lab, you should be able to:
- 🖋️ Write **Bruno test scripts** for automated validation.
- 📦 Extract values from API responses using **Post-response scripts**.
- 🔐 Manage and use **Environment Variables**.
- 🧠 Verify **Business Rules**, not just HTTP status codes.
- 🚀 Catch regressions automatically before they hit production.

---

## 🛠️ Setup Instructions

### 1️⃣ Prepare the Project
- **Fork this repository** to your own GitHub account.
- **Clone it** locally to your machine.

### 2️⃣ Start the API Server
The backend is a lightweight Flask application.
- **Requirements:** Python 3.10+ installed.
- **Navigate** to the `auntie-som-noodle-api` folder.
- **Install dependencies:**  
  ```bash
  pip install flask
  ```
- **Run the server:**  
  ```bash
  python app.py
  ```
- The server will run at: `http://localhost:5000`

### 3️⃣ Setup Bruno
- Download and install [Bruno](https://www.usebruno.com).
- Create a **New Collection** named `Auntie Som Lab`.
- Create an **Environment** (e.g., `local`) and set a variable `baseUrl` to `http://localhost:5000`.

---

## 📑 API Reference

### 🔐 Authentication
`POST /auth/login` - Get an access token.
- **Body (JSON):**
  ```json
  {
    "username": "student",
    "password": "hungry"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "accessToken": "uuid-token-string",
    "expiresIn": 3600
  }
  ```

---

### 🍜 Menu
`GET /menu` - View available items and stock levels.
- **Response (200 OK):**
  ```json
  [
    { "id": 1, "name": "Tom Yum Noodles", "price": 50, "stock": 2 },
    { "id": 2, "name": "Fried Rice", "price": 45, "stock": 1 }
  ]
  ```

---

### 🛒 Orders
`POST /orders` - Place a new order.
- **Headers:** `Authorization: Bearer <token>`
- **Body (JSON):**
  ```json
  {
    "itemId": 1,
    "quantity": 1
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "orderId": "ORD-abc123",
    "status": "created",
    "totalPrice": 45
  }
  ```

`GET /orders/<orderId>` - Retrieve order details.
- **Response (200 OK):**
  ```json
  {
    "orderId": "ORD-abc123",
    "status": "created",
    "totalPrice": 45
  }
  ```

---

## 🕵️ Your Mission: The Silent Auditor

Your task is to create a comprehensive Bruno collection that validates the entire workflow.  

⚠️ **The Catch:** Nephew Lek left several **logic bugs** in the system. Some endpoints might return `200 OK` even when the business logic is completely broken.

**Your collection must include:**
1.  **Auth Flow**: Automatically store the `accessToken` from login and use it for subsequent requests.
2.  **Order Validation**: Ensure orders can only be placed with valid auth, valid items, and available stock.
3.  **Data Integrity**: Check that the `totalPrice` calculated by the API matches your expectations.
4.  **Edge Cases**: What happens if you order more than what's in stock? What happens if you request a non-existent order?

> [!TIP]
> **Clicking "Send" is not testing.** Your tests must contain scripts (Assertions or Javascript) that **FAIL** when the system behaves incorrectly.

---

## 🧠 Rules of the Lab
- ❌ **Do NOT** modify the `app.py` backend code.
- ❌ **Do NOT** rely on manual checking.
- ✅ **Use environment variables** for the Base URL and Tokens.
- ✅ **Use Scripts/Assertions** for all validations.

---

## 📦 What to Submit

1.  **Push your Bruno collection folder** to your GitHub repository.
2.  **Update your README.md** (the one in your fork) with:
    - A summary of the bugs you discovered.
    - How your tests detect these bugs.
4.  **Send the GitHub link** to your instructor via Discord.

---
*Good luck. Auntie Som is counting on you!* 🍜🔥
