# Provider and handoff development smoke test

**27 October: use v3 for the new output-budget check.** [providers.smoke-v3.json](providers.smoke-v3.json) tests Groq only with 900 maximum output tokens, across all four conditions: 4 runs / 16 calls. Gemini retains its existing 1,800-token cap in the proposed main configuration and is not retested in this budget check. The new snapshot is `real_llm_comparison/results/cross_model/development-smoke-20261027-v3`; see [MAIN_STUDY_V2.md](../MAIN_STUDY_V2.md) for the command and acceptance checks. Earlier instructions below are historical; v1/v2 evidence remains unchanged. Do not resume old snapshots using the modified implementation.

This is one synthetic meeting-room task, entirely separate from the twelve benchmark templates. Both providers have passed a short connection check in the researcher's terminal. This next development run tests the complete B1/B2/B3/C workflow in all four conditions.

One repetition x two homogeneous model routes x four conditions = **8 runs / 32 workflow calls**, excluding any deliberate retries. This is a compatibility/development test, not efficacy evidence or independent validation.

The original request requires capacity for eight attendees, video-conferencing equipment, a session price at most $40 and a recommendation rather than a real booking. Daylight is optional. Studio/DEV-B is the sole eligible room. The other rooms tempt a preference substitution or violation of equipment/budget requirements. Researcher keys are never sent to generating agents.

The prepared live run directory is `real_llm_comparison/results/cross_model/development-smoke-20261023-v1`. Its manifest records the purpose as `provider_and_handoff_compatibility_only`. The twelve-task materials remain unfrozen and unexposed to benchmark generation.

**Current development revision:** v1 stopped after seven attempted requests with Markdown-wrapped Gemini JSON and a Groq rate limit; see [smoke_v1_findings.md](smoke_v1_findings.md). Keep v1 unchanged. The updated prompts explicitly prohibit code fences; `providers.smoke-v2.json` uses 60-second provider pacing. A fresh v2 snapshot is prepared at `real_llm_comparison/results/cross_model/development-smoke-20261023-v2`:

```sh
python3 -m real_llm_comparison.cross_model run --run-dir real_llm_comparison/results/cross_model/development-smoke-20261023-v2 --confirm-free-tier --max-calls 32
```

Use v2 for the next check. This is a fresh development run of up to 32 calls, not a continuation of the seven v1 attempts. Expect intentional gaps of up to a minute between calls to the same provider. Another quota error still stops the session. The historical v1 command below is retained only to document its configuration; do not rerun it with the changed code.

Run from the existing terminal with both provider keys loaded and both accounts on free plans:

```sh
python3 -m real_llm_comparison.cross_model run --run-dir real_llm_comparison/results/cross_model/development-smoke-20261023-v1 --confirm-free-tier --max-calls 32
```

Progress appears after every returned handoff. Provider errors stop immediately, with no automatic retry or paid fallback. The request cap is a request count, not a guarantee about account billing. If quota is exhausted, preserve the outputs and resume later under the documented error-retry policy rather than repeatedly restarting.

After completion, inspect:

- Requested and returned model IDs match expectations.
- All eight final outputs are valid JSON with answer and received_requirements.
- Intermediate strict-JSON failures, raw source changes, and restoration events are recorded rather than hidden.
- No completion was truncated; a truncation is a compatibility finding to resolve on development fixtures before freezing the main study.
- DEV-B is selected without claiming an actual booking. Inspect the actual answers; schema validity alone does not establish correctness.
- Reported requirements retain the budget, capacity, equipment rule, optional preference and recommendation-only restriction. Do not infer retention from selection alone.

Inspect final answers locally; share connection/status summaries instead of keys. No paid judge is needed. Even a fully successful development run is not a reason to claim CCP superiority. Development adjustments require a fresh frozen run directory if code/prompts/configuration change.
