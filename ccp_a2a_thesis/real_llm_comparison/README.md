# Real LLM CCP Comparison

This folder runs a live-model version of the thesis comparison inside the main
thesis simulator repository:

- **Text protocol:** agents pass free-form natural language.
- **CCP protocol:** agents pass a structured JSON Canonical Context Payload.
- **Metrics:** reuses the simulator's Context Retention Score and accuracy logic.

The harness calls a real LLM for Agent B (forwarding) and Agent C (final extraction
and decision), while reusing the existing simulator tasks.

## Quick Start

From the thesis simulator root:

```bash
export OPENAI_API_KEY="your_key_here"
python3 real_llm_comparison/run_real_llm_comparison.py --trials 1 --task Food
```

The default model is `gpt-4.1-nano`, chosen as a low-cost option for pilot runs.
Override it if needed:

```bash
OPENAI_MODEL="gpt-4o-mini" python3 real_llm_comparison/run_real_llm_comparison.py --trials 3
```

Results are written to:

```text
real_llm_comparison/results/real_llm_results.json
```

## Dry Run

Use dry-run mode to inspect the task and protocol payloads without calling an API:

```bash
python3 real_llm_comparison/run_real_llm_comparison.py --dry-run
```

## Notes

- Omit `--temperature` for models that reject sampling controls.
- Use `--temperature 0.7` with compatible models when you want more drift pressure.
- Use `--task Food` or another category name to run one task during prompt tuning.
- Use `--api-mode chat_completions` for OpenAI-compatible providers that do not
  support the Responses API.
