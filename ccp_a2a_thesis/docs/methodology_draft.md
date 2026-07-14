# Methodology Draft

## Methodological Approach

This thesis uses a comparative experimental design to evaluate whether Canonical Context Payloads (CCP) reduce context drift in agent-to-agent communication. The experiment compares two communication conditions under the same task set, agent pipeline, random seed, and evaluation metrics:

1. **Baseline unstructured text protocol**, where agents pass the user request and constraints as natural-language text.
2. **CCP structured protocol**, where agents pass the same information through a structured payload with explicit context fields, lineage, and metadata.

The independent variable is the communication protocol used between agents. The dependent variables are task accuracy, Context Retention Score (CRS), and safety/constraint violations.

## Canonical Context Payload Structure

In the prototype, a CCP is represented as a JSON-like dictionary. It contains:

| Field | Purpose |
| --- | --- |
| `task_id` | Unique task identifier. |
| `agent_id` | Agent that created or last initialized the payload. |
| `timestamp` | Payload creation time in ISO format. |
| `request` | Original user request. |
| `context` | Structured key-value constraints for known invariant fields such as `diet`, `allergy`, `seat`, and `injury`. |
| `extended_context` | Open-ended list for constraints not included in the fixed schema, such as `purpose` and `interest`. Each entry includes `key`, `value`, `criticality`, and `provenance`. |
| `constraints` | Human-readable constraint list generated from structured context fields. |
| `state_lineage` | Ordered history of agent actions on the payload. |
| `metadata` | Version, priority, and trace information. |

The main design principle is that safety-critical or task-critical information is not left only inside free-form language. Instead, it is copied into explicit fields that downstream agents can inspect deterministically.

## Baseline Method

The baseline is an unstructured text communication protocol. Agent A converts each task into a compact natural-language message, for example:

```text
User request: Recommend a dinner recipe | Dietary restriction: vegetarian | Allergy: peanut allergy
```

Agent B forwards the message after simulated drift. Agent C extracts constraints using semantic fuzzy matching rather than exact string matching. This makes the comparison fairer because the baseline can still recognize equivalent phrases such as "plant-based" for vegetarian or "seat by window" for window seat.

## Agent Pipeline

The implemented experiment uses three sequential agents:

| Agent | Role | Function |
| --- | --- | --- |
| Agent A | Request Processor | Converts the original task into either text or CCP format. |
| Agent B | Context Forwarder | Simulates context drift during inter-agent communication. |
| Agent C | Decision Maker | Produces the final response and detects whether required constraints survived. |

Communication follows a fixed linear pipeline:

```text
User task -> Agent A -> Agent B -> Agent C -> Final output
```

Both protocols use the same pipeline. The only difference is the representation passed between agents.

## Task Set

The current simulator uses five task categories:

| Task ID | Category | Request | Constraints |
| --- | --- | --- | --- |
| 001 | Food | Recommend a dinner recipe | `diet=vegetarian`, `allergy=peanut allergy` |
| 002 | Flight | Book a flight seat | `seat=window seat` |
| 003 | Workout | Plan a workout routine | `injury=knee pain` |
| 004 | Laptop | Recommend a laptop | `purpose=gaming` |
| 005 | Travel | Plan a travel itinerary | `interest=food` |

These tasks were selected to include both safety-critical constraints and ordinary preferences. In the present implementation, `allergy` and `injury` are treated as safety-critical constraints, while `diet`, `seat`, `purpose`, and `interest` are treated as preference or task-quality constraints.

## Trials and Reproducibility

Each task is evaluated across 100 stochastic trials per protocol. With five tasks and two protocols, the experiment produces:

```text
5 tasks x 100 trials x 2 protocols = 1,000 protocol executions
```

The random seed is fixed at `42` to support reproducibility. The implemented configuration is:

```python
NUM_TRIALS = 100
SEED = 42
CCP_DRIFT_RATE = 0.08
```

