# VP Multi-Agent Decision Pipeline

A Python/Anthropic-SDK reimplementation of a Langflow multi-agent decision pipeline.
Takes a raw Decision Brief and produces a final, paste-ready Decision Memo +
Confidence Report, with full per-agent token/cost tracking.

## Flow

```
Decision Brief
   -> Planner            (task decomposition, missing info, decision criteria)
   -> Researcher         (facts, assumptions, unknowns, risk triggers)
   -> Analyzer A (Customer/Revenue lens) ──┐
   -> Analyzer B (Risk/Privacy lens)       ┘
   -> Synthesis          (merges A & B, resolves conflicts explicitly)
   -> Critic              (red-team review)
   -> Reviser              (addresses critique, adds ESCALATE flag)
   -> Confidence Scorer    (0-100 score + rationale)
   -> Publisher            (final paste-ready artefact)
```

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
