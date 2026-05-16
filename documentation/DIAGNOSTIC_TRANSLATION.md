# Deterministic Translation Layer (DTL) — Technical Reference

## Overview

The `analysis.py` script implements the **Deterministic Translation Layer (DTL)** — a multi-stage pipeline that transforms raw reinforcement learning telemetry from N trained agents into a structured, semantically-rich **Diagnostic Report** consumed by downstream LLM prompts in the ARD (Autonomous Reward Design) loop.

The pipeline is deterministic by design: every numeric threshold, boolean flag, and classification rule is hard-coded, ensuring zero ambiguity or hallucination risk when the Strategist LLM interprets results. The process flows through three stages:

1. **Per-Seed Analysis** — extract low-level metrics from each agent's logs independently
2. **Cross-Seed Aggregation** — produce population-level robustness metrics across all N seeds
3. **Semantic Translation** — convert aggregated JSON payloads into structured Markdown diagnostic sections

The final assembled report is the input to the LLM reward design loop.

---

## Input Data Sources

For each training iteration, the system ingests three CSV log types, one file per seed:

| File Pattern | Source | Captures |
|:---|:---|:---|
| `progress_iter{XX}_seed{N}.csv` | SB3 built-in logger | PPO optimization metrics (KL, entropy, value loss, etc.) |
| `iter{XX}_seed{N}_train.csv` | `MultiEnvEpisodeTracker` callback | Terminal observations, episode reward breakdowns, per-component rewards |
| `iter{XX}_seed{N}_eval.csv` | Evaluation script | Full timestep-by-timestep state/action traces during deterministic evaluation |

---

## Entry Points

### `generate_metric_payload(iteration, num_of_seeds=3)`

The primary compute entry point. Orchestrates all per-seed analysis and cross-seed aggregation for a given iteration. Uses `ExperimentWorkspace` to resolve file paths, then saves the final payload to the `metric_payloads` directory via `ws.save_metrics()`.

The saved payload has the following top-level structure:

```json
{
  "multi_seed_optimization_health": { ... },
  "multi_seed_stochastic_health":   { ... },
  "multi_seed_evaluation_health":   { ... }
}
```

### `generate_diagnostic_report(metrics: dict) -> str`

The translation entry point. Accepts the saved metrics dict and sequentially calls the three translation functions, concatenating their Markdown output into the final Diagnostic Report string.

---

## Stage 1: Per-Seed Analysis

Each seed is analyzed independently by one of three functions depending on the data source.

---

### A. Optimization Dynamics — `analyze_single_seed_progress()`

**Source:** `progress_iter{XX}_seed{N}.csv`
**Goal:** Detect whether PPO training is numerically stable and making meaningful policy updates.

All metrics are computed using a rolling window (default `window_size=10`) and then **extracted from the final 25% of training** to isolate converged behavior.

| Metric | Computation | Flag |
|:---|:---|:---|
| **Trust Region Integrity** | Rolling Pearson correlation between `clip_fraction` and `approx_kl` | `is_thrashing_flag = True` if mean corr < 0.3 |
| **Critic Saturation Index (CSI)** | `value_loss / (rolling_reward_variance + ε)` | `critic_diverged_flag = True` if CSI > 10.0 **and** explained variance < 0.5 |
| **Explained Variance** | Directly from SB3 log (`train/explained_variance`) | Part of critic divergence compound flag |
| **Policy Update Efficiency** | `Δpg_loss / (\|Δkl\| + ε)` | `is_plateaued_flag = True` if \|score\| < 0.05 |
| **Entropy Sacrifice Rate** | `Δentropy / (\|Δkl\| + ε)` | — |
| **Final Entropy Retained (%)** | `(-mean_entropy_loss / log(4)) × 100` (assumes 4 discrete actions) | `premature_convergence_flag = True` if < 10% |

**Trajectory exports (for cross-seed aggregation):**
- `critic_saturation_trend` — CSI values over the final quartile
- `explained_variance_trend` — explained variance over the final quartile
- `reward_trend` — mean episode reward over the final quartile

---

### B. Reward Topology — `analyze_single_seed_stochastic()`

**Source:** `iter{XX}_seed{N}_train.csv`
**Goal:** Determine whether the LLM-generated reward function is mathematically aligned with the true task objective.

Uses a rolling window of `min(500, len(df)//4)` episodes. All key metrics are extracted from the **final 20%** of training.

#### Objective Alignment
- `is_success` is derived from `terminal_status.str.contains('landed')`, giving a binary ground-truth label
- `objective_alignment_rho`: rolling Pearson correlation between `ep_rew_total` and `is_success`
- `survival_hacking_idx`: rolling Pearson correlation between `ep_len` and `ep_rew_total`

