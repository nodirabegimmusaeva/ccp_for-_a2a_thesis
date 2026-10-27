# Main-study v2 preparation: 27 October 2026

Status: Groq development check passed; **main v2 frozen, not started**. Specification SHA-256: `2fe109138ba889072b2bd4cd616977436b4c23220677372795a844614fd1790a`.

The approved freeze is in `research_artifacts/cross_model_v2/freeze`; the fresh working copy is `real_llm_comparison/results/cross_model/main-study-20261027-v2`. The freeze receipt hashes its files and confirms that benchmark materials and the complete schedule equal v1. V2's initial execution ledger contains zero events. All 45 offline tests pass.

## Start main-study v2, batch 1

```sh
caffeinate -i python3 -m real_llm_comparison.cross_model run \
  --run-dir real_llm_comparison/results/cross_model/main-study-20261027-v2 \
  --confirm-free-tier \
  --batch 1 \
  --max-calls 32
```

Run this in the terminal with both keys loaded and free-tier quota available. It starts a fresh main comparison, not a continuation of v1. Keep one numbered batch per invocation, 60-second provider pacing, explicit operational retries and no paid fallback. Repeating a completed batch makes no calls. Advance to the next number only after the current batch finishes. All 36 batches contain both models and all four conditions for one task/repetition.

The user requested a provider-specific adjustment after an observed Groq error. [providers.main-v2.json](providers.main-v2.json) keeps the default cap at 1,800 tokens and overrides only Qwen/Groq to 900. Gemini is unchanged, not unlimited. The same budget applies to every role and all four conditions within each model. The runner now validates the optional model-level cap and sends it as `max_tokens`; the manifest's model configuration will record the override when v2 is frozen.

## Reason and v1 disposition

The saved diagnostic `transport_diagnostic_00003.json` in the v1 execution folder reports HTTP 429, type `tokens`, and an output-tokens-per-minute limit of 1,000 versus the requested 1,800. Remaining daily requests and combined per-minute tokens were fully available in that response. This is direct evidence of an output allowance incompatibility, not evidence that the researcher's daily quota was exhausted. Extra spacing alone cannot make that particular 1,800-token request eligible under the reported limit.

Preserve the v1 immutable freeze archive and working ledger. As of this amendment they contain four attempts: one returned B1, one authentication failure and two rate-limit failures, with no final task output. Main execution therefore began operationally but no complete run was obtained. Keep v1 separate as an interrupted configuration, including its raw returned response. Do not reuse B1 in a fresh v2 run or count it as v2 evidence. The updated runner deliberately rejects resuming old snapshots because its code hash changed.

Only the Groq output budget is being revised in generation settings. All twelve benchmark tasks, evidence, scoring keys, prompts, four conditions, routes, three repetitions, seed 42 and 60-second provider pacing remain unchanged. An offline check confirms the proposed v2 schedule is identical to v1. Versioned [main_study_protocol.v2.json](main_study_protocol.v2.json) records the amendment without editing the v1 protocol or freeze.

## Completed separate development check

The researcher completed development v3 on 27 October. All 16 requests returned with `finish_reason: stop`; all four final outputs were schema-valid; all six structured B outputs parsed and preserved their source. The three protected-condition handoffs applied restoration but required no source corrections. Output-token usage ranged from 176 to 539, below the 900 cap; known total usage was 13,997 tokens. Investigator inspection found that every final answer recommended Studio/DEV-B, explained its mandatory eligibility, and disclaimed an actual booking. This is one development task, not blinded scoring or evidence of a CCP/restoration advantage. It does not guarantee absence of truncation on longer benchmark tasks; retain and report any such findings without quality retries.

The existing meeting-room development task is separate from the twelve benchmark templates. Its snapshot uses Groq alone, all four conditions and one repetition: **4 runs / 16 calls**. The following is the historical development command, not the next main-study command:

With both accounts kept on free tiers, run in the terminal where the Groq key is loaded:

```sh
caffeinate -i python3 -m real_llm_comparison.cross_model run \
  --run-dir real_llm_comparison/results/cross_model/development-smoke-20261027-v3 \
  --confirm-free-tier \
  --batch 1 \
  --max-calls 16
```

This development configuration contains only Groq, so a Gemini key was not needed for this check. No task was modified to manufacture a desired result. Development v3 is complete; do not rerun it for a more favorable outcome.

After this compatibility review, main v2 was frozen in a new directory. Main counts remain 288 runs / 1,152 workflow calls, split into 36 balanced batches. No paid fallback or judge API is added.

## Interpretation

This evaluates provider-constrained deployments with different output budgets. The primary condition contrasts are within each model, where the cap is held constant. Comparisons across models must disclose 900 versus 1,800 tokens and provider defaults; differences cannot be attributed to intrinsic model capability alone. Report usage and truncation separately by model and condition. Do not call the asymmetric configuration an equal-budget comparison or evidence that larger budgets improve reliability.
