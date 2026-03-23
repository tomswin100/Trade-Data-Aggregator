import os
import sys
from typing import Iterable

import altair as alt
import pandas as pd
import streamlit as st

# =========================
# PATH SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# =========================
# IMPORT BACKEND LOGIC
# =========================
from load_and_validate import (
    ACCOUNTS_FILE,
    BOOKED_TRADES_FILE,
    EXECUTED_TRADES_FILE,
    load_all_data,
)
from validate_data import run_validation_checks
from reconcile_trades import reconcile_executed_vs_booked
from generate_reports import build_daily_summary, combine_all_issues
from ui_styles import apply_shared_styles, render_sidebar_nav


BRAND_BLUE = "#1D4ED8"
BRAND_BLUE_STRONG = "#1E40AF"
BRAND_BLUE_MID = "#3B82F6"
BRAND_BLUE_LIGHT = "#93C5FD"
BRAND_BLUE_SOFT = "#DBEAFE"
BRAND_BLUE_SOFT_ALT = "#BFDBFE"
SUCCESS_GREEN = "#059669"
WARNING_AMBER = "#D97706"
DANGER_RED = "#B91C1C"
SLATE_MUTED = "#94A3B8"

SEVERITY_ORDER = ["High", "Medium", "Low", "Unknown"]
SEVERITY_COLORS = [DANGER_RED, WARNING_AMBER, BRAND_BLUE, SLATE_MUTED]
TRADE_CONTEXT_DOMAIN = ["Executed", "Booked", "Matched", "Report Items"]
TRADE_CONTEXT_COLORS = [BRAND_BLUE, BRAND_BLUE_LIGHT, SUCCESS_GREEN, DANGER_RED]
ISSUE_ORIGIN_DOMAIN = ["Data Check", "Reconciliation Break"]
ISSUE_ORIGIN_COLORS = [BRAND_BLUE, DANGER_RED]
SEQUENTIAL_BLUE_RANGE = [BRAND_BLUE_SOFT, BRAND_BLUE]
BLUE_CATEGORICAL_RANGE = [
    BRAND_BLUE,
    BRAND_BLUE_MID,
    BRAND_BLUE_LIGHT,
    BRAND_BLUE_SOFT_ALT,
    "#E8F1FF",
]

st.set_page_config(
    page_title="Trade Support Dashboard — Trade Exception Monitor",
    page_icon="📈",
    layout="wide",
)
apply_shared_styles()
render_sidebar_nav("Dashboard")


def get_data_signature():
    """Use file timestamps so cached dashboard data refreshes after regeneration."""
    input_files = [EXECUTED_TRADES_FILE, BOOKED_TRADES_FILE, ACCOUNTS_FILE]
    return tuple(os.path.getmtime(path) if os.path.exists(path) else None for path in input_files)


@st.cache_data(show_spinner=False)
def load_dashboard_data(_data_signature):
    """Reload the latest generated data and derive dashboard datasets."""
    executed_df, booked_df, accounts_df = load_all_data()
    validation_df = run_validation_checks(executed_df, booked_df, accounts_df)
    reconciliation_df = reconcile_executed_vs_booked(executed_df, booked_df)
    all_issues_df = combine_all_issues(validation_df, reconciliation_df)
    summary_df = build_daily_summary(executed_df, booked_df, all_issues_df)

    return (
        executed_df,
        booked_df,
        validation_df,
        reconciliation_df,
        all_issues_df,
        summary_df,
    )


def extract_summary_count(summary_df, summary_value):
    matching_rows = summary_df.loc[summary_df["summary_value"] == summary_value, "count"]
    if matching_rows.empty:
        return 0
    return int(matching_rows.iloc[0])


def sort_with_priority(values: Iterable[str]):
    """Keep High/Medium/Low in a business-friendly order."""
    values = [value for value in values if pd.notna(value)]
    ordered = [value for value in SEVERITY_ORDER if value in values]
    remaining = sorted(value for value in values if value not in SEVERITY_ORDER)
    return ordered + remaining


def first_available(series, default_text="Unknown"):
    non_null_values = series.dropna()
    if non_null_values.empty:
        return default_text
    return str(non_null_values.iloc[0])


def ordered_domain(values):
    cleaned_values = [str(value) for value in values if pd.notna(value)]
    return list(dict.fromkeys(cleaned_values))


def categorical_blue_scale(values):
    domain = ordered_domain(values)
    return alt.Scale(domain=domain, range=BLUE_CATEGORICAL_RANGE[: len(domain)])