#### Terminal Entropy
- One-hot encodes `terminal_status`, computes rolling mean distribution, then entropy normalized by `log(num_classes)`
- `systemic_policy_collapse_flag = True` if mean normalized entropy < 0.1

#### Intra-Rollout Volatility
- Groups episodes by `rollout_id` (frozen policy weights), computes coefficient of variation (CV) of reward per rollout
- High CV indicates the environment is stochastic relative to the reward scale

#### Dynamic Component Credit Assignment (Tier 1 + Tier 2)

For each `reward_*` column, the function computes:

**Pearson correlations** against five target proxy series:

| Correlation Key | Target Series |
|:---|:---|
| `succ` | `is_success` (binary landing label) |
| `imp` | `-sqrt(x_vel² + y_vel²)` (impact softness proxy) |
| `sp` | `-sqrt(x_pos² + y_pos²)` (spatial proximity proxy) |
| `kin` | `-sqrt(x_vel² + y_vel²)` (kinematic proxy) |
| `att` | `-\|angle\|` (attitude proxy) |

**Tier 1 — Mutual Information (MI) against `is_success`:**
Computed via `sklearn.mutual_info_classif` in a batched call (shared kNN tree across all components, `n_neighbors=3`). Active only when `is_success` has both classes present and `len(df) >= 10`. When unavailable, `mi_succ` defaults to `0.0`.

MI captures **non-linear dependencies** (thresholds, quadratics, saturating functions) that Pearson misses. It is used exclusively for the **success rung** — proxy rungs use Pearson only.

---

### C. Behavioral Kinematics — `analyze_single_seed_eval()`

**Source:** `iter{XX}_seed{N}_eval.csv`
**Goal:** Translate deterministic evaluation trajectories into interpretable physical control metrics. All metrics are independent of reward — computed purely from state/action observations.

Computed per episode, then averaged across all evaluation episodes:

| Metric | Computation |
|:---|:---|
| **Chatter Rate** | `(action.diff() != 0).sum() / (ep_len - 1)` — frequency of action switching |
| **No-op Duty** | Fraction of timesteps with `action == 0` |
| **Main Thruster Duty** | Fraction of timesteps with `action == 2` |
| **Side Thruster Duty** | Fraction of timesteps with `action == 1` or `action == 3` |
| **Descent Efficiency** | `(y_pos.max() - y_pos.min()) / (main_fires + side_fires + ε)` — vertical descent per fuel unit |
| **Attitude Phase-Space Volume** | `mean(sqrt(angle² + angular_vel²))` — combined rotational instability |
| **Macro-Oscillations** | Count of lateral velocity sign reversals where `\|x_pos\| > 0.2` — large overcorrections |
| **Success** | `1.0` if `'landed' in status`, else `0.0` |

Raw per-episode arrays (`efficiencies`, `chatter_rates`, `macro_oscillations`, `attitude_phases`, `statuses`) are exported for cross-seed variance computation.

---

## Stage 2: Cross-Seed Aggregation

Three aggregation functions consume lists of per-seed payloads and produce the population-level JSON sub-payloads.

---

### A. `aggregate_progress_seeds()`

Produces `multi_seed_optimization_health`.

| Field | Computation | Semantic Flag |
|:---|:---|:---|
| `mean_final_reward` | Mean of per-seed mean reward (final quartile) | — |
| `cross_seed_reward_std` | Std across seeds | — |
| `cross_seed_snr` | `reward_mean / (reward_std + ε)` | `highly_unstable_optimization_landscape_flag = True` if SNR < 1.0 **and** trajectory isomorphism ρ < 0.3 |
| `mean_critic_saturation_index` | Mean CSI across seeds | — |
| `critic_saturation_variance` | Variance of CSI across seeds | — |
| `systemic_critic_divergence_flag` | `True` if **all** seeds have CSI > 10.0 | — |
| `mean_trajectory_isomorphism_rho` | Mean pairwise Pearson correlation of final-quartile reward trajectories across all seed combinations | — |
| `is_initialization_sensitive` | `True` if reward_std > \|reward_mean\| × 0.5 | — |
| `is_universally_converged` | `True` if reward_mean > 0 **and** reward_std < \|reward_mean\| × 0.2 | — |

---

### B. `aggregate_stochastic_seeds()`

Produces `multi_seed_stochastic_health`.

#### Active Rung Selection (Dynamic Target Metric)

The aggregator automatically selects the appropriate optimization target based on population success rate:

| Condition | Target Name | Active Rung (`metric_key`) |
|:---|:---|:---|
| `0 < success_rate < 1` | Task Success | `succ` |
| `success_rate == 1.0` | Impact Softness | `imp` |
| `success_rate == 0.0` | Composite Viability (`dominant_failure`) | `composite` |

