# CCP A2A Thesis Simulator

This repository contains the simulator used to compare unstructured text
agent-to-agent communication with Canonical Context Payload (CCP) structured
communication for context-drift experiments.

## Quick Start

Run all commands from the repository root:

```bash
cd /Users/nodirabegim/Downloads/Uni/a2a-thesis/ccp_a2a_thesis
source .venv/bin/activate
python main.py
```

The default experiment configuration is in `config.py`:

- `NUM_TRIALS = 100`
- `SEED = 42`
- `CCP_DRIFT_PROBABILITY = 0.15`
- five task categories: Food, Flight, Workout, Laptop, Travel

The simulator prints per-task and aggregate results to the terminal. Running
`main.py` also writes plots to `plots/`.

## Reproducibility

For a detailed explanation of the protocol implementations, drift model,
expected outputs, and sanity checks, see
`docs/simulator_reproducibility.md`.

## Important Result Note

Results produced before the simulator-v3 matcher and CCP drift fixes should
not be reported as final thesis numbers. The Travel baseline matcher previously
missed the literal `interest=food` constraint, and the older CCP drift model
over-counted low-impact metadata failures.
