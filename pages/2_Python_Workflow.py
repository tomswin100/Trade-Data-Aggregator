import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from ui_styles import apply_shared_styles, render_sidebar_nav

SCRIPT_PREVIEWS = [
    (
        "Generator",
        "generate_sample_data.py",
        "Creates the synthetic equity trade data and seeds booking errors into the booked dataset.",
    ),
    (
        "Loader",
        "src/load_and_validate.py",
        "Loads the generated CSV files, checks schemas, and standardises data types for the rest of the workflow.",
    ),
    (
        "Data Checks",
        "src/validate_data.py",
        "Runs data-quality and reference-data checks such as missing fields and inactive account usage.",
    ),
    (
        "Reconciliation",
        "src/reconcile_trades.py",
        "Compares executed and booked trades to surface booking breaks and field mismatches.",
    ),
    (
        "Reporting",
        "src/generate_reports.py",
        "Builds the exception report dataset, daily summary, and Excel output files.",
    ),
]


def read_script(relative_path):
    script_path = BASE_DIR / relative_path
    if not script_path.exists():
        return script_path, None
    return script_path, script_path.read_text(encoding="utf-8")


st.set_page_config(
    page_title="Python Workflow — Trade Exception Monitor",
    page_icon="🐍",
    layout="wide",
)
apply_shared_styles()
render_sidebar_nav("Python Workflow")

st.title("Python Workflow")
st.write(
    "A raw-code view of the Python scripts behind the trade support workflow, "
    "from synthetic data generation through data checks, reconciliation, and reporting."
)
st.caption(
    "Use this page to show the underlying implementation alongside the workflow "
    "and dashboard views."
)

st.info(
    "These script previews are read-only and mirror the backend workflow used by the app."
)

tabs = st.tabs([label for label, _, _ in SCRIPT_PREVIEWS])

for tab, (label, relative_path, description) in zip(tabs, SCRIPT_PREVIEWS):
    with tab:
        script_path, script_contents = read_script(relative_path)
        st.markdown(f"#### {label}")
        st.caption(description)
        st.write(f"File: `{relative_path}`")

        if script_contents is None:
            st.error(f"Unable to locate `{relative_path}`.")
            continue

        line_count = len(script_contents.splitlines())
        info_col1, info_col2 = st.columns(2)
        info_col1.metric("Lines", line_count)
        info_col2.metric("Language", "Python")

        st.code(script_contents, language="python")
