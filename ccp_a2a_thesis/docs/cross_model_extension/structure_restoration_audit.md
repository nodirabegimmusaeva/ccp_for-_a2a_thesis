# Structure and restoration: existing implementation audit

Checked 22 October 2026. Read-only code and saved-result inspection; 17 offline unit tests passed. No live API calls, code changes, commits or pushes were made for this audit.

## Finding

The four-condition design already exists in `real_llm_comparison/study.py` and was included in commit `d6fa342` (Enhance complaint study framework and add new analysis tools). This is the municipal complaint-handoff study discussed in the chat titled **Strengthen CCP thesis validation**. It is not yet an implementation of the twelve synthetic extension tasks.

| Condition | Behavior verified in the implementation |
| --- | --- |
| `text` | Natural-language handoff, without a protected original supplied again |
| `text_pinned` | Natural-language handoff plus original source text supplied to every B and C call |
| `ccp_raw` | JSON handoff with no restoration; malformed output is forwarded verbatim |
| `ccp_restored` | JSON handoff with the source deep-copied from the original record after every B call |

The complaint implementation protects the source record. It does not establish field-specific criticality enforcement, an execution gate, or a completed evaluation of the proposed twelve tasks. The new task schema and role prompts will require adaptation.

`study_analysis.py` provides paired, scenario-cluster comparisons for `text_pinned - text`, `ccp_raw - text`, `ccp_restored - ccp_raw`, and `ccp_restored - text_pinned`. Each contrast is conditional on the implemented prompts and protection mechanisms. Pinned text and restored JSON implement different forms of protection; this is not a clean universal decomposition into additive format and restoration effects.

## Saved live evidence

The saved directory `real_llm_comparison/results/20261005-225809-ea4f584e` records a preliminary development pilot with eight real-source complaint records, one repetition and two B handoffs followed by C, using GPT-4.1 nano.

| Condition | Completed runs | Workflow API calls | Intermediate parse errors | Restoration events |
| --- | ---: | ---: | ---: | ---: |
| text | 8 | 24 | Not applicable | 0 |
| text_pinned | 8 | 24 | Not applicable | 0 |
| ccp_raw | 8 | 24 | 6 of 16 | 0 |
| ccp_restored | 8 | 24 | 4 of 16 | 7 of 16 |

Totals: 32 completed final outputs, 96 workflow calls and 68,788 tokens. Completed means structurally valid, not substantively correct. No model-evaluation objects are attached to these results. A blinded human-review packet exists, but completed independent ratings were not established by this audit. Research reuse remains recorded as preliminary/unconfirmed in the run documentation. Do not publish raw complaints or private mappings as part of an indiscriminate push.

Two other saved runs are synthetic development/fixture checks and must not be presented as held-out real-world validation.

## Original 103/450 finding

Reproduced offline using:

```sh
python3 -m real_llm_comparison.study_tools legacy-audit real_llm_comparison/results/real_llm_results.json
```

The audit counts 450 raw CCP B outputs and 103 outputs with at least one canonical-field difference. Changed-field counts overlap:

| Field | Outputs differing on this field |
| --- | ---: |
| request | 101 |
| context | 22 |
| constraints | 18 |
| extended_context | 17 |
| metadata | 10 |
| task_id | 1 |

This is a structural equality audit. The 103 outputs are not automatically 103 lost safety constraints. Semantic classification remains needed: harmless paraphrase, omission, weakening, contradiction, ownership change, and metadata-only changes. Compare raw and forwarded records, retaining task, setting and hop identifiers. An audit of restored trajectories cannot reconstruct how an unprotected pipeline would have evolved after earlier altered handoffs; that requires the separate `ccp_raw` condition.

## Git state relevant to a pre-extension checkpoint

The four-condition implementation and original tests are already committed locally in `d6fa342`. Current modified tracked files are `study.py`, `tests/test_complaint_study.py`, and `docs/complaint_study_protocol.md`. Those modifications concern evaluator anchors, data-loading/preliminary-run handling, and development-data documentation; they do not introduce the four conditions anew.

Additional study-related files remain untracked, including `real_dataset.py`, `tests/test_real_dataset.py`, and `data/complaints_development.json`. The modified complaint-study test now depends on that development fixture, so pushing only the tracked test delta would leave an incomplete reproducible checkpoint. Review and select related additions together. Exclude unrelated slide builds, private data and unfinished twelve-task materials from a checkpoint intended only for the existing study. This audit does not certify remote state or authorize a push.

## Consequence for the twelve-task extension

The earlier two-condition proposal must be revised to use all four conditions if it is to address the examiner's structure/restoration feedback directly. With 12 tasks, two models, four conditions and three repetitions, the main study would contain **288 runs and 1,152 workflow calls** for B1/B2/B3/C, excluding retries and any additional evaluator calls. Do not add mixed-model experiments to this number; budget them separately. Free-tier execution may need to span multiple quota days.

The task materials remain unchanged and not frozen. Update their protocol, output format, run budget and freeze manifest before implementing the extension. Existing implementation is substantial progress; empirical resolution still requires scoring and analysis, rather than merely showing that all four branches execute.
