# Simulator Reproducibility Notes

This document records the implementation choices needed to reproduce the fixed
CCP vs. text-protocol simulator results.

## Environment

Use the checked-out repository and its local virtual environment:

```bash
cd /Users/nodirabegim/Downloads/Uni/a2a-thesis/ccp_a2a_thesis
source .venv/bin/activate
python --version
python main.py
```

The project dependencies are listed in `requirements.txt`. The simulator was
verified with the repository-local `.venv`.

## Experiment Configuration

The reproducible defaults are defined in `config.py`:

```python
NUM_TRIALS = 100
SEED = 42
CCP_DRIFT_PROBABILITY = 0.15
```

The text protocol uses constraint-specific drift probabilities:

```python
CONSTRAINT_DRIFT_PROBS = {
    "allergy": 0.12,
    "injury": 0.15,
    "diet": 0.25,
    "seat": 0.28,
    "purpose": 0.35,
    "interest": 0.38,
}
```

The CCP protocol uses explicit structured failure modes whose probabilities
sum to `0.15`:

```python
CCP_FAILURE_MODES = {
    "constraint_value_alteration": 0.04,
    "constraint_omission": 0.03,
    "constraint_type_mismatch": 0.02,
    "schema_validation_failure": 0.02,
    "field_type_error": 0.02,
    "lineage_corruption": 0.01,
    "timestamp_error": 0.01,
}
```

## Fixed Baseline Matcher

The text baseline matcher is implemented in `protocols/fuzzy_matcher.py`.
It includes canonical synonym mappings from `config.CONSTRAINT_SYNONYMS`.
The Travel task fix is the important regression case:

```python
"food": [
    "food",
    "food interest",
    "interest food",
    "foodie",
    "culinary",
    "restaurant",
    "local food",
    "local cuisine",
]
```

This ensures the text baseline can detect Task 005's `interest=food`
constraint when Agent A emits `Interest: food`.

## CCP Drift Model

The structured drift simulator is implemented in
`protocols/drift_simulator.py` as `CCPDriftSimulator`.

Key reproducibility details:

- Agent B passes `trial_id` and `task_id` into the CCP drift simulator.
- The per-trial random generator uses `SEED + task_id * 10000 + trial_id`.
- Payloads are deep-copied before mutation.
- Constraint-impacting failures alter fields read by Agent C:
  `context`, `extended_context`, and `constraints`.
- Metadata-only failures remain in the model for realism but have low
  probability.

This avoids the older behavior where many CCP failures changed metadata fields
that Agent C never inspected.

## Verified 100-Trial Run

The following check was run without writing plots:

```bash
python -B - <<'PY'
from experiments.runner import ExperimentRunner

runner = ExperimentRunner()
results = runner.run_full_experiment()
print(results)
PY
```

Verified aggregate output:

| Protocol | Mean Accuracy | Mean CRS | Total Trials |
| --- | ---: | ---: | ---: |
| Text | 0.766 | 0.802 | 500 |
| CCP | 0.868 | 0.878 | 500 |

Verified per-task summary:

| Task | Text Accuracy | Text CRS | CCP Accuracy | CCP CRS |
| --- | ---: | ---: | ---: | ---: |
| Food | 0.61 | 0.79 | 0.86 | 0.91 |
| Flight | 0.68 | 0.68 | 0.78 | 0.78 |
| Workout | 0.88 | 0.88 | 0.93 | 0.93 |
| Laptop | 0.66 | 0.66 | 0.87 | 0.87 |
| Travel | 1.00 | 1.00 | 0.90 | 0.90 |

The Travel text baseline is no longer zero, and CCP is no longer artificially
perfect.

## Sanity Checks for Future Researchers

Before reporting new thesis numbers, verify:

- `config.py` has `NUM_TRIALS = 100` and `SEED = 42`.
- `CONSTRAINT_SYNONYMS["food"]` includes the literal string `"food"`.
- `CCP_FAILURE_MODES` sums to `CCP_DRIFT_PROBABILITY`.
- Re-running the same task/trial produces the same CCP drift event.
- Aggregate CCP accuracy is meaningfully below 1.0 and above the text baseline.
- Results from older simulator versions are not mixed with fixed simulator
  results.
