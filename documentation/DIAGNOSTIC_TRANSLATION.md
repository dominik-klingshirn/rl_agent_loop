
---

# Diagnostic Report Generation Pipeline (Technical Description)

## Overview

The `analysis.py` script implements a **multi-layer diagnostic system** that transforms raw reinforcement learning telemetry into a **structured, semantically meaningful report** for downstream decision-making by a Large Language Model (LLM).

The pipeline operates across **three levels of analysis**:

1. **Optimization Dynamics (Training Stability)**
2. **Reward Topology (Objective Alignment)**
3. **Behavioral Kinematics (Physical Agent Behavior)**

Each level extracts signals from different data sources, aggregates them across multiple random seeds, and converts them into **LLM-readable insights**.

---

## Input Data Sources

For each training iteration, the system ingests three types of CSV logs:

### 1. Training Optimization Logs (`progress.csv`)

* PPO metrics (KL divergence, entropy, value loss, etc.)
* Captures *how learning is happening*

### 2. Episode-Level Training Logs (`train_eps.csv`)

* Terminal states (e.g., landed, crashed)
* Reward component breakdowns
* Captures *what the reward function is actually incentivizing*

### 3. Evaluation Trajectories (`eval.csv`)

* Full timestep-by-timestep state/action traces
* Captures *how the trained agent behaves physically*

---

## Stage 1: Per-Seed Analysis

Each seed is analyzed independently to extract **low-level metrics**.

---

### A. Optimization Dynamics Analysis (Training Stability)

**Goal:** Detect whether PPO training is stable and meaningful.

Key metrics:

* **Trust Region Integrity**

  * Rolling correlation between KL divergence and clipping
  * Detects unstable updates (“thrashing”)

* **Critic Saturation Index**

  * Ratio of value loss to reward variance
  * Identifies when the value network is overwhelmed by noise

* **Policy Update Efficiency**

  * Measures how effectively gradient updates improve policy

* **Entropy Sacrifice Rate**

  * Tracks how quickly exploration is lost

* **Final Quartile Extraction**

  * Focuses only on the last 25% of training (converged behavior)

---

### B. Reward Topology Analysis (Objective Alignment)

**Goal:** Determine whether the reward function aligns with the true task.

Key metrics:

* **Objective Alignment (ρ)**

  * Correlation between total reward and actual success (landing)
  * Detects inverted or misleading reward functions

* **Survival Hacking Index**

  * Correlation between episode length and reward
  * Detects “reward farming” behaviors (e.g., hovering)

* **Terminal Mode Entropy**

  * Diversity of outcomes (collapse vs exploration)

* **Intra-Rollout Variability**

  * Sensitivity of reward under fixed policy

---

### C. Behavioral Kinematics Analysis (Physical Behavior)

**Goal:** Translate trajectories into interpretable physical behavior.

Key metrics:

* **Chatter Rate**

  * Frequency of action switching (control instability)

* **Fuel Usage Proxy**

  * Distribution of thruster activations

* **Descent Efficiency**

  * Vertical progress per unit of fuel

* **Attitude Phase-Space**

  * Combined angle and angular velocity instability

* **Macro-Oscillations**

  * Large lateral corrections (oversteering)

* **Terminal Outcome Tagging**

  * Semantic classification (landed, crashed, etc.)

---

## Stage 2: Cross-Seed Aggregation

After per-seed analysis, results are aggregated to measure **robustness and consistency**.

---

### A. Cross-Seed Robustness

* **Signal-to-Noise Ratio (SNR)**

  * Mean reward / reward variance
  * Measures consistency across seeds

* **Initialization Sensitivity**

  * Detects “lottery ticket” policies

---

### B. Trajectory Isomorphism

* Pairwise correlation between reward trajectories across seeds
* Measures whether agents **learn the same strategy**

---

### C. Kinematic Stability

* Coefficient of variation for:

  * Efficiency
  * Chatter rate
* Detects sensitivity to randomness in physical behavior

---

### D. Population-Level Failure Analysis

* Aggregated terminal state distribution
* Identifies dominant failure modes

---

## Stage 3: Reward Component Credit Assignment

**Goal:** Diagnose individual reward terms.

For each reward component:

* Correlation with:

  * Success
  * Stability
  * Position
  * Velocity
  * Orientation

Each component is classified as:

* 🔴 **Traitor Component**

  * Encourages failure (negative correlation with success)

* 🟡 **Dead Weight**

  * Too small to matter

* 🟢 **Useful Signal**

  * Positively aligned with task success

---

## Stage 4: Semantic Translation Layer

All numerical metrics are converted into **natural language diagnostic reports**.

Three structured sections are generated:

---

### 1. Optimization Health Report

* Convergence status (Converged / Unstable / Sensitive)
* Critic health diagnostics
* Learning stability analysis

---

### 2. Reward Topology Report

* Objective alignment evaluation
* Reward hacking detection
* Component-level contribution table

---

### 3. Behavioral Kinematics Report

* Success rate and robustness
* Physical control quality
* Failure mode breakdown

---

## Final Output

The system produces a **single structured diagnostic report** that:

* Encodes complex RL dynamics into **interpretable insights**
* Removes ambiguity and hallucination risk for LLMs
* Enables **closed-loop reward function improvement**

---

## Key Insight

This pipeline is not just analysis—it is a **translation layer between reinforcement learning and language models**.

It converts:

* High-dimensional, noisy training data
  into
* Structured, semantically meaningful reasoning inputs

This is what enables the **autonomous reward design loop** to function.


