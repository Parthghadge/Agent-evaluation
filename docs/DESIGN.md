# Design Documentation

## Architecture Overview

The AI Agent Evaluation Pipeline is designed as a modular, event-driven system that:

1. **Ingests** multi-turn conversations (batch + real-time)
2. **Evaluates** using multiple evaluator types
3. **Integrates** human feedback and handles annotator disagreement
4. **Generates** improvement suggestions automatically
5. **Calibrates** evaluators over time (meta-evaluation)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Ingest API │───▶│  Ingester    │───▶│ Evaluation      │
│  (batch/RT) │    │  (buffer)    │    │ Pipeline        │
└─────────────┘    └──────────────┘    └────────┬────────┘
                                                │
       ┌────────────────────────────────────────┼────────────────────────┐
       │                                        ▼                        │
       │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
       │  │ LLM-as-Judge │  │ Tool Eval    │  │ Coherence    │          │
       │  └──────────────┘  └──────────────┘  └──────────────┘          │
       │  ┌──────────────┐  ┌──────────────┐                            │
       │  │ Heuristics   │  │ Feedback     │                            │
       │  └──────────────┘  │ Integrator   │                            │
       │                    └──────────────┘                            │
       └────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
       ┌────────────────────────────────────────────────────────────────┐
       │  Suggestion Engine  │  Meta-Evaluator  │  Store (DB/Redis)      │
       └────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Modular Evaluators

Each evaluator is independent and can be run in parallel. The pipeline merges results into a unified `Evaluation` object. This allows:

- Adding new evaluators without changing existing ones
- Disabling LLM evaluator for cost control (use `use_llm=False`)
- A/B testing evaluator variants

### 2. Buffered Ingestion for Throughput

The `Ingester` buffers conversations and flushes when `batch_size` is reached (default 100). Callbacks are invoked per batch. For 1000+ conversations/minute:

- Batches of 100 → ~10 callbacks/minute
- Each callback triggers evaluation; evaluations can be parallelized
- Redis/Celery would offload evaluation to workers in production

### 3. Feedback Integration Strategy

- **Agreement**: Simplified metric = (most_common_label_count / total)
- **Weighted scores**: Human annotations weighted by confidence; blended with automated scores
- **Routing**: Low scores (<0.6), critical issues, or annotator disagreement → human review

### 4. Self-Updating Mechanism

- `SuggestionEngine` tracks issue counts across evaluations
- Patterns (e.g., `tool_hallucination` occurring 10+ times) trigger suggestions
- Prompt suggestions: explicit instructions, examples, validation
- Tool suggestions: schema improvements, parameter descriptions, validation rules

### 5. Meta-Evaluation

- `MetaEvaluator` stores (evaluation, human_scores) pairs
- Calibration computes MAE between automated and human scores
- Outputs: recommended adjustments, blind spots, precision/recall
- Flywheel: Human feedback → calibration → better evaluators → better evals

## Scaling Strategy

### 10x Load (10k conversations/minute)

- **Ingestion**: Increase `batch_size` to 500; add Redis queue for ingestion
- **Evaluation**: Run N worker processes; each consumes from queue
- **Storage**: Move from in-memory store to PostgreSQL; use connection pooling
- **LLM**: Rate limit; use batch API if available; consider cheaper model

### 100x Load (100k conversations/minute)

- **Ingestion**: Kafka/RabbitMQ for ingestion; multiple consumer groups
- **Evaluation**: Kubernetes with auto-scaling workers; evaluators in separate services
- **Storage**: Sharded Postgres or TimescaleDB; cache hot data in Redis
- **LLM**: Dedicated eval model cluster; async batching; consider smaller/faster models
- **Sampling**: Evaluate 10–20% of traffic; full eval on sampled + flagged

## Trade-offs

| Decision | Optimized For | Trade-off |
|----------|---------------|-----------|
| In-memory store | Simplicity, local dev | Not durable; doesn't scale |
| SQLite/asyncpg | Flexibility | Production needs Postgres |
| LLM-as-Judge | Quality alignment | Cost, latency |
| Heuristic evaluators | Speed, no API cost | Less nuanced |
| Simplified agreement | Implementation speed | Krippendorff's alpha more rigorous |
| Pattern-based suggestions | Actionability | May miss novel failure modes |

## Sample Scenarios Coverage

1. **Tool Call Regression**: `ToolCallEvaluator` checks parameter format, execution success. Pattern in `SuggestionEngine` suggests prompt/tool fixes.
2. **Context Loss**: `CoherenceEvaluator` flags long conversations; suggests summarization in prompt.
3. **Annotator Disagreement**: `FeedbackIntegrator.should_route_to_human()` returns true when agreement < 0.6; routes to tiebreaker.
