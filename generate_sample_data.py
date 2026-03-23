import csv
import os
import random
from datetime import datetime, timedelta

# =========================
# PATH SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "data")

# =========================
# CONFIG
# =========================
NUM_TRADES = 100
DEFAULT_RANDOM_SEED = 42
PRICE_VARIATION_PERCENT = 0.05
MIN_TRADES_FOR_ISSUES = 20
ACCOUNT_COUNT = 20
ACTIVE_ACCOUNT_COUNT = 18

BOOKING_USERS = ["ops_user_1", "ops_user_2", "ops_user_3"]
BOOKING_STATUS_ISSUES = ["PENDING", "CANCELLED"]

ISSUE_COUNT_RANGES = {
    "missing_booking": (4, 6),
    "duplicate_trade_id": (2, 3),
    "orphan_booking": (1, 2),
    "quantity_mismatch": (2, 4),
    "price_mismatch": (2, 4),
    "currency_mismatch": (1, 2),
    "missing_settlement_date": (2, 3),
    "missing_account_id": (1, 2),
    "inactive_account_used": (1, 2),
    "non_final_status": (2, 3),
}

SIDES = ["BUY", "SELL"]
CURRENCIES = ["NZD", "AUD", "USD"]  # kept for injected currency mismatches
BOOKING_STATUSES = ["BOOKED", "PENDING", "CANCELLED"]

# Ticker reference map: approximate market + currency + anchor price.
# These are not live prices, but they keep the synthetic dataset in
# believable ranges for a trade support demo.
TICKER_REFERENCE = {
    "AAPL":  {"market": "NASDAQ", "currency": "USD", "base_price": 215.40},
    "AMZN":  {"market": "NASDAQ", "currency": "USD", "base_price": 201.85},
    "AMD":   {"market": "NASDAQ", "currency": "USD", "base_price": 164.20},
    "AVGO":  {"market": "NASDAQ", "currency": "USD", "base_price": 214.65},
    "META":  {"market": "NASDAQ", "currency": "USD", "base_price": 615.20},
    "MSFT":  {"market": "NASDAQ", "currency": "USD", "base_price": 421.75},
    "GOOGL": {"market": "NASDAQ", "currency": "USD", "base_price": 185.60},
    "NFLX":  {"market": "NASDAQ", "currency": "USD", "base_price": 978.45},
    "TSLA":  {"market": "NASDAQ", "currency": "USD", "base_price": 235.80},
    "NVDA":  {"market": "NASDAQ", "currency": "USD", "base_price": 128.90},
    "AIR":   {"market": "NZX",    "currency": "NZD", "base_price": 0.62},
    "ATM":   {"market": "NZX",    "currency": "NZD", "base_price": 3.28},
    "EBO":   {"market": "NZX",    "currency": "NZD", "base_price": 37.15},
    "FPH":   {"market": "NZX",    "currency": "NZD", "base_price": 34.20},
    "MEL":   {"market": "NZX",    "currency": "NZD", "base_price": 6.10},
    "IFT":   {"market": "NZX",    "currency": "NZD", "base_price": 11.15},
    "MFT":   {"market": "NZX",    "currency": "NZD", "base_price": 7.05},
    "SPK":   {"market": "NZX",    "currency": "NZD", "base_price": 2.35},
    "CEN":   {"market": "NZX",    "currency": "NZD", "base_price": 8.95},
}

TICKERS = list(TICKER_REFERENCE.keys())

# Optional realism: broker pools by market
MARKET_BROKERS = {
    "NZX": ["JPM", "UBS", "CITI"],
    "NASDAQ": ["GS", "JPM", "BAML", "CITI"],
}

# Settlement cycle by market
SETTLEMENT_DAYS = {
    "NZX": 2,
    "NASDAQ": 2,
}


# =========================
# HELPERS
# =========================
def ensure_output_folder():
    """Create the output folder if it doesn't exist."""
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)


def random_trade_date():
    """Return a random trade date within the last 5 days."""
    today = datetime.today().date()
    days_back = random.randint(0, 4)
    return today - timedelta(days=days_back)


def add_business_days(start_date, business_days):
    """Add business days to a date, skipping weekends."""
    current_date = start_date
    days_added = 0

    while days_added < business_days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # Monday=0, Sunday=6
            days_added += 1

    return current_date


def format_date(date_value):
    return date_value.strftime("%Y-%m-%d")


def format_datetime(dt_value):
    return dt_value.strftime("%Y-%m-%d %H:%M:%S")


def make_trade_id(number):
    return f"T{number:05d}"


def make_account_id(number):
    return f"A{number:04d}"


def choose_unique_indices(total_count, issue_count, used_indices=None):
    """
    Return unique row indices for a specific issue type so one booked
    row is not overloaded with multiple random breaks.
    """
    if used_indices is None:
        used_indices = set()

    available_indices = [index for index in range(total_count) if index not in used_indices]
    if not available_indices:
        return []

    selection_size = min(issue_count, len(available_indices))
    selected_indices = random.sample(available_indices, selection_size)
    used_indices.update(selected_indices)
    return selected_indices


