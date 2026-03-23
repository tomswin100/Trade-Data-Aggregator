import os
import pandas as pd

# =========================
# PATH SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

EXECUTED_TRADES_FILE = os.path.join(DATA_DIR, "executed_trades.csv")
BOOKED_TRADES_FILE = os.path.join(DATA_DIR, "booked_trades.csv")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts_reference.csv")

# =========================
# REQUIRED COLUMNS
# =========================
REQUIRED_EXECUTED_COLUMNS = [
    "trade_id",
    "account_id",
    "ticker",
    "side",
    "quantity",
    "price",
    "currency",
    "trade_date",
    "settlement_date",
    "execution_time",
    "broker",
    "market",
]

REQUIRED_BOOKED_COLUMNS = [
    "trade_id",
    "account_id",
    "ticker",
    "side",
    "quantity",
    "price",   # we will standardise booked_price -> price if needed
    "currency",
    "trade_date",
    "settlement_date",
    "status",
    "booked_by",
    "booking_time",
]

REQUIRED_ACCOUNTS_COLUMNS = [
    "account_id",
    "client_name",
    "base_currency",
    "account_status",
]


# =========================
# BASIC FILE CHECKS
# =========================
def check_file_exists(file_path):
    """Raise an error if the file does not exist."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")


def check_not_empty(df, file_name):
    """Raise an error if DataFrame has no rows."""
    if df.empty:
        raise ValueError(f"{file_name} has no rows.")


def check_not_completely_blank(df, file_name):
    """Raise an error if all rows are fully blank."""
    if df.dropna(how="all").empty:
        raise ValueError(f"{file_name} is completely blank.")


def check_required_columns(df, required_columns, file_name):
    """Raise an error if required columns are missing."""
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"{file_name} is missing required columns: {missing_columns}"
        )


# =========================
# CLEANING HELPERS
# =========================
def standardise_column_names(df):
    """Strip whitespace and lower-case all column names."""
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def rename_booked_price_if_needed(df):
    """
    Rename booked_price to price if needed so later reconciliation
    logic can compare executed and booked files more easily.
    """
    if "booked_price" in df.columns and "price" not in df.columns:
        df = df.rename(columns={"booked_price": "price"})
    return df


def convert_date_columns(df, date_columns):
    """Convert listed columns to datetime where present."""
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def convert_numeric_columns(df, numeric_columns):
    """Convert listed columns to numeric where present."""
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# =========================
# LOAD + CLEAN ONE FILE
# =========================
def load_and_clean_csv(file_path, required_columns, file_name, date_columns=None, numeric_columns=None):
    """
    Load a CSV file, standardise columns, run basic checks,
    and convert data types.
    """
    check_file_exists(file_path)

    df = pd.read_csv(file_path)

    check_not_empty(df, file_name)
    check_not_completely_blank(df, file_name)

    df = standardise_column_names(df)
    df = rename_booked_price_if_needed(df)

    check_required_columns(df, required_columns, file_name)

    if date_columns:
        df = convert_date_columns(df, date_columns)

    if numeric_columns:
        df = convert_numeric_columns(df, numeric_columns)

    return df


# =========================
# LOAD ALL INPUT FILES
# =========================
def load_all_data():
    """
    Load and clean all project input files.
    Returns:
        executed_df, booked_df, accounts_df
    """
    executed_df = load_and_clean_csv(
        file_path=EXECUTED_TRADES_FILE,
        required_columns=REQUIRED_EXECUTED_COLUMNS,
        file_name="executed_trades.csv",
        date_columns=["trade_date", "settlement_date", "execution_time"],
        numeric_columns=["quantity", "price"],
    )

    booked_df = load_and_clean_csv(
        file_path=BOOKED_TRADES_FILE,
        required_columns=REQUIRED_BOOKED_COLUMNS,
        file_name="booked_trades.csv",
        date_columns=["trade_date", "settlement_date", "booking_time"],
        numeric_columns=["quantity", "price"],
    )

    accounts_df = load_and_clean_csv(
        file_path=ACCOUNTS_FILE,
        required_columns=REQUIRED_ACCOUNTS_COLUMNS,
        file_name="accounts_reference.csv",
        date_columns=None,
        numeric_columns=None,
    )

    return executed_df, booked_df, accounts_df


# =========================
# TEST RUN
# =========================
def main():
    try:
        executed_df, booked_df, accounts_df = load_all_data()

        print("Files loaded successfully.\n")

        print("Executed trades:")
        print(executed_df.head())
        print("\nExecuted trades info:")
        print(executed_df.dtypes)

        print("\n" + "=" * 60 + "\n")

        print("Booked trades:")
        print(booked_df.head())
        print("\nBooked trades info:")
        print(booked_df.dtypes)

        print("\n" + "=" * 60 + "\n")

        print("Accounts reference:")
        print(accounts_df.head())
        print("\nAccounts reference info:")
        print(accounts_df.dtypes)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    
    