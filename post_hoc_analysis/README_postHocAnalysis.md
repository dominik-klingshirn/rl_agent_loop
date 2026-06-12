# ARD Post-Hoc Evaluation Tooling

An extraction and aggregation pipeline for analyzing Autonomous Reward Design (ARD) campaign runs. Converts the raw JSON/CSV/`.py` artifacts each run leaves behind into per-iteration CSVs, cross-run summary tables, and interactive HTML dashboards.

> **Scope of this document.** This README covers the **extraction + aggregation** layer only: how raw run artifacts become CSVs and dashboards. The **Tier 1 RunScore** (per-run scoring — PPV, PolicyRetention, TR) and the **Tier 2 Orchestration/Cognition** evaluation framework are documented separately; their design rationale lives in a companion spec next to this file. Where those concerns surface here, they appear as pointers, not specifications.

---

## What This Does

**In 30 seconds:** You have N ≥ 1 campaign runs under `experiments/`. Each run produced 10+ iterations, and each iteration left behind structured artifacts. This tooling reads **four structured sources per iteration plus the accepted reward code**, stitches them together, and produces paper-ready CSVs and self-contained dashboards.

The five inputs per iteration:

- `iter{NN}_metric_payload.json` — deterministic RL outcome metrics (PSR, ρ, terminal distribution, component flags). The ground truth for outcomes.
- `iter{NN}_cognition_record.json` — the LLM call records (proposal types, RL selection). Text, so regex is used here — but only for LLM-behaviour fields, never for outcome metrics.
- `experiment_ledger.json` — structured Validator verdicts (status, hypothesis, post-mortem). One file per run.
- `ChatResponse_data.csv` — per-call token counts and durations across all six phases. One file per run.
- `iter{NN}_reward.py` + `iter{NN}_changes.patch` — the accepted reward code and its unified diff. Parsed via **AST** for component deltas and structural flags; the patch supplies raw diff size.

Outputs:

- **Three CSV files** — one row per iteration, one per run, one cross-run summary with mean ± std.
- **One JSON audit trail** — nested structure for debugging any number back to its source.
- **Three interactive HTML dashboards** — self-contained, all data embedded; charts render client-side via Chart.js from CDN.

**Key design:** Outcome metrics come directly from the payload JSON — no markdown parsing. Validator verdicts come from the ledger — no regex on the prompt. Component excisions/additions come from **AST set-difference between consecutive `reward.py` files**, which overrides the Strategist's self-reported prose (that self-report silently undercounts). Cognition records are touched only for proposal-type taxonomy and RL selection — the two things they are uniquely good for.

---

## Files

### Core Scripts

**`extract_cognition.py`** — Library for per-iteration extraction. Pure stdlib.
- `load_metric_payload(path)` → `OutcomeMetrics` — parses payload JSON directly.
- `extract_cognition_record(path)` → `CognitionRecord` — parses cognition JSON for LLM behaviour only.
- `load_ledger(path)` → `dict[int, LedgerEntry]` — parses Validator verdicts from the ledger.
- `analyze_reward_ast(path)` — AST analysis of a reward `.py`: component set, double-count flags, ghost vars.
- `load_run(campaign_path, cfg)` → `RunSummary` — aggregates all iterations in one campaign folder.
- `aggregate_across_runs(runs, sig)` → `ModelSummary` — cross-run mean ± std for one model configuration.
- `load_chat_responses(csv_path, cognition_json_dir=…)` — type-cleans ChatResponse data, converts ns → seconds, optionally joins response/thinking text from the cognition records.
- `RunPaths` — resolves every per-iteration file path under one campaign folder.
- `AggregationConfig` — tunable thresholds for regression/recovery detection (see Data Flow below).

**`analyze_run.py`** — Per-run triage entry point. Pure stdlib (plus `compute_run_score`).
- Called automatically by `outer_loop.sh` after each campaign completes.
- Reads one campaign's structured sources via `extract_cognition` and writes, under `{campaign}/{model_dir}/reports/`:
  - `triage_report.html` — self-contained per-run dashboard
  - `triage_summary.json` — machine-readable headline stats (regression/recovery counts, verdicts, floor-rule flags, RunScore)
  - `run_score.json` — the Tier 1 RunScore payload
