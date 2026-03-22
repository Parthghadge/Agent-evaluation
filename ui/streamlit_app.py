"""Streamlit UI for the AI Agent Evaluation Pipeline."""
import os
import streamlit as st
import httpx
import json

API_BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1")


def fetch_conversations():
    """Fetch available conversations from API."""
    try:
        with httpx.Client() as client:
            r = client.get(f"{API_BASE}/conversations?limit=100", timeout=10)
            r.raise_for_status()
            return r.json().get("conversations", [])
    except Exception:
        return []


st.set_page_config(page_title="AI Agent Evaluation Pipeline", layout="wide")
st.title("AI Agent Evaluation Pipeline")
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.caption("Continuous evaluation and improvement of AI agents")
with col_refresh:
    if st.button("🔄 Refresh list"):
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["Ingest", "Evaluate", "Results", "Suggestions"])

# Sample conversation for quick demo
SAMPLE_CONV = {
    "conversation_id": "conv_abc123",
    "agent_version": "v2.3.1",
    "turns": [
        {
            "turn_id": 1,
            "role": "user",
            "content": "I need to book a flight to NYC next week",
            "timestamp": "2024-01-15T10:30:00Z",
        },
        {
            "turn_id": 2,
            "role": "assistant",
            "content": "I'd be happy to help you book a flight to NYC...",
            "tool_calls": [
                {
                    "tool_name": "flight_search",
                    "parameters": {"destination": "NYC", "date_range": "2024-01-22/2024-01-28"},
                    "result": {"status": "success", "flights": ["..."]},
                    "latency_ms": 450,
                }
            ],
            "timestamp": "2024-01-15T10:30:02Z",
        },
    ],
    "feedback": {
        "user_rating": 4,
        "ops_review": {"quality": "good", "notes": "Correct tool usage"},
        "annotations": [
            {"type": "tool_accuracy", "label": "correct", "annotator_id": "ann_001"},
        ],
    },
    "metadata": {"total_latency_ms": 1200, "mission_completed": True},
}


with tab1:
    st.header("Ingest Conversations")
    st.write("Ingest conversations for evaluation. Use sample or paste your own JSON.")
    if st.button("Load sample conversation"):
        st.session_state["ingest_json"] = json.dumps(SAMPLE_CONV, indent=2)
    ingest_raw = st.text_area(
        "Conversation JSON",
        value=st.session_state.get("ingest_json", json.dumps(SAMPLE_CONV, indent=2)),
        height=300,
    )
    if st.button("Ingest"):
        try:
            data = json.loads(ingest_raw)
            with httpx.Client() as client:
                r = client.post(f"{API_BASE}/ingest", json=data, timeout=30)
                r.raise_for_status()
                st.success(f"Ingested: {r.json().get('conversation_id', 'OK')}")
        except Exception as e:
            st.error(str(e))

# Fetch conversations for dropdown (shared across Evaluate, Results, Suggestions)
convs = fetch_conversations()
conv_options = [
    (f"{c.get('conversation_id', '')} (v{c.get('agent_version', '?')})", c["conversation_id"])
    for c in convs if c.get("conversation_id")
]
conv_ids = [c["conversation_id"] for c in convs if c.get("conversation_id")]

with tab2:
    st.header("Run Evaluation")
    if conv_options:
        selected_label = st.selectbox(
            "Select conversation",
            options=[o[0] for o in conv_options],
            key="eval_conv",
        )
        conv_id = next((o[1] for o in conv_options if o[0] == selected_label), conv_ids[0])
    else:
        conv_id = None
        st.info("No conversations yet. Ingest some in the **Ingest** tab first.")
    if st.button("Evaluate", disabled=conv_id is None, key="btn_eval"):
        try:
            with httpx.Client() as client:
                r = client.post(f"{API_BASE}/evaluate/{conv_id}", timeout=60)
                r.raise_for_status()
                ev = r.json()
                st.json(ev)
                scores = ev.get("scores", {})
                col1, col2, col3 = st.columns(3)
                col1.metric("Overall Score", f"{scores.get('overall', 0):.2f}")
                col2.metric("Response Quality", f"{scores.get('response_quality', 0):.2f}")
                col3.metric("Tool Accuracy", f"{scores.get('tool_accuracy', 0):.2f}")
        except Exception as e:
            st.error(str(e))

with tab3:
    st.header("View Results")
    if conv_options:
        selected_label = st.selectbox(
            "Select conversation",
            options=[o[0] for o in conv_options],
            key="res_conv",
        )
        conv_id_res = next((o[1] for o in conv_options if o[0] == selected_label), conv_ids[0])
    else:
        conv_id_res = None
        st.info("No conversations yet. Ingest some in the **Ingest** tab first.")
    if st.button("Fetch", disabled=conv_id_res is None, key="btn_fetch"):
        try:
            with httpx.Client() as client:
                r = client.get(f"{API_BASE}/evaluations/{conv_id_res}", timeout=10)
                r.raise_for_status()
                data = r.json()
                st.json(data)
        except Exception as e:
            st.error(str(e))

with tab4:
    st.header("Improvement Suggestions")
    if conv_options:
        filter_options = [("All conversations", None)] + conv_options
        selected_filter = st.selectbox(
            "Filter by conversation (optional)",
            options=[o[0] for o in filter_options],
            key="sugg_conv",
        )
        filter_conv_id = next((o[1] for o in filter_options if o[0] == selected_filter), None)
    else:
        filter_conv_id = None
    if st.button("Get Suggestions", key="btn_sugg"):
        try:
            with httpx.Client() as client:
                r = client.get(f"{API_BASE}/suggestions?min_count=1", timeout=10)
                r.raise_for_status()
                data = r.json()
            prompt_suggestions = data.get("prompt_suggestions", [])
            tool_suggestions = data.get("tool_suggestions", [])
            if filter_conv_id:
                prompt_suggestions = [s for s in prompt_suggestions if filter_conv_id in s.get("example_conversation_ids", [])]
                tool_suggestions = [s for s in tool_suggestions if filter_conv_id in s.get("example_conversation_ids", [])]
                if not prompt_suggestions and not tool_suggestions:
                    st.info(f"No suggestions specifically for this conversation yet.")
            st.subheader("Prompt Suggestions")
            for s in prompt_suggestions:
                st.write(f"**{s['suggestion']}**")
                st.caption(s["rationale"])
            st.subheader("Tool Suggestions")
            for s in tool_suggestions:
                st.write(f"**{s['suggestion']}**")
                st.caption(s["rationale"])
        except Exception as e:
            st.error(str(e))
