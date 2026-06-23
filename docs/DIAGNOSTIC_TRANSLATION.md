# Deterministic Translation Layer (DTL) — Technical Reference

## Overview

The `analysis.py` script implements the **Deterministic Translation Layer (DTL)** — a multi-stage pipeline that transforms raw reinforcement learning telemetry from N trained agents into a structured, semantically-rich **Diagnostic Report** consumed by downstream LLM prompts in the ARD (Autonomous Reward Design) loop.

The pipeline is deterministic by design: every numeric threshold, boolean flag, and classification rule is hard-coded, ensuring zero ambiguity or hallucination risk when the LLM orchestration pipeline interprets results. The process flows through three stages:

1. **Per-Seed Analysis** — extract low-level metrics from each agent's logs independently
2. **Cross-Seed Aggregation** — produce population-level robustness metrics across all N seeds
3. **Semantic Translation** — convert aggregated JSON payloads into structured Markdown diagnostic sections

The final assembled report is the input to the LLM reward design loop.

### Diagnostic Philosophy: Conditional Expectation over Correlation

The current pipeline treats **conditional expectation** — not linear correlation — as ground truth for objective alignment. The driving signal is the **Global Conditional Delta** `Δ = E[R | land] − E[R | fail]`: the difference in expected return between successful and failed episodes. Its sign is unambiguous regardless of variance, class imbalance, or reward-surface shape.

Point-biserial correlation (`ρ`) between reward and the binary success label is retained, but **demoted to a narrative descriptor** that drives no flags on its own. The reason is that `ρ` is fragile precisely where reward functions are most interesting: it collapses toward zero (or flips sign) under class imbalance, threshold/saturating reward terms, and high intra-class variance, even when landing strictly dominates in return. Where `ρ` and `Δ` disagree, the disagreement is itself diagnostic — it localizes **non-linearity** in the reward topology rather than misalignment.

This philosophy extends to component-level credit assignment: Mutual Information detects that a non-linear dependency *exists*, and a per-step **Conditional Direction Delta** resolves *which direction* it points (helper vs. traitor).

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

### `generate_metric_payload(iteration, num_of_seeds=4)`

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

> **Cross-payload coupling:** `translate_reward_topology()` reads from *both* the stochastic and evaluation payloads. The displayed Global Conditional Delta is sourced from the **evaluation** payload (deterministic policy), while the inversion/divergence diagnosis flags are sourced from the **stochastic** payload (training-time policy). See Stage 3, Section 3 for the rationale.

---

## Stage 1: Per-Seed Analysis

Each seed is analyzed independently by one of three functions depending on the data source.

---

### A. Optimization Dynamics — `analyze_single_seed_progress()`

**Source:** `progress_iter{XX}_seed{N}.csv`
**Goal:** Detect whether PPO training is numerically stable and making meaningful policy updates.

All metrics are computed using a rolling window (default `window_size=10`) and then **extracted from the final 25% of training** to isolate converged behavior.

| Metric | Computation | Flag | Design Rationale |
|:---|:---|:---|:---|
| **Trust Region Integrity** | Rolling Pearson correlation between `clip_fraction` and `approx_kl` | `is_thrashing_flag = True` if mean corr < 0.3 | A healthy trust region couples clipping to KL; decoupling signals the optimizer is fighting itself. |
| **Critic Saturation Index (CSI)** | `value_loss / (rolling_reward_variance + ε)` | `critic_diverged_flag = True` if CSI > 10.0 **and** explained variance < 0.5 | Normalizes value loss by the reward variance the critic is *supposed* to explain — scale-free divergence detector. |
| **Explained Variance** | Directly from SB3 log (`train/explained_variance`) | Part of critic divergence compound flag | Guards CSI against false positives when raw loss is high but the critic still tracks structure. |
| **Policy Update Efficiency** | `Δpg_loss / (\|Δkl\| + ε)` | `is_plateaued_flag = True` if \|score\| < 0.05 | Measures policy movement per unit of trust-region budget spent; near-zero = stalled updates. |
| **Final Entropy Retained (%)** | `(-mean_entropy_loss / log(4)) × 100` (assumes 4 discrete actions) | `premature_convergence_flag = True` if < 10% | Normalizes against max entropy of a 4-action space to detect collapse to a near-deterministic policy. |