def build_trade_reference(executed_df, booked_df):
    """Attach descriptive trade attributes to exceptions for filtering and charts."""
    executed_columns = [
        "trade_id",
        "trade_date",
        "settlement_date",
        "ticker",
        "side",
        "account_id",
        "broker",
        "market",
        "currency",
    ]
    booked_columns = [
        "trade_id",
        "trade_date",
        "settlement_date",
        "ticker",
        "side",
        "account_id",
        "status",
        "currency",
    ]

    executed_reference = executed_df[executed_columns].drop_duplicates(subset=["trade_id"], keep="first")
    booked_reference = booked_df[booked_columns].drop_duplicates(subset=["trade_id"], keep="first")

    trade_reference = executed_reference.merge(
        booked_reference,
        on="trade_id",
        how="outer",
        suffixes=("_executed", "_booked"),
    )

    combined_fields = {
        "trade_date": ("trade_date_executed", "trade_date_booked"),
        "settlement_date": ("settlement_date_executed", "settlement_date_booked"),
        "ticker": ("ticker_executed", "ticker_booked"),
        "side": ("side_executed", "side_booked"),
        "account_id": ("account_id_executed", "account_id_booked"),
        "currency": ("currency_executed", "currency_booked"),
    }

    for final_column, (executed_column, booked_column) in combined_fields.items():
        trade_reference[final_column] = trade_reference[executed_column].combine_first(
            trade_reference[booked_column]
        )

    trade_reference["booking_status"] = trade_reference["status"]

    return trade_reference[
        [
            "trade_id",
            "trade_date",
            "settlement_date",
            "ticker",
            "side",
            "account_id",
            "currency",
            "broker",
            "market",
            "booking_status",
        ]
    ]


def enrich_issues(all_issues_df, executed_df, booked_df):
    """Blend issue-level data with trade attributes for filtering and storytelling."""
    if all_issues_df.empty:
        enriched_df = all_issues_df.copy()
        enriched_df["issue_origin"] = pd.Series(dtype="object")
        enriched_df["trade_day"] = pd.Series(dtype="datetime64[ns]")
        return enriched_df

    enriched_df = all_issues_df.copy()
    comparison_values_present = (
        enriched_df["executed_value"].fillna("").astype(str).str.strip().ne("")
        | enriched_df["booked_value"].fillna("").astype(str).str.strip().ne("")
    )
    enriched_df["issue_origin"] = comparison_values_present.map(
        {True: "Reconciliation Break", False: "Data Check"}
    )

    trade_reference = build_trade_reference(executed_df, booked_df)
    enriched_df = enriched_df.merge(trade_reference, on="trade_id", how="left")

    enriched_df["trade_day"] = pd.to_datetime(enriched_df["trade_date"], errors="coerce").dt.normalize()
    enriched_df["ticker"] = enriched_df["ticker"].fillna("Unknown")
    enriched_df["market"] = enriched_df["market"].fillna("Unknown")
    enriched_df["broker"] = enriched_df["broker"].fillna("Unknown")

    return enriched_df


def build_trade_context_df(summary_df):
    """Show where exceptions sit within overall trade processing volume."""
    return pd.DataFrame(
        [
            {"metric": "Executed", "count": extract_summary_count(summary_df, "total_executed_trades")},
            {"metric": "Booked", "count": extract_summary_count(summary_df, "total_booked_trades")},
            {"metric": "Matched", "count": extract_summary_count(summary_df, "total_matched_trades")},
            {"metric": "Report Items", "count": extract_summary_count(summary_df, "total_exceptions")},
        ]
    )


