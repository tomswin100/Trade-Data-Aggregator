import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st
import graphviz

# =========================
# PATH SETUP
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# =========================
# IMPORT BACKEND LOGIC
# =========================
from generate_sample_data import main as generate_demo_data
from load_and_validate import load_all_data
from validate_data import run_validation_checks
from reconcile_trades import reconcile_executed_vs_booked
from generate_reports import (
    combine_all_issues,
    build_daily_summary,
    write_exceptions_report_excel,
    save_daily_summary,
    EXCEPTIONS_REPORT_FILE,
    DAILY_SUMMARY_FILE,
)
from ui_styles import apply_shared_styles, render_sidebar_nav

# =========================
# ENSURE OUTPUT FOLDER EXISTS
# =========================
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Trade Exception Monitor — Demo",
    page_icon="📊",
    layout="wide",
)
apply_shared_styles()
render_sidebar_nav("Workflow")

# =========================
# SESSION STATE SETUP
# =========================
if "demo_data_generated" not in st.session_state:
    st.session_state.demo_data_generated = False

if "accounts_preview" not in st.session_state:
    st.session_state.accounts_preview = None

if "executed_preview" not in st.session_state:
    st.session_state.executed_preview = None

if "booked_preview" not in st.session_state:
    st.session_state.booked_preview = None

if "run_log" not in st.session_state:
    st.session_state.run_log = []

if "validation_df" not in st.session_state:
    st.session_state.validation_df = pd.DataFrame()

if "reconciliation_df" not in st.session_state:
    st.session_state.reconciliation_df = pd.DataFrame()

if "all_issues_df" not in st.session_state:
    st.session_state.all_issues_df = pd.DataFrame()

if "summary_df" not in st.session_state:
    st.session_state.summary_df = pd.DataFrame()

if "report_time" not in st.session_state:
    st.session_state.report_time = None

if "checks_run" not in st.session_state:
    st.session_state.checks_run = False

if "demo_run_seed" not in st.session_state:
    st.session_state.demo_run_seed = None