**Trajectory exports (for cross-seed aggregation):**
- `critic_saturation_trend` — CSI values over the final quartile
- `explained_variance_trend` — explained variance over the final quartile
- `reward_trend` — mean episode reward over the final quartile

> **Note:** `entropy_sacrifice_rate` (`Δentropy / (\|Δkl\| + ε)`) is computed as an intermediate column but is **not written to the payload**. It currently surfaces nowhere in the report. See *Archived & Vestigial Metrics*.

---

### B. Reward Topology — `analyze_single_seed_stochastic()`

**Source:** `iter{XX}_seed{N}_train.csv`
**Goal:** Determine whether the LLM-generated reward function is mathematically aligned with the true task objective.

Uses a rolling window of `min(500, len(df)//4)` episodes. All key metrics are extracted from the **final 20%** of training (the "late stage").

#### Objective Alignment
- `is_success` is derived from `terminal_status.str.contains('landed')`, giving a binary ground-truth label
- `objective_alignment_rho`: rolling Pearson correlation between `ep_rew_total` and `is_success` — **narrative signal only** (see philosophy note above)
- `survival_hacking_idx`: rolling Pearson correlation between `ep_len` and `ep_rew_total` — **narrative signal only; no longer drives the survival-hacking flag** (the flag is now conditional-reward based; see Stage 2B)

#### Conditional Reward Means
- `mean_reward_by_terminal_state`: late-stage mean `ep_rew_total` grouped by `terminal_status`. This is the per-seed input to the population-level Global Conditional Delta `Δ` and to the survival-hacking check.
- `avg_crash_length`, `avg_landed_length`: late-stage mean `ep_len` for crashed vs. landed episodes — exposes whether failures are fast (early crash) or slow (drift/timeout).

#### Terminal Entropy
- One-hot encodes `terminal_status`, computes rolling mean distribution, then entropy normalized by `log(num_classes)`
- Surfaces as `terminal_entropy_norm`; drives `systemic_policy_collapse_flag` at the population level

#### Intra-Rollout Volatility
- Groups episodes by `rollout_id` (frozen policy weights), computes coefficient of variation (CV) of reward per rollout
- High CV indicates the environment is stochastic relative to the reward scale, with the policy held fixed

#### Dynamic Component Credit Assignment

For each `reward_*` column, the function computes three classes of signal:

**1. Pearson correlations** against five target proxy series:

| Correlation Key | Target Series | Proxy For |
|:---|:---|:---|
| `succ` | `is_success` (binary landing label) | Task success |
| `imp` | `-sqrt(x_vel² + y_vel²)` | Impact softness |
| `sp` | `-sqrt(x_pos² + y_pos²)` | Spatial proximity to pad |
| `kin` | `-sqrt(x_vel² + y_vel²)` | Kinematic gentleness |
| `att` | `-\|angle\|` | Attitude (upright) |

**2. Mutual Information (MI) against `is_success`:**
Computed via `sklearn.mutual_info_classif` in a batched call (shared kNN tree across all components, `n_neighbors=3`, `random_state=seed_id`). Active only when `is_success` has both classes present and the finite-row count ≥ 10. When unavailable, `mi_succ` defaults to `0.0`. MI captures **non-linear dependencies** (thresholds, quadratics, saturating gates) that Pearson misses. It is computed exclusively against the **success label** — proxy rungs use Pearson only.

**3. Conditional Direction Delta (per-step normalized):**
For each component, `mean(R_comp / ep_len | success) − mean(R_comp / ep_len | failure)` over late-stage episodes. Gated on `delta_sufficient_samples` (≥ 3 episodes in *both* the success and failure groups). **Design rationale:** MI tells you a non-linear dependency *exists* but is sign-blind. The Conditional Direction Delta resolves its *direction* — whether the component pays out more on successes (helper) or on failures (traitor) — on a per-timestep basis so that long and short episodes are comparable.

