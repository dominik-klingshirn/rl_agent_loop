# Tier 1 RunScore — Specification

*Companion document to the README. Canonical reference for the Tier 1 `RunScore`: its formula, inputs, and the reasoning behind each term. Implemented in `post_hoc_analysis/compute_run_score.py`.*

---

## 1. Purpose & Scope

`RunScore` is a single scalar in `[0, 1]` that summarizes the **RL-policy performance of one full reward-function search** — i.e. how good the reward functions discovered over a campaign's iterations actually were at producing landing policies.

It scores the *outcome* of the search, not the agents that ran it. Orchestration fidelity (did edits propagate correctly) and cognition quality (were the decisions sound) are deliberately **out of scope** here and live in the Tier 2 framework. `RunScore` answers one question: *across this run's iterations, how strong, how sustained, and how reproducible were the resulting policies?*

---

## 2. Formula

```
RunScore = PPV^0.4 · PolRet^0.4 · TR^0.2
```

A weighted **geometric mean** of three orthogonal components (exponents sum to 1.0):

| Component | Weight | Captures |
|---|---|---|
| **PPV** — Peak Policy Value | 0.4 | *Discovery* — did the search ever find a strong reward function? |
| **PolRet** - Policy Retention | 0.4 | *Sustainment* — was quality held across the horizon, or a one-off spike? |
| **TR** — Training Robustness | 0.2 | *Reproducibility* — are the best iterations' results consistent across seeds? |

Discovery and sustainment are co-dominant; reliability acts as a lower-weighted modifier on the two.

---

## 3. The Building Block: Graded Success (`GS`)

All three components are computed over a per-iteration **graded success** score that nests a coarse goal inside a precision goal:

```
GS_i = w · s_any_i + (1 − w) · s_cen_i
```

- **`s_any_i`** — *any-landing rate*: the sum of all `landed_*` fractions in the iteration's population terminal distribution (the macro goal: land at all).
- **`s_cen_i`** — *centered-landing rate*: the `landed_centered` fraction alone (the micro/precision goal: land on the pad).
- **`w` = `gs_w`** (default `0.35`): with the default, `GS = 0.35·any + 0.65·centered`, so precision landings are weighted more heavily than bare landings.

Terminal statuses are assigned in `src/evaluation.py` at episode end; `landed_centered` requires the lander upright, both legs down, and `|x| < 0.2`.

---

## 4. Inputs & Provenance

Each per-iteration signal is read from a specific block of `iter*_metric_payload.json`. The success signals come from **stochastic training rollouts**; the efficiency penalty from the **deterministic eval set**; divergence from the **optimization/progress** logs.

| Signal | Payload key | Source telemetry |
|---|---|---|
| `s_any`, `s_cen` | `multi_seed_stochastic_health.population_terminal_distribution` | training rollouts (`*_train.csv`) |
| seed success rates (→ `σ_norm`) | `multi_seed_stochastic_health.global_reward_topology.seed_success_rates` | training rollouts |
| `E_pen` (efficiency penalty) | `multi_seed_evaluation_health.kinematic_stability.population_mean_chatter_rate` | deterministic eval (`*_eval.csv`) |
| divergence flag | `multi_seed_optimization_health.critic_robustness.systemic_critic_divergence_flag` | progress logs (`progress_*.csv`) |

A per-seed `success_rate` is the fraction of late-stage episodes ending in *any* landing status (`'landed' in status`), so both `s_any` and the dispersion term are built on the any-landing definition.

---

## 5. Component Definitions

### 5.1 PPV — Peak Policy Value

```
PPV = max_i [ GS_i · max(0, 1 − λ2 · E_pen_i) ]
```

The single best iteration the search produced, discounted by an efficiency penalty (`λ2 = 0.5`). A peak reached through wasteful, chattery control is worth less than a clean one. This is the run's **ceiling** — proof the search *could* find a good reward function. Cross-seed reliability was intentionally removed from PPV; it is owned solely by TR (Section 5.3) to keep the three terms orthogonal.

### 5.2 PolRet - Policy Retention

```
PolRet = (1 / (N−1)) · Σ_{i=0}^{N−2} (GS_i + GS_{i+1}) / 2     (0 if N < 2)
```

The trapezoidal mean of `GS` across the iteration horizon — the time-averaged graded success of the whole search trajectory. It rewards runs that *held* their gains and penalizes runs that spiked once and collapsed. Where PPV measures the ceiling, this measures the floor-to-ceiling area.

### 5.3 TR — Training Robustness

```
K        = top-ceil(N/3) iterations ranked by GS_i
σ_norm_i = std(seed_success_rates_i) / 0.5        (0 if < 2 seeds)
TR       = (1 / |K|) · Σ_{i ∈ K} [ 1 − min(1, σ_norm_i) ]
```

Among the highest-scoring iterations (`K`, the top third by `GS`), how reproducible were the successes across seeds? `σ_norm` is the cross-seed standard deviation of per-seed success rates, normalized by `0.5` — the worst-case bimodal split (half the seeds fully succeed, half fully fail) has `std = 0.5`, mapping to `1.0` before clamping. High dispersion (a "lottery-ticket" policy that only works for some seeds) drives TR down. This term keeps PPV honest: a brilliant peak that only one seed can reproduce is not trustworthy.

---

## 6. Aggregation

Before combining, each base is clamped to `[eps, 1.0]` with `eps = 0.001`, then multiplied with its exponent:

```
RunScore = clamp(PPV)^0.4 · clamp(PolRet)^0.4 · clamp(TR)^0.2
```

The **geometric mean** is deliberate: it is non-compensatory. A near-zero value in any one dimension drags the whole score toward zero, so a run cannot buy back a collapsed component with a strong one. The `eps` floor caps that penalty — a single zero shrinks the score sharply but does not annihilate it, preserving rank-ordering among weak runs.

---

## 7. Validity Layer: Divergence Gate

Distinct from the scalar score, each run carries a validity verdict:

```
diverged_run = ( #{ i ∈ K : divergence_flag_i } > |K| / 2 )
```

If a majority of the top-third iterations (`K`) show `systemic_critic_divergence_flag` (all seeds' critics saturated), the run is flagged **diverged**. Diverged runs are **excluded from the Mann-Whitney U** campaign comparison rather than zeroed — their `RunScore` is still computed and reported, but it does not contribute evidence to a statistical claim, because the underlying optimization was unsound.

---

## 8. Parameters & Defaults

| Parameter | Default | Role |
|---|---|---|
| `gs_w` | `0.35` | any-landing vs. centered-landing weight in `GS` |
| `lambda2` | `0.5` | efficiency-penalty strength in PPV |
| `eps` | `0.001` | floor for geometric-mean bases |
| `e_pen_key` | `population_mean_chatter_rate` | environment-specific efficiency penalty key (pass `none` to disable) |

---

## 9. Design Notes

- **Reliability moved from SNR to dispersion.** An earlier TR formulation used a reward signal-to-noise ratio; it was replaced by cross-seed success dispersion (`σ_norm`). A vestigial `snr` field is still collected per iteration for display but defaults to `0.0` and no longer feeds the score.
- **Structured sources only.** Every input is read from the structured metric payload — terminal distributions, seed success rates, divergence flags — never parsed from LLM prose, consistent with the project's separation of measured physical facts from model output.
- **Orthogonality is the organizing principle.** PPV (ceiling), PolRet (sustainment), and TR (reproducibility) are kept deliberately non-overlapping so the geometric mean penalizes each failure mode independently rather than double-counting any one.
