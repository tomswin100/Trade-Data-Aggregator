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
# CONFIG
# =========================
PRICE_TOLERANCE = 0.01

SEVERITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


# =========================
# HELPERS
# =========================
def format_value(value):
    """
    Format values so the output looks cleaner.
    """
    if pd.isna(value):
        return ""

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    return value


def make_recon_issue(
    trade_id,
    source_file,
    exception_type,
    executed_value,
    booked_value,
    severity,
    recommended_action,
    status="Open"
):
    return {
        "trade_id": trade_id,
        "source_file": source_file,
        "exception_type": exception_type,
        "executed_value": format_value(executed_value),
        "booked_value": format_value(booked_value),
        "severity": severity,
        "recommended_action": recommended_action,
        "status": status,
    }


def values_different(val1, val2):
    """
    Generic comparison helper.
    """
    if pd.isna(val1) and pd.isna(val2):
        return False
    if pd.isna(val1) or pd.isna(val2):
        return True
    return val1 != val2


def price_different(executed_price, booked_price, tolerance=PRICE_TOLERANCE):
    """
    Price comparison with tolerance.
    """
    if pd.isna(executed_price) and pd.isna(booked_price):
        return False
    if pd.isna(executed_price) or pd.isna(booked_price):
        return True
    return abs(executed_price - booked_price) > tolerance


# =========================
# DUPLICATE TRADE ID CHECKS
# =========================
def check_duplicate_trade_ids(df, source_file):
    """
    Return one duplicate issue per duplicated trade_id.
    """
    issues = []

    duplicate_counts = (
        df["trade_id"]
        .dropna()
        .value_counts()
    )

    duplicate_counts = duplicate_counts[duplicate_counts > 1]

    for trade_id, count in duplicate_counts.items():
        issues.append(
            make_recon_issue(
                trade_id=trade_id,
                source_file=source_file,
                exception_type="duplicate_trade_id",
                executed_value=f"{count} records" if source_file == "executed_trades.csv" else "",
                booked_value=f"{count} records" if source_file == "booked_trades.csv" else "",
                severity="High",
                recommended_action="Review duplicate trade ID records and confirm the correct record before rerunning checks.",
            )
        )

    return issues


