"""FastAPI application for the AI Agent Evaluation Pipeline."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.models import Conversation, Evaluation
from src.ingestion import Ingester
from src.ingestion.store import ConversationStore
from src.evaluators import EvaluationPipeline
from src.feedback import FeedbackIntegrator
from src.meta_eval import MetaEvaluator
from src.suggestions import SuggestionEngine


# Global store (in production use DI/DB)
store = ConversationStore()
ingester = Ingester()
pipeline = EvaluationPipeline(use_llm=True)
feedback_integrator = FeedbackIntegrator()
meta_eval = MetaEvaluator()
suggestion_engine = SuggestionEngine()


async def on_batch(batch: list[Conversation]):
    """Process ingested batches: store and evaluate."""
    for conv in batch:
        await store.save_conversation(conv)
        eval_result = await pipeline.evaluate(conv)
        eval_result = feedback_integrator.blend_with_human_feedback(eval_result, conv)
        await store.save_evaluation(eval_result)
        suggestion_engine.ingest_evaluation(eval_result)
        human = meta_eval.human_scores_from_feedback(conv)
        if human:
            meta_eval.add_ground_truth(eval_result, human)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ingester.register_callback(on_batch)
    yield
    await ingester.flush()


app = FastAPI(
    title="AI Agent Evaluation Pipeline",
    description="Continuous evaluation and improvement of AI agents",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Ingestion ---

@app.post("/api/v1/ingest", response_model=dict)
async def ingest_conversation(conversation: Conversation):
    """Ingest a single conversation (real-time)."""
    conv_id = await ingester.ingest_one(conversation)
    await ingester.flush()  # Ensure processed for demo
    return {"conversation_id": conv_id, "status": "ingested"}


@app.post("/api/v1/ingest/batch", response_model=dict)
async def ingest_batch(conversations: list[Conversation]):
    """Ingest a batch of conversations."""
    ids = await ingester.ingest_batch(conversations)
    await ingester.flush()
    return {"conversation_ids": ids, "count": len(ids)}


# --- Evaluation ---

@app.post("/api/v1/evaluate/{conversation_id}", response_model=Evaluation)
async def evaluate_conversation(conversation_id: str):
    """Run evaluation on a stored conversation."""
    conv = await store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    result = await pipeline.evaluate(conv)
    result = feedback_integrator.blend_with_human_feedback(result, conv)
    await store.save_evaluation(result)
    return result


@app.post("/api/v1/evaluate", response_model=Evaluation)
async def evaluate_inline(conversation: Conversation):
    """Evaluate a conversation inline (without storing)."""
    result = await pipeline.evaluate(conversation)
    return result


# --- Results ---

@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation by ID."""
    conv = await store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@app.get("/api/v1/evaluations/{conversation_id}")
async def get_evaluations(conversation_id: str):
    """Get all evaluations for a conversation."""
    evals = await store.get_evaluations(conversation_id)
    return {"conversation_id": conversation_id, "evaluations": evals}


@app.get("/api/v1/conversations")
async def list_conversations(
    agent_version: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    """List conversations with optional filters."""
    convs = await store.list_conversations(agent_version=agent_version, limit=limit)
    return {"conversations": convs}


# --- Improvement Suggestions ---

@app.get("/api/v1/suggestions")
async def get_suggestions(min_count: int = Query(1, ge=1)):
    """Get improvement suggestions from failure patterns."""
    patterns = suggestion_engine.get_failure_patterns(min_count=min_count)
    prompt_suggestions = suggestion_engine.suggest_prompt_fixes(patterns)
    tool_suggestions = suggestion_engine.suggest_tool_fixes(patterns)
    return {
        "patterns": patterns,
        "prompt_suggestions": prompt_suggestions,
        "tool_suggestions": tool_suggestions,
    }


# --- Meta-Evaluation ---

@app.get("/api/v1/meta/calibration")
async def get_calibration():
    """Get evaluator calibration results."""
    results = meta_eval.calibrate()
    return {"calibration": [r.__dict__ for r in results]}


@app.get("/health")
async def health():
    return {"status": "ok"}
