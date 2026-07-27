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

Raw request/response logs are also written to:

```text
real_llm_comparison/results/raw_api_calls.json
```

The raw call log includes request payloads, model parameters, prompts, user
messages, raw API responses, status codes, timing, task id, protocol, trial,
agent role, and hop index. It does **not** log the API key or Authorization
header.

For CCP runs, the harness keeps two versions of each intermediate hop:

- `agent_b_raw_outputs`: the model's exact JSON output.
- `agent_b_outputs`: the normalized CCP payload passed to the next hop.

Normalization preserves canonical fields (`task_id`, `context`,
`extended_context`, `request`, `constraints`, and `metadata`) from the previous
payload and appends state lineage deterministically. This prevents fabricated
timestamps or rewritten canonical fields from becoming the next agent's source
of truth, while still keeping the raw model behavior available for failure-mode
analysis.

## Experiment Conditions

The harness supports the main methodological variants needed for thesis testing:

```bash
# Low-temperature protocol effectiveness condition
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 10 \
  --model gpt-4.1-nano \
  --temperature 0.1

# Higher-temperature robustness condition
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 10 \
  --model gpt-4.1-nano \
  --temperature 0.7

# Run both temperature conditions in one command
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 10 \
  --model gpt-4.1-nano \
  --temperatures 0.1 0.7
```

Agent B can use three instruction modes:

```bash
# Minimal forwarding test; useful as a fair protocol baseline
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 20 \
  --agent-b-mode forward \
  --temperature 0.7

# Constraint-aware processing; useful as a ceiling-effect/control condition
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 20 \
  --agent-b-mode process \
  --temperature 0.7

# Concise summarization; stronger drift-pressure condition
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 20 \
  --agent-b-mode summarize \
  --temperature 0.7
```

Multi-hop drift can be tested by increasing `--hops`:

```bash
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 10 \
  --hops 3 \
  --agent-b-mode process \
  --temperature 0.7
```

Optional LLM-as-judge scoring checks whether the final response actually respects
the detected constraints and substantively completes the task:

```bash
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 10 \
  --judge
```

The judge inspects the full final response for contradictions. For example, a
recipe that says it is peanut-free but includes peanut butter, peanut oil, satay,
or crushed peanuts should receive a violation. The harness also runs a small
deterministic safety scan and reports `hard_violation_rate` for obvious cases
such as peanut ingredients in a peanut-allergy task, meat in a vegetarian task,
or high-impact knee-stress exercises in a knee-injury task.

For a stronger thesis run, use at least 50 trials after prompt tuning:

```bash
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 50 \
  --model gpt-4.1-nano \
  --temperatures 0.7 1.0 \
  --agent-b-modes forward summarize process \
  --hops 3 \
  --judge \
  --batch
```

To vary chain length too:

```bash
python3 real_llm_comparison/run_real_llm_comparison.py \
  --trials 30 \
  --model gpt-4.1-nano \
  --temperatures 0.7 1.0 \
  --agent-b-modes forward summarize \
  --hops-values 1 3 5 \
  --judge \
  --batch
```

Interpret `process` carefully: because it explicitly asks agents to extract and
emphasize constraints, it may produce ceiling effects where text and CCP both
score perfectly. The stronger protocol test is whether CCP helps under weaker
or more compression-heavy instructions such as `forward` and `summarize`.

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
- The result JSON records the exact prompts, model, temperature, hop count, and
  Agent B mode so the experiment can be cited in the thesis appendix.
- The result metadata includes `created_at_local` and `completed_at_local` from
  the machine running the script, including timezone offset. These timestamps are
  generated by Python, not by the LLM.
- `raw_api_calls.json` records the request/response trace needed for debugging
  and auditability. Do not commit it if the prompts or outputs contain private
  data.
- Agent A is still deterministic local code. Treat this as a limitation: the
  current harness tests downstream communication drift, not LLM-generated CCP
  construction errors.