# =========================
# CORE RECONCILIATION
# =========================
def reconcile_executed_vs_booked(executed_df, booked_df):
    """
    Reconcile executed trades against booked trades using trade_id.
    """
    issues = []

    # 1. Duplicate trade IDs in either file
    issues.extend(check_duplicate_trade_ids(executed_df, "executed_trades.csv"))
    issues.extend(check_duplicate_trade_ids(booked_df, "booked_trades.csv"))

    # 2. Outer join to capture all records
    merged_df = executed_df.merge(
        booked_df,
        on="trade_id",
        how="outer",
        suffixes=("_executed", "_booked"),
        indicator=True
    )

    # 3. Check each merged row
    for _, row in merged_df.iterrows():
        trade_id = row.get("trade_id")

        # Missing booking
        if row["_merge"] == "left_only":
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="missing_booking",
                    executed_value="present",
                    booked_value="missing",
                    severity="High",
                    recommended_action="Review the booking workflow and confirm the executed trade has been booked.",
                )
            )
            continue

        # Booking without execution
        if row["_merge"] == "right_only":
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="orphan_booking",
                    executed_value="missing",
                    booked_value="present",
                    severity="High",
                    recommended_action="Review the orphan booking and confirm whether a matching execution exists.",
                )
            )
            continue

        # Quantity mismatch
        if values_different(row.get("quantity_executed"), row.get("quantity_booked")):
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="quantity_mismatch",
                    executed_value=row.get("quantity_executed"),
                    booked_value=row.get("quantity_booked"),
                    severity="High",
                    recommended_action="Review the booked quantity against the executed trade and correct the booking.",
                )
            )

        # Price mismatch
        if price_different(row.get("price_executed"), row.get("price_booked")):
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="price_mismatch",
                    executed_value=row.get("price_executed"),
                    booked_value=row.get("price_booked"),
                    severity="Medium",
                    recommended_action="Review the booked price against the executed trade and correct the booking if needed.",
                )
            )

        # Currency mismatch
        if values_different(row.get("currency_executed"), row.get("currency_booked")):
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="currency_mismatch",
                    executed_value=row.get("currency_executed"),
                    booked_value=row.get("currency_booked"),
                    severity="High",
                    recommended_action="Review the booked currency against the executed trade before settlement cutoff.",
                )
            )

        # Settlement date mismatch
        if values_different(row.get("settlement_date_executed"), row.get("settlement_date_booked")):
            issues.append(
                make_recon_issue(
                    trade_id=trade_id,
                    source_file="reconciliation",
                    exception_type="settlement_date_mismatch",
                    executed_value=row.get("settlement_date_executed"),
                    booked_value=row.get("settlement_date_booked"),
                    severity="Medium",
                    recommended_action="Review settlement instructions and correct the booked settlement date before end of day.",
                )
            )

    issues_df = pd.DataFrame(issues)

    if issues_df.empty:
        issues_df = pd.DataFrame(columns=[
            "trade_id",
            "source_file",
            "exception_type",
            "executed_value",
            "booked_value",
            "severity",
            "recommended_action",
            "status",
        ])
        return issues_df

    # Add sort key for severity
    issues_df["severity_rank"] = issues_df["severity"].map(SEVERITY_ORDER)

    # Sort by severity, exception type, trade_id
    issues_df = issues_df.sort_values(
        by=["severity_rank", "exception_type", "trade_id"],
        ascending=[True, True, True]
    )

    # Drop helper column
    issues_df = issues_df.drop(columns=["severity_rank"])

    # Reset index
    issues_df = issues_df.reset_index(drop=True)

    return issues_df


# =========================
# SUMMARY OUTPUT
# =========================
def build_reconciliation_summary(issues_df):
    """
    Build a summary table with counts by exception type and severity.
    """
    if issues_df.empty:
        return pd.DataFrame(columns=["summary_type", "summary_value", "count"])

    summary_rows = []

    # Total issues
    summary_rows.append({
        "summary_type": "total_issues",
        "summary_value": "all",
        "count": len(issues_df)
    })

    # By severity
    severity_counts = issues_df["severity"].value_counts()
    for severity, count in severity_counts.items():
        summary_rows.append({
            "summary_type": "severity",
            "summary_value": severity,
            "count": count
        })

    # By exception type
    exception_counts = issues_df["exception_type"].value_counts()
    for exception_type, count in exception_counts.items():
        summary_rows.append({
            "summary_type": "exception_type",
            "summary_value": exception_type,
            "count": count
        })

    return pd.DataFrame(summary_rows)


# =========================
# SAVE OUTPUTS
# =========================
def save_reconciliation_issues(issues_df):
    output_file = os.path.join(OUTPUT_DIR, "reconciliation_issues.csv")
    issues_df.to_csv(output_file, index=False)
    return output_file


def save_reconciliation_summary(summary_df):
    output_file = os.path.join(OUTPUT_DIR, "reconciliation_summary.csv")
    summary_df.to_csv(output_file, index=False)
    return output_file


# =========================
# TEST RUN
# =========================
def main():
    try:
        executed_df, booked_df, accounts_df = load_all_data()

        issues_df = reconcile_executed_vs_booked(executed_df, booked_df)
        summary_df = build_reconciliation_summary(issues_df)

        print("\nReconciliation issues found:")
        print(issues_df)

        print("\nReconciliation summary:")
        print(summary_df)

        issues_file = save_reconciliation_issues(issues_df)
        summary_file = save_reconciliation_summary(summary_df)

        print(f"\nReconciliation issues saved to: {issues_file}")
        print(f"Reconciliation summary saved to: {summary_file}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    