---

### C. Behavioral Kinematics — `analyze_single_seed_eval()`

**Source:** `iter{XX}_seed{N}_eval.csv`
**Goal:** Translate deterministic evaluation trajectories into interpretable physical control metrics. All metrics are independent of reward — computed purely from state/action observations.

Computed per episode, then averaged across all evaluation episodes:

| Metric | Computation | Design Rationale |
|:---|:---|:---|
| **Chatter Rate** | `(action.diff() != 0).sum() / (ep_len − 1)` | Frequency of action switching — proxy for jagged reward near decision boundaries. |
| **No-op Duty** | Fraction of timesteps with `action == 0` | Thruster-idle fraction. |
| **Main Thruster Duty** | Fraction of timesteps with `action == 2` | Vertical-burn fraction. |
| **Side Thruster Duty** | Fraction of timesteps with `action == 1` or `action == 3` | Lateral-burn fraction. |
| **Descent Efficiency** | `(y_pos.max() − y_pos.min()) / (main_fires + side_fires + ε)` | Vertical distance descended per fuel unit — reward-independent thermodynamic proxy. |
| **Attitude Phase-Space Volume** | `mean(sqrt(angle² + angular_vel²))` | Combined rotational instability in (angle, angular velocity) phase space. |
| **Macro-Oscillations** | `(lateral-velocity sign reversals where \|x_pos\| > 0.2) / (steps with \|x_pos\| > 0.2 + ε) × 100` | **Normalized rate** (oscillations per 100 exposed steps), *not* a raw count — so episodes of different length are comparable. |
| **Success** | `1.0` if `'landed' in status`, else `0.0` | Ground-truth terminal label. |

**Additional per-seed exports:**
- `eval_reward_by_terminal_state`: mean `ep_rew_total` grouped by terminal status — the **deterministic-policy** input to the eval-side conditional delta (see Stage 2C).
- Raw per-episode arrays (`efficiencies`, `chatter_rates`, `macro_oscillations`, `attitude_phases`, `statuses`) for cross-seed variance computation.

---

## Stage 2: Cross-Seed Aggregation

Three aggregation functions consume lists of per-seed payloads and produce the population-level JSON sub-payloads.

---

### A. `aggregate_progress_seeds()`

Produces `multi_seed_optimization_health`.

| Field | Computation | Semantic Flag | Design Rationale |
|:---|:---|:---|:---|
| `mean_final_reward` | Mean of per-seed mean reward (final quartile) | — | — |
| `cross_seed_reward_std` | Std across seeds | — | — |
| `cross_seed_cv` | `reward_std / (\|reward_mean\| + ε)` | feeds `highly_unstable_optimization_landscape_flag` | Scale-aware dispersion bounded at 0; replaces SNR, which blew up as `reward_mean → 0`. Lower = more reproducible. |
| `within_seed_terminal_cv` | Mean over seeds of `std(reward_trend) / (\|mean(reward_trend)\| + ε)` on the final quartile | `is_terminal_unstable = True` if > 0.15 | Detects non-stationarity *inside* the converged window — i.e. the policy is still churning and may not retain. |
| `mean_critic_saturation_index` | Mean CSI across seeds | — | — |
| `critic_saturation_variance` | Variance of CSI across seeds | — | — |
| `systemic_critic_divergence_flag` | `True` if **all** seeds have CSI > 10.0 | — | Requires unanimity to avoid penalizing the reward for a single unlucky seed. |
| `mean_trajectory_isomorphism_rho` | Mean pairwise Pearson correlation of final-quartile reward trajectories across all seed pairs | feeds `highly_unstable_optimization_landscape_flag` | Asks "do seeds learn the *same way*," not just "do they end up the same." |
| `highly_unstable_optimization_landscape_flag` | `True` if `cross_seed_cv > 0.5` **and** `mean_trajectory_isomorphism_rho < 0.3` | — | Combines outcome dispersion with path dissimilarity — a jagged multi-minimum landscape. |
| `is_initialization_sensitive` | `True` if `reward_std > \|reward_mean\| × 0.5` | — | — |
| `is_universally_converged` | `True` if `reward_mean > 0` **and** `reward_std < \|reward_mean\| × 0.2` | — | — |
| `is_terminal_unstable` | `True` if `within_seed_terminal_cv > 0.15` | — | — |

