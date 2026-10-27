# Running the cross-model extension

Implemented separately in `real_llm_comparison/cross_model/`. Existing legacy and municipal-complaint experiments are unchanged. No external dependencies are required. Main comparison: two homogeneous routes, all four conditions, twelve tasks, three repetitions: **288 runs / 1,152 workflow calls**, before operational retries.

## Current boundaries

- **27 October amendment:** [MAIN_STUDY_V2.md](MAIN_STUDY_V2.md) supersedes the historical v1 launch instructions. Model definitions may now include an optional integer `max_output_tokens` override; otherwise `settings.max_output_tokens` applies. This changes request construction, so old freezes remain readable for analysis but cannot resume with the modified implementation. The Groq-only development check passed and main v2 is frozen, not started.
- The checked-in provider configuration is an example, not proof of account access. Google Gemini and Groq-hosted Qwen use their respective provider keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) from the environment. No OpenAI endpoint, key, paid fallback or automatic provider substitution is supported. No credentials are read by `plan`, `freeze`, `simulate`, `review`, `score`, `analyze` or `publish`.
- API compatibility documentation: <https://ai.google.dev/gemini-api/docs/openai> and <https://console.groq.com/docs/openai>. Verify currently accessible model IDs and free quotas in your accounts before freezing. The program cannot verify billing status; `--confirm-free-tier` is an explicit account-level acknowledgement, not a machine-enforced dollar cap. Keep paid billing disabled. Local `--max-calls` limits requests, not money or tokens.
- Sampling and reasoning default to omission, recorded as null. These are provider defaults, not evidence of equivalent sampling or compute budgets. Do not silently substitute unsupported settings. Finalize settings before freeze using separate development fixtures.
- The canonical source contains the **entire original user request** in `source.request`. Both conditions start with the same substantive request. It does not import evaluator labels into agent inputs, infer a new constraint schema, or independently test criticality labels. This is an intentional bounded adaptation of the complaint source-restoration design.
- Every agent receives the fixed evidence packet. The user request is available downstream through the handoff, a protected-original attachment (`text_pinned`), or restoration (`ccp_restored`). Shared prompts contain no task-specific answer keys. Each JSON request envelope is transport serialization; the `text` handoff itself remains natural language.
- A is Python. B1 selects options/facts, B2 checks them, B3 assembles a proposal, C answers. C always returns `answer` plus a textual `received_requirements` self-report. The same output requirement applies to every condition. Eliciting retention can influence behavior; it is a limitation of this design. No model judge runs automatically.
- CCP malformed output is forwarded verbatim in `ccp_raw`. In `ccp_restored`, the exact source is reinstated and invalid raw output is retained as working notes. Working proposals are never restored to evaluator answers. All raw outputs, inputs, requested/returned models, usage and transformations are logged.

## Offline preparation

From the repository package directory:

```sh
python3 -m real_llm_comparison.cross_model plan
python3 -m unittest discover -s tests
```

Exercise the transport/checkpoint/review path without a model or credentials. Use a fresh directory:

```sh
python3 -m real_llm_comparison.cross_model simulate --repetitions 1 --run-dir /tmp/ccp-extension-offline
python3 -m real_llm_comparison.cross_model review --run-dir /tmp/ccp-extension-offline --output /tmp/ccp-extension-review
python3 -m real_llm_comparison.cross_model analyze --run-dir /tmp/ccp-extension-offline
```

Simulation uses fixed transport responses, prominently marked OFFLINE. It provides **no model-quality evidence**. It cannot demonstrate that a provider accepts the requested settings. Do not present its counts as live experimental results.

## Freeze and live execution

The approved 24 October main-study freeze already exists. Follow [MAIN_STUDY_FREEZE.md](MAIN_STUDY_FREEZE.md), using `--batch N --max-calls 32` and its exact execution directory. Do not create another main freeze using the generic example below. Numbered batches reject skipping unfinished earlier batches, require explicit retries of saved operational errors, and stop at their own boundary even when the call cap has room remaining. Provider cooldowns carry across checkpointed restarts. The unnumbered command below describes the generic interface, which can skip saved API-error jobs; it is not the frozen main-study batching procedure.

Review requests, evidence, scoring keys, handoff prompts and provider settings first. Keep debugging examples separate from these benchmark templates. Freezing requires a deliberate acknowledgement and creates a new directory containing immutable task/key/config/code/schedule snapshots. It does not rewrite the original `prepared_not_frozen` materials.

```sh
python3 -m real_llm_comparison.cross_model freeze --approve-materials --run-dir real_llm_comparison/results/cross_model/main-v1
```

Load provider keys securely into the shell environment; never put keys in the JSON configuration or command arguments. After confirming the accounts are on free tiers:

```sh
python3 -m real_llm_comparison.cross_model run --run-dir real_llm_comparison/results/cross_model/main-v1 --confirm-free-tier --max-calls 40
```

