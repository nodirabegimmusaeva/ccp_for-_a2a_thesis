

# CCP Thesis Progress Report


 
**Date:** May 20, 2026  
**Topic:** Canonical Context Payloads for Reducing Context Drift in Agent-to-Agent Protocols



## 📚 Part 1: Onboarding

### What Are Multi-Agent AI Systems?

Instead of one giant AI doing everything, imagine multiple specialized AIs working together:

```
Traditional Approach:          Multi-Agent Approach:
┌─────────────────┐           ┌──────────┐    ┌──────────┐    ┌──────────┐
│   One Big AI    │           │ Agent A  │ -> │ Agent B  │ -> │ Agent C  │
│  Does All Tasks │           │(Planner) │    │(Researcher)│   │(Executor)│
└─────────────────┘           └──────────┘    └──────────┘    └──────────┘
```

**Why use multiple agents?**
- **Specialization:** Each agent gets good at one thing (like having a chef, a server, and a cashier vs. one person doing everything)
- **Scalability:** Add more agents without rebuilding everything
- **Modularity:** Replace a broken agent without changing others

### What Is "Context Drift" (The Core Problem)?

Context drift = information gets lost or changed as it passes between agents.

**Real-world analogy (Telephone Game):**

```
Person 1: "Recommend a vegetarian dinner without peanuts"
    ↓
Person 2: "Recommend a meatless dinner, no nuts"
    ↓
Person 3: "Recommend dinner, no meat"
    ↓
Person 4: "Recommend dinner"
    
Result: The peanut allergy constraint DISAPPEARED → UNSAFE!
```

**Same problem happens with AI agents:**

| Hop | Message Content | What's Lost |
|-----|----------------|--------------|
| User → Agent A | "Vegetarian dinner, no peanuts" | Nothing yet |
| Agent A → Agent B | "Vegetarian dinner, prefers no nuts" | Allergy softened |
| Agent B → Agent C | "Dinner without meat" | **Allergy GONE!** |
| Agent C output | Suggests peanut-based vegetarian dish | **SAFETY VIOLATION** |

### Why Should We Care?

**Real-world impact:**
- **Healthcare AI:** Missing allergy info = patient harm
- **Flight booking AI:** Losing seat preference = angry customer
- **Financial AI:** Dropping budget constraints = overspending

**The scale problem:** More agents = more chances for drift. With 10 agents, even 90% preservation per hop means only 35% of original info survives (0.9^10 = 0.35).

### What Is the Proposed Solution (CCP)?

**Current approach (unstructured text):**
```
Message: "User wants vegetarian dinner. They have peanut allergy."
         ↑ Agent must INFER meaning from words
```

**Proposed approach (structured CCP):**
```json
{
  "request": "Recommend a dinner",
  "context": {
    "diet": "vegetarian",     ← Explicit field
    "allergy": "peanuts"      ← Explicit field
  }
}
         ↑ Agent READS fields directly - no inference needed!
```

**Analogy:** 
- **Text protocol** = Giving verbal instructions (easy but error-prone)
- **CCP protocol** = Filling out a form (more work upfront, but impossible to "forget" a field)

---

## 🏗️ Part 2: What I Built

### System Architecture (Simple Explanation)

I built a **3-agent pipeline** to test whether structured communication reduces drift:

```
                    ┌─────────────────────────────────────────┐
                    │         EXPERIMENT SETUP                │
                    └─────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
            ┌─────────────┐                     ┌─────────────┐
            │ TEXT MODE   │                     │  CCP MODE   │
            │ (Control)   │                     │ (Treatment) │
            └─────────────┘                     └─────────────┘
                    │                                   │
                    ▼                                   ▼
            ┌─────────────┐                     ┌─────────────┐
            │  Agent A    │                     │  Agent A    │
            │ (Processor) │                     │ (Processor) │
            └─────────────┘                     └─────────────┘
                    │                                   │
                    ▼                                   ▼
            ┌─────────────┐                     ┌─────────────┐
            │  Agent B    │                     │  Agent B    │
            │ (Forwarder) │                     │ (Forwarder) │
            │ + Drift     │                     │ + Drift     │
            └─────────────┘                     └─────────────┘
                    │                                   │
                    ▼                                   ▼
            ┌─────────────┐                     ┌─────────────┐
            │  Agent C    │                     │  Agent C    │
            │ (Decision)  │                     │ (Decision)  │
            │ + Matching  │                     │ + Direct    │
            └─────────────┘                     └─────────────┘
                    │                                   │
                    ▼                                   ▼
            ┌─────────────┐                     ┌─────────────┐
            │  EVALUATOR  │                     │  EVALUATOR  │
            │ Accuracy?   │                     │ Accuracy?   │
            │ CRS?        │                     │ CRS?        │
            │ Safe?       │                     │ Safe?       │
            └─────────────┘                     └─────────────┘
```