- **RunScore and floor-rule internals are out of scope here** — see the companion scoring spec. What matters for this README: `analyze_run.py` must run per campaign **before** cross-run aggregation, because `aggregate_runs.py` reads each run's `triage_summary.json` for regression/recovery counts and run scores.

**`aggregate_runs.py`** — Cross-run CLI wrapper. Pure stdlib.
- Discovers campaigns matching a glob, loads all runs, aggregates by Strategist model.
- Writes the three CSVs and the JSON audit dump.
- Renders the three HTML dashboards from a single embedded payload.

> **Pointer — Tier 1 scoring:** `compute_run_score.py` produces the RunScore consumed by `analyze_run.py`. Its components, weights, and floor rules are specified in the companion evaluation-framework spec, not here.

---

## Quick Start

### Prerequisites

- Python 3.9+
- The extraction + aggregation layer (`extract_cognition.py`, `analyze_run.py`, `aggregate_runs.py`) is pure stdlib.
- A modern browser for the dashboards (charts load Chart.js from CDN; internet needed only on first load).

These scripts live in `post_hoc_analysis/`; there is no install step.

### Step 1 — Per-run triage (auto-run by `outer_loop.sh`)

`outer_loop.sh` calls this after each campaign, so usually you don't run it by hand. To regenerate manually:

```bash
cd ~/Projects/RL-Lab/rl_agent_loop

python3 post_hoc_analysis/analyze_run.py \
    --campaign 2026-05-13_spin_crash_10cycles_1MSteps_remote_run1
```

This writes `triage_report.html`, `triage_summary.json`, and `run_score.json` under that run's `reports/` folder. Run it for every campaign you intend to aggregate.

### Step 2 — Cross-run aggregation

```bash
python3 post_hoc_analysis/aggregate_runs.py \
    --experiments-root experiments \
    --campaign-glob '*spin_crash_10cycles_1MSteps*remote*' \
    --label spin_crash_remote
```

**Arguments:**
- `--experiments-root` — Path to your `experiments/` folder (default: `experiments`).
- `--campaign-glob` *(required)* — Glob (relative to experiments-root) matching campaigns to aggregate. **Omit the `_runN` suffix** so the glob matches all run folders of the same training configuration together.
- `--label` — Label for output files and dashboard titles (default: sanitized version of the glob).
- `--output-dir` — Output directory (default: `post_hoc_analysis/outputs/{label}/`).
- `--established_floor` — Fraction 0–1; minimum PSR a run must reach before a drop can count as a sharp regression (default: `0.40`).
- `--regression_k` — Std multiplier for the regression threshold (default: `2.0`).
- `--regression_min_floor_pp` — Minimum regression threshold in percentage-points regardless of std (default: `10.0`).
- `--recovery_window` — Max iterations after a regression within which a bounce-back counts as recovery; `0` = unbounded (default: `0`).
- `--primary-metric` — Which metric drives regression/recovery detection: `psr` or `centered` (default: `psr`).
- `--force` — Overwrite an existing output directory.

> Flag-naming note: `analyze_run.py` exposes the same knobs with hyphens (`--established-floor`), while `aggregate_runs.py` uses underscores (`--established_floor`). Mind the difference until they're unified.

### Outputs

Writes to `post_hoc_analysis/outputs/{label}/`:

```
├── iterations_long.csv          (one row per iter)
├── runs_summary.csv             (one row per run)
├── cross_run_summary.csv        (one row per model, mean±std) ← HEADLINE TABLE
├── aggregated_data.json         (full nested audit)
├── pipeline_performance.html    (dashboard 1 — RL + cognition)
├── compute_cost.html            (dashboard 2 — LLM compute)
└── code_evolution.html          (dashboard 3 — reward-code evolution)
```

### View dashboards

```bash
open post_hoc_analysis/outputs/spin_crash_remote/pipeline_performance.html
open post_hoc_analysis/outputs/spin_crash_remote/compute_cost.html
open post_hoc_analysis/outputs/spin_crash_remote/code_evolution.html
```

All data is embedded in the HTML — no server required. Chart.js loads from CDN (internet needed only on first load).

---

## Understanding the Data Flow

### Per-Iteration Assembly

For each iteration, the structured sources are stitched together:

```
iter07_metric_payload.json
├─ multi_seed_optimization_health
│  ├─ population_metrics: {cross_seed_cv, mean_final_reward, ...}
│  ├─ critic_robustness: {mean_critic_saturation_index, ...}
│  └─ learning_dynamics: {mean_trajectory_isomorphism_rho, ...}
├─ multi_seed_stochastic_health
│  ├─ global_reward_topology: {mean_objective_alignment_rho, survival_hacking_rho, ...}
│  ├─ dynamic_component_analysis: {reward_X: {alignment_rho, is_traitor, ...}, ...}
│  └─ policy_fragility: {mean_intra_rollout_cv, terminal_entropy_norm, ...}
└─ multi_seed_evaluation_health
   ├─ success_robustness: {population_mean_success_rate, ...}
   ├─ kinematic_stability: {population_mean_efficiency, ...}
   ├─ lateral_control: {population_mean_macro_oscillations, ...}
   └─ failure_mode_analysis: {population_terminal_distribution: {landed_centered: 0.3, crashed: 0.2, ...}}

iter07_cognition_record.json
├─ iteration: 7
├─ calls: [
│  ├─ {phase: "strategist",     response_content: "...[Proposal 1]...[Proposal 2]..."}
│  ├─ {phase: "research_lead",  response_content: "...**Selected Proposal:** Proposal 1..."}
│  └─ ...other phases...
└─ ...

experiment_ledger.json (one file for the whole run)
├─ experiments: [
│  ├─ {id: 1, hypothesis_payload: "...", validation_post_mortem: "**Status:** Regressed\n..."}
│  ├─ {id: 7, hypothesis_payload: "...", validation_post_mortem: "**Status:** Validated\n..."}
│  └─ ...
└─ ...

ChatResponse_data.csv (one file for the whole run; ~6 rows per iteration × phases)
├─ iteration,phase,model_name,prompt_eval_count,eval_count,total_duration_ns,...
├─ 1,strategist,gemma4-26b-mlx,3335,1237,93000000000,...
└─ ...

iter07_reward.py  +  iter07_changes.patch
├─ reward.py → AST → component set, double-count flags, ghost vars
└─ changes.patch → raw diff size (lines added/removed, hunk count)
```

**Extraction logic:**
1. Load **payload** → `OutcomeMetrics` (PSR, ρ, terminal distribution, component flags).
2. Load **cognition record** → `CognitionRecord` (proposal types, selected proposal).
3. Load **ledger** → look up the iteration → extract status from the `**Status:**` field in the post-mortem.
4. Load **chat rows** → per-phase tokens and durations for this iteration.
5. AST-diff **reward.py** against the previous iteration → component delta (excised/added), structural flags.

