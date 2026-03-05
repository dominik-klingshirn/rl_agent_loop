# Autonomous Algorithmic Reward Design (ARD) via Multi-Agent Orchestration

**A locally-hosted, closed-loop pipeline that translates continuous-control physics into deterministic statistics to autonomously write, train, and debug Reinforcement Learning reward functions.**

## Executive Summary

Reinforcement Learning (RL) is notorious for its brittleness. Reward shaping is traditionally a manual "dark art" where a slight miscalculation in a penalty coefficient causes an agent to exploit the environment—like hovering indefinitely to farm survival points instead of landing.

This project completely automates the Algorithmic Reward Design (ARD) cycle. It replaces human intuition with a 6-stage Multi-Agent LLM architecture that evaluates physical telemetry, generates novel mathematical reward functions, writes the Python code, trains a PPO agent, and scientifically validates the outcome.

**Key Innovations:**

* **The Deterministic Translation Layer:** Instead of feeding raw neural network weights, this pipeline translates PPO rollout telemetry into **objective statistics** (e.g., Critic Saturation Index). It converts an RL black-box into an interpretable tabular problem.

* **Isolated "Chain-of-Agents" Architecture:** Reasoning is strictly decoupled from execution to prevent hallucination. A **Strategist** generates hypotheses, while a **Coder** injects logic directly into the Gymnasium environment wrapper.

* **Algorithmic Credit Assignment:** The system computes **Pearson correlations** between reward components and task success. A Validator agent identifies "Traitor Components" to prevent cyclic reward hacking.

* **High-Efficiency Local Execution:** Designed to run unsupervised on local hardware. A single 8B-parameter model rewrites physics and trains the agent in **under 8 minutes per iteration**.




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