---

### B. `aggregate_stochastic_seeds()`

Produces `multi_seed_stochastic_health`.

#### Active Rung Selection (Dynamic Target Metric)

The aggregator automatically selects the appropriate optimization target based on population success rate, so credit assignment always references a target with discriminative signal:

| Condition | Target Name | Active Rung (`metric_key`) |
|:---|:---|:---|
| `0 < success_rate < 1` | Task Success | `succ` |
| `success_rate == 1.0` | Impact Softness | `imp` |
| `success_rate == 0.0` | Composite Viability (`dominant_failure`) | `composite` |

**Composite rung weights** (when `success_rate == 0`), blended over `sp / kin / att`:

| Dominant Failure | w_sp | w_kin | w_att |
|:---|:---:|:---:|:---:|
| `out_of_bounds` | 0.7 | 0.2 | 0.1 |
| `crashed` | 0.2 | 0.5 | 0.3 |
| `hover_timeout` | 0.6 | 0.2 | 0.2 |
| `landed_but_slid_into_valley` | 0.1 | 0.7 | 0.2 |
| *(default)* | 0.33 | 0.33 | 0.34 |

#### Global Reward Topology

| Field | Computation | Design Rationale |
|:---|:---|:---|
| `mean_objective_alignment_rho` | Mean of per-seed `objective_alignment_rho` | **Narrative descriptor only.** Point-biserial estimator; does not drive any flag. |
| `global_conditional_delta` | `E[R \| land] − E[R \| fail]` across the seed population (from `mean_reward_by_terminal_state`). `None` at 0% or 100% success | **Ground truth for alignment.** Sign is unambiguous under variance/imbalance/non-linearity. Undefined when one class has no episodes. |
| `topology_is_inverted_flag` | `True` if `global_conditional_delta < 0` | The agent earns strictly more for failing than landing — the core gradient points the wrong way. |
| `rho_delta_divergence_flag` | `True` if `global_conditional_delta > 0` **and** `mean_objective_alignment_rho < 0` | Linear `ρ` says misaligned, conditional expectation says aligned → the topology is **non-linear**, not broken. Preserve the mechanism. |
| `mean_survival_hacking_rho` | Mean of per-seed `survival_hacking_idx` | Narrative only. |
| `survival_hacking_detected_flag` | `True` if `mean(hover_timeout reward) > mean(landing reward)`, requiring ≥ 1 hover seed and ≥ 1 landing seed | Direct conditional comparison: is hovering literally more profitable than landing? Replaces the noisy `ep_len`-vs-reward correlation. |
| `target_metric_name`, `active_rung_is_success` | From rung selection | Forwarded so the translator renders the correct table schema. |
| `seed_success_rates` | Per-seed late-stage success rates | Exposes the raw distribution behind the population mean. |

#### Component Diagnostics

For each reward component, after averaging correlations/MI/delta across seeds (`relative_contribution = |mean_component_value| / Σ|mean_component_value|`):

