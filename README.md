# VP Multi-Agent Decision Pipeline

A Python/Anthropic-SDK reimplementation of a Langflow multi-agent decision pipeline.
Takes a raw Decision Brief and produces a final, paste-ready Decision Memo +
Confidence Report, with full per-agent token/cost tracking.

## Flow

Designed flow, mapped to the source prompt-library demo steps:

```
Decision Brief (Option 1: Premium Subscription Tier)
        │
        ▼
   1. PLANNER  (Demo 2)        → TASK_DECOMPOSITION, MISSING_INFO, DECISION_CRITERIA
        │
        ▼
   2. RESEARCHER  (Demo 3)     → FACTS, ASSUMPTIONS, UNKNOWNS, RISK_TRIGGERS
        │
        ├──────────────┬───────────────┐
        ▼              ▼
   3. ANALYZER A   3. ANALYZER B        (run in parallel — both take Brief+Planner+Researcher)
   (Customer/Revenue   (Risk/Reliability/
    lens, Demo 6-7A)    Privacy lens, Demo 6-7B)
        │              │
        └──────┬───────┘
               ▼
   4. SYNTHESIS AGENT (Demo 6-8)  → merges A+B, resolves conflicts explicitly
               │
               ▼
   5. CRITIC (Demo 6-9)           → red-team critique of synthesis memo
               │
               ▼
   6. REVISER (Demo 6-10)         → revised memo addressing critique + ESCALATE
               │
               ▼
   7. CONFIDENCE SCORER (Demo 6-11) → score + why + what would increase confidence
               │
               ▼
   8. PUBLISHER (Demo 6-12)       → final paste-ready artefact (memo + confidence)
               │
               ▼
   Output: final_decision_brief.md + cost_report.json/md
```

> **Note:** Analyzer A and B are conceptually parallel (both depend only on
> Brief + Planner + Researcher output). The current `run_pipeline.py`
> implementation calls them sequentially for simplicity; cost/timing for
> each is tracked independently in `cost_report.md`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

## Run

```bash
python3 run_pipeline.py
```

## Outputs (in `output/`)

- `final_decision_brief.md` — final Publisher artefact + cost summary
- `pipeline_trace.json` — full intermediate output of every agent
- `cost_report.md` — per-agent and total token usage / cost (USD)

## Input

`input/decision_brief.md` — Decision Brief (Option 1: Premium Subscription Tier
for NovaCart, used as the scenario for this run).

## Prompts

Each agent's system prompt lives in `prompts/`, taken from the Multi-Agent LangFlow
Demo prompt library (Demo 2, Demo 3, Demo 6 Steps 7A-12).