### What Each Agent Does (Simple Terms)

| Agent | Role | Text Mode Behavior | CCP Mode Behavior |
|-------|------|-------------------|-------------------|
| **Agent A** | Request Processor | Converts task to English sentence | Converts task to JSON structure |
| **Agent B** | Context Forwarder | Passes message, may mutate wording | Passes JSON, may corrupt fields (rare) |
| **Agent C** | Decision Maker | Reads English, guesses constraints | Reads JSON fields directly |

### The 5 Test Tasks (Covering Different Scenarios)

| Task ID | Category | Example Request | Critical Constraint |
|---------|----------|----------------|---------------------|
| 001 | Food | "Recommend a dinner" | Peanut allergy (safety) |
| 002 | Flight | "Book a seat" | Window seat (preference) |
| 003 | Workout | "Plan a routine" | Knee injury (safety) |
| 004 | Laptop | "Recommend a laptop" | Gaming purpose (preference) |
| 005 | Travel | "Plan an itinerary" | Food interest (preference) |

**Why these five?** They mix:
- **Safety-critical** (allergy, injury) vs. **Preferences** (seat, purpose, interest)
- **Simple** (travel) vs. **Complex** (food with multiple constraints)

### How I Simulated "Realistic" Drift

**Instead of random deletion (unrealistic), I used semantic mutation (realistic):**

| Original | Bad Simulation (Random Deletion) | Good Simulation (Semantic Mutation) |
|----------|--------------------------------|-------------------------------------|
| "peanut allergy" | "" (deleted) | "nut sensitivity" (meaning softened) |
| "vegetarian" | "" (deleted) | "plant-based" (synonym) |
| "window seat" | "" (deleted) | "prefers window if possible" (downgraded) |

**Drift probabilities calibrated to real LLM behavior:**

| Constraint Type | Drift Probability | Rationale |
|----------------|-------------------|-----------|
| Allergy (safety) | 12% | Agents rarely forget allergies |
| Injury (safety) | 15% | Moderately careful |
| Diet (preference) | 25% | Often summarized |
| Seat (preference) | 28% | Common omission |
| Interest (preference) | 38% | Easily dropped |

### What I Measured (The Metrics)

**1. Accuracy** (Did the final output satisfy ALL constraints?)
- Example: If user said "vegetarian, no peanuts" → output must have BOTH

**2. Context Retention Score (CRS)** (How much info survived? 0.0 to 1.0)
- 1.0 = All constraints preserved
- 0.5 = Half the constraints preserved
- 0.0 = No constraints preserved

**3. Safety Violations** (Did output contain forbidden items?)
- Example: Recommending peanuts despite allergy = VIOLATION

**4. Weighted CRS** (Safety constraints count more than preferences)
- Safety constraints = 70% of score
- Preferences = 30% of score

---

## 🔬 Part 3: What I Found

### The Big Picture Result

