# Main-study freeze: 24 October 2026

**Historical freeze; do not resume v1.** On 27 October, v1 stopped on a Groq output-token quota incompatibility. See [MAIN_STUDY_V2.md](MAIN_STUDY_V2.md) for the user-approved provider-specific budget amendment. The freeze archive remains unchanged; statements below describe its original pre-execution state.

**Frozen; main execution has not started.** No main-study API requests were made while preparing this freeze. The twelve task templates, evidence, scoring keys and readable task/key documents are byte-identical to their pre-freeze Git versions. Their historical `prepared_not_frozen` metadata is intentionally retained; the approved manifest and receipt establish the freeze.

Specification SHA-256: `44f7312098404926a7bf46ce472a714c28863b981962776c9b4919f87016ef28`.

| Setting | Frozen value |
| --- | --- |
| Models | Google `gemini-3.5-flash-lite`; Groq `qwen/qwen3.8-27b` |
| Routes | Each model fills all four agent roles in its own route |
| Conditions | `text`, `text_pinned`, `ccp_raw`, `ccp_restored` |
| Repetitions / order seed | 3 / 42 |
| Total | 288 runs; 1,152 returned workflow calls if complete, excluding failed attempts/retries |
| Output budget | 1,800 maximum output tokens per request |
| Temperature / reasoning effort | Omitted; provider defaults, not matched sampling settings |
| Pacing | 60 seconds after the previous same-provider attempt finishes, including across saved restarts |
| Batches | 36 numbered batches, each 8 runs / 32 returned calls |
| Per-invocation cap | 32 attempted requests, including failed attempts |
| New spending / judge API calls | $0 / 0; manual evaluation |

Each batch contains one task and repetition with both routes and all four conditions. The existing seeded schedule remains unchanged; batch boundaries only partition it. The first batch is T1, repetition 0. Use the frozen batch plan for the remaining order. Evidence ordering is matched within each task/repetition. Mixed routes are excluded from this main study.

## Saved files

- [Provider configuration](providers.main-v1.json) and [operational protocol](main_study_protocol.json).
- [Immutable freeze folder](../../research_artifacts/cross_model_v1/freeze), including the [manifest](../../research_artifacts/cross_model_v1/freeze/manifest.json), [receipt](../../research_artifacts/cross_model_v1/freeze/freeze_receipt.json), [batch plan](../../research_artifacts/cross_model_v1/freeze/batch_plan.json), task/key snapshots, complete schedule, and implementation snapshot. The receipt hashes every frozen JSON file except itself, including the empty initial state and operational protocol.
- Working execution copy: `real_llm_comparison/results/cross_model/main-study-20261024-v1`. This ignored directory contains the evolving checkpoint and eventual raw outputs. The archived freeze's empty state remains unchanged. Reviewed results can later be published separately through the existing publication command.

The final implementation adds numbered batches and restart pacing to the development-tested runner. Its code hash therefore differs from development smoke v2. These execution changes passed offline tests; no new live compatibility or main-task trial was conducted. Both development studies remain separate from the main evidence.

## Running one batch when ready

From the package directory, with both keys already exported in your terminal and the accounts verified as free-tier eligible with sufficient quota:

```sh
caffeinate -i python3 -m real_llm_comparison.cross_model run \
  --run-dir real_llm_comparison/results/cross_model/main-study-20261024-v1 \
  --confirm-free-tier \
  --batch 1 \
  --max-calls 32
```

This command is provided for later execution; it was not run during freezing. It stops at batch 1's boundary. Repeating it resumes only that batch, or makes zero requests if already complete. Move to `--batch 2` only when batch 1 is complete, continuing through batch 36. Run one batch at a time, without an automatic loop through all batches. A shorter invocation cap can pause a batch earlier without changing its contents or design.

Check remaining free quota before each batch. The request cap does not cap tokens, and 60-second spacing cannot guarantee that every request fits a token-rate limit. Other use of the same accounts is not coordinated by this runner. Paid billing must remain disabled; the runner cannot independently enforce account billing status. No paid fallback, provider substitution or automatic retry is allowed.

On an API/network error, stop and inspect access/quota. Honor `Retry-After` when provided; wait for the quota reset when needed. Then repeat the **same batch number and call cap**, adding `--retry-errors`. Only failed operational calls are retried; saved successful hops are reused. Keep every failed attempt in the ledger. A pending request after interruption requires inspection and explicit `--abandon-pending` before retrying; its outcome and token use may be unknown. Malformed final model outputs are retained and never retried for quality. Earlier incomplete batches cannot be skipped by the numbered interface.

## Interpretation and changes

Use the existing scoring rules: strict task success, reported CRS, raw/forwarded preservation and final compliance remain separate. The protected field is the whole original request, not evaluator-authored criticality labels. Analyze models separately with matched task/repetition comparisons; repeated calls do not create new independent task templates. No effect size or efficacy conclusion comes from development compatibility checks.

Do not change tasks, keys, prompts, model settings or schedule after main execution begins. If a provider becomes unavailable, pause and document the issue; do not silently substitute a model. Any revised study specification requires a new version while preserving this freeze and any collected evidence.
