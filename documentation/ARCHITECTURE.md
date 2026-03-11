# Architecture Overview: Multi-Agent Algorithmic Reward Design (Phase 1)

This document details the system architecture and data flow for the Phase 1 Algorithmic Reward Design (ARD) pipeline. The system is designed as a fully autonomous, decoupled, dual-node loop that translates sparse physical telemetry into deterministic dense reward functions using a Mixture of Experts (MoE) LLM orchestration.

## 1. The Core Infrastructure Split

To prevent context saturation and resource bottlenecks, the pipeline is strictly divided across two hardware nodes connected via an automated SSH/SCP bridge.

* **Node 1 (Execution Node):** A Linux server handling computationally expensive parallel PPO training and raw metric aggregation.
* **Node 2 (Cognition Node):** A local Mac (Apple Silicon) orchestrating the multi-agent LLM reasoning pipeline and maintaining the evolutionary memory.

## 2. The Data Flow (Per Iteration)

### Step 1: Execution & Telemetry (Node 1)

1. **Parallel PPO Training:** The Linux node receives a new `reward.py` script. It spawns vectorized environments (`LunarLander-v3`) and trains agents across multiple seeds simultaneously to ensure statistical significance.
2. **Raw Telemetry Generation:** The environments output step-by-step CSVs tracking physical states (position, velocity, angular momentum, actuator chatter).
3. **Metric Aggregation:** A local `analysis.py` script runs on the Linux node, compressing the massive CSV files into a lightweight `metrics.json` payload, which is then sent via SCP back to the Cognition Node.

### Step 2: Deterministic Translation (Node 2)

Raw neural network weights and raw CSVs cause LLMs to hallucinate. Before any LLM inference occurs, the Mac node translates `metrics.json` into a semantic **Diagnostic Report**.

* It calculates the Pearson correlation ($\rho$) between specific mathematical reward components and physical success proxies (e.g., Euclidean distance to the landing pad).
* It identifies "Traitor Components"—reward terms that have a negative $\rho$ value, indicating the agent is actively being punished for succeeding.

### Step 3: Multi-Agent Meta-Reasoning (Node 2)

The Diagnostic Report is fed into a 6-stage routing protocol. Each "Agent" is a distinct LLM call with strict temperature and system prompt boundaries to prevent logic collapse.

1. **Validator:** Reviews the prior iteration's intended hypothesis against the current Diagnostic Report. It specifically hunts for Goodhart's Law (reward hacking) and logs a permanent Post-Mortem.
2. **Strategist (High Temp, High Parameter):** Reads the Diagnostic Report and the historical Ledger. Generates 3 novel mathematical topologies to fix the identified physical failures.
3. **Organizer (Low Temp):** Sanitizes the Strategist's abstract math into a strict Markdown schema.
4. **Research Lead (Low Temp):** Acts as the executive filter. Applies Occam's Razor to select the single most viable mathematical hypothesis.
5. **Dispatcher:** Routes the chosen hypothesis, splitting it into a `<CODER_PAYLOAD>` and a `<VALIDATOR_PAYLOAD>`.
6. **Coder (Syntax-Strict Model):** Operates in a highly restricted sandbox. Translates the payload into a strictly formatted Python function (`calculate_reward(obs, info)`).

### Step 4: Code Validation & Handoff

Before the new code is deployed, a deterministic `CodeValidator` compiles the script in an isolated Python AST environment. It injects a dummy observation array to verify the function signature and checks for unauthorized library imports. If successful, the new `reward.py` is shipped back to Node 1, and the loop repeats.

## 3. State Management

The pipeline relies on two core modules to maintain state across iterations and network boundaries:

* **Workspace Manager:** Dynamically generates isolated, timestamped directory trees for every campaign, segregating telemetry, generated code, and cognition traces.
* **Experiment Ledger:** A JSON-backed evolutionary memory. It acts as the "dead drop" where the Dispatcher leaves hypotheses for the Validator to read in the future, preventing the system from falling into cyclical mathematical traps.

