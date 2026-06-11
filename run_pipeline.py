"""
VP Multi-Agent Decision Pipeline
=================================
Replicates a Langflow multi-agent flow:

  Decision Brief
       -> Planner
       -> Researcher
       -> Analyzer A (Customer/Revenue lens) ─┐
       -> Analyzer B (Risk/Privacy lens)      ┘
       -> Synthesis
       -> Critic
       -> Reviser
       -> Confidence Scorer
       -> Publisher

Tracks per-agent and cumulative token usage / cost, written to
output/cost_report.md and output/pipeline_trace.json, with the final
artefact written to output/final_decision_brief.md.

Usage:
    python3 run_pipeline.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True, encoding="utf-8")

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 4096

# Claude Sonnet pricing (per million tokens)
PRICE_INPUT_PER_M = 3.0
PRICE_OUTPUT_PER_M = 15.0

ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

client = anthropic.Anthropic(api_key=api_key, timeout=120.0, max_retries=2)

usage_log = []


def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def track_cost(label, message, elapsed_s):
    inp = message.usage.input_tokens
    out = message.usage.output_tokens
    cost = (inp * PRICE_INPUT_PER_M + out * PRICE_OUTPUT_PER_M) / 1_000_000
    entry = {
        "label": label,
        "input_tokens": inp,
        "output_tokens": out,
        "cost_usd": round(cost, 6),
        "time_s": round(elapsed_s, 2),
    }
    usage_log.append(entry)
    print(f"  [{label}] in={inp} out={out} -> ${cost:.4f} ({elapsed_s:.2f}s)")
    return entry


def call_agent(label: str, prompt_text: str) -> str:
    print(f"\n=== Running: {label} ===")
    start = time.monotonic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt_text}],
    )
    elapsed = time.monotonic() - start
    track_cost(label, message, elapsed)
    return message.content[0].text.strip()


def main():
    brief = (INPUT / "decision_brief.md").read_text(encoding="utf-8")
    trace = {"brief": brief}

    # 1. Planner
    plan = call_agent("1-Planner", load_prompt("01_planner.txt").format(brief=brief))
    trace["planner"] = plan

    # 2. Researcher
    research = call_agent(
        "2-Researcher",
        load_prompt("02_researcher.txt").format(brief=brief, plan=plan),
    )
    trace["researcher"] = research

    # 3a. Analyzer A (Customer/Revenue)
    memo_a = call_agent(
        "3a-Analyzer_A_Customer",
        load_prompt("03_analyzer_a.txt").format(brief=brief, plan=plan, research=research),
    )
    trace["analyzer_a"] = memo_a

    # 3b. Analyzer B (Risk/Privacy)
    memo_b = call_agent(
        "3b-Analyzer_B_Risk",
        load_prompt("03_analyzer_b.txt").format(brief=brief, plan=plan, research=research),
    )
    trace["analyzer_b"] = memo_b

    # 4. Synthesis
    synthesis = call_agent(
        "4-Synthesis",
        load_prompt("04_synthesis.txt").format(memo_a=memo_a, memo_b=memo_b),
    )
    trace["synthesis"] = synthesis

    # 5. Critic
    critique = call_agent(
        "5-Critic",
        load_prompt("05_critic.txt").format(memo=synthesis),
    )
    trace["critic"] = critique

    # 6. Reviser
    revised = call_agent(
        "6-Reviser",
        load_prompt("06_reviser.txt").format(memo=synthesis, critique=critique),
    )
    trace["reviser"] = revised

    # 7. Confidence Scorer
    confidence = call_agent(
        "7-Confidence_Scorer",
        load_prompt("07_confidence.txt").format(memo=revised),
    )
    trace["confidence"] = confidence

    # 8. Publisher
    published = call_agent(
        "8-Publisher",
        load_prompt("08_publisher.txt").format(memo=revised, confidence=confidence),
    )
    trace["publisher"] = published

    # ── Cost summary ────────────────────────────────────────────────
    total_in = sum(e["input_tokens"] for e in usage_log)
    total_out = sum(e["output_tokens"] for e in usage_log)
    total_cost = sum(e["cost_usd"] for e in usage_log)

    total_time = sum(e["time_s"] for e in usage_log)

    cost_lines = ["# Token & Cost Report\n", f"_Generated: {datetime.now().isoformat(timespec='seconds')}_\n", f"_Model: {MODEL}_\n"]
    cost_lines.append("| Agent | Model | Input Tokens | Output Tokens | Time (s) | Cost (USD) |")
    cost_lines.append("|---|---|---:|---:|---:|---:|")
    for e in usage_log:
        cost_lines.append(f"| {e['label']} | {MODEL} | {e['input_tokens']} | {e['output_tokens']} | {e['time_s']:.2f} | ${e['cost_usd']:.4f} |")
    cost_lines.append(f"| **TOTAL** | {MODEL} | **{total_in}** | **{total_out}** | **{total_time:.2f}** | **${total_cost:.4f}** |")
    cost_report = "\n".join(cost_lines) + "\n"

    (OUTPUT / "cost_report.md").write_text(cost_report, encoding="utf-8")
    (OUTPUT / "pipeline_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")

    final_artifact = published + "\n\n---\n\n" + cost_report
    (OUTPUT / "final_decision_brief.md").write_text(final_artifact, encoding="utf-8")

    # ── Per-agent output files ─────────────────────────────────────
    agent_dir = OUTPUT / "agent_outputs"
    agent_dir.mkdir(exist_ok=True)
    agent_files = {
        "brief": ("00_decision_brief.md", "Decision Brief (Input)"),
        "planner": ("01_planner.md", "1 - Planner Output"),
        "researcher": ("02_researcher.md", "2 - Researcher Output"),
        "analyzer_a": ("03a_analyzer_a_customer.md", "3a - Analyzer A (Customer/Revenue Lens) Output"),
        "analyzer_b": ("03b_analyzer_b_risk.md", "3b - Analyzer B (Risk/Privacy Lens) Output"),
        "synthesis": ("04_synthesis.md", "4 - Synthesis Output"),
        "critic": ("05_critic.md", "5 - Critic Output"),
        "reviser": ("06_reviser.md", "6 - Reviser Output"),
        "confidence": ("07_confidence_scorer.md", "7 - Confidence Scorer Output"),
        "publisher": ("08_publisher.md", "8 - Publisher Output (Final)"),
    }
    for key, (fname, title) in agent_files.items():
        (agent_dir / fname).write_text(f"# {title}\n\n{trace.get(key, '')}\n", encoding="utf-8")

    print("\n" + cost_report)
    print("Done. Outputs written to ./output/ (per-agent files in ./output/agent_outputs/)")


if __name__ == "__main__":
    main()
