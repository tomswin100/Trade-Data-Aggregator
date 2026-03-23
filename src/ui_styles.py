import streamlit as st


def apply_shared_styles():
    """Apply a cleaner institutional visual theme across pages."""
    st.markdown(
        """
        <style>
        :root {
            --tem-bg: #F4F7FB;
            --tem-surface: #FFFFFF;
            --tem-surface-soft: #F8FBFF;
            --tem-text: #0F172A;
            --tem-text-secondary: #475569;
            --tem-border: #D9E2EC;
            --tem-accent: #1D4ED8;
            --tem-accent-soft: #DBEAFE;
            --tem-success: #059669;
            --tem-warning: #D97706;
            --tem-danger: #B91C1C;
            --tem-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        }

        .stApp {
            background: var(--tem-bg);
            color: var(--tem-text);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f7faff 0%, #f4f7fb 100%);
            border-right: 1px solid var(--tem-border);
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem;
        }

        h1, h2, h3, h4, h5, h6,
        p, label, span, div {
            color: inherit;
        }

        div[data-testid="stMetric"] {
            background: var(--tem-surface);
            border: 1px solid var(--tem-border);
            border-radius: 16px;
            padding: 0.85rem 0.95rem;
            box-shadow: var(--tem-shadow);
        }

        div[data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        button[data-baseweb="tab"] {
            background: var(--tem-surface);
            border: 1px solid var(--tem-border);
            border-radius: 999px;
            padding: 0.45rem 0.95rem;
        }

        button[data-baseweb="tab"] p {
            color: var(--tem-text-secondary);
            font-weight: 600;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--tem-accent);
            border-color: var(--tem-accent);
            box-shadow: 0 8px 20px rgba(29, 78, 216, 0.2);
        }

        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #ffffff;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--tem-border);
            background: var(--tem-surface);
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 999px;
            font-weight: 600;
            padding-left: 1rem;
            padding-right: 1rem;
            border: 1px solid var(--tem-accent);
            background: var(--tem-accent);
            color: #ffffff;
            box-shadow: 0 10px 24px rgba(29, 78, 216, 0.14);
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            border-color: var(--tem-accent);
            background: #1e40af;
            color: #ffffff;
        }

        div[data-testid="stAlert"] {
            border-radius: 14px;
            border: 1px solid var(--tem-border);
        }

        div[data-testid="stAlert"] p {
            color: var(--tem-text-secondary);
        }

        [data-testid="stMarkdownContainer"] a {
            color: var(--tem-accent);
        }

        [data-testid="stCaptionContainer"] {
            color: var(--tem-text-secondary);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_nav(current_page):
    """Render a cleaner sidebar navigation panel."""
    st.sidebar.markdown(
        """
        <div style="
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 18px;
            padding: 1rem 1rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        ">
            <div style="font-size: 0.78rem; color: #475569; text-transform: uppercase; letter-spacing: 0.12em;">
                Trade Data Aggregator
            </div>
            <div style="font-size: 1.08rem; font-weight: 700; color: #0f172a; margin-top: 0.22rem;">
                Demo Navigation
            </div>
            <div style="font-size: 0.9rem; color: #475569; margin-top: 0.38rem; line-height: 1.55;">
                Switch between the workflow view, the trade support dashboard, and the Python workflow.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.page_link(
        "app.py",
        label="Workflow",
        use_container_width=True,
    )
    st.sidebar.page_link(
        "pages/1_Exception_Dashboard.py",
        label="Dashboard",
        use_container_width=True,
    )
    st.sidebar.page_link(
        "pages/2_Python_Workflow.py",
        label="Python Workflow",
        use_container_width=True,
    )

    st.sidebar.caption(f"Current view: {current_page}")
    st.sidebar.divider()
