# Autonomous Algorithmic Reward Design (ARD) via Multi-Agent Orchestration

**A locally-hosted, closed-loop pipeline that translates continuous-control physics into deterministic statistics to autonomously write, train, and debug Reinforcement Learning reward functions.**

## Executive Summary

Reinforcement Learning (RL) is notorious for its brittleness. Reward shaping is traditionally a manual "dark art" where a slight miscalculation in a penalty coefficient causes an agent to exploit the environment—like hovering indefinitely to farm survival points instead of landing.

This project completely automates the Algorithmic Reward Design (ARD) cycle. It replaces human intuition with a 6-stage Multi-Agent LLM architecture that evaluates physical telemetry, generates novel mathematical reward functions, writes the Python code, trains a PPO agent, and scientifically validates the outcome.

**Key Innovations:**

* **The Deterministic Translation Layer:** Instead of feeding raw neural network weights or vague visual descriptions to an LLM, this pipeline translates raw PPO rollout telemetry into pure, objective statistics (e.g., Critic Saturation Index, Trajectory Isomorphism, Actuator Chatter Rates). It converts an RL black-box problem into an interpretable tabular data problem.
<br>
* **Isolated "Chain-of-Agents" Architecture:** To prevent LLM hallucination and syntax collapse, reasoning is strictly decoupled from execution. A creative "Strategist" generates the mathematical hypotheses, an executive "Research Lead" filters them via Occam's Razor, and a rigid "Coder" injects the precise Python logic directly into the Gymnasium environment wrapper.
<br>
* **Algorithmic Credit Assignment & Goodhart’s Law Detection:** The system actively computes Pearson correlations ($\rho$) between individual reward components and semantic task success. A dedicated "Validator" agent identifies "Traitor Components" that invert their intended effect, compressing failed policies into an immutable Experiment Ledger to prevent cyclic reward hacking.
<br>
* **High-Efficiency Local Execution:** Designed to run completely unsupervised on local hardware. Utilizing distributed compute (Linux server for PPO training, MacBook Pro for model inference), a single 8B-parameter reasoning model dynamically rewrites environment physics, trains the agent, and runs post-mortem validation in under 8 minutes per iteration.



```mermaid
graph TD
    %% Define Styles
    classDef linux fill:#2b2d42,stroke:#61afef,stroke-width:2px,color:#fff
    classDef mac fill:#fdf6e3,stroke:#e06c75,stroke-width:2px,color:#333
    classDef llm fill:#98c379,stroke:#282c34,stroke-width:2px,color:#000
    classDef file fill:#e5c07b,stroke:#d19a66,stroke-width:2px,color:#000

    %% Subgraphs for Hardware Separation
    subgraph "Node 1: Linux Training Server (Execution & Physics)"
        A[PPO Agent Training<br/>Stable-Baselines3]:::linux
        B[Gymnasium Env<br/>LunarLander-v3]:::linux
        C[Deterministic Translation Layer<br/>Pandas/NumPy]:::linux
        
        A <-->|Actions / Obs| B
        B -->|Raw Telemetry CSVs| C
    end

    subgraph "Shared File System"
        D[(Diagnostic Report.md)]:::file
        E[(Experiment Ledger.txt)]:::file
        F[(reward_function.py)]:::file
    end

    subgraph "Node 2: MacBook Pro (M4 Max) - Inference Orchestration"
        G[Strategist LLM<br/>Hypothesis Generation]:::llm
        H[Organizer LLM<br/>Format Structuring]:::llm
        I[Research Lead LLM<br/>Executive Decision]:::llm
        J[Dispatcher LLM<br/>Payload Routing]:::llm
        K[Coder LLM<br/>Python Implementation]:::llm
        L[Validator LLM<br/>Post-Mortem Analysis]:::llm
        
        G --> H
        H --> I
        I --> J
        J -->|Math & Constraints| K
        J -->|Hypothesis & Metrics| L
    end

    %% Cross-Node Connections
    C -->|Aggregates Physics & Kinematics| D
    D -->|Context| G
    E -->|History| G
    E -->|History| I
    K -->|Overwrites| F
    F -->|Imports| B
    L -->|Appends| E
```
