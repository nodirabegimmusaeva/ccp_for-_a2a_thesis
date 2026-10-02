# Complaint handoff study: implementation and remaining evidence

This is a new study, not a reinterpretation of the five-template pilot. Run it with
`python3 -m real_llm_comparison.study`. The legacy entry point and saved results
remain available for reproducing historical numbers. Do not combine their metrics.

## Conditions and estimands

- text: unprotected labeled natural-language source and working notes.
- text_pinned: text plus immutable original source at every B and C call.
- ccp_raw: JSON source and working notes; no normalization or hidden JSON repair.
- ccp_restored: JSON with source restored from the initial deep-copied record.

All conditions receive the same routing directory, original information, common
preservation instructions and output-token budget. Reference annotations are never
sent to generating agents. JSON formatting instructions necessarily differ; the
raw-versus-text contrast estimates representation under these prompts, not a universal
intrinsic JSON effect. Protected-text versus restored-CCP compares two protection
implementations, not perfectly identical interventions. Do not attribute additive
percentages of the gain to format/restoration.

A is deterministic serialization, B1 classifies issues, subsequent B hops prepare
instructions, C drafts the work order. Initial extraction quality is outside this
experiment. Raw malformed JSON is forwarded verbatim and recorded; restored CCP
recovers source fields. Neither condition receives a final-action repair gate.

## Dataset

`real_llm_comparison/data/complaints_fixture.json` contains two SYNTHETIC software
fixtures, one per split. These are NOT a research sample or held-out validation.

Offline `study_tools prepare SNAPSHOT OUTPUT` imports Xalq Nazorati map JSON,
retaining both hintContent (narrative) and balloonContent (category/address), plus
category identifiers. It excludes coordinates and unrelated fields. It does not
redact personal information automatically. Store imports in ignored private_data/.
The draft is deliberately unreviewed and cannot be run until annotated.

Required work before real experiments:
1. Document reuse permission/terms and snapshot collection date in provenance.
2. Review and redact personal information, including identifying addresses where
   unnecessary. Preserve location conflict semantics using consistent aliases.
3. Identify exact and near duplicates; update group_id to keep related records in
   one split. Initial importer groups only whitespace-normalized exact narratives.
4. Annotate constraint IDs, requirements and deliverables independently of model
   outputs. Keep these under reference, never in the source payload.
5. Verify a routing directory. Category labels are not department ground truth.
   With no directory, the model must request routing clarification.
6. Set review_status=reviewed, provenance.privacy_review=complete and
   provenance.reuse_status=permitted only when those statements are accurate.
7. Freeze development/heldout split before tuning; do not open heldout examples
   for prompt development. Select a diverse sample with enough multi-issue cases.

The loader rejects unreviewed records and cross-split group overlap. This is a
provenance assertion, not automatic proof of lawful reuse or de-identification.

## Evaluation

The final-output schema checks validity, not substantive correctness. There is no
keyword accuracy score. Optional separate-model evaluation uses reference constraint
IDs and pass/fail/uncertain judgments for retention and compliance, plus completion
and evidence. Evaluator parse failures remain unscored, not zero-quality answers.
Reported retention describes all information available to C, including the pinned
original where applicable. Raw-versus-forwarded hop records permit separate audits.

Human packet export includes source, reference and final work order, with randomized
IDs and a separate PRIVATE mapping. Do not give the mapping to raters. It evaluates
final compliance/completion, not handoff retention. Use two independent rating files;
score all rows pass/fail/uncertain, then compute agreement before adjudicating.
The packet includes all completed outputs; sample in balanced strata if reducing it.
Failures stay in run denominators; report scored coverage and uncertainty separately.

A different judge model is partial independence, not human validation. Blind final
response review hides explicit condition names, not every possible stylistic clue.

## Runs and reproducibility

Dry run (no credentials/network required):

    python3 -m real_llm_comparison.study --dataset real_llm_comparison/data/complaints_fixture.json --dry-run

Live development run using the existing environment key:

    python3 -m real_llm_comparison.study --dataset PATH_TO_REVIEWED_DATASET --models MODEL_A MODEL_B --judge-model DIFFERENT_MODEL --trials 3 --run-dir real_llm_comparison/results/complaints-pilot

Model IDs must be chosen from models available to the account. Default model is
retained from the historical harness, not a recommendation of current pricing.

Add --resume with identical settings and directory to continue. Completed attempts,
including failures, are retained, not retried invisibly. A manifest mismatch rejects
resume. The manifest hashes the full dataset and Python source, records prompts,
model settings and git revision. Writes are atomic after each condition attempt;
interruption inside an attempt may require repeating that attempt. Output filenames
are confined to a unique new run directory. Never edit a run in place.

Condition order is shuffled within each model/task/repetition using a fixed local
seed. This seed does not seed API generation. Models execute sequentially: report
possible service-time effects. Token budgets are matched; truncation is logged.
Local processing timing covers parsing, restoration and diffing together, not a
separately measured JSON Schema validator. API attempts include retries; end-to-end
includes backoff; judge cost is stored separately. Unknown token usage stays null.

## Commands

    python3 -m real_llm_comparison.study_tools audit SNAPSHOT.json
    python3 -m real_llm_comparison.study_tools prepare SNAPSHOT.json PRIVATE_DRAFT.json
    python3 -m real_llm_comparison.study_tools legacy-audit real_llm_comparison/results/real_llm_results.json
    python3 -m real_llm_comparison.study_tools export RUN/results.json DATASET.json REVIEW_DIRECTORY
    python3 -m real_llm_comparison.study_tools agreement RATER_A.csv RATER_B.csv

Structural audit counts are not semantic-loss counts. Manually classify differences
as omitted/altered/weakened facts, harmless paraphrases, metadata changes or malformed
outputs. Correlation with final outcomes is descriptive, not counterfactual repair benefit.

## Still required before thesis claims

- Real-data permission, privacy review, reference annotations and routing validation.
- Development pilot, frozen prompts and a sufficiently varied held-out sample.
- Live two-model comparison and independent human assessment.
- Run study_analysis on completed results for paired scenario-cluster bootstrap
  intervals. Review complete-pair exclusions and sample size; repetitions are not
  independent new tasks. No significance claim is produced by this harness.
- Literature/benchmark and novelty audit; revise slides and prose only after results.

Do not interpret synthetic simulation probabilities as observed frequencies. The
original simulator remains an assumed-error sensitivity experiment. No token savings,
production safety guarantee, or grade improvement is claimed by these changes.
