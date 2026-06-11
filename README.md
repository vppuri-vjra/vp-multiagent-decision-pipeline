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

## What happens technically at each step

Every step is a single `client.messages.create()` call to the Anthropic API
(model set via `ANTHROPIC_MODEL`, default `claude-sonnet-4-5`, `max_tokens=4096`).
The prompt template for each step is loaded from `prompts/` and `.format()`-filled
with outputs from prior steps, then sent as a single user message (no chat history
carried between steps — each call is stateless/independent).

| # | Step | Prompt file | Inputs (`.format()` placeholders) | Output captured as | Saved to |
|---|------|-------------|-----------------------------------|---------------------|----------|
| 1 | Planner | `01_planner.txt` | `{brief}` | `trace["planner"]` | `agent_outputs/01_planner.md` |
| 2 | Researcher | `02_researcher.txt` | `{brief}`, `{plan}` | `trace["researcher"]` | `agent_outputs/02_researcher.md` |
| 3a | Analyzer A (Customer/Revenue) | `03_analyzer_a.txt` | `{brief}`, `{plan}`, `{research}` | `trace["analyzer_a"]` | `agent_outputs/03a_analyzer_a_customer.md` |
| 3b | Analyzer B (Risk/Privacy) | `03_analyzer_b.txt` | `{brief}`, `{plan}`, `{research}` | `trace["analyzer_b"]` | `agent_outputs/03b_analyzer_b_risk.md` |
| 4 | Synthesis | `04_synthesis.txt` | `{memo_a}`, `{memo_b}` | `trace["synthesis"]` | `agent_outputs/04_synthesis.md` |
| 5 | Critic | `05_critic.txt` | `{memo}` (= synthesis) | `trace["critic"]` | `agent_outputs/05_critic.md` |
| 6 | Reviser | `06_reviser.txt` | `{memo}` (= synthesis), `{critique}` | `trace["reviser"]` | `agent_outputs/06_reviser.md` |
| 7 | Confidence Scorer | `07_confidence.txt` | `{memo}` (= revised) | `trace["confidence"]` | `agent_outputs/07_confidence_scorer.md` |
| 8 | Publisher | `08_publisher.txt` | `{memo}` (= revised), `{confidence}` | `trace["publisher"]` | `agent_outputs/08_publisher.md` |

After step 8, `run_pipeline.py`:
1. Sums `usage.input_tokens` / `usage.output_tokens` from every API response and computes
   cost using Sonnet pricing ($3/M input, $15/M output) → `cost_report.md`
2. Times each `client.messages.create()` call with `time.monotonic()` → "Time (s)" column
3. Writes the full `trace` dict (every agent's raw output, including the original brief)
   → `pipeline_trace.json`
4. Concatenates the Publisher output + cost report → `final_decision_brief.md`
5. Writes each `trace` value to its own file under `agent_outputs/` for readability

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