**Composite rung weights** (when `success_rate == 0`):

| Dominant Failure | w_sp | w_kin | w_att |
|:---|:---:|:---:|:---:|
| `out_of_bounds` | 0.7 | 0.2 | 0.1 |
| `crashed` | 0.2 | 0.5 | 0.3 |
| `hover_timeout` | 0.6 | 0.2 | 0.2 |
| `landed_but_slid_into_valley` | 0.1 | 0.7 | 0.2 |
| *(default)* | 0.33 | 0.33 | 0.34 |

#### Component Diagnostics

For each reward component, after averaging correlations/MI across seeds:

| Flag | Condition |
|:---|:---|
| `is_traitor_component` | `mean_rho < -0.2` (actively penalizing successful behavior) |
| `is_hidden_dependency` | On success rung **and** `\|rho_succ\| < 0.15` **and** `mi_succ > 0.05` (non-linear dependency Pearson missed) |
| `is_dead_weight` | On success rung: `relative_contribution < 1%` **and** `mi_succ < 0.05`; On proxy rung: `relative_contribution < 1%` only |
| `is_dead_weight` guard | MI guard prevents misclassifying small-coefficient gating terms (e.g. threshold bonuses) as inert |

The `active_rung_is_success` boolean is forwarded to the translation layer to conditionally render MI columns in the report table.

---

### C. `aggregate_eval_seeds()`

Produces `multi_seed_evaluation_health`.

| Field | Computation | Semantic Flag |
|:---|:---|:---|
| `population_mean_success_rate` | Mean of per-seed success rates | `universal_success_flag = True` if min(success_rates) > 0.85 |
| `cross_seed_success_std` | Std across seeds | `is_lottery_ticket_policy_flag = True` if std > 0.4 |
| `efficiency_coefficient_of_variation` | `std(efficiencies) / (mean + ε)` | `kinematically_sensitive_to_initialization_flag = True` if CV > 0.5 |
| `chatter_coefficient_of_variation` | `std(chatter_rates) / (mean + ε)` | Same flag as above (OR condition) |
| `population_mean_macro_oscillations` | Mean across seeds | `systemic_lateral_instability_flag = True` if > 5.0 |
| `stable_but_suboptimal_flag` | `True` if mean_success < 0.2 **and** std_success < 0.1 | Fails consistently the same way |
| `population_terminal_distribution` | Rebuilt from per-seed episode status arrays (weighted by episode count) | — |

---

## Stage 3: Semantic Translation Layer

Three translation functions convert the aggregated JSON into named Markdown sections. Their outputs are concatenated by `generate_diagnostic_report()` to form the final report.

---

### Section 1: Optimization Dynamics & Critic Health — `translate_optimization_health()`

**Input:** `metrics["multi_seed_optimization_health"]`

Produces `### 1. Optimization Dynamics & Critic Health` with three subsections:

**Status Header (top-level convergence label):**
- 🟢 `CONVERGED` — `is_universally_converged == True`
- 🟡 `HIGHLY SENSITIVE TO INITIALIZATION` — `is_initialization_sensitive == True` (overrides converged)
- 🔴 `UNSTABLE/FAILED` — neither flag is set

**A. Cross-Seed Robustness** — Reports SNR with diagnosis text:
- SNR < 1.0 → Chaotic reward landscape, policy enforcement failure
- SNR ≥ 1.0 → Consistent, learnable landscape

**B. Value Network (Critic) Integrity** — Reports CSI with graded diagnosis:
- `systemic_critic_divergence_flag` → CRITICAL FAILURE, action required (simplify dense reward terms)
- CSI > 5.0 → Warning (reduce scale of dense penalties)
- Otherwise → Healthy

**C. Optimization Landscape** — Reports trajectory isomorphism ρ:
- `highly_unstable_optimization_landscape_flag` → Completely uncorrelated learning curves, jagged landscape with multiple local minima

---

### Section 2: Kinematic Behavior & Physical Robustness — `translate_behavior_kinematics()`

**Input:** `metrics["multi_seed_evaluation_health"]`

Produces `### 2. Kinematic Behavior & Physical Robustness` with three subsections:

**A. Universal Policy Robustness** — Reports population success rate with contextual diagnosis:
- `is_lottery_ticket_policy_flag` → LOTTERY TICKET POLICY (relies on lucky initialization)
- `universal_success_flag` → Exceptional robustness
- `stable_but_suboptimal_flag` → Consistent failure, mathematically wrong policy

**B. Thermodynamic & Actuator Efficiency** — Reports descent efficiency and chatter rate:
- `kinematically_sensitive_to_initialization_flag` → High kinematic sensitivity warning
- Chatter rate > 0.2 → Severe actuator chattering, action required (smooth penalties / add action-continuity reward)
- `systemic_lateral_instability_flag` → Macro-oscillations, action required (rebalance X-velocity and angle penalties)

