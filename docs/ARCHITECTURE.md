# Architecture Overview: Multi-Agent Algorithmic Reward Design (Branch 1)

This document details the system architecture and data flow for the Branch 1 Algorithmic Reward Design (ARD) pipeline. 
The system is designed as a fully autonomous, decoupled, dual-node loop that translates sparse physical telemetry into deterministic dense reward functions using a 'Mixture-of-Agents' LLM orchestration.

## 1. The Core Infrastructure Split

To prevent context saturation and resource bottlenecks, the pipeline is strictly divided across two hardware nodes connected via an automated SSH/SCP bridge.

* **Node 1 (Execution Node):** A Linux server handling computationally expensive parallel PPO training and raw metric aggregation.
* **Node 2 (Cognition Node):** A local Mac (Apple Silicon) orchestrating the multi-agent LLM reasoning pipeline and maintaining the evolutionary memory.

## 2. The Data Flow (Per Iteration)

### Step 1: Execution & Telemetry (Node 1)

1. **Vectorized PPO Training Across Multiple Deterministic Random Seeds:** The Linux node receives a new `reward.py` script. It spawns vectorized environments (`LunarLander-v3`) and trains across multiple seeds to ensure statistical significance. (*in parallel where the hardware supports it, otherwise sequentially — identical learning outcomes either way*) 
2. **Raw Telemetry Generation:** The environments output step-by-step CSVs tracking physical states (position, velocity, angular momentum, actuator chatter).
3. **Metric Aggregation:** A local `analysis.py` script runs on the Linux node, compressing the massive CSV files into a lightweight metric-payload JSON (`iter{NN}_metric_payload.json`), which is then sent via SCP back to the Cognition Node.

### Step 2: Deterministic Translation (Node 2)

Raw neural-network weights and raw CSVs cause LLMs to hallucinate. Before any LLM inference, the Mac node translates the iteration's metric payload (`iter{NN}_metric_payload.json`) into a semantic **Diagnostic Report** via the Deterministic Translation Layer (`analysis.py`). Every flag and classification is produced by hard-coded thresholds, the LLM never infers facts from raw numbers. (Full reference:`docs/DIAGNOSTIC_TRANSLATION.md`.)

* **Objective alignment** is judged by the **Global Conditional Delta**
  `Δ = E[R | land] − E[R | fail]`, the gap in expected return between successful and failed episodes ; whose *sign* is stable under class imbalance, variance, and non-linear reward shapes. 
  Point-biserial correlation (ρ) is retained only as a narrative descriptor; where ρ and Δ disagree, the disagreement localizes **non-linearity**, not misalignment.
* **Component-level credit assignment is dual-channel:** 
  Mutual Information detects that a non-linear dependency *exists*, and a per-step **Conditional Direction Delta** resolves its sign
  Splitting the diagnosis into NEGATIVELY ALIGNED / HIDDEN TRAITOR (rewards failure) / NON-LINEAR HELPER (rewards success) / unresolved.
* **The correlation target is dynamic:** 
  A ladder of:  task success → impact softness → failure-weighted composite viability, is selected by the population success rate.
  Guaranteeing the target is always discriminative (a 0%-success agent has no success variance to correlate against).

### Step 3: Multi-Agent Meta-Reasoning (Node 2)

The Diagnostic Report is fed into a 6-stage routing protocol. Each "Agent" is a distinct LLM call with strict temperature and system prompt boundaries to prevent logic collapse.

1. **Validator:** Reviews the prior iteration's intended hypothesis against the current Diagnostic Report. It specifically hunts for Goodhart's Law (reward hacking) and logs a permanent Post-Mortem.
2. **Strategist (High Temp, High Parameter):** Reads the Diagnostic Report and the historical Ledger. Generates 3 novel mathematical topologies to fix the identified physical failures.
3. **Organizer (Low Temp):** Sanitizes the Strategist's abstract math into a strict Markdown schema.
4. **Research Lead (Low Temp):** Acts as the executive filter. Cross-references current Strategist proposals against outcomes of previous iterations logged in the `Experiment Ledger` to select the single most viable mathematical hypothesis.
5. **Dispatcher:** Routes the chosen hypothesis, splitting it into a `<CODER_PAYLOAD>` and a `<VALIDATOR_PAYLOAD>`.
6. **Coder (Syntax-Strict Model):** Operates in a highly restricted sandbox. Translates the payload into a strictly formatted Python function (`calculate_reward(obs, info)`).

### Step 4: Code Validation & Handoff

Before deployment, a deterministic `CodeValidator` class (`code_validation.py`) gates the generated function. 
It runs static AST checks:
* syntax, an import whitelist (`math`, `numpy`, `gymnasium`, `typing`), forbidden-call/-module blacklists (`eval`, `exec`, `open`, `os`, `subprocess`, …) 
* a scope check that catches helper functions called but never defined. 

If valid after static analysis it then:
* executes the function in a restricted sandbox against a **boundary stress-test suite**: six physical states (zero, freefall, max-spin, hard-impact, perfect-landing, out-of-bounds) × all four discrete actions
* verifies signature is named exactly `calculate_reward(obs, info)` and returns a 2-tuple on every boundary. 

The Coder retries up to five times on failure. On success, the new `reward.py` ships back to Node 1 and the loop repeats.

## 3. State Management

Every LLM inference is a zero-shot prediction. The pipeline relies on two core modules to maintain state across iterations and network boundaries:

* **Workspace Manager:** Dynamically generates isolated, timestamped directory trees for every campaign, segregating telemetry, generated code, and cognition traces.
* **Experiment Ledger:** A JSON-backed evolutionary memory. It acts as the "dead drop" where the Dispatcher leaves hypotheses for the Validator to read in the future, preventing the system from falling into cyclical mathematical traps.

## Related References

- **Diagnostic signal definitions:** [docs/DIAGNOSTIC_TRANSLATION.md](DIAGNOSTIC_TRANSLATION.md)
- **Run provenance & comparability:** [docs/ARD_PROVENANCE_DESIGN.md](ARD_PROVENANCE_DESIGN.md)
- **Run scoring & statistical comparison:** see Evaluation & Reproducibility in `README.md`