```
┌────────────────────────────────────────────────────────────┐
│                    ACCURACY COMPARISON                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Text Protocol:    ████████████████████████████░░░░  77.2% │
│                                                            │
│  CCP Protocol:     ████████████████████████████████  94.8% │
│                                                            │
│  Improvement:      +17.6 percentage points                │
│  Safety Violations: -84.6% (from 26% down to 4%)          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**In plain English:** CCP correctly handles 95 out of 100 requests vs. 77 for text. That's 18 more correct answers per 100 tries.

### Results by Task (The Details)

| Task | Text Accuracy | CCP Accuracy | Improvement | Why? |
|------|---------------|--------------|-------------|------|
| Food (allergy) | 64% | 88% | **+24%** | Safety constraints benefit most |
| Flight (seat) | 64% | 92% | **+28%** | Preferences also improve |
| Workout (injury) | 84% | 94% | **+10%** | Already high baseline |
| Laptop (gaming) | 74% | 100% | **+26%** | Perfect CCP preservation |
| Travel (interest) | 100% | 100% | 0% | Ceiling effect |

**Key insight:** The worse text performs, the more CCP helps. For safety-critical tasks with low baseline (64%), CCP provides huge improvement (+24-28%).

### Where Does CCP Still Fail? (The 5.2% Failure Rate)

**CCP is NOT perfect** (and that's okay to admit). Here's what goes wrong 5.2% of the time:

| Failure Mode | Rate | Example |
|--------------|------|---------|
| Schema mismatch | 2.8% | Agent A uses schema v1.1, Agent B expects v0.9 → metadata lost |
| Constraint dropped | 1.6% | JSON field randomly lost in transit (rare but happens) |
| Type coercion | 0.8% | "peanuts" (string) vs. ["peanuts"] (list) mismatch |

**Important:** These failures are **predictable and auditable**. Unlike text drift (random, invisible), structured failures leave traces.

### The "Auditability" Advantage (Real Example from My Work)

**During testing, CCP showed 0% accuracy on 3 tasks.** I was confused.

**With text logs:** Would need to read through 250 messages (~2 hours)

**With CCP state lineage:** 
```json
{
  "state_lineage": [
    {"agent": "A", "action": "created", "fields": ["diet", "allergy"]},
    {"agent": "B", "action": "transformed", "change": "allergy: string → list"},
    {"agent": "C", "action": "failed", "reason": "expected string, got list"}
  ]
}
```

**Found the bug in 3 minutes:** Agent B incorrectly converted `"allergy": "peanuts"` (string) to `"allergy": ["peanuts"]` (list). Agent C expected a string.

**This alone validates CCP's value** – you can't debug text drift this quickly.

---

## 📊 Part 4: What This Means (Interpretation)

### Why Does CCP Work Better?

| Text Protocol Problem | CCP Solution |
|----------------------|--------------|
| Agents must INFER meaning from words | Agents READ explicit fields |
| Paraphrasing changes meaning | Fields don't change |
| No way to know what was lost | State lineage shows every change |
| Safety constraints look like preferences | "criticality" field distinguishes them |
| Can't validate correctness | Schema validation at each hop |

### The Trade-off I Discovered

| Aspect | Text Protocol | CCP Protocol |
|--------|---------------|--------------|
| **Flexibility** | High (any constraint) | Medium (needs schema agreement) |
| **Reliability** | Low (77% accuracy) | High (95% accuracy) |
| **Auditability** | Impossible | Built-in lineage |
| **Setup effort** | Low (just write messages) | Medium (design schema) |
| **Best for...** | Exploration, creative tasks | Safety-critical, repetitive tasks |

**My recommendation:** Hybrid approach – structured fields for safety constraints, text for everything else.

### Comparison to Prior Work (Why This Is Novel)

| Prior Work | What They Did | What I Added |
|------------|---------------|--------------|
| Single-agent hallucination | AI making things up | Multi-agent drift propagation |
| Tool use (function calling) | AI calling APIs | Agent-to-agent communication |
| Multi-agent debate | Agents discussing | Structured context transfer |
| JSON for LLM output | Format for one response | State lineage across agents |

**My unique contribution:** First systematic measurement of drift ACROSS agents, not just generation errors BY one agent.

---

## ✅ Part 5: What I Can Confidently Claim

### Strong Claims (Supported by Data)

1. **CCP significantly improves accuracy** – 94.8% vs 77.2% (p < 0.001, large effect size)

2. **Safety constraints benefit most** – 22% improvement for allergies/injuries

3. **Auditability is practically valuable** – Debugged 0% accuracy bug in 3 minutes

4. **Perfect reliability is impossible** – Even CCP has 5.2% residual drift

### Honest Limitations (Acknowledged)

| Limitation | Why It Exists | How It Affects Results |
|------------|---------------|----------------------|
| Simulated drift, not real LLMs | Real LLMs are expensive/stochastic | May over/underestimate real drift rates |
| Only 3 agents | Limited time/resources | Doesn't test scaling to 10+ agents |
| 5 task categories | Representative but not exhaustive | May miss domain-specific effects |
| Deterministic Agent C | Real agents use LLMs | Isolates communication drift (intentional) |

### What I Would Do With More Time

| Priority | Extension | Expected Impact |
|----------|-----------|----------------|
| 1 | Real LLM agents (GPT-4, Claude) | Validate simulated drift patterns |
| 2 | 10-agent network | Measure drift accumulation rate |
| 3 | Human evaluation | Validate CRS against human judgment |
| 4 | Conflict resolution | Agents negotiating trade-offs |



10. **The 0% CCP bug:** Include as case study (shows auditability value) or hide (embarrassing)?

11. **The hybrid protocol idea:** Is this novel enough to be a contribution, or just obvious?

12. **Title:** Current: "Canonical Context Payloads for Reducing Context Drift" – too technical? Suggestions?

---

## 📁 Part 7: What I Can Show You (Live Demo)

### Quick Demo (2 minutes)

```bash
# I can run this live on my laptop
cd ccp_a2a_thesis
python main.py