Repeat the same run command to continue. Successful calls are checkpointed after each hop. At the request cap, execution pauses between calls. All HTTP/network errors stop the session without automatic retries. The event ledger preserves failed attempts. By default, existing API-error jobs are skipped on a later invocation and remain visible in coverage. Use `--retry-errors` deliberately to resume failed jobs from their last successfully recorded hop.

If a process terminates during a request, its outcome may be unknown. Default resume rejects an unresolved pending event. After inspection, `--abandon-pending` records the event as unknown; it does not itself retry that job. Combine with `--retry-errors` only if knowingly requesting another attempt. Requests with unknown outcomes may already have consumed quota. Do not run two executors concurrently against the same directory (a process lock rejects concurrent runs). Do not edit files in a frozen run. Changed source code or materials reject execution resume; analysis/review can still read a valid historical snapshot.

No rerunning completed/invalid outputs for a better answer. New settings require a new run. Model and task order are seeded and mixed across conditions; item order is matched across paired conditions. Python's seed does not seed provider sampling. Preserve the model response IDs and dates; if a provider model changes, report it rather than claiming a fixed snapshot.

For exploratory mixed routes, make a separate config with routes such as `["gemini", "qwen", "gemini", "qwen"]` and its reverse. Freeze it in a separate run directory and analyze route-specific effects. GPT is deliberately unavailable under the zero-new-spending scope. Do not add mixed routes after seeing main-study results without identifying the addition as exploratory.

## Human review and analysis

```sh
python3 -m real_llm_comparison.cross_model review --run-dir RUN_DIRECTORY --output REVIEW_DIRECTORY
```

Distribute `review_packet.json` and independent copies of `ratings_template.csv` to raters; withhold `PRIVATE_mapping.json`. A separate raw-handoff packet supports semantic audit. It does not automatically label structural differences as drift. Final compliance is assessed from `answer`; reported retention is assessed from `received_requirements`. Blank or malformed self-reports cannot be treated as demonstrated retention. Review includes invalid final outputs but excludes unfinished/API-error outputs with coverage disclosed. Raters may infer formatting/model identity; do not claim perfect blinding.

All expected cells must be pass/fail/uncertain with an evidence explanation. Preference satisfaction alone may be `not_applicable` when it cannot be met by a mandatory-compliant choice or selection must be withheld; this never removes the preference from the retention denominator. Keys and scoring IDs remain researcher-only. There is no exact-answer string matching. A correct catalog selection can comply without repeating its attributes; a wrong selection fails despite repeating the requirement. Preferences never compensate for mandatory failure. Strict success requires every mandatory criterion plus task completion; format-invalid outputs fail strict success. Uncertain judgments stay unresolved, not automatically failed or silently dropped.

```sh
python3 -m real_llm_comparison.cross_model score --run-dir RUN_DIRECTORY --packet-dir REVIEW_DIRECTORY --ratings RATINGS.csv --output SCORES.json
python3 -m real_llm_comparison.cross_model analyze --run-dir RUN_DIRECTORY --scores SCORES.json
```

Reported CRS and compliance include uncertainty bounds. Retention is also stratified by mandatory, safety-related and preference categories. These are run-level averages over scored outputs; inspect per-task keys/coverage. Preference satisfaction is a descriptive human rating, displayed only for strictly successful outputs with applicable preferences; it is not inferred from strings. A single imported sheet is not independent validation or adjudication. For multiple raters retain both files and establish agreement before selecting an adjudicated sheet:

```sh
python3 -m real_llm_comparison.cross_model agreement --left RATER_A.csv --right RATER_B.csv
```

This validates a common nonempty rating set and reports raw agreement and Cohen's kappa pooled and by rating kind. Raters may assess a prespecified balanced subset for agreement, but the imported final/adjudicated scoring sheet must cover the whole exported review packet.

Success contrasts compare paired repetitions, then weight task templates equally. Exploratory bootstrap intervals resample templates, not repeated calls. Excluded/unscored/unresolved pairs and operational failures remain visible. Token totals include known usage only; missing usage remains unknown. Pacing time is separate from returned-call API duration. No claim of intrinsic JSON effects, real-world safety or universal future-model robustness follows from these outputs.

## Publish the research evidence

Temporary working runs stay under ignored `results/`. Export a complete reviewed synthetic snapshot to a tracked location:

```sh
python3 -m real_llm_comparison.cross_model publish --run-dir RUN_DIRECTORY --scores SCORES.json --destination research_artifacts/cross_model_v1 --reviewed
```

The exporter includes all scheduled jobs and recorded failed attempts, frozen requests, scoring keys, prompts, code snapshot, model settings, raw/forwarded outputs and analysis. It does not choose successful cases. Credentials, environment files and private reviewer mappings are excluded. A basic credential-pattern check blocks suspicious content, but cannot replace human review. Publication does not commit or push files. The publication hashes identify the exact exported JSON objects. Keep preliminary or simulation status intact; do not present incomplete or unscored data as a completed comparative evaluation.
