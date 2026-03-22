#!/bin/bash
# Use PORT from env if set (Render, Railway, etc.), else 8501
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
port="${PORT:-8501}"
exec streamlit run ui/streamlit_app.py --server.port "$port" --server.address 0.0.0.0