| Flag | Condition | Design Rationale |
|:---|:---|:---|
| `is_traitor_component` | `mean_rho < -0.2` **OR** `is_hidden_traitor` | Captures both linear and non-linear opposition to the objective. |
| `is_hidden_dependency` | Success rung **and** `\|mean_rho_succ\| < 0.15` **and** `mean_mi_succ > 0.05` | Umbrella flag: a non-linear dependency Pearson missed. Direction may be unresolved. |
| `is_hidden_traitor` | `is_hidden_dependency` **and** `delta_sufficient` **and** `conditional_direction_delta < 0` | Non-linear, pays out more on failures. |
| `is_hidden_helper` | `is_hidden_dependency` **and** `delta_sufficient` **and** `conditional_direction_delta > 0` | Non-linear, pays out more on successes — preserve its structure. |
| `is_dead_weight` | Success rung: `relative_contribution < 1%` **and** `mean_mi_succ < 0.05`. Proxy rung: `relative_contribution < 1%` only | The MI guard prevents misclassifying small-coefficient gating terms (e.g. threshold bonuses) as inert. |
| `is_high_magnitude_neutral` | Proxy rung **and** `relative_contribution > 20%` **and** `\|mean_rho\| < 0.2` | A component consuming large gradient share whose relationship to the (proxy) objective is indeterminate at the current success rate. |

Each component additionally exports `alignment_rho`, `alignment_mi_succ`, `relative_magnitude_pct`, and `conditional_direction_delta`.

#### Policy Fragility

| Field | Computation | Semantic Flag |
|:---|:---|:---|
| `mean_intra_rollout_cv` | Mean of per-seed intra-rollout CV | — |
| `mean_terminal_entropy_norm` | Mean of per-seed normalized terminal entropy | `systemic_policy_collapse_flag = True` if < 0.1 |

---

### C. `aggregate_eval_seeds()`

Produces `multi_seed_evaluation_health`.

| Field | Computation | Semantic Flag |
|:---|:---|:---|
| `population_mean_success_rate` | Mean of per-seed success rates | `universal_success_flag = True` if min(success_rates) > 0.85 |
| `cross_seed_success_std` | Std across seeds | `is_lottery_ticket_policy_flag = True` if std > 0.4 |
| `efficiency_coefficient_of_variation` | `std(efficiencies) / (mean + ε)` | `kinematically_sensitive_to_initialization_flag = True` if CV > 0.5 |
| `chatter_coefficient_of_variation` | `std(chatter_rates) / (mean + ε)` | Same flag as above (OR condition) |
| `population_mean_macro_oscillations` | Mean across seeds (rate per 100 exposed steps) | `systemic_lateral_instability_flag = True` if > 2.0 |
| `stable_but_suboptimal_flag` | `True` if mean_success < 0.2 **and** std_success < 0.1 | Fails consistently the same way |
| `population_terminal_distribution` | Rebuilt from per-seed episode status arrays (weighted by episode count) | — |
| `eval_global_conditional_delta` | `E[R \| land] − E[R \| fail]` over **deterministic-eval** episodes (from `eval_reward_by_terminal_state`); `None` if either class absent | — |
| `eval_topology_inverted_flag` | `True` if eval-side failure reward > landing reward | Deterministic-policy mirror of the train-side inversion check |

**Why an eval-side delta in addition to the train-side one:** the stochastic (training) delta reflects the exploring policy; the eval delta reflects the *deployed* deterministic policy. The report displays the eval-side `Δ` as the headline number (it is what the final policy actually earns) while using the train-side flags for diagnosis (they reflect the gradient the optimizer is climbing).

---

## Stage 3: Semantic Translation Layer

Three translation functions convert the aggregated JSON into named Markdown sections. Their outputs are concatenated by `generate_diagnostic_report()` to form the final report.

---

### Section 1: Optimization Dynamics & Critic Health — `translate_optimization_health()`

**Input:** `metrics["multi_seed_optimization_health"]`

Produces `### 1. Optimization Dynamics & Critic Health` with three subsections.

**Status Header (top-level convergence label):**
- 🟢 `CONVERGED` — `is_universally_converged == True`
- 🟡 `HIGHLY SENSITIVE TO INITIALIZATION` — `is_initialization_sensitive == True` (overrides converged)
- 🔴 `UNSTABLE/FAILED` — neither flag is set

