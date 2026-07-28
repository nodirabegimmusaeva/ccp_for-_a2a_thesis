"""Run a real-LLM CCP vs text comparison."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from real_llm_comparison.metrics import collect_api_calls, local_timestamp, summarize_conditions
from real_llm_comparison.orchestration import dry_run, run_batch_conditions, run_temperature_condition, select_tasks

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--task", help="Run one task category, e.g. Food")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"))
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=os.getenv("OPENAI_API_MODE", "responses"),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional sampling temperature. Omitted by default because some models reject it.",
    )
    parser.add_argument(
        "--temperatures",
        nargs="+",
        type=float,
        help="Run multiple temperature conditions, e.g. --temperatures 0.1 0.7.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Run multiple model conditions, e.g. --models gpt-4.1-nano gpt-4o-mini.",
    )
    parser.add_argument(
        "--agent-b-mode",
        choices=["forward", "process", "summarize"],
        default="forward",
        help="Forward is minimal; process extracts constraints; summarize increases drift pressure.",
    )
    parser.add_argument(
        "--agent-b-modes",
        nargs="+",
        choices=["forward", "process", "summarize"],
        help="Run multiple Agent B instruction modes.",
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=1,
        help="Number of Agent-B-style hops before final Agent C scoring.",
    )
    parser.add_argument(
        "--hops-values",
        nargs="+",
        type=int,
        help="Run multiple hop-count conditions, e.g. --hops-values 1 3 5.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run the Cartesian product of models, temperatures, modes, and hop values.",
    )
    parser.add_argument(
        "--resume-partial",
        action="store_true",
        help="For batch runs, skip completed conditions from real_llm_results.partial.json.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Add an LLM-as-judge pass to evaluate whether the final response respects constraints.",
    )
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry transient API failures this many times before failing.",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=3.0,
        help="Initial retry delay in seconds; later retries use exponential backoff.",
    )
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.hops < 1:
        raise SystemExit("--hops must be at least 1.")
    if args.hops_values and any(hops < 1 for hops in args.hops_values):
        raise SystemExit("--hops-values entries must be at least 1.")
    if args.retries < 0:
        raise SystemExit("--retries must be 0 or greater.")
    if args.retry_backoff < 0:
        raise SystemExit("--retry-backoff must be 0 or greater.")

    tasks = select_tasks(args.task)
    if args.dry_run:
        dry_run(tasks)
        return

    if args.batch or args.models or args.agent_b_modes or args.hops_values:
        results = run_batch_conditions(args)
    elif args.temperatures:
        run_started_at_unix = time.time()
        results = {
            "metadata": {
                "model": args.model,
                "api_mode": args.api_mode,
                "temperature_conditions": args.temperatures,
                "trials_per_task": args.trials,
                "agent_b_mode": args.agent_b_mode,
                "hops": args.hops,
                "judge_enabled": args.judge,
                "created_at_unix": run_started_at_unix,
                "created_at_local": local_timestamp(),
            },
            "conditions": [],
        }
        for temperature in args.temperatures:
            print(f"\n=== Temperature condition: {temperature} ===")
            results["conditions"].append(
                {
                    "temperature": temperature,
                    "results": run_temperature_condition(args, temperature),
                }
            )
        results["condition_summary"] = summarize_conditions(results["conditions"])
        results["metadata"]["completed_at_unix"] = time.time()
        results["metadata"]["completed_at_local"] = local_timestamp()
    else:
        results = run_temperature_condition(args, args.temperature)

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "real_llm_results.json"
    raw_output_path = output_dir / "raw_api_calls.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    raw_output_path.write_text(
        json.dumps(collect_api_calls(results), indent=2), encoding="utf-8"
    )

    print("\nSummary")
    if "summary" in results:
        print(json.dumps(results["summary"], indent=2))
    else:
        print(json.dumps(results["condition_summary"], indent=2))
    print(f"\nSaved: {output_path}")
    print(f"Raw API calls: {raw_output_path}")
