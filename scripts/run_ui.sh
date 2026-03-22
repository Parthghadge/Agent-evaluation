#!/bin/bash
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
