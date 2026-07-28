"""Task selection, dry runs, batching, and checkpoint orchestration."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.agent_a import AgentA
from core.task import Task, TaskManager

from real_llm_comparison.experiment import RealLLMComparison
from real_llm_comparison.llm_client import LLMClient
from real_llm_comparison.metrics import local_timestamp, summarize_conditions

def select_tasks(category: Optional[str]) -> List[Task]:
    tasks = TaskManager.get_all_tasks()
    if not category:
        return tasks
    matches = [task for task in tasks if task.category.lower() == category.lower()]
    if not matches:
        available = ", ".join(task.category for task in tasks)
        raise SystemExit(f"Unknown task {category!r}. Available: {available}")
    return matches



def dry_run(tasks: List[Task]) -> None:
    agent_a = AgentA()
    for task in tasks:
        print(f"\n=== {task.category} ===")
        print("Text payload:")
        print(agent_a.process(task.to_dict(), protocol="text"))
        print("\nCCP payload:")
        print(json.dumps(agent_a.process(task.to_dict(), protocol="ccp"), indent=2))


def run_temperature_condition(
    args: argparse.Namespace,
    temperature: Optional[float],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY or run with --dry-run.")

    client = LLMClient(
        api_key=api_key,
        model=args.model,
        base_url=args.base_url,
        api_mode=args.api_mode,
        temperature=temperature,
        timeout=args.timeout,
        retries=args.retries,
        retry_backoff=args.retry_backoff,
    )
    runner = RealLLMComparison(
        client,
        trials=args.trials,
        sleep_seconds=args.sleep,
        agent_b_mode=args.agent_b_mode,
        hops=args.hops,
        judge=args.judge,
        progress_callback=progress_callback,
    )
    return runner.run(select_tasks(args.task))


def run_batch_conditions(args: argparse.Namespace) -> Dict[str, Any]:
    run_started_at_unix = time.time()
    temperatures = args.temperatures or (
        [args.temperature] if args.temperature is not None else [None]
    )
    modes = args.agent_b_modes or [args.agent_b_mode]
    hops_values = args.hops_values or [args.hops]
    models = args.models or [args.model]

    checkpoint_path = Path(__file__).resolve().parent / "results" / "real_llm_results.partial.json"
    if args.resume_partial and checkpoint_path.exists():
        results = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        results.setdefault("metadata", {})
        results.setdefault("conditions", [])
        results["metadata"]["resumed_at_unix"] = time.time()
        results["metadata"]["resumed_at_local"] = local_timestamp()
    else:
        results = {
            "metadata": {
                "models": models,
                "api_mode": args.api_mode,
                "temperature_conditions": temperatures,
                "agent_b_modes": modes,
                "hops_values": hops_values,
                "trials_per_task": args.trials,
                "judge_enabled": args.judge,
                "created_at_unix": run_started_at_unix,
                "created_at_local": local_timestamp(),
            },
            "conditions": [],
        }

    def write_batch_checkpoint() -> None:
        if any("results" in condition for condition in results["conditions"]):
            results["condition_summary"] = summarize_conditions(
                [
                    condition
                    for condition in results["conditions"]
                    if "results" in condition
                ]
            )
        results["metadata"]["last_checkpoint_at_unix"] = time.time()
        results["metadata"]["last_checkpoint_at_local"] = local_timestamp()
        checkpoint_path.parent.mkdir(exist_ok=True, parents=True)
        checkpoint_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    def condition_key(condition: Dict[str, Any]) -> Tuple[Any, Any, Any, Any]:
        return (
            condition.get("model"),
            condition.get("agent_b_mode"),
            condition.get("hops"),
            condition.get("temperature"),
        )

    completed_keys = {
        condition_key(condition)
        for condition in results["conditions"]
        if condition.get("status") == "completed" and "results" in condition
    }

    original_model = args.model
    original_mode = args.agent_b_mode
    original_hops = args.hops
    for model in models:
        args.model = model
        for mode in modes:
            args.agent_b_mode = mode
            for hops in hops_values:
                args.hops = hops
                for temperature in temperatures:
                    key = (model, mode, hops, temperature)
                    if key in completed_keys:
                        print(
                            "\n=== Skipping completed condition: "
                            f"model={model}, mode={mode}, hops={hops}, "
                            f"temperature={temperature} ==="
                        )
                        continue
                    results["conditions"] = [
                        condition
                        for condition in results["conditions"]
                        if not (
                            condition_key(condition) == key
                            and condition.get("status") != "completed"
                        )
                    ]
                    print(
                        "\n=== Condition: "
                        f"model={model}, mode={mode}, hops={hops}, "
                        f"temperature={temperature} ==="
                    )
                    condition_record: Dict[str, Any] = {
                        "model": model,
                        "agent_b_mode": mode,
                        "hops": hops,
                        "temperature": temperature,
                        "status": "running",
                    }
                    results["conditions"].append(condition_record)

                    def checkpoint_condition(partial_run: Dict[str, Any]) -> None:
                        condition_record["results"] = partial_run
                        condition_record["status"] = "running"
                        write_batch_checkpoint()

                    condition_record["results"] = run_temperature_condition(
                        args, temperature, progress_callback=checkpoint_condition
                    )
                    condition_record["status"] = "completed"
                    write_batch_checkpoint()

    args.model = original_model
    args.agent_b_mode = original_mode
    args.hops = original_hops
    results["condition_summary"] = summarize_conditions(results["conditions"])
    results["metadata"]["completed_at_unix"] = time.time()
    results["metadata"]["completed_at_local"] = local_timestamp()
    return results
