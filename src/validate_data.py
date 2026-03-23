import os
import pandas as pd

from load_and_validate import load_all_data

# =========================
# OUTPUT PATH
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# =========================
# HELPER: CREATE ISSUE ROW
# =========================
def make_issue(issue_type, row_number, trade_id, description, severity, file_name):
    """
    Create a standard issue dictionary so all validation results
    have the same structure.
    """
    return {
        "file_name": file_name,
        "issue_type": issue_type,
        "row_number": row_number,
        "trade_id": trade_id,
        "description": description,
        "severity": severity,
    }


# =========================
# HELPER: CHECK MISSING FIELDS
# =========================
def check_missing_required_fields(df, required_fields, file_name):
    """
    Check for missing values in required fields.
    Returns a list of issue dictionaries.
    """
    issues = []

    for index, row in df.iterrows():
        for field in required_fields:
            value = row.get(field)

            if pd.isna(value) or str(value).strip() == "":
                trade_id = row.get("trade_id", None)

                issues.append(
                    make_issue(
                        issue_type=f"missing_{field}",
                        row_number=index + 2,  # +2 because CSV header is row 1
                        trade_id=trade_id if pd.notna(trade_id) else None,
                        description=f"Missing required field '{field}' in {file_name}.",
                        severity="High",
                        file_name=file_name,
                    )
                )

    return issues


# =========================
# HELPER: CHECK DUPLICATE ACCOUNT IDs
# =========================
def check_duplicate_account_ids(accounts_df):
    """
    Check for duplicate account_id values in the accounts reference file.
    """
    issues = []

    duplicates_mask = accounts_df["account_id"].duplicated(keep=False)
    duplicate_rows = accounts_df[duplicates_mask]

    for index, row in duplicate_rows.iterrows():
        issues.append(
            make_issue(
                issue_type="duplicate_account_id",
                row_number=index + 2,
                trade_id=None,
                description=f"Duplicate account_id '{row['account_id']}' found in accounts_reference.csv.",
                severity="High",
                file_name="accounts_reference.csv",
            )
        )

    return issues


# =========================
# HELPER: CHECK INACTIVE ACCOUNT USED
# =========================
def check_inactive_accounts_used(executed_df, booked_df, accounts_df):
    """
    Check whether inactive accounts are used in executed or booked trades.
    """
    issues = []

    inactive_accounts = accounts_df.loc[
        accounts_df["account_status"].str.upper() == "INACTIVE",
        "account_id"
    ].dropna().tolist()

    # Check executed trades
    for index, row in executed_df.iterrows():
        account_id = row.get("account_id")
        trade_id = row.get("trade_id", None)

        if pd.notna(account_id) and account_id in inactive_accounts:
            issues.append(
                make_issue(
                    issue_type="inactive_account_used",
                    row_number=index + 2,
                    trade_id=trade_id if pd.notna(trade_id) else None,
                    description=f"Inactive account '{account_id}' used in executed_trades.csv.",
                    severity="Medium",
                    file_name="executed_trades.csv",
                )
            )

    # Check booked trades
    for index, row in booked_df.iterrows():
        account_id = row.get("account_id")
        trade_id = row.get("trade_id", None)

        if pd.notna(account_id) and account_id in inactive_accounts:
            issues.append(
                make_issue(
                    issue_type="inactive_account_used",
                    row_number=index + 2,
                    trade_id=trade_id if pd.notna(trade_id) else None,
                    description=f"Inactive account '{account_id}' used in booked_trades.csv.",
                    severity="Medium",
                    file_name="booked_trades.csv",
                )
            )

    return issues


# =========================
# MAIN VALIDATION FUNCTION
# =========================
def run_validation_checks(executed_df, booked_df, accounts_df):
    """
    Run all validation checks and return a DataFrame of issues.
    """
    all_issues = []

    trade_required_fields = [
        "trade_id",
        "account_id",
        "ticker",
        "quantity",
        "price",
        "currency",
        "trade_date",
        "settlement_date",
    ]

    # Missing fields checks
    all_issues.extend(
        check_missing_required_fields(
            executed_df,
            trade_required_fields,
            "executed_trades.csv"
        )
    )

    all_issues.extend(
        check_missing_required_fields(
            booked_df,
            trade_required_fields,
            "booked_trades.csv"
        )
    )

    # Accounts file checks
    all_issues.extend(check_duplicate_account_ids(accounts_df))
    all_issues.extend(check_inactive_accounts_used(executed_df, booked_df, accounts_df))

    issues_df = pd.DataFrame(all_issues)

    if issues_df.empty:
        issues_df = pd.DataFrame(columns=[
            "file_name",
            "issue_type",
            "row_number",
            "trade_id",
            "description",
            "severity",
        ])

    return issues_df


# =========================
# OPTIONAL: SAVE OUTPUT
# =========================
def save_validation_issues(issues_df):
    """
    Save validation issues to CSV for inspection.
    """
    output_file = os.path.join(OUTPUT_DIR, "validation_issues.csv")
    issues_df.to_csv(output_file, index=False)
    return output_file


# =========================
# TEST RUN
# =========================
def main():
    try:
        executed_df, booked_df, accounts_df = load_all_data()

        issues_df = run_validation_checks(executed_df, booked_df, accounts_df)

        print("\nValidation issues found:")
        print(issues_df)

        print("\nIssue counts by severity:")
        if not issues_df.empty:
            print(issues_df["severity"].value_counts())
        else:
            print("No validation issues found.")

        output_file = save_validation_issues(issues_df)
        print(f"\nValidation issues saved to: {output_file}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    
    