**A. Cross-Seed Robustness & Terminal Stationarity** — reports two scale-aware CVs:
- *Cross-Seed Reproducibility (CV):* pre-convergence → reproducibility undefined; > 0.5 → high dispersion, topology not enforcing a consistent policy; > 0.2 → moderate variance, similar-but-not-identical solutions; else → strong consistency.
- *Within-Seed Terminal Stationarity (CV):* `is_terminal_unstable` → optimization still churning in the final quartile, converged policy non-stationary; else → settled.

**B. Value Network (Critic) Integrity** — reports CSI with graded diagnosis:
- `systemic_critic_divergence_flag` → CRITICAL FAILURE, action required (simplify dense reward terms)
- CSI > 5.0 → Warning (reduce scale of dense penalties)
- Otherwise → Healthy

**C. Optimization Landscape** — reports trajectory isomorphism `ρ`:
- `highly_unstable_optimization_landscape_flag` → uncorrelated learning curves, jagged landscape with competing local minima

---

### Section 2: Kinematic Behavior & Physical Robustness — `translate_behavior_kinematics()`

**Input:** `metrics["multi_seed_evaluation_health"]`

Produces `### 2. Kinematic Behavior & Physical Robustness` with three subsections.

**A. Universal Policy Robustness** — reports population success rate with contextual diagnosis:
- `is_lottery_ticket_policy_flag` → LOTTERY TICKET POLICY (relies on lucky initialization)
- `universal_success_flag` → Exceptional robustness
- `stable_but_suboptimal_flag` → Consistent failure, mathematically wrong policy

**B. Thermodynamic & Actuator Efficiency** — reports descent efficiency and chatter rate:
- `kinematically_sensitive_to_initialization_flag` → high kinematic sensitivity warning
- Chatter rate > 0.2 → severe actuator chattering, action required (smooth penalties / add action-continuity reward)
- `systemic_lateral_instability_flag` → macro-oscillations, action required (rebalance X-velocity and angle penalties)

**C. Population Terminal Distribution** — reports all terminal-state percentages sorted by frequency.

---

### Section 3: Reward Topology & Credit Assignment — `translate_reward_topology()`

**Input:** `metrics["multi_seed_stochastic_health"]` (flags) **and** `metrics["multi_seed_evaluation_health"].failure_mode_analysis` (displayed `Δ`)

Produces `### 3. Reward Topology & Algorithmic Credit Assignment` with three subsections.

**A. Global Objective Alignment (Oracle Test)** — reports the ground-truth `Δ` and the narrative `ρ`:
- **Global Conditional Delta** `Δ = E[R│land] − E[R│fail]` (from the eval payload) — labeled *ground truth*; rendered `undefined (single-class population)` when `None`.
- **Objective Alignment (ρ)** — labeled *narrative descriptor — point-biserial estimator*.
- Diagnosis branches (driven by the stochastic-payload flags):
  - `topology_is_inverted_flag` → **CRITICAL FAILURE** — conditional expectation is inverted; the core gradient direction is wrong.
  - `rho_delta_divergence_flag` → **ρ-Delta Divergence** — `ρ` is noisy/negative but conditional expectation confirms landing pays more; topology is non-linear (threshold saturation / high variance). Preserve the mechanism.
  - `Δ > 0` → **Aligned** — landing yields strictly higher expected return.
  - `survival_hacking_detected_flag` → **Action Required** — agent farms points by hovering/delaying.

**B. Component-Level Contribution Table** — a dynamic Markdown table rendered per active rung:

*On success rung (`active_rung_is_success == True`):*

| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `component_name` | ρ value | MI value | X.X% | Flag |

*On proxy/composite rung:*

| Reward Component | Correlation w/ {Target} (ρ) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `component_name` | ρ value | X.X% | Flag |

**Diagnostic flag legend** (resolved in priority order; hidden-direction flags carry an inline `δ=±x.xxx/step`):

