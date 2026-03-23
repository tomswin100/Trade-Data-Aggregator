# Institutional Trade Support Workflow Demo

A Streamlit-based demo application that emulates equity trade data, detects booking errors and reconciliation breaks, and supports lightweight exception reporting through a simple Python workflow.

This project uses synthetic data generated locally to show how a trade operations or middle-office support tool might identify booking errors, data-quality issues, and reconciliation breaks without relying on real client or market data.

## Overview

The application is designed around a simple operational workflow:

1. Generate synthetic demo datasets
2. Preview the generated source files
3. Run data checks and reconciliation
4. Review exception report items and lightweight trade support insights in the interface
5. Download generated reports

The primary workflow interface is implemented in `app.py`, with backend processing logic in `src/` and a separate chart-focused `Trade Support Dashboard` page in `pages/`.

## Current Interface

The main UI is a Streamlit workflow page with a wide layout and five numbered workflow sections, plus a separate `Trade Support Dashboard` page for chart-based review.

### Landing area

When the app loads, it shows:

- The title: **Institutional Trade Support Workflow Demo**
- A short description of the tool
- An "About the demo dataset" section explaining that all files are synthetic
- An info banner indicating the app runs in demo mode
- A workflow diagram showing the end-to-end process from demo data generation through reporting

### 1. Generate demo data

This section contains a **Generate Demo Data** button.

When clicked, the app:

- Generates a fresh accounts reference dataset
- Generates clean executed trades
- Generates booked trades with intentional sample errors
- Saves CSV files into the `data/` folder
- Resets any prior run results in session state
- Stores in-memory previews so they can be shown in the UI immediately

### 2. Preview generated data

After demo data has been generated, the app unlocks a preview section with three tabs:

- **Accounts**
- **Executed Trades**
- **Booked Trades**

Each tab displays:

- A row count
- A scrollable dataframe preview

### 3. Run data checks and reconciliation

After data exists, the app enables a **Run Checks** button.

When clicked, the app:

- Loads the CSV inputs from disk
- Runs data checks
- Runs reconciliation checks
- Combines all issues into a single exception report dataset
- Builds a daily summary table
- Writes report files to the `output/` folder
- Captures a run timestamp and run log for display

If no demo data has been generated yet, the app instead shows an info message telling the user to generate data first.

### 4. Review outputs

Once checks have been run, the app shows a review section with:

- Summary metrics
- Issue breakdown metrics
- Run log messages
- Data check items preview
- Reconciliation breaks preview
- Exception report preview
- Lightweight data insight charts in the dashboard page
- Daily summary table
- Report creation status

#### Summary metrics shown in the UI

The interface displays four headline metrics:

- Executed trades
- Booked trades
- Matched trades
- Exception report items

#### Issue breakdown shown in the UI

A second metric row shows:

- Data check items
- Reconciliation breaks
- High severity issues
- Medium severity issues

#### Exception report filters

The exception report preview includes three dropdown filters:

- Filter by severity
- Filter by issue type
- Filter by source file

The filtered table currently shows these columns:

- `trade_id`
- `source_file`
- `exception_type`
- `severity`
- `recommended_action`
- `status`

### 5. Download reports

After a successful run, the app exposes download buttons for:

- **Download exception report (Excel)**
- **Download daily summary (CSV)**

These only appear when the corresponding files exist.

## What The App Currently Checks

The application performs two main categories of checks: data checks and reconciliation.

## Data Checks

Data check logic is implemented in `src/validate_data.py`.

The app currently checks for:

- Missing required fields in `executed_trades.csv`
- Missing required fields in `booked_trades.csv`
- Duplicate `account_id` values in `accounts_reference.csv`
- Use of inactive accounts in executed or booked trades

### Trade fields currently treated as required

For both trade files, the data check layer checks these fields:

- `trade_id`
- `account_id`
- `ticker`
- `quantity`
- `price`
- `currency`
- `trade_date`
- `settlement_date`

### Data check output shape

Data check items are represented with these fields:

- `file_name`
- `issue_type`
- `row_number`
- `trade_id`
- `description`
- `severity`

## Reconciliation Checks

Reconciliation logic is implemented in `src/reconcile_trades.py`.

The app reconciles executed and booked trades using `trade_id` and currently checks for:

- Duplicate trade IDs
- Missing bookings
- Orphan bookings
- Quantity mismatches
- Price mismatches
- Currency mismatches
- Settlement date mismatches

### Severity logic

The reconciliation layer currently uses these severities:

- `High`
- `Medium`
- `Low`

In practice, the current checks mainly produce High and Medium issues.

### Price tolerance

Price differences are flagged when the absolute difference between executed and booked price is greater than `0.01`.

### Reconciliation output shape

Reconciliation breaks are represented with these fields:

- `trade_id`
- `source_file`
- `exception_type`
- `executed_value`
- `booked_value`
- `severity`
- `recommended_action`
- `status`

## Exception Reporting

Reporting logic is implemented in `src/generate_reports.py`.

After data checks and reconciliation complete, the app standardises both issue sets into a single exception report table with this structure:

- `trade_id`
- `source_file`
- `exception_type`
- `severity`
- `executed_value`
- `booked_value`
- `recommended_action`
- `status`

The combined dataset is sorted by:

1. Severity
2. Issue type
3. Trade ID

## Generated Reports

The app currently generates two user-facing reports from the interface.

### `exceptions_report.xlsx`

This Excel report is written to `output/exceptions_report.xlsx` and contains:

- An `Exceptions` worksheet
- A `Report_Info` worksheet

The Excel writer also applies:

- A frozen top row
- Auto-filters
- Auto-sized columns

The `Report_Info` worksheet currently includes:

- `report_name`
- `generated_timestamp`
- `total_executed_trades`
- `total_booked_trades`
- `total_matched_trades`
- `total_exceptions`

### `daily_summary.csv`

This CSV report is written to `output/daily_summary.csv`.

It includes summary rows for:

- Total executed trades
- Total booked trades
- Total matched trades
- Exception report item count
- Issue counts by type
- Issue counts by severity

## Demo Data

Synthetic data generation is implemented in `generate_sample_data.py`.

The generator currently creates:

- 20 account records
- 100 executed trades
- A booked trade file derived from executed trades and then deliberately modified

### Input files created in `data/`

The app works with three input files:

- `data/accounts_reference.csv`
- `data/executed_trades.csv`
- `data/booked_trades.csv`

### Current file schemas

#### `accounts_reference.csv`

Columns:

- `account_id`
- `client_name`
- `base_currency`
- `account_status`

#### `executed_trades.csv`

Columns:

- `trade_id`
- `account_id`
- `ticker`
- `side`
- `quantity`
- `price`
- `currency`
- `trade_date`
- `settlement_date`
- `execution_time`
- `broker`
- `market`

#### `booked_trades.csv`

Columns:

- `trade_id`
- `account_id`
- `ticker`
- `side`
- `quantity`
- `price`
- `currency`
- `trade_date`
- `settlement_date`
- `status`
- `booked_by`
- `booking_time`

## Types Of Demo Issues Injected

The booked dataset is intentionally seeded with realistic operational issues so the app has exceptions to detect.

The generator currently injects examples of:

- Missing bookings
- Orphan bookings
- Duplicate trade IDs
- Quantity mismatches
- Price mismatches
- Currency mismatches
- Missing settlement dates
- Missing account IDs
- Inactive account usage
- Non-final booking statuses such as `PENDING` and `CANCELLED`

## Important Current Limitation

Although the demo generator injects non-final booking statuses, the current data check and reconciliation logic does **not** explicitly flag booking status issues yet.

So the interface already surfaces many booking errors and reconciliation breaks, but booking status checks are not currently implemented.

## Current Project Structure

```text
trade_exception_monitor/
├── app.py
├── generate_sample_data.py
├── pages/
│   └── 1_Exception_Dashboard.py
├── requirements.txt
├── README.md
├── data/
├── output/
└── src/
    ├── load_and_validate.py
    ├── validate_data.py
    ├── reconcile_trades.py
    ├── generate_reports.py
    └── ui_styles.py
```

## Running The App

### Install dependencies

Create a virtual environment and install the project requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional note about Graphviz

The UI uses a workflow diagram via the `graphviz` Python package in `app.py`.

If your environment does not already have it available, install it with:

```bash
pip install graphviz
```

If diagram rendering fails on your machine, you may also need the Graphviz system package installed separately.

### Start the Streamlit interface

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit in your browser.

## Backend Scripts

The backend modules can also be run directly for standalone testing:

- `src/load_and_validate.py`
- `src/validate_data.py`
- `src/reconcile_trades.py`
- `src/generate_reports.py`

These scripts print summaries to the console and may also write output files into `output/`.

## Notes

- This project uses synthetic data only.
- The app is intended as a workflow demo rather than a production trade support system.
- The interface is stateful within a Streamlit session using `st.session_state`.
- The app writes data files and report files locally to the repository folders.
- The current implementation focuses on usability and transparency rather than authentication, persistence, or production deployment concerns.

## Summary

Institutional Trade Support Workflow Demo is currently a working Streamlit demo that:

- Generates synthetic equity trade datasets
- Validates core data quality issues
- Reconciles executed vs booked trades
- Combines exceptions into a reviewable dataset
- Surfaces lightweight trade-data insights in a dashboard view
- Produces downloadable Excel and CSV reports
- Exposes the workflow through a simple five-step interface

