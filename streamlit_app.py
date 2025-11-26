"""Streamlit chat app for the Deep Shot NFL Stats API."""

import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Deep Shot - NFL Stats",
    page_icon="🏈",
    layout="wide",
)


def check_api_health() -> bool:
    """Check if the API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def process_chat(messages: list[dict]) -> dict | None:
    """Send conversation history to the NFL chat API."""
    chat_messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
        if msg["role"] in ("user", "assistant")
    ]

    try:
        response = requests.post(
            f"{API_BASE_URL}/nfl/chat",
            json={"messages": chat_messages},
            timeout=120,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    except requests.exceptions.ConnectionError:
        return {
            "error": "Could not connect to the API. Make sure the server is running."
        }
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The query may be too complex."}


with st.sidebar:
    st.header("🏈 Deep Shot")
    st.markdown("NFL Stats Assistant")

    st.divider()

    api_status = check_api_health()
    if api_status:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Offline")
        st.markdown(
            """
            Start the API:
            ```bash
            python main.py
            ```
            """
        )

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.header("💡 Try asking...")
    example_queries = [
        "How many touchdowns did the Lions score?",
        "Who leads the league in passing yards?",
        "What's Patrick Mahomes' passer rating?",
        "Compare rushing yards for the top 5 RBs",
        "Which team has the best defense?",
    ]

    for query in example_queries:
        if st.button(query, key=f"example_{query}", use_container_width=True):
            st.session_state.pending_query = query
            st.rerun()

    st.divider()
    st.caption("Powered by [nflreadpy](https://nflreadpy.nflverse.com/)")


st.title("🏈 Deep Shot")
st.caption("Ask me anything about NFL statistics!")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and "details" in message:
            details = message["details"]
            with st.expander("📊 Details", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Attempts", details.get("attempts", 1))
                with col2:
                    has_code = details.get("code_generated") is not None
                    st.metric("Used Code", "Yes" if has_code else "No")

                if details.get("code_generated"):
                    st.markdown("**Generated Code:**")
                    st.code(details["code_generated"], language="python")

                if details.get("raw_data"):
                    st.markdown("**Raw Data:**")
                    st.json(details["raw_data"])


def handle_user_input(user_input: str):
    """Process user input and get response."""
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        if not api_status:
            error_msg = "I can't process your request right now - the API is offline. Please start the server and try again."
            st.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
            return

        with st.spinner("Analyzing NFL data..."):
            result = process_chat(st.session_state.messages)

        if result and "error" in result:
            st.error(result["error"])
            st.session_state.messages.append(
                {"role": "assistant", "content": f"❌ {result['error']}"}
            )
        elif result:
            response_text = result.get("response", "I couldn't find an answer.")
            st.markdown(response_text)

            details = {
                "attempts": result.get("attempts", 1),
                "code_generated": result.get("code_generated"),
                "raw_data": result.get("raw_data"),
            }

            with st.expander("📊 Details", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Attempts", details.get("attempts", 1))
                with col2:
                    has_code = details.get("code_generated") is not None
                    st.metric("Used Code", "Yes" if has_code else "No")

                if details.get("code_generated"):
                    st.markdown("**Generated Code:**")
                    st.code(details["code_generated"], language="python")

                if details.get("raw_data"):
                    st.markdown("**Raw Data:**")
                    st.json(details["raw_data"])

            st.session_state.messages.append(
                {"role": "assistant", "content": response_text, "details": details}
            )
        else:
            error_msg = "Something went wrong. Please try again."
            st.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )


if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_user_input(query)

if prompt := st.chat_input("Ask about NFL stats..."):
    handle_user_input(prompt)

if not st.session_state.messages:
    st.info(
        "👋 Hi! I'm your NFL stats assistant. Ask me anything about players, teams, or game statistics!"
    )