**C. Population Terminal Distribution** — Reports all terminal state percentages sorted by frequency.

---

### Section 3: Reward Topology & Credit Assignment — `translate_reward_topology()`

**Input:** `metrics["multi_seed_stochastic_health"]`

Produces `### 3. Reward Topology & Algorithmic Credit Assignment` with three subsections:

**A. Global Objective Alignment (Oracle Test)** — Reports `mean_objective_alignment_rho`:
- `topology_is_inverted_flag` → CRITICAL FAILURE (reward negatively correlated with success)
- ρ < 0.5 → Weak alignment warning
- `survival_hacking_detected_flag` → Survival hacking action required (add temporal penalty)

**B. Component-Level Contribution Table** — A dynamic Markdown table rendered per active rung:

*On success rung (`active_rung_is_success == True`):*

| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `component_name` | ρ value | MI value | X.X% | Flag |

*On proxy/composite rung:*

| Reward Component | Correlation w/ {Target} (ρ) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `component_name` | ρ value | X.X% | Flag |

**Diagnostic flag legend:**

| Flag | Condition |
|:---|:---|
| 🔴 **NEGATIVELY ALIGNED** | `is_traitor_component == True` (ρ < -0.2) |
| 🟣 **HIDDEN DEPENDENCY** | `is_hidden_dependency == True` (non-linear; examine functional form) |
| 🟡 **LOW MAGNITUDE** | `is_dead_weight == True` (< 1% of gradient) |
| ⚪ Neutral/Noisy | ρ < 0.2, no other flags |
| 🟢 Optimal | No adverse flags |

**C. Stochastic Policy Fragility** — Reports intra-rollout CV and terminal entropy:
- `systemic_policy_collapse_flag` → Complete collapse into single failure mode
- CV > 0.5 → Highly fragile policy (performance swings with frozen weights)

---

## Metric Payload JSON Schema (Summary)

```
{
  "multi_seed_optimization_health": {
    "population_metrics":   { mean_final_reward, cross_seed_reward_std, cross_seed_snr },
    "critic_robustness":    { mean_critic_saturation_index, critic_saturation_variance, systemic_critic_divergence_flag },
    "learning_dynamics":    { mean_trajectory_isomorphism_rho, highly_unstable_optimization_landscape_flag },
    "summary_flags":        { is_initialization_sensitive, is_universally_converged }
  },
  "multi_seed_stochastic_health": {
    "global_reward_topology":     { mean_objective_alignment_rho, topology_is_inverted_flag,
                                    mean_survival_hacking_rho, survival_hacking_detected_flag,
                                    target_metric_name, active_rung_is_success },
    "dynamic_component_analysis": {
      "<reward_component>": { alignment_rho, alignment_mi_succ, is_traitor_component,
                              is_hidden_dependency, relative_magnitude_pct, is_dead_weight }
    },
    "policy_fragility":           { mean_intra_rollout_cv, mean_terminal_entropy_norm, systemic_policy_collapse_flag },
    "population_terminal_distribution": { "<status>": fraction }
  },
  "multi_seed_evaluation_health": {
    "success_robustness":    { population_mean_success_rate, cross_seed_success_std, is_lottery_ticket_policy_flag },
    "kinematic_stability":   { population_mean_efficiency, efficiency_coefficient_of_variation,
                               population_mean_chatter_rate, chatter_coefficient_of_variation,
                               kinematically_sensitive_to_initialization_flag },
    "lateral_control":       { population_mean_macro_oscillations, systemic_lateral_instability_flag },
    "failure_mode_analysis": { population_terminal_distribution, stable_but_suboptimal_flag, universal_success_flag }
  }
}
```

---

## Key Design Principles

This pipeline is not just analysis — it is a **translation layer between reinforcement learning and language models**.

- **Determinism over inference:** All semantic classifications (flags, labels, table entries) are produced by hard-coded thresholds. The LLM never infers facts from raw numbers.
- **Separation of compute and translation:** Analysis and aggregation run on the Linux training node; translation runs on the Mac-side inference pipeline.
- **Dynamic adaptation:** The active optimization rung (success / impact softness / composite viability) is selected automatically based on population success rate, ensuring credit assignment is always contextually valid.
- **Tier 1 MI integration:** Mutual Information augments Pearson correlation to surface non-linear reward dependencies (gating functions, thresholds, quadratics) that would otherwise appear as neutral noise.
- **Closed-loop reward design:** The final Diagnostic Report directly enables the Strategist LLM to make targeted, evidence-based modifications to the reward function in the next ARD iteration.