To reproduce the experiment, another researcher should:

1. Clone the `simulator_v3` branch.
2. Install dependencies from `requirements.txt`.
3. Run the experiment using the project virtual environment or Python interpreter.
4. Confirm that `NUM_TRIALS`, `SEED`, task definitions, and drift probabilities match the reported configuration.

## Drift Simulation

The text protocol simulates context drift by probabilistically removing constraint phrases from the forwarded message. Drift probabilities vary by constraint type:

| Constraint Type | Drift Probability |
| --- | ---: |
| allergy | 0.12 |
| injury | 0.15 |
| diet | 0.25 |
| seat | 0.28 |
| purpose | 0.35 |
| interest | 0.38 |

The CCP protocol simulates structured communication failures with an 8% probability. Possible CCP failure modes include schema mismatch, dropped constraint entries, and field type errors.

## Success and Failure Criteria

A trial is counted as successful if Agent C preserves and acts on all required constraints from the original task.

For safety-critical constraints, failure occurs if the final output does not detect the constraint. For example, if the original task contains `allergy=peanut allergy`, the trial fails when the final response does not preserve the peanut allergy.

For preference constraints, failure occurs if the final output does not detect the relevant user requirement and produces a warning or incomplete response. For example, a flight-seat task fails if the window-seat preference is lost before the decision stage.

## Accuracy Calculation

Accuracy is calculated as a binary outcome per trial:

```text
accuracy = 1 if all required constraints are preserved and satisfied
accuracy = 0 otherwise
```

Mean accuracy is then calculated as:

```text
mean accuracy = successful trials / total trials
```

Accuracy is reported separately for the text protocol and the CCP protocol, then compared using the difference in mean accuracy.

## Context Retention Score

The Context Retention Score (CRS) measures how many original constraints survive to the final agent:

```text
CRS = number of preserved original constraints / number of original constraints
```

For example, if a task has two constraints, `diet=vegetarian` and `allergy=peanut allergy`, and only the vegetarian constraint is detected at the final output, then:

```text
CRS = 1 / 2 = 0.50
```

CRS is useful because it captures partial context preservation, while accuracy captures whether the complete task succeeded.

## Methodology Slide Version

**Study Design:** Comparative experimental simulation of two A2A communication protocols: unstructured text vs Canonical Context Payloads.

**Agents:** 3-agent linear pipeline: Request Processor -> Context Forwarder -> Decision Maker.

**Tasks:** 5 task categories: Food, Flight, Workout, Laptop, Travel. Tasks include safety-critical constraints such as allergy and injury, plus preference constraints such as seat, purpose, and interest.

**Trials:** 100 trials per task per protocol, fixed random seed `42`, total 1,000 protocol executions.

**Baseline:** Natural-language message passing with semantic fuzzy constraint matching.

**CCP Condition:** JSON-like structured payload containing `task_id`, `agent_id`, `request`, `context`, `extended_context`, `constraints`, `state_lineage`, and `metadata`.

**Evaluation Metrics:** Binary task accuracy, Context Retention Score, safety violations, and drift reports.

**Success Criterion:** A run succeeds when all original task constraints are preserved and reflected in the final agent output.

## Current Implementation Notes Before Final Thesis Claims

The methodology above matches the current simulator, but two implementation issues should be resolved before reporting final results:

1. The text baseline currently fails the Travel task too harshly because the fuzzy matcher does not recognize the literal phrase `food` as `food_interest`, even though the task constraint is `interest=food`.
2. The CCP condition currently reaches perfect accuracy in the latest local run because simulated CCP drift often affects fields that Agent C does not use for final constraint detection. To make the experiment stronger, CCP failure modes should sometimes affect the same structured fields used by downstream agents, or the thesis should clearly frame CCP as preserving context under the tested failure model.

Because of these issues, final numerical claims should be treated as preliminary until the baseline matcher and CCP drift model are aligned.