def seed_random_for_run(seed=None):
    """
    Seed the random generator once per dataset run so each generation
    is fresh but still reproducible if the seed is captured.
    """
    if seed is None:
        seed = int(datetime.now().timestamp() * 1_000_000)

    random.seed(seed)
    return seed


def resolve_issue_counts():
    """
    Keep the issue mix fresh between runs without letting counts drift
    too far away from the expected demo story.
    """
    return {
        issue_type: random.randint(min_count, max_count)
        for issue_type, (min_count, max_count) in ISSUE_COUNT_RANGES.items()
    }


# =========================
# STEP A: CREATE ACCOUNTS
# =========================
def generate_accounts():
    """
    Create a small accounts reference dataset.
    Some accounts will be inactive so later checks can catch them.
    """
    accounts = []
    for i in range(1, ACCOUNT_COUNT + 1):
        account = {
            "account_id": make_account_id(i),
            "client_name": f"Client_{i}",
            "base_currency": random.choice(CURRENCIES),
            "account_status": "ACTIVE" if i <= ACTIVE_ACCOUNT_COUNT else "INACTIVE"
        }
        accounts.append(account)
    return accounts


# =========================
# STEP B: CREATE CLEAN EXECUTED TRADES
# =========================
def generate_executed_trades(accounts, num_trades):
    """
    Create the clean source-of-truth trade file with realistic
    ticker/market/currency combinations.
    """
    executed_trades = []
    active_accounts = [account for account in accounts if account["account_status"] == "ACTIVE"]

    for i in range(1, num_trades + 1):
        trade_id = make_trade_id(i)
        trade_date = random_trade_date()

        ticker = random.choice(TICKERS)
        ticker_info = TICKER_REFERENCE[ticker]

        market = ticker_info["market"]
        currency = ticker_info["currency"]
        base_price = ticker_info["base_price"]

        settlement_days = SETTLEMENT_DAYS[market]
        settlement_date = add_business_days(trade_date, settlement_days)

        hour = random.randint(9, 16)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        execution_time = datetime.combine(trade_date, datetime.min.time()).replace(
            hour=hour, minute=minute, second=second
        )

        account = random.choice(active_accounts)

        min_price = base_price * (1 - PRICE_VARIATION_PERCENT)
        max_price = base_price * (1 + PRICE_VARIATION_PERCENT)
        price = round(random.uniform(min_price, max_price), 2)

        broker = random.choice(MARKET_BROKERS[market])

        trade = {
            "trade_id": trade_id,
            "account_id": account["account_id"],
            "ticker": ticker,
            "side": random.choice(SIDES),
            "quantity": random.choice([100, 200, 300, 500, 750, 1000, 1500, 2000]),
            "price": price,
            "currency": currency,
            "trade_date": format_date(trade_date),
            "settlement_date": format_date(settlement_date),
            "execution_time": format_datetime(execution_time),
            "broker": broker,
            "market": market,
        }

        executed_trades.append(trade)

    return executed_trades


# =========================
# STEP C: CREATE BOOKED TRADES
# =========================
def generate_booked_trades(executed_trades):
    """
    Start by copying executed trades into booked trades,
    then later inject deliberate errors.
    """
    booked_trades = []

    for trade in executed_trades:
        execution_dt = datetime.strptime(trade["execution_time"], "%Y-%m-%d %H:%M:%S")
        booking_delay_minutes = random.randint(5, 90)
        booking_time = execution_dt + timedelta(minutes=booking_delay_minutes)

        booked_trade = {
            "trade_id": trade["trade_id"],
            "account_id": trade["account_id"],
            "ticker": trade["ticker"],
            "side": trade["side"],
            "quantity": trade["quantity"],
            "price": trade["price"],
            "currency": trade["currency"],
            "trade_date": trade["trade_date"],
            "settlement_date": trade["settlement_date"],
            "status": "BOOKED",
            "booked_by": random.choice(BOOKING_USERS),
            "booking_time": format_datetime(booking_time),
        }

        booked_trades.append(booked_trade)

    return booked_trades