**Why these sources?**
- The payload is deterministic, machine-readable, and already on disk. It *is* the ground truth for outcomes.
- The cognition record is LLM text; regex is used only for proposal types and RL selection. Outcome-metric parsing is deliberately *not* done here — the Validator prompt embeds two diagnostics (prior iteration's baseline + current results), and a top-down regex would grab the wrong one (the historical off-by-one bug).
- The ledger carries structured verdicts, not markdown to be scraped.
- AST set-difference on the reward files is the authoritative source for what actually changed in the dict — it catches silent excisions the Strategist's PART 1 prose misses.

### Per-Run Aggregation

```
IterationRecord[iter1, iter2, ..., iter10]
    ↓
load_run(cfg: AggregationConfig)
    ├─ Peak PSR / peak centered (max across iters)
    ├─ Final PSR / final centered (last iter)
    ├─ Regression / recovery counts (from triage_summary.json, written by analyze_run.py)
    ├─ Stability score (σ of PSR across iters)
    ├─ Proposal-type distributions (modifications, additions, clusters, unknowns)
    ├─ Validator verdict histogram ({Validated: 2, Regressed: 5, ...})
    └─ Excision counts (AST-verified, mean per iter)
    ↓
RunSummary
```

### Cross-Run Aggregation

```
RunSummary[run1, run2, run3]
    ↓
aggregate_across_runs()
    ├─ peak_psr_mean / peak_psr_std (mean ± std of each run's peak)
    ├─ regression_count_mean / recovery_count_mean (± std)
    ├─ stability_score_mean / stability_score_std (σ of run-level σ's)
    ├─ proposal_type_mean_per_iter (mean of each type per iter, averaged across runs)
    └─ All run summaries (for drill-down)
    ↓
ModelSummary ← one row in cross_run_summary.csv
```

### Regression / Recovery Detection (`AggregationConfig`)

Behavioural events within a run are detected against a regression model, not a fixed collapse/recovery cutoff:

- `established_floor` (0.40) — a run must first reach this PSR before any drop is eligible to count as a sharp regression. Keeps early-training noise from registering as regressions.
- `regression_k` (2.0) — the regression threshold scales with `regression_k ×` the run's cross-iteration std.
- `regression_min_floor_pp` (10.0) — a hard floor on that threshold in pp, so a very stable run still needs a meaningful drop to flag.
- `recovery_window` (0) — how many iterations after a regression a bounce-back may occur and still count as recovery; `0` = unbounded.
- `primary_landing_metric` (`psr`) — which metric the detection runs on (`psr` or `centered`).

The exact comparison lives in the detection code; these knobs are the tunable surface.

---

## CSV Column Reference

### `iterations_long.csv`

One row per (model, campaign, iteration). Suitable for plotting, filtering, statistical tests.

**Outcome metrics (fractions 0–1 unless noted):**
- `psr` — population success rate (`population_mean_success_rate` from payload)
- `centered_rate` — `landed_centered` from the terminal distribution
- `objective_alignment_rho`, `survival_hacking_rho` — ρ values from topology analysis
- `cross_seed_cv` — cross-seed coefficient of variation
- `critic_saturation_index`, `trajectory_isomorphism_rho`, `intra_rollout_cv`, `terminal_entropy_norm` — optimization / fragility metrics
- `mean_descent_efficiency`, `actuator_chatter_rate`, `macro_oscillations` — kinematic metrics
- Terminal distribution: `term_landed_centered`, `term_landed_off_centered`, `term_landed_but_slid_into_valley`, `term_crashed`, `term_out_of_bounds`, `term_hover_timeout`
- Component rollups: `n_components`, `n_optimal`, `n_traitor`, `n_dead_weight`, `n_hidden_dependency`, `n_hidden_helper`, `n_high_magnitude_neutral`
- Flags: `is_lottery_ticket`, `survival_hacking_detected`, `is_initialization_sensitive`, `is_universally_converged`

**Cognition / code (LLM behaviour + ground-truth change):**
- `validator_status` — from the ledger (e.g. `Validated`, `Regressed`, `Goodhart Trap`)
- `excision_count` — components removed, **from AST set-difference between consecutive `reward.py` files** (not the Strategist's PART 1 prose, which can undercount)
- `prop_modification`, `prop_addition`, `prop_cluster`, `prop_unknown` — proposal counts by inferred type
- `selected_proposal_index` — which proposal the Research Lead chose
- `parse_warnings` — semicolon-separated parsing issues (e.g. `no_proposals_parsed`, `ledger_post_mortem_pending`)

### `runs_summary.csv`

One row per run. Suitable for comparing runs of the same model.

- `iteration_count` — total iterations
- `peak_psr`, `peak_centered` — best across all iters
- `iter_final_psr`, `iter_final_centered` — last iteration
- `regression_count`, `recovery_count` — event counts (from `triage_summary.json`)
- `stability_score` — σ of PSR across iters
- `total_excisions`, `mean_excisions_per_iter` — AST-verified excision totals
- `prop_*_total` — proposals of each type across all iters
- `validator_verdicts` — JSON dict `{status: count}`, e.g. `{"Regressed": 5, "Mixed": 3, "Validated": 2}`
- `iterations_with_warnings` — iters with parsing warnings

### `cross_run_summary.csv`

One row per model configuration (one Strategist model, one campaign signature). **This is the headline table for the paper.**

- `model` — Strategist model name (e.g. `gemma4-26b-mlx`)
- `campaign_signature` — the glob you passed
- `n_runs` — number of runs aggregated
- `peak_psr`, `peak_centered` — `mean ± std` of each run's peak
- `iter_final_psr`, `iter_final_centered` — `mean ± std` of final metrics
- `regression_count`, `recovery_count` — `mean ± std`
- `stability_score` — `mean ± std` of run-level σ's
- `mean_excisions_per_iter` — averaged across runs
- `mean_modifications_per_iter`, `mean_additions_per_iter`, `mean_clusters_per_iter` — mean proposal-type rates per iter

---

## HTML Dashboards

### `pipeline_performance.html` — RL outcomes + LLM cognition

- **Cross-run summary** — mean ± std headline table.
- **Per-metric trajectories** — one chart per metric (PSR, centered, …), one line per run.
- **Terminal mode distribution per iteration** — stacked bars per run, one bar per iteration.
- **Validator verdict per iteration** — colored verdict grid (one row per run).
- **Verdict–Outcome Alignment** — % of iterations where the verdict sign matched the ΔPSR sign.
- **Proposal types per iteration** — mean across runs (modification / addition / cluster / unknown).
- **Excisions per iteration (AST-verified)** — line per run.
- **Objective Alignment ρ** — point-biserial correlation of reward with success.

### `compute_cost.html` — LLM compute

- **Per-phase totals** — calls, wall time, prompt/gen tokens, throughput, % of total time, summed across runs and iterations.
- **Per-run cost summary** — same breakdown per run.
- **Wall time per PSR-pp delivered** — efficiency (lower = more efficient).
- **Final PSR vs total wall time** — efficiency scatter (top-left = best).
- **Total wall time per iteration** — per run + median.
- **Gen tokens / second per phase** — throughput scatter across all calls.
- **Phase avg time per iteration** — per run.
- **Prompt size growth** — mean prompt tokens per phase across iterations (watch for ledger bloat).
- **Response output size growth** — mean gen tokens per phase across iterations.

### `code_evolution.html` — reward-code evolution

- **Component Count per Iteration** — how the reward dict grows/shrinks.
- **Component Churn per Iteration** — excised + added per iteration, per run.
- **Diff Size per Iteration** — lines changed from `changes.patch`, per run.
- **Structural Flag Rates per Iteration (AST)** — double-count / ghost-var rates.
- **Cross-run Summary** — code-evolution headline stats.
- **Cross-run Convergence** — Jaccard similarity of final component sets across runs.
- **Productive Churn Ratio** — churn that survived vs. churn later reverted.
- **Component Survival Curve** — how long components persist once introduced.

---

## Troubleshooting

### "No campaigns matched glob"
The glob didn't match any folders under `experiments/`. Check `ls experiments/`, confirm the pattern is a valid shell glob (case-sensitive), and remember to omit the `_runN` suffix so all runs of a configuration match together.

### Regression / recovery counts are blank
These come from each run's `triage_summary.json`. Run `analyze_run.py` for every campaign **before** aggregating; if the summary is missing, those columns are empty.

### "Missing payload" or "Missing cognition record"
An iteration is included only if it has **both** a metric payload and a cognition record. Check:
`experiments/CAMPAIGN/MODEL/telemetry/metric_payloads/iter07_metric_payload.json` and
`experiments/CAMPAIGN/MODEL/cognition/json_cognition_records/iter07_cognition_record.json`.
Iterations missing either file are skipped.

### Dashboard shows "—" or "NaN"
Usually fine — outcome metrics can be `None` if they weren't computed, and render as "—". If a metric is `None` across *all* iterations, payload generation may have failed silently; check `aggregated_data.json` for the per-iteration values.

### Dashboard charts don't render
Chart.js didn't load from CDN, or the embedded JSON is malformed. Check the browser console (F12), confirm you're online, and validate the audit dump: `python3 -m json.tool aggregated_data.json > /dev/null`.

### Proposal types show as "unknown"
The Strategist's response didn't match the classifier patterns. Check the `parse_warnings` column for which proposal failed, inspect the response in the cognition record, and extend `_infer_proposal_type()` with a new pattern.

### Validator status is "Unparsed"
The post-mortem text didn't carry a recognizable `**Status:**` field. Check the `validation_post_mortem` field in the ledger and adjust the status regex if the Validator used a new format.

---

## Advanced Usage

### Custom regression config

```bash
python3 post_hoc_analysis/aggregate_runs.py \
    --campaign-glob '*spin_crash*remote*' \
    --established_floor 0.50 \
    --regression_k 2.5 \
    --regression_min_floor_pp 12.0 \
    --recovery_window 2
```

Interpretation: a run must reach 50% PSR before drops are eligible; a regression must exceed `max(2.5 × std, 12pp)`; recovery counts only if it lands within 2 iterations.

### Use the library directly

```python
from pathlib import Path
from post_hoc_analysis.extract_cognition import load_run, aggregate_across_runs

run = load_run(Path("experiments/2026-05-13_spin_crash_10cycles_1MSteps_remote_run1"))
print(f"Peak PSR: {run.peak_psr}")

for it in run.iterations:
    print(f"Iter {it.iteration}: PSR={it.outcomes.population_success_rate}, "
          f"ρ={it.outcomes.objective_alignment_rho}, "
          f"validator={it.validator_status}")

runs = [
    load_run(Path("experiments/2026-05-13_spin_crash_10cycles_1MSteps_remote_run1")),
    load_run(Path("experiments/2026-05-13_spin_crash_10cycles_1MSteps_remote_run2")),
    load_run(Path("experiments/2026-05-13_spin_crash_10cycles_1MSteps_remote_run3")),
]
summary = aggregate_across_runs(runs, campaign_signature="spin_crash_10cycles_1MSteps_remote")
print(f"Peak PSR mean ± std: {summary.peak_psr_mean} ± {summary.peak_psr_std}")
```

### Smoke-test the library

```bash
python3 post_hoc_analysis/extract_cognition.py --smoke-test
```

Loads sample iter payloads, cognition records, ledger, and ChatResponse CSV from a fixed sample directory and prints per-iteration extraction results. Useful for verifying the library parses cleanly before running on full data; adjust the sample path in `__main__` if your fixtures live elsewhere.

---

## Architecture Notes

**Structured sources over regex.** Outcome metrics are read from the deterministic payload JSON, verdicts from the structured ledger, and code changes from AST analysis of the reward files. Regex is confined to genuinely unstructured LLM prose — proposal-type classification and RL selection. This isolation is deliberate: an earlier design parsed outcome metrics out of the Validator's post-mortem markdown, and because that prompt embeds two diagnostics (prior baseline + current results), a top-down regex grabbed the wrong one and produced an off-by-one error. Reading from the payload removes that failure mode entirely and keeps the audit trail traceable — any number traces back to a specific source file.

**AST over self-report.** The Strategist's PART 1 prose can claim "no excisions" while a component was in fact dropped from the dict. Component deltas therefore come from AST set-difference between consecutive `reward.py` files, not from prose.

**Data immutability.** Payloads, ledger, and reward files are written by the training loop; the tools never modify them. Outputs are fully regenerable and deterministic — rerunning on the same campaigns yields identical CSVs and dashboards.

**Scaling.** The library loads one iteration at a time, so memory is O(iteration count), not O(dataset size). All computations are simple statistics. HTML files are self-contained and need no server to view or share.

---

## File Manifest

```
post_hoc_analysis/
├── extract_cognition.py          ← Core extraction library (stdlib)
├── analyze_run.py                ← Per-run triage entry point (called by outer_loop.sh)
├── aggregate_runs.py             ← Cross-run CLI wrapper
├── compute_run_score.py          ← Tier 1 RunScore (specified in the companion scoring doc)
├── README_postHocAnalysis.md     ← This file
└── outputs/                      ← Generated by aggregate_runs.py
    └── {label}/
        ├── iterations_long.csv       ← Per-iteration details
        ├── runs_summary.csv          ← Per-run aggregates
        ├── cross_run_summary.csv     ← Paper headline table (mean ± std)
        ├── aggregated_data.json      ← Audit dump
        ├── pipeline_performance.html ← Dashboard 1 (RL + cognition)
        ├── compute_cost.html         ← Dashboard 2 (LLM compute)
        └── code_evolution.html       ← Dashboard 3 (reward-code evolution)
```

Per-run artifacts (`triage_report.html`, `triage_summary.json`, `run_score.json`) are written by `analyze_run.py` under each run's own `reports/` folder, not into `outputs/`.

---

## See Also

- **Evaluation-framework spec** *(companion document, next to this README)* — the rationale and full specification for the curated evaluation framework: Tier 1 RunScore (PPV, PolicyRetention, TR) and Tier 2 Orchestration/Cognition fidelity. This README intentionally defers all scoring and orchestration-fidelity semantics there.
