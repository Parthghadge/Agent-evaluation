# AI Agent Evaluation Pipeline

A modular, production-ready evaluation pipeline for continuously improving AI agents. Detects regressions, aligns evals with user feedback, and generates actionable improvement suggestions.

## Features

- **Data Ingestion**: Batch + real-time, 1000+ conversations/minute capable
- **Evaluation Framework**:
  - LLM-as-Judge (response quality, helpfulness, factuality)
  - Tool Call Evaluator (selection, parameters, hallucination, execution)
  - Multi-turn Coherence (context maintenance, consistency)
  - Heuristic Checks (latency, format, required fields)
- **Feedback Integration**: Annotator disagreement handling, confidence weighting, human routing
- **Self-Updating**: Auto-generated prompt and tool improvement suggestions
- **Meta-Evaluation**: Calibrate evaluators against human ground truth

## Architecture

See [docs/DESIGN.md](docs/DESIGN.md) for architecture, scaling, and trade-offs.

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) OpenAI API key for LLM-as-Judge

### Local Development

```bash
# Create virtualenv and install
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run API
export PYTHONPATH=$(pwd)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal: Run Streamlit UI
streamlit run ui/streamlit_app.py --server.port 8501

# Seed sample data (after API is up)
python scripts/seed_sample.py
```

### Docker

```bash
docker-compose up --build
```

- API: http://localhost:8000
- Streamlit UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest` | Ingest single conversation |
| POST | `/api/v1/ingest/batch` | Ingest batch of conversations |
| POST | `/api/v1/evaluate/{conversation_id}` | Evaluate stored conversation |
| POST | `/api/v1/evaluate` | Evaluate inline (body: conversation JSON) |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| GET | `/api/v1/evaluations/{id}` | Get evaluations for conversation |
| GET | `/api/v1/conversations` | List conversations (optional: agent_version, limit) |
| GET | `/api/v1/suggestions` | Get improvement suggestions (optional: min_count) |
| GET | `/api/v1/meta/calibration` | Get evaluator calibration results |
| GET | `/health` | Health check |

## Conversation Schema

```json
{
  "conversation_id": "conv_abc123",
  "agent_version": "v2.3.1",
  "turns": [
    {
      "turn_id": 1,
      "role": "user",
      "content": "I need to book a flight to NYC next week",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "turn_id": 2,
      "role": "assistant",
      "content": "I'd be happy to help...",
      "tool_calls": [
        {
          "tool_name": "flight_search",
          "parameters": {"destination": "NYC", "date_range": "2024-01-22/2024-01-28"},
          "result": {"status": "success"},
          "latency_ms": 450
        }
      ]
    }
  ],
  "feedback": {
    "user_rating": 4,
    "ops_review": {"quality": "good"},
    "annotations": [{"type": "tool_accuracy", "label": "correct", "annotator_id": "ann_001"}]
  },
  "metadata": {"total_latency_ms": 1200, "mission_completed": true}
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required for LLM-as-Judge |
| `OPENAI_BASE_URL` | https://api.openai.com/v1 | Use for Azure/other compatible APIs |
| `LATENCY_THRESHOLD_MS` | 1000 | Latency warning threshold |
| `DATABASE_URL` | sqlite+aiosqlite:///./agent_eval.db | DB connection |
| `REDIS_URL` | redis://localhost:6379/0 | For queue (future) |

## Project Structure

```
├── api/
│   └── main.py           # FastAPI app
├── src/
│   ├── models/           # Conversation, Evaluation schemas
│   ├── ingestion/        # Ingester, store
│   ├── evaluators/       # LLM, Tool, Coherence, Heuristics, Pipeline
│   ├── feedback/         # Feedback integrator
│   ├── meta_eval/        # Meta-evaluator calibration
│   └── suggestions/      # Suggestion engine
├── ui/
│   └── streamlit_app.py  # Streamlit UI
├── scripts/              # Run scripts, seed
├── docs/
│   └── DESIGN.md         # Architecture & design
├── sample_conversations.jsonl
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Deployment (Render / Railway / Fly.io)

1. Set `OPENAI_API_KEY` in environment
2. Use `uvicorn` as process; expose port 8000 (or `$PORT` if platform provides it)
3. For Streamlit: `./scripts/run_streamlit.sh` or `streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
4. Set `API_BASE` to your API URL (e.g. `https://your-api.onrender.com/api/v1`) so the UI can reach it
5. Replace in-memory store with PostgreSQL for persistence

### Troubleshooting: Errno 99 "Cannot assign requested address"

- Ensure the server binds to `0.0.0.0`, not `localhost` (`.streamlit/config.toml` does this)
- Use `--server.address 0.0.0.0 --server.headless true` in the run command
- If the platform assigns `PORT`, pass `--server.port $PORT`
- Set `API_BASE` to the full URL of your deployed API (not `localhost`)

## License

MIT