def build_exception_type_chart(filtered_df):
    chart_data = (
        filtered_df.groupby(["exception_type", "severity"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    chart_data["severity"] = chart_data["severity"].fillna("Unknown")
    chart_data["severity_order"] = chart_data["severity"].map(
        {severity: index for index, severity in enumerate(SEVERITY_ORDER)}
    ).fillna(len(SEVERITY_ORDER))

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("count:Q", title="Report items"),
            y=alt.Y(
                "exception_type:N",
                title=None,
                sort=alt.SortField(field="count", order="descending"),
            ),
            color=alt.Color(
                "severity:N",
                title="Severity",
                scale=alt.Scale(domain=SEVERITY_ORDER, range=SEVERITY_COLORS),
            ),
            order=alt.Order("severity_order:Q"),
            tooltip=["exception_type", "severity", "count"],
        )
        .properties(title="Which booking errors and break types are driving this run?", height=360)
    )


def build_source_heatmap(filtered_df):
    chart_data = (
        filtered_df.groupby(["source_file", "exception_type"], dropna=False)
        .size()
        .reset_index(name="count")
    )

    return (
        alt.Chart(chart_data)
        .mark_rect()
        .encode(
            x=alt.X("source_file:N", title=None),
            y=alt.Y("exception_type:N", title=None),
            color=alt.Color("count:Q", title="Count", scale=alt.Scale(range=SEQUENTIAL_BLUE_RANGE)),
            tooltip=["source_file", "exception_type", "count"],
        )
        .properties(title="Where are exception report hotspots coming from?", height=360)
    )


def build_trade_context_chart(summary_df):
    chart_data = build_trade_context_df(summary_df)

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("metric:N", title=None),
            y=alt.Y("count:Q", title="Trades / issues"),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(domain=TRADE_CONTEXT_DOMAIN, range=TRADE_CONTEXT_COLORS),
            ),
            tooltip=["metric", "count"],
        )
        .properties(title="How large is the trade flow relative to the exception report?", height=360)
    )


def build_trade_volume_by_date_chart(executed_df):
    chart_data = executed_df.copy()
    chart_data["trade_day"] = pd.to_datetime(chart_data["trade_date"], errors="coerce").dt.normalize()
    chart_data = (
        chart_data.dropna(subset=["trade_day"])
        .groupby(["trade_day", "market"], dropna=False)
        .size()
        .reset_index(name="count")
    )

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("trade_day:T", title="Trade date"),
            y=alt.Y("count:Q", title="Trades"),
            color=alt.Color(
                "market:N",
                title="Market",
                scale=categorical_blue_scale(chart_data["market"].tolist()),
            ),
            tooltip=["trade_day:T", "market", "count"],
        )
        .properties(title="Trade volume by date", height=320)
    )


def build_trade_side_chart(executed_df):
    chart_data = executed_df.groupby(["side", "market"], dropna=False).size().reset_index(name="count")

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("side:N", title=None),
            y=alt.Y("count:Q", title="Trades"),
            color=alt.Color(
                "market:N",
                title="Market",
                scale=categorical_blue_scale(chart_data["market"].tolist()),
            ),
            tooltip=["side", "market", "count"],
        )
        .properties(title="Buy / sell mix", height=320)
    )


def build_trade_market_chart(executed_df):
    chart_data = executed_df.groupby("market", dropna=False).size().reset_index(name="count")

    return (
        alt.Chart(chart_data)
        .mark_arc(innerRadius=70)
        .encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color(
                "market:N",
                title="Market",
                scale=categorical_blue_scale(chart_data["market"].tolist()),
            ),
            tooltip=["market", "count"],
        )
        .properties(title="Trade distribution by market", height=320)
    )


def build_trade_ticker_chart(executed_df):
    chart_data = (
        executed_df.groupby("ticker", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("count:Q", title="Trades"),
            y=alt.Y("ticker:N", title=None, sort="-x"),
            color=alt.value(BRAND_BLUE),
            tooltip=["ticker", "count"],
        )
        .properties(title="Most traded tickers", height=320)
    )


def build_trade_broker_chart(executed_df):
    chart_data = (
        executed_df.groupby("broker", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("count:Q", title="Trades"),
            y=alt.Y("broker:N", title=None, sort="-x"),
            color=alt.value(BRAND_BLUE_STRONG),
            tooltip=["broker", "count"],
        )
        .properties(title="Broker activity", height=320)
    )


def build_ticker_chart(filtered_df):
    chart_data = (
        filtered_df.groupby("ticker", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("count:Q", title="Report items"),
            y=alt.Y("ticker:N", title=None, sort="-x"),
            color=alt.value(DANGER_RED),
            tooltip=["ticker", "count"],
        )
        .properties(title="Most affected tickers", height=320)
    )