# =========================
# STEP D: INJECT DELIBERATE ERRORS
# =========================
def inject_errors(booked_trades, accounts, executed_trades, issue_counts):
    """
    Deliberately make the booked trades messy so the reconciliation
    tool has exceptions to find.
    """
    if len(booked_trades) < MIN_TRADES_FOR_ISSUES:
        print("Need at least 20 booked trades to inject useful test errors.")
        return booked_trades

    inactive_account_ids = [
        account["account_id"]
        for account in accounts
        if account["account_status"] == "INACTIVE"
    ]

    # 1. Remove some trades entirely to create missing bookings.
    missing_booking_indices = random.sample(
        range(len(booked_trades)),
        min(issue_counts["missing_booking"], len(booked_trades)),
    )
    for remove_index in sorted(missing_booking_indices, reverse=True):
        booked_trades.pop(remove_index)

    used_indices = set()
    base_row_count = len(booked_trades)

    # 2. Duplicate some trade IDs in the booked file.
    duplicate_indices = choose_unique_indices(
        len(booked_trades),
        issue_counts["duplicate_trade_id"],
        used_indices,
    )
    for duplicate_index in duplicate_indices:
        trade_to_duplicate = booked_trades[duplicate_index].copy()
        trade_to_duplicate["booked_by"] = random.choice(BOOKING_USERS)
        booked_trades.append(trade_to_duplicate)

    # 3. Add orphan bookings that have no matching executed trade.
    next_trade_number = len(executed_trades) + 1
    orphan_indices = choose_unique_indices(
        len(booked_trades),
        issue_counts["orphan_booking"],
        used_indices,
    )
    for orphan_index in orphan_indices:
        orphan_trade = booked_trades[orphan_index].copy()
        orphan_trade["trade_id"] = make_trade_id(next_trade_number)
        orphan_trade["booked_by"] = random.choice(BOOKING_USERS)
        booked_trades.append(orphan_trade)
        next_trade_number += 1

    # Keep duplicate and orphan rows focused on those exception types only.
    used_indices = set(duplicate_indices + orphan_indices)
    used_indices.update(range(base_row_count, len(booked_trades)))

    # 4. Quantity mismatches.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["quantity_mismatch"],
        used_indices,
    ):
        booked_trades[issue_index]["quantity"] += random.choice([50, 100, 200])

    # 5. Price mismatches.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["price_mismatch"],
        used_indices,
    ):
        booked_trades[issue_index]["price"] = round(
            float(booked_trades[issue_index]["price"]) + random.uniform(0.5, 5.0),
            2,
        )

    # 6. Currency mismatches.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["currency_mismatch"],
        used_indices,
    ):
        current_currency = booked_trades[issue_index]["currency"]
        possible_currencies = [currency for currency in CURRENCIES if currency != current_currency]
        if possible_currencies:
            booked_trades[issue_index]["currency"] = random.choice(possible_currencies)

    # 7. Missing settlement dates.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["missing_settlement_date"],
        used_indices,
    ):
        booked_trades[issue_index]["settlement_date"] = ""

    # 8. Missing account IDs.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["missing_account_id"],
        used_indices,
    ):
        booked_trades[issue_index]["account_id"] = ""

    # 9. Inactive account usage in booked trades.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["inactive_account_used"],
        used_indices,
    ):
        if inactive_account_ids:
            booked_trades[issue_index]["account_id"] = random.choice(inactive_account_ids)

    # 10. Non-final booking statuses.
    for issue_index in choose_unique_indices(
        len(booked_trades),
        issue_counts["non_final_status"],
        used_indices,
    ):
        booked_trades[issue_index]["status"] = random.choice(BOOKING_STATUS_ISSUES)

    return booked_trades


# =========================
# STEP E: WRITE CSV FILES
# =========================
def write_csv(file_path, rows, fieldnames):
    """Write a list of dictionaries to a CSV file."""
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =========================
# MAIN
# =========================
def main(seed=None):
    ensure_output_folder()
    run_seed = seed_random_for_run(seed if seed is not None else DEFAULT_RANDOM_SEED + int(datetime.now().timestamp() * 1_000_000))
    issue_counts = resolve_issue_counts()

    # 1. Create accounts reference
    accounts = generate_accounts()

    # 2. Create clean executed trades
    executed_trades = generate_executed_trades(accounts, NUM_TRADES)

    # 3. Create booked trades from executed trades
    booked_trades = generate_booked_trades(executed_trades)

    # 4. Inject deliberate errors into booked trades
    booked_trades = inject_errors(booked_trades, accounts, executed_trades, issue_counts)

    # 5. Define fieldnames for each file
    accounts_fields = ["account_id", "client_name", "base_currency", "account_status"]
    executed_fields = [
        "trade_id", "account_id", "ticker", "side", "quantity", "price",
        "currency", "trade_date", "settlement_date", "execution_time",
        "broker", "market"
    ]
    booked_fields = [
        "trade_id", "account_id", "ticker", "side", "quantity", "price",
        "currency", "trade_date", "settlement_date", "status",
        "booked_by", "booking_time"
    ]

    # 6. Write output files
    write_csv(os.path.join(OUTPUT_FOLDER, "accounts_reference.csv"), accounts, accounts_fields)
    write_csv(os.path.join(OUTPUT_FOLDER, "executed_trades.csv"), executed_trades, executed_fields)
    write_csv(os.path.join(OUTPUT_FOLDER, "booked_trades.csv"), booked_trades, booked_fields)

    print("Sample data generated successfully.")
    print(f"Run seed: {run_seed}")
    print(f"Files saved in: {OUTPUT_FOLDER}/")
    print("- accounts_reference.csv")
    print("- executed_trades.csv")
    print("- booked_trades.csv")

    return accounts, executed_trades, booked_trades, run_seed


if __name__ == "__main__":
    main()
    
    