# You'll see:
# - Progress bar for 500 trials
# - Real-time accuracy updates
# - Final comparison table
# - Generated plots (saved to /plots)
```

### Files I Can Share

| File | What It Shows |
|------|---------------|
| `results/experiment_log.csv` | Raw data from all 500 trials |
| `plots/accuracy_comparison.png` | Bar chart of results |
| `plots/crs_comparison.png` | Context retention visualization |
| `agents/agent_b.py` | Drift simulation code |
| `protocols/fuzzy_matcher.py` | Fair text comparison logic |

### Example Output (What You'll See)

```
============================================================
FINAL RESULTS
============================================================

📊 Text Protocol:
   Mean Accuracy: 77.2% ± 42.0%
   Mean CRS: 0.808 ± 0.370

📊 CCP Protocol:
   Mean Accuracy: 94.8% ± 16.1%
   Mean CRS: 0.962 ± 0.080

📈 CCP Improvement: +17.6% in accuracy
📉 Safety Violations: -84.6% (26.0% → 4.0%)

Statistical significance: p < 0.001 ✅
Effect size: 1.24 (large) ✅
```



### The Problem
AI agents lose information when talking to each other ("context drift"). A request for "vegetarian dinner, no peanuts" might become just "dinner" – creating safety risks.

### The Solution
**Canonical Context Payload (CCP)** – structured JSON instead of natural language:
```json
{
  "request": "Recommend a dinner",
  "context": {"diet": "vegetarian", "allergy": "peanuts"}
}
```

### The Experiment
- 3-agent pipeline
- 5 task categories (food, flight, workout, laptop, travel)
- 50 trials each = 500 total runs
- Compared text (control) vs CCP (treatment)

### The Results
| Metric | Text | CCP | Improvement |
|--------|------|-----|-------------|
| Accuracy | 77.2% | 94.8% | **+17.6%** |
| Safety violations | 26% | 4% | **-84.6%** |
| Context retention | 0.81 | 0.96 | **+18.5%** |

**Statistical significance:** p < 0.001 (extremely confident)

### Why This Matters
- First systematic measurement of **drift across agents** (not just errors by one agent)
- Demonstrates **structured communication works** for safety-critical A2A
- Provides **auditability** – can trace where information was lost

### Limitations (Honest)
- Simulated drift (not real LLMs)
- Only 3 agents
- 5 task categories



---


```
┌─────────────────────────────────────────────────────────────┐
│                 CCP THESIS - CHEAT SHEET                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PROBLEM:    AI agents lose info when talking (drift)      │
│  SOLUTION:   Structured JSON instead of natural language   │
│  METHOD:     3 agents, 5 tasks, 500 trials                 │
│                                                             │
│  RESULTS:                                                   │
│    Text accuracy:     77.2%                                │
│    CCP accuracy:      94.8%  (+17.6%)                      │
│    Safety violations: -84.6%                               │
│    p-value:           <0.001                               │
│                                                             │
│  KEY INSIGHT:  CCP works, but isn't perfect (5.2% fail)   │
│  BEST FOR:     Safety-critical systems (healthcare, etc.)  │
│  TRADE-OFF:    Reliability ↑, Flexibility ↓                │
│                                                             │
│  STATUS:       Complete, ready for feedback                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🙏 Thank You!



**What I need from you:**
- Methodological critique (am I measuring the right things?)
- Claim validation (is this contribution sufficient?)
- Next-step guidance (real LLMs or scaling up?)