# =========================
# PAGE HEADER
# =========================
st.markdown(
    """
    <style>
    .hero-eyebrow {
        display: inline-block;
        font-size: 0.77rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #1d4ed8;
        background: #dbeafe;
        border: 1px solid #bfdbfe;
        border-radius: 999px;
        padding: 0.26rem 0.58rem;
        margin-bottom: 0.9rem;
    }

    .hero-eyebrow-wrap {
        text-align: center;
    }

    .hero-panel {
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        border: 1px solid #d9e2ec;
        border-radius: 24px;
        padding: 1.75rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
        position: relative;
        overflow: hidden;
    }

    .hero-panel::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 5px;
        background: linear-gradient(180deg, #1d4ed8 0%, #93c5fd 100%);
    }

    .hero-title {
        font-size: 2.05rem;
        font-weight: 750;
        color: #0f172a;
        line-height: 1.15;
        margin-bottom: 0.9rem;
        letter-spacing: -0.02em;
        text-align: center;
    }

    .hero-copy {
        color: #334155;
        font-size: 1rem;
        line-height: 1.72;
        max-width: 920px;
        margin: 0 auto;
        text-align: center;
    }

    .overview-card {
        background: #ffffff;
        border: 1px solid #d9e2ec;
        border-radius: 18px;
        padding: 1.15rem 1.1rem;
        min-height: 180px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.045);
        position: relative;
    }

    .overview-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.58rem;
        display: flex;
        align-items: center;
        gap: 0.55rem;
    }

    .overview-card-marker {
        width: 11px;
        height: 11px;
        border-radius: 999px;
        background: #1d4ed8;
        box-shadow: 0 0 0 5px #dbeafe;
        flex-shrink: 0;
    }

    .overview-card-body {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #475569;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-panel">
        <div class="hero-eyebrow-wrap">
            <div class="hero-eyebrow">Post-Trade Controls Demo</div>
        </div>
        <div class="hero-title">Trade Exception Monitor — Demo</div>
        <p class="hero-copy">
            This workflow helps trade support teams identify where executed trades and booked trades do not align.
            It surfaces exceptions such as missing bookings, mismatched quantities, pricing discrepancies, and account-reference issues in a format that can be monitored and investigated quickly.
            The goal is to turn raw trade records into clear operational signals for faster exception management and cleaner post-trade control.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

card_col1, card_col2, card_col3 = st.columns(3)

with card_col1:
    st.markdown(
        """
        <div class="overview-card">
            <div class="overview-card-title"><span class="overview-card-marker"></span>Randomised Data Generation</div>
            <p class="overview-card-body">
                Synthetic institutional-style trade logs are generated to emulate executed and booked trade activity for exception testing and workflow demonstration.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col2:
    st.markdown(
        """
        <div class="overview-card">
            <div class="overview-card-title"><span class="overview-card-marker"></span>Python Data Processing</div>
            <p class="overview-card-body">
                Python logic cleans, standardises, compares, and aggregates trade records to identify booking errors, reconciliation breaks, and static-data issues.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col3:
    st.markdown(
        """
        <div class="overview-card">
            <div class="overview-card-title"><span class="overview-card-marker"></span>Dashboard and Reporting Output</div>
            <p class="overview-card-body">
                Exceptions are transformed into summary views, charts, and monitoring outputs so support teams can quickly investigate operational breaks.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption(
    "Use the sidebar to move between the workflow view, the trade support dashboard, and the Python workflow."
)

st.subheader("Workflow overview")
st.caption("A high-level view of how generated trade records move through checks, reconciliation, and reporting.")

workflow = graphviz.Digraph()
workflow.attr(rankdir="LR", splines="spline", bgcolor="transparent", nodesep="0.6", ranksep="1.0")
workflow.attr("node", shape="box", style="filled,rounded", fontname="Helvetica", fontsize="11")
workflow.attr("edge", color="#94a3b8", penwidth="1.4")

# Nodes
workflow.node(
    "A",
    "Generate\nDemo Data",
    fillcolor="#1d4ed8",
    fontcolor="white",
    color="#1d4ed8",
)

workflow.node(
    "B",
    "Accounts\nReference",
    fillcolor="#dbeafe",
    fontcolor="#0f172a",
    color="#93c5fd",
)

workflow.node(
    "C",
    "Booked Trades\n(with seeded breaks)",
    fillcolor="#dbeafe",
    fontcolor="#0f172a",
    color="#93c5fd",
)

workflow.node(
    "D",
    "Executed\nTrades",
    fillcolor="#dbeafe",
    fontcolor="#0f172a",
    color="#93c5fd",
)

workflow.node(
    "E",
    "Data Checks",
    fillcolor="#bfdbfe",
    fontcolor="#0f172a",
    color="#60a5fa",
)

workflow.node(
    "F",
    "Reconciliation\nChecks",
    fillcolor="#bfdbfe",
    fontcolor="#0f172a",
    color="#60a5fa",
)

workflow.node(
    "G",
    "Exception\nReport",
    fillcolor="#ffffff",
    fontcolor="#0f172a",
    color="#1d4ed8",
)

workflow.node(
    "H",
    "Daily\nSummary",
    fillcolor="#ffffff",
    fontcolor="#0f172a",
    color="#1d4ed8",
)

# Keep the three data sources vertically aligned
with workflow.subgraph() as s:
    s.attr(rank="same")
    s.node("B")
    s.node("C")
    s.node("D")

# Outputs aligned
with workflow.subgraph() as s:
    s.attr(rank="same")
    s.node("G")
    s.node("H")

# Edges
workflow.edge("A", "B")
workflow.edge("A", "C")
workflow.edge("A", "D")

workflow.edge("B", "E")
workflow.edge("C", "E")
workflow.edge("C", "F")
workflow.edge("D", "F")

workflow.edge("E", "G")
workflow.edge("F", "G")
workflow.edge("F", "H")

st.graphviz_chart(workflow, use_container_width=True)
# =========================
# 1. GENERATE DEMO DATA
# =========================
st.subheader("1. Generate demo data")

if st.button("Generate Demo Data", type="secondary"):
    try:
        st.session_state.run_log = []
        st.session_state.run_log.append("Started demo data generation.")

        result = generate_demo_data()
        if result is None:
            raise ValueError(
                "generate_demo_data() returned None. "
                "Check generate_sample_data.py and ensure main() returns "
                "(accounts, executed_trades, booked_trades)."
            )

        if len(result) == 4:
            accounts, executed_trades, booked_trades, run_seed = result
        else:
            accounts, executed_trades, booked_trades = result
            run_seed = None

        st.session_state.demo_data_generated = True
        st.session_state.accounts_preview = pd.DataFrame(accounts)
        st.session_state.executed_preview = pd.DataFrame(executed_trades)
        st.session_state.booked_preview = pd.DataFrame(booked_trades)
        st.session_state.demo_run_seed = run_seed

        st.session_state.run_log.append("Generated accounts reference dataset.")
        st.session_state.run_log.append("Generated executed trades dataset.")
        st.session_state.run_log.append("Generated booked trades dataset with seeded booking errors.")
        if run_seed is not None:
            st.session_state.run_log.append(f"Generated fresh dataset using run seed {run_seed}.")
        st.session_state.run_log.append("Saved demo CSV files to the data folder.")

        # reset prior results
        st.session_state.validation_df = pd.DataFrame()
        st.session_state.reconciliation_df = pd.DataFrame()
        st.session_state.all_issues_df = pd.DataFrame()
        st.session_state.summary_df = pd.DataFrame()
        st.session_state.report_time = None
        st.session_state.checks_run = False

        st.success("Fresh demo data generated successfully.")

    except Exception as e:
        st.error(f"Error generating demo data: {e}")

# =========================
# 2. PREVIEW GENERATED DATA
# =========================
if st.session_state.demo_data_generated:
    st.subheader("2. Preview generated data")
    if st.session_state.demo_run_seed is not None:
        st.caption(f"Latest generated dataset seed: `{st.session_state.demo_run_seed}`")

    tab1, tab2, tab3 = st.tabs(["Accounts", "Executed Trades", "Booked Trades"])

    with tab1:
        st.write(f"Rows: {len(st.session_state.accounts_preview)}")
        st.dataframe(
            st.session_state.accounts_preview,
            use_container_width=True,
            height=450
        )

    with tab2:
        st.write(f"Rows: {len(st.session_state.executed_preview)}")
        st.dataframe(
            st.session_state.executed_preview,
            use_container_width=True,
            height=450
        )

    with tab3:
        st.write(f"Rows: {len(st.session_state.booked_preview)}")
        st.dataframe(
            st.session_state.booked_preview,
            use_container_width=True,
            height=450
        )

# =========================
# 3. RUN DATA CHECKS AND RECONCILIATION
# =========================
if st.session_state.demo_data_generated:
    st.subheader("3. Run data checks and reconciliation")
    run_checks = st.button("Run Checks", type="primary")
else:
    st.subheader("3. Run data checks and reconciliation")
    st.info("Generate demo data first to enable data checks and reconciliation.")
    run_checks = False
    
if run_checks:
    try:
        st.session_state.run_log = []

        # Load data
        executed_df, booked_df, accounts_df = load_all_data()
        st.session_state.run_log.append("Loaded executed_trades.csv.")
        st.session_state.run_log.append("Loaded booked_trades.csv.")
        st.session_state.run_log.append("Loaded accounts_reference.csv.")

        # Data checks
        validation_df = run_validation_checks(executed_df, booked_df, accounts_df)
        st.session_state.run_log.append(
            f"Data checks completed: {len(validation_df)} items found."
        )

        # Reconciliation
        reconciliation_df = reconcile_executed_vs_booked(executed_df, booked_df)
        st.session_state.run_log.append(
            f"Reconciliation completed: {len(reconciliation_df)} breaks found."
        )

        # Combine + summary
        all_issues_df = combine_all_issues(validation_df, reconciliation_df)
        summary_df = build_daily_summary(executed_df, booked_df, all_issues_df)
        st.session_state.run_log.append(
            f"Exception report prepared: {len(all_issues_df)} total items."
        )

        # Write reports
        write_exceptions_report_excel(all_issues_df, executed_df, booked_df)
        save_daily_summary(summary_df)
        st.session_state.run_log.append("Generated exceptions_report.xlsx.")
        st.session_state.run_log.append("Generated daily_summary.csv.")

        # Save to session state
        st.session_state.validation_df = validation_df
        st.session_state.reconciliation_df = reconciliation_df
        st.session_state.all_issues_df = all_issues_df
        st.session_state.summary_df = summary_df
        st.session_state.report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.checks_run = True

        st.success("Data checks and reconciliation completed successfully.")
        st.success("Reports generated successfully.")

    except Exception as e:
        st.error(f"Error: {e}")

# =========================
# 4. REVIEW OUTPUTS
# =========================
if st.session_state.checks_run:
    st.subheader("4. Review outputs")

    validation_df = st.session_state.validation_df
    reconciliation_df = st.session_state.reconciliation_df
    all_issues_df = st.session_state.all_issues_df
    summary_df = st.session_state.summary_df

    # Summary metrics
    total_executed = 0
    total_booked = 0
    total_matched = 0
    total_exceptions = len(all_issues_df)

    if not summary_df.empty:
        matched_rows = summary_df.loc[
            summary_df["summary_value"] == "total_matched_trades", "count"
        ]
        executed_rows = summary_df.loc[
            summary_df["summary_value"] == "total_executed_trades", "count"
        ]
        booked_rows = summary_df.loc[
            summary_df["summary_value"] == "total_booked_trades", "count"
        ]

        if not executed_rows.empty:
            total_executed = int(executed_rows.iloc[0])
        if not booked_rows.empty:
            total_booked = int(booked_rows.iloc[0])
        if not matched_rows.empty:
            total_matched = int(matched_rows.iloc[0])

    if all_issues_df.empty:
        run_summary_text = "This run produced no exception report items."
    else:
        top_exception_type = all_issues_df["exception_type"].value_counts().idxmax()
        top_exception_count = int(all_issues_df["exception_type"].value_counts().iloc[0])
        run_summary_text = (
            f"This run produced {len(all_issues_df)} exception report items across "
            f"{all_issues_df['trade_id'].dropna().nunique()} affected trades. "
            f"`{top_exception_type}` is currently the largest booking error / break driver with "
            f"{top_exception_count} case(s)."
        )

    st.info(run_summary_text)

    st.markdown("#### Summary metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Executed trades", total_executed)
    c2.metric("Booked trades", total_booked)
    c3.metric("Matched trades", total_matched)
    c4.metric("Exception report items", total_exceptions)
    st.caption(
        "`Matched trades` are trade IDs present in both executed and booked datasets. "
        "`Exception report items` combines data-check items and reconciliation breaks."
    )

    # Issue breakdown
    high_count = len(all_issues_df[all_issues_df["severity"] == "High"]) if not all_issues_df.empty else 0
    medium_count = len(all_issues_df[all_issues_df["severity"] == "Medium"]) if not all_issues_df.empty else 0

    st.markdown("#### Issue breakdown")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Data check items", len(validation_df))
    b2.metric("Reconciliation breaks", len(reconciliation_df))
    b3.metric("High severity", high_count)
    b4.metric("Medium severity", medium_count)
    st.caption(
        "`Data check items` capture data-quality or reference-data problems. "
        "`Reconciliation breaks` capture differences between executed and booked trades."
    )

    # Run log
    st.markdown("#### Run log")
    if st.session_state.run_log:
        for message in st.session_state.run_log:
            st.write(f"- {message}")
    else:
        st.write("No run activity yet.")

    # Data checks preview
    st.markdown("#### Data check items preview")
    if validation_df.empty:
        st.write("No data check items found.")
    else:
        st.dataframe(validation_df, use_container_width=True, height=300)

    # Reconciliation preview
    st.markdown("#### Reconciliation breaks preview")
    if reconciliation_df.empty:
        st.write("No reconciliation breaks found.")
    else:
        st.dataframe(reconciliation_df, use_container_width=True, height=300)

    # Exception report preview
    st.markdown("#### Exception report preview")
    if all_issues_df.empty:
        st.success("No exception report items found.")
    else:
        st.caption("Use the filters below to narrow the exception report to the items you want to review first.")
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        with filter_col1:
            severity_options = ["All"] + sorted(
                all_issues_df["severity"].dropna().unique().tolist()
            )
            selected_severity = st.selectbox("Filter by severity", severity_options)

        with filter_col2:
            exception_options = ["All"] + sorted(
                all_issues_df["exception_type"].dropna().unique().tolist()
            )
            selected_exception = st.selectbox("Filter by issue type", exception_options)

        with filter_col3:
            source_options = ["All"] + sorted(
                all_issues_df["source_file"].dropna().unique().tolist()
            )
            selected_source = st.selectbox("Filter by source file", source_options)

        filtered_df = all_issues_df.copy()

        if selected_severity != "All":
            filtered_df = filtered_df[filtered_df["severity"] == selected_severity]

        if selected_exception != "All":
            filtered_df = filtered_df[filtered_df["exception_type"] == selected_exception]

        if selected_source != "All":
            filtered_df = filtered_df[filtered_df["source_file"] == selected_source]

        st.write(f"Showing {len(filtered_df)} item(s).")

        preview_columns = [
            "trade_id",
            "source_file",
            "exception_type",
            "severity",
            "recommended_action",
            "status",
        ]

        st.dataframe(
            filtered_df[preview_columns],
            use_container_width=True,
            height=450
        )

    # Daily summary
    st.markdown("#### Daily summary")
    st.dataframe(summary_df, use_container_width=True, height=300)

    # Report status
    st.markdown("#### Report status")
    if st.session_state.report_time:
        st.write(f"Exception report created: `exceptions_report.xlsx` at {st.session_state.report_time}")
        st.write(f"Daily summary created: `daily_summary.csv` at {st.session_state.report_time}")

# =========================
# 5. DOWNLOAD REPORTS
# =========================
if st.session_state.checks_run:
    st.subheader("5. Download reports")

    if os.path.exists(EXCEPTIONS_REPORT_FILE):
        with open(EXCEPTIONS_REPORT_FILE, "rb") as f:
            st.download_button(
                label="Download exception report (Excel)",
                data=f,
                file_name="exceptions_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    if os.path.exists(DAILY_SUMMARY_FILE):
        with open(DAILY_SUMMARY_FILE, "rb") as f:
            st.download_button(
                label="Download daily summary (CSV)",
                data=f,
                file_name="daily_summary.csv",
                mime="text/csv",
            )
            
    