def build_trend_or_market_chart(filtered_df):
    dated_df = filtered_df.dropna(subset=["trade_day"]).copy()

    if dated_df["trade_day"].nunique() > 1:
        chart_data = (
            dated_df.groupby(["trade_day", "severity"], dropna=False)
            .size()
            .reset_index(name="count")
        )
        chart_data["severity"] = chart_data["severity"].fillna("Unknown")

        return (
            alt.Chart(chart_data)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                x=alt.X("trade_day:T", title="Trade date"),
                y=alt.Y("count:Q", title="Report items"),
                color=alt.Color(
                    "severity:N",
                    title="Severity",
                    scale=alt.Scale(domain=SEVERITY_ORDER, range=SEVERITY_COLORS),
                ),
                tooltip=["trade_day:T", "severity", "count"],
            )
            .properties(title="Are report items concentrated on particular trade dates?", height=320)
        )

    chart_data = (
        filtered_df.groupby(["market", "severity"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    chart_data["severity"] = chart_data["severity"].fillna("Unknown")

    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("count:Q", title="Report items"),
            y=alt.Y("market:N", title=None, sort="-x"),
            color=alt.Color(
                "severity:N",
                title="Severity",
                scale=alt.Scale(domain=SEVERITY_ORDER, range=SEVERITY_COLORS),
            ),
            tooltip=["market", "severity", "count"],
        )
        .properties(title="Where are booking errors and breaks concentrated by market?", height=320)
    )


def build_insight_text(filtered_df):
    if filtered_df.empty:
        return "No exception report items match the selected filters."

    top_exception_type = first_available(filtered_df["exception_type"].value_counts().index.to_series())
    top_exception_count = int(filtered_df["exception_type"].value_counts().iloc[0])
    exception_share = round((top_exception_count / len(filtered_df)) * 100)

    high_severity_count = int((filtered_df["severity"] == "High").sum())
    affected_trades = filtered_df["trade_id"].dropna().nunique()
    top_source = first_available(filtered_df["source_file"].value_counts().index.to_series())
    top_ticker = first_available(filtered_df["ticker"].value_counts().index.to_series())

    return (
        f"`{top_exception_type}` is the main issue driver in the current view "
        f"with {top_exception_count} cases ({exception_share}% of filtered issues). "
        f"{high_severity_count} high-severity items are currently in scope, spanning "
        f"{affected_trades} impacted trades. The heaviest concentration is in `{top_source}`, "
        f"with `{top_ticker}` appearing most often."
    )


def build_run_summary_text(df):
    if df.empty:
        return "No exception report items were generated for the current run."

    validation_count = int((df["issue_origin"] == "Data Check").sum())
    reconciliation_count = int((df["issue_origin"] == "Reconciliation Break").sum())
    top_severity = "High" if int((df["severity"] == "High").sum()) > 0 else "Medium"

    dominant_issue_origin = (
        "reconciliation breaks" if reconciliation_count >= validation_count else "data checks"
    )

    return (
        f"This run produced {len(df)} exception report items across {df['trade_id'].dropna().nunique()} trades. "
        f"The current issue mix is led by {dominant_issue_origin}, with "
        f"{validation_count} data-check items and {reconciliation_count} reconciliation breaks in scope. "
        f"Priority review should focus on the {top_severity.lower()}-severity items first."
    )


def render_snapshot_metrics(df):
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Report items in view", len(df))
    metric_col2.metric("Trades affected", df["trade_id"].dropna().nunique())
    metric_col3.metric("High severity", int((df["severity"] == "High").sum()))
    metric_col4.metric("Medium severity", int((df["severity"] == "Medium").sum()))
    st.caption(
        "`Trades affected` counts distinct trade IDs in the current view. "
        "`High severity` and `Medium severity` show the current investigation priority."
    )


def render_issue_table(df, heading):
    st.markdown(heading)
    st.caption("Use this table as the investigation queue for the filtered exception report.")
    preview_columns = [
        "trade_id",
        "exception_type",
        "severity",
        "source_file",
        "market",
        "broker",
        "recommended_action",
        "status",
    ]
    st.dataframe(df[preview_columns], use_container_width=True, height=420)


def render_severity_origin_chart(df, title):
    severity_breakdown = (
        df.groupby(["severity", "issue_origin"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    severity_breakdown["severity"] = severity_breakdown["severity"].fillna("Unknown")

    severity_chart = (
        alt.Chart(severity_breakdown)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("severity:N", title=None, sort=sort_with_priority(severity_breakdown["severity"].tolist())),
            y=alt.Y("count:Q", title="Report items"),
            color=alt.Color(
                "issue_origin:N",
                title="Issue origin",
                scale=alt.Scale(domain=ISSUE_ORIGIN_DOMAIN, range=ISSUE_ORIGIN_COLORS),
            ),
            tooltip=["severity", "issue_origin", "count"],
        )
        .properties(title=title, height=320)
    )
    st.altair_chart(severity_chart, use_container_width=True)


def render_split_section(section_name, section_df, description, secondary_chart):
    st.markdown(f"#### {section_name}")
    st.caption(description)

    if section_df.empty:
        st.info(f"No {section_name.lower()} items match the current filters.")
        return

    render_snapshot_metrics(section_df)
    st.info(build_insight_text(section_df))

    row1_col1, row1_col2 = st.columns((1.25, 1))
    with row1_col1:
        st.altair_chart(build_exception_type_chart(section_df), use_container_width=True)
    with row1_col2:
        st.altair_chart(secondary_chart(section_df), use_container_width=True)

    row2_col1, row2_col2 = st.columns((1.1, 1))
    with row2_col1:
        st.altair_chart(build_source_heatmap(section_df), use_container_width=True)
    with row2_col2:
        render_severity_origin_chart(section_df, f"{section_name} severity mix")

    render_issue_table(section_df, f"#### {section_name} items")


def render_trade_tab(executed_df, booked_df, summary_df):
    st.markdown("#### Trade overview")
    st.caption("A general view of the trade population behind the exception analysis.")

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Executed trades", len(executed_df))
    metric_col2.metric("Booked trades", len(booked_df))
    metric_col3.metric("Matched trades", extract_summary_count(summary_df, "total_matched_trades"))
    metric_col4.metric("Markets covered", executed_df["market"].dropna().nunique())

    row1_col1, row1_col2 = st.columns((1.5, 1))
    with row1_col1:
        st.altair_chart(build_trade_volume_by_date_chart(executed_df), use_container_width=True)
    with row1_col2:
        st.altair_chart(build_trade_market_chart(executed_df), use_container_width=True)

    row2_col1, row2_col2 = st.columns((1, 1))
    with row2_col1:
        st.altair_chart(build_trade_side_chart(executed_df), use_container_width=True)
    with row2_col2:
        st.altair_chart(build_trade_ticker_chart(executed_df), use_container_width=True)

    row3_col1, row3_col2 = st.columns((1, 1))
    with row3_col1:
        st.altair_chart(build_trade_broker_chart(executed_df), use_container_width=True)
    with row3_col2:
        currency_mix = (
            executed_df.groupby("currency", dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        currency_chart = (
            alt.Chart(currency_mix)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("currency:N", title=None),
                y=alt.Y("count:Q", title="Trades"),
                color=alt.Color(
                    "currency:N",
                    title="Currency",
                    scale=categorical_blue_scale(currency_mix["currency"].tolist()),
                ),
                tooltip=["currency", "count"],
            )
            .properties(title="Currency mix", height=320)
        )
        st.altair_chart(currency_chart, use_container_width=True)

    st.markdown("#### Trade data preview")
    preview_columns = [
        "trade_id",
        "trade_date",
        "ticker",
        "side",
        "quantity",
        "price",
        "currency",
        "broker",
        "market",
    ]
    st.dataframe(executed_df[preview_columns], use_container_width=True, height=420)


st.title("Trade Support Dashboard")
st.write(
    "A chart-first view of booking errors, reconciliation breaks, exception report patterns, "
    "and lightweight trade support insights for the latest synthetic equity trade run."
)

try:
    data_signature = get_data_signature()
    if any(signature is None for signature in data_signature):
        raise FileNotFoundError

    with st.spinner("Loading the latest trade and exception data..."):
        (
            executed_df,
            booked_df,
            validation_df,
            reconciliation_df,
            all_issues_df,
            summary_df,
        ) = load_dashboard_data(data_signature)

except FileNotFoundError:
    st.info(
        "No generated trade files were found yet. Open the main app page, generate demo data, "
        "and then return here for the trade support dashboard."
    )
    st.stop()
except Exception as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()

dashboard_df = enrich_issues(all_issues_df, executed_df, booked_df)

st.sidebar.header("Trade support filters")

severity_options = sort_with_priority(dashboard_df["severity"].dropna().unique().tolist())
selected_severities = st.sidebar.multiselect(
    "Severity",
    options=severity_options,
    default=severity_options,
)

exception_options = sorted(dashboard_df["exception_type"].dropna().unique().tolist())
selected_exceptions = st.sidebar.multiselect(
    "Issue type",
    options=exception_options,
    default=exception_options,
)

source_options = sorted(dashboard_df["source_file"].dropna().unique().tolist())
selected_sources = st.sidebar.multiselect(
    "Source file",
    options=source_options,
    default=source_options,
)

market_options = sorted(dashboard_df["market"].dropna().unique().tolist())
selected_markets = st.sidebar.multiselect(
    "Market",
    options=market_options,
    default=market_options,
)

broker_options = sorted(dashboard_df["broker"].dropna().unique().tolist())
selected_brokers = st.sidebar.multiselect(
    "Broker",
    options=broker_options,
    default=broker_options,
)

filtered_df = dashboard_df.copy()

if selected_severities:
    filtered_df = filtered_df[filtered_df["severity"].isin(selected_severities)]

if selected_exceptions:
    filtered_df = filtered_df[filtered_df["exception_type"].isin(selected_exceptions)]

if selected_sources:
    filtered_df = filtered_df[filtered_df["source_file"].isin(selected_sources)]

if selected_markets:
    filtered_df = filtered_df[filtered_df["market"].isin(selected_markets)]

if selected_brokers:
    filtered_df = filtered_df[filtered_df["broker"].isin(selected_brokers)]

available_trade_days = sorted(
    {pd.Timestamp(trade_day).date() for trade_day in filtered_df["trade_day"].dropna().tolist()}
)
if available_trade_days:
    min_trade_day = available_trade_days[0]
    max_trade_day = available_trade_days[-1]
    selected_trade_days = st.sidebar.slider(
        "Trade date range",
        min_value=min_trade_day,
        max_value=max_trade_day,
        value=(min_trade_day, max_trade_day),
    )
    start_day, end_day = selected_trade_days
    filtered_df = filtered_df[
        filtered_df["trade_day"].isna()
        | (
            (filtered_df["trade_day"].dt.date >= start_day)
            & (filtered_df["trade_day"].dt.date <= end_day)
        )
    ]

filtered_summary_df = summary_df.copy()

if filtered_df.empty:
    st.warning("The current filter combination returned no report items. Adjust the filters to see charts.")
    st.stop()

overview_tab, validation_tab, reconciliation_tab, trades_tab = st.tabs(
    ["Overview", "Data Checks", "Reconciliation Breaks", "Trades"]
)

validation_df_filtered = filtered_df[filtered_df["issue_origin"] == "Data Check"].copy()
reconciliation_df_filtered = filtered_df[filtered_df["issue_origin"] == "Reconciliation Break"].copy()

with overview_tab:
    st.markdown("#### Snapshot")
    st.caption("Use this view to understand the main booking errors and reconciliation breaks before drilling deeper.")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Report items in view", len(filtered_df))
    metric_col2.metric("Trades affected", filtered_df["trade_id"].dropna().nunique())
    metric_col3.metric("Data check items", len(validation_df_filtered))
    metric_col4.metric("Reconciliation breaks", len(reconciliation_df_filtered))
    st.caption(
        "`Data check items` are data-quality or reference-data problems. "
        "`Reconciliation breaks` are differences between executed and booked trades."
    )

    st.info(build_run_summary_text(filtered_df))
    st.info(build_insight_text(filtered_df))

    row1_col1, row1_col2 = st.columns((1.5, 1))
    with row1_col1:
        st.altair_chart(build_exception_type_chart(filtered_df), use_container_width=True)
    with row1_col2:
        st.altair_chart(build_trade_context_chart(filtered_summary_df), use_container_width=True)

    row2_col1, row2_col2 = st.columns((1.25, 1))
    with row2_col1:
        st.altair_chart(build_source_heatmap(filtered_df), use_container_width=True)
    with row2_col2:
        st.altair_chart(build_ticker_chart(filtered_df), use_container_width=True)

    row3_col1, row3_col2 = st.columns((1, 1))
    with row3_col1:
        st.altair_chart(build_trend_or_market_chart(filtered_df), use_container_width=True)
    with row3_col2:
        render_severity_origin_chart(filtered_df, "Severity mix by issue origin")

    render_issue_table(filtered_df, "#### Filtered exception report")

with validation_tab:
    render_split_section(
        section_name="Data Checks",
        section_df=validation_df_filtered,
        description="Data-quality and reference-data checks such as missing values, inactive accounts, and duplicate records.",
        secondary_chart=build_trend_or_market_chart,
    )

with reconciliation_tab:
    render_split_section(
        section_name="Reconciliation Breaks",
        section_df=reconciliation_df_filtered,
        description="Executed-versus-booked trade breaks such as missing bookings, orphan bookings, and field mismatches.",
        secondary_chart=build_ticker_chart,
    )

with trades_tab:
    render_trade_tab(executed_df, booked_df, filtered_summary_df)
