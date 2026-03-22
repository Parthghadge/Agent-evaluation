"""Streamlit UI for the AI Agent Evaluation Pipeline."""
import os
import streamlit as st
import httpx
import json

API_BASE = os.environ.get("API_BASE", "http://localhost:8000/api/v1")

st.set_page_config(page_title="AI Agent Evaluation Pipeline", layout="wide")
st.title("AI Agent Evaluation Pipeline")
st.caption("Continuous evaluation and improvement of AI agents")

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

with tab2:
    st.header("Run Evaluation")
    conv_id = st.text_input("Conversation ID", value="conv_abc123")
    if st.button("Evaluate"):
        try:
            with httpx.Client() as client:
                r = client.post(f"{API_BASE}/evaluate/{conv_id}", timeout=60)
                r.raise_for_status()
                ev = r.json()
                st.json(ev)
                scores = ev.get("scores", {})
                st.metric("Overall Score", f"{scores.get('overall', 0):.2f}")
                st.metric("Response Quality", f"{scores.get('response_quality', 0):.2f}")
                st.metric("Tool Accuracy", f"{scores.get('tool_accuracy', 0):.2f}")
        except Exception as e:
            st.error(str(e))

with tab3:
    st.header("View Results")
    conv_id_res = st.text_input("Conversation ID (Results)", value="conv_abc123", key="res_id")
    if st.button("Fetch"):
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
    if st.button("Get Suggestions"):
        try:
            with httpx.Client() as client:
                r = client.get(f"{API_BASE}/suggestions?min_count=1", timeout=10)
                r.raise_for_status()
                data = r.json()
                st.subheader("Prompt Suggestions")
                for s in data.get("prompt_suggestions", []):
                    st.write(f"**{s['suggestion']}**")
                    st.caption(s["rationale"])
                st.subheader("Tool Suggestions")
                for s in data.get("tool_suggestions", []):
                    st.write(f"**{s['suggestion']}**")
                    st.caption(s["rationale"])
        except Exception as e:
            st.error(str(e))