| Flag | Condition |
|:---|:---|
| 🔴 **NEGATIVELY ALIGNED** | linear gradient opposes success (`is_traitor_component` via `ρ < -0.2`) — remove or negate |
| 🔴 **HIDDEN TRAITOR** | `is_hidden_traitor` — non-linear association with failure; examine functional form (threshold/saturation) |
| 🔵 **NON-LINEAR HELPER** | `is_hidden_helper` — non-linear positive contribution; preserve this component's structure |
| 🟣 **HIDDEN DEPENDENCY** | `is_hidden_dependency` with direction unresolved (insufficient samples); examine functional form |
| 🟡 **LOW MAGNITUDE** | `is_dead_weight` (< 1% of gradient) |
| 🟠 **UNRESOLVED INFLUENCE** | `is_high_magnitude_neutral` — high gradient share, objective relationship indeterminate at current success rate |
| ⚪ Neutral/Noisy | `ρ < 0.2`, no other flags |
| 🟢 Optimal | no adverse flags |

**C. Stochastic Policy Fragility** — reports intra-rollout CV and terminal entropy:
- `systemic_policy_collapse_flag` → complete collapse into a single failure mode (KL penalty likely trapped a local minimum)
- CV > 0.5 → highly fragile policy (performance swings with frozen weights)

---

## Metric Payload JSON Schema (Summary)

```
{
  "multi_seed_optimization_health": {
    "population_metrics":   { mean_final_reward, cross_seed_reward_std,
                              cross_seed_cv, within_seed_terminal_cv },
    "critic_robustness":    { mean_critic_saturation_index, critic_saturation_variance,
                              systemic_critic_divergence_flag },
    "learning_dynamics":    { mean_trajectory_isomorphism_rho,
                              highly_unstable_optimization_landscape_flag },
    "summary_flags":        { is_initialization_sensitive, is_universally_converged,
                              is_terminal_unstable }
  },
  "multi_seed_stochastic_health": {
    "global_reward_topology":     { mean_objective_alignment_rho,        // narrative only
                                    global_conditional_delta, topology_is_inverted_flag,
                                    rho_delta_divergence_flag,
                                    mean_survival_hacking_rho, survival_hacking_detected_flag,
                                    target_metric_name, active_rung_is_success,
                                    seed_success_rates },
    "dynamic_component_analysis": {
      "<reward_component>": { alignment_rho, alignment_mi_succ,
                              is_traitor_component, is_hidden_dependency,
                              is_hidden_traitor, is_hidden_helper,
                              conditional_direction_delta,
                              relative_magnitude_pct, is_dead_weight,
                              is_high_magnitude_neutral }
    },
    "policy_fragility":           { mean_intra_rollout_cv, mean_terminal_entropy_norm,
                                    systemic_policy_collapse_flag },
    "population_terminal_distribution": { "<status>": fraction }
  },
  "multi_seed_evaluation_health": {
    "success_robustness":    { population_mean_success_rate, cross_seed_success_std,
                               is_lottery_ticket_policy_flag },
    "kinematic_stability":   { population_mean_efficiency, efficiency_coefficient_of_variation,
                               population_mean_chatter_rate, chatter_coefficient_of_variation,
                               kinematically_sensitive_to_initialization_flag },
    "lateral_control":       { population_mean_macro_oscillations, systemic_lateral_instability_flag },
    "failure_mode_analysis": { population_terminal_distribution, stable_but_suboptimal_flag,
                               universal_success_flag,
                               eval_topology_inverted_flag, eval_global_conditional_delta }
  }
}
```

---

## Key Design Principles

This pipeline is not just analysis — it is a **translation layer between reinforcement learning and language models**.

- **Determinism over inference:** All semantic classifications (flags, labels, table entries) are produced by hard-coded thresholds. The LLM never infers facts from raw numbers.
- **Conditional expectation over correlation:** Objective alignment is judged by `Δ = E[R│land] − E[R│fail]`, whose sign is robust to variance, class imbalance, and non-linear reward shapes. Point-biserial `ρ` is retained only as a narrative descriptor; `ρ`/`Δ` disagreement is read as evidence of non-linearity, not misalignment.
- **Direction-resolved non-linearity:** MI detects that a non-linear dependency exists; the per-step Conditional Direction Delta resolves whether it helps or hurts, splitting a single ambiguous flag into HIDDEN TRAITOR / NON-LINEAR HELPER / unresolved.
- **Scale-aware dispersion:** Reproducibility is measured with coefficient of variation (bounded at 0, monotonic in instability) rather than SNR, which is undefined as mean reward approaches zero.
- **Separation of compute and translation:** Analysis and aggregation run on the Linux training node; translation runs on the Mac-side inference pipeline.
- **Dynamic adaptation:** The active optimization rung (success / impact softness / composite viability) is selected automatically by population success rate, so credit assignment always references a discriminative target.
- **Closed-loop reward design:** The final Diagnostic Report directly enables the LLM pipeline to make targeted, evidence-based modifications to the reward function in the next ARD iteration.

---

## Archived & Vestigial Metrics

Metrics or formulations that were present in earlier versions of the pipeline and have since been replaced or retired. Listed for provenance and to prevent re-introduction.

| Retired Metric / Formulation | Replaced By | Reason |
|:---|:---|:---|
| **Cross-Seed SNR** — `reward_mean / (reward_std + ε)` | `cross_seed_cv` (the inverse: `reward_std / (\|reward_mean\| + ε)`) | SNR diverges as mean reward → 0 and is unbounded; CV is bounded at 0, scale-aware, and monotonic in instability. |
| **SNR-driven `highly_unstable_optimization_landscape_flag`** (`SNR < 1.0 and ρ < 0.3`) | CV-driven (`cross_seed_cv > 0.5 and ρ < 0.3`) | Follows from the SNR → CV migration; threshold recalibrated to the inverted, bounded metric. |
| **ρ-driven `topology_is_inverted_flag`** (reward negatively correlated with `is_success`) | `Δ`-driven (`global_conditional_delta < 0`) | Point-biserial `ρ` reads ≈0 or negative under class imbalance, threshold/saturating rewards, and high variance even when landing strictly dominates. Conditional expectation is sign-stable. |
| **`mean_objective_alignment_rho` as a flag driver** | Demoted to **narrative descriptor** | Too fragile to gate decisions; retained for human readability and as input to the `rho_delta_divergence_flag` non-linearity signal. |
| **ρ-driven survival hacking** (flag from `survival_hacking_idx`: `ep_len` vs `ep_rew_total` correlation) | Conditional comparison (`mean(hover_timeout reward) > mean(landing reward)`) | The length-reward correlation conflated legitimate long successful flights with hovering. The conditional comparison asks the question directly. `survival_hacking_idx` retained as a narrative signal. |
| **Single 🟣 HIDDEN DEPENDENCY flag** (non-linear dependency, undirected) | Direction-resolved trio: 🔴 HIDDEN TRAITOR / 🔵 NON-LINEAR HELPER / 🟣 unresolved | The original flag marked a component was non-linear but not whether to keep or cut it. The Conditional Direction Delta supplies direction; 🟣 now denotes only the residual case where samples are insufficient to resolve direction. |
| **Macro-Oscillations as a raw count** (count of sign reversals where `\|x_pos\| > 0.2`); flag threshold `> 5.0` | Normalized **rate** (reversals per 100 exposed steps); flag threshold `> 2.0` | Raw counts scaled with episode length, so longer episodes looked more unstable purely by duration. Normalizing by exposed steps makes the metric length-invariant; threshold recalibrated for the rate. |
| **`entropy_sacrifice_rate`** — `Δentropy / (\|Δkl\| + ε)` *(vestigial)* | *(none — currently unused)* | Still computed as an intermediate column in `analyze_single_seed_progress()` but never written to the payload, so it surfaces nowhere in the report. Candidate to either export (paired with a flag) or remove. |
