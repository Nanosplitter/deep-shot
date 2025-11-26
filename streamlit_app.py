"""Streamlit app for testing the Deep Shot NFL Stats API."""

import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Deep Shot - NFL Stats",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Deep Shot - NFL Stats Assistant")
st.markdown("Ask questions about NFL statistics and get AI-powered answers.")


def check_api_health() -> bool:
    """Check if the API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def process_query(query: str) -> dict | None:
    """Send a query to the NFL API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/nfl/process",
            json={"input": query},
            timeout=120,
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Make sure the server is running.")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. The query may be too complex.")
        return None


with st.sidebar:
    st.header("⚙️ Settings")

    api_status = check_api_health()
    if api_status:
        st.success("✅ API is running")
    else:
        st.error("❌ API is not running")
        st.markdown(
            """
            Start the API with:
            ```bash
            python main.py
            ```
            or
            ```bash
            uvicorn app.main:app --reload
            ```
            """
        )

    st.divider()

    st.header("📝 Example Queries")
    example_queries = [
        "How many touchdowns did the Lions score this season?",
        "Who leads the league in passing yards in 2025?",
        "What is Patrick Mahomes' passer rating this season?",
        "How many interceptions did Jared Goff throw in his worst game?",
        "Which team has the best rushing offense this year?",
    ]

    for query in example_queries:
        if st.button(query, key=query, use_container_width=True):
            st.session_state.query_input = query

    st.divider()
    st.markdown("**Built with** [nflreadpy](https://nflreadpy.nflverse.com/)")


if "query_input" not in st.session_state:
    st.session_state.query_input = ""

if "history" not in st.session_state:
    st.session_state.history = []

query = st.text_area(
    "Ask a question about NFL stats:",
    value=st.session_state.query_input,
    height=100,
    placeholder="e.g., How many touchdowns did the Lions score this season?",
)

col1, col2 = st.columns([1, 5])
with col1:
    submit = st.button("🔍 Search", type="primary", use_container_width=True)
with col2:
    clear = st.button("🗑️ Clear History", use_container_width=True)

if clear:
    st.session_state.history = []
    st.rerun()

if submit and query:
    if not api_status:
        st.error("Cannot submit query - API is not running.")
    else:
        with st.spinner("Analyzing NFL data..."):
            result = process_query(query)

        if result:
            st.session_state.history.insert(
                0,
                {
                    "query": query,
                    "result": result,
                },
            )
            st.session_state.query_input = ""

if st.session_state.history:
    st.divider()
    st.header("📊 Results")

    for i, item in enumerate(st.session_state.history):
        with st.container():
            st.markdown(f"**Question:** {item['query']}")

            result = item["result"]

            st.markdown("### Answer")
            st.markdown(result.get("response", "No response"))

            with st.expander("🔧 Details", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Attempts", result.get("attempts", 1))

                with col2:
                    has_code = result.get("code_generated") is not None
                    st.metric("Code Generated", "Yes" if has_code else "No")

                if result.get("code_generated"):
                    st.markdown("**Generated Code:**")
                    st.code(result["code_generated"], language="python")

                if result.get("raw_data"):
                    st.markdown("**Raw Data:**")
                    st.json(result["raw_data"])

            st.divider()
else:
    st.info("👆 Enter a question above to get started!")

st.markdown(
    """
    ---
    <div style="text-align: center; color: #888;">
        Deep Shot NFL Stats Assistant | Powered by OpenAI & nflreadpy
    </div>
    """,
    unsafe_allow_html=True,
)
