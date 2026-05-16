# ARD Post-Hoc Evaluation Tooling

A complete extraction and aggregation pipeline for analyzing Autonomous Reward Design (ARD) ablation runs. Converts raw JSON/CSV payloads into paper-ready CSVs and interactive HTML dashboards.

## What This Does

**In 30 seconds:** You have N ≥ 1 training runs under `experiments/`. Each run produced 10+ iterations of:
- A deterministic metric payload (`iter{NN}_metric_payload.json`) — RL outcomes
- An LLM cognition record (`iter{NN}_cognition_record.json`) — proposal types, excisions, selections
- A structured Validator ledger (`experiment_ledger.json`) — status, hypothesis, post-mortem
- LLM call logs (`ChatResponse_data.csv`) — tokens, durations per phase

This tooling **reads all three sources per iteration**, stitches them together without regex, and produces:
- **Three CSV files** — one row per iteration, one per run, one cross-run summary with mean ± std
- **One JSON audit trail** — nested structure for debugging
- **Two interactive HTML dashboards** — no external dependencies, all data embedded, Charts rendered by Chart.js from CDN

**Key design:** All outcome metrics come directly from the payload JSON (no markdown parsing). All Validator verdicts come from the ledger (no regex on the prompt). Cognition records are touched only for proposal-type taxonomy and RL selection — the two things they're uniquely good for.

---

## Files

### Core Scripts

**`extract_cognition.py`** — Library for per-iteration extraction
- `load_metric_payload(path)` → `OutcomeMetrics` — parses payload JSON directly
- `extract_cognition_record(path)` → `CognitionRecord` — parses cognition JSON for LLM behavior only
- `load_ledger(path)` → dict[iteration, LedgerEntry] — parses Validator verdicts from ledger
- `load_run(campaign_path, cfg)` → `RunSummary` — aggregates all iterations in one campaign folder
- `aggregate_across_runs(runs, sig)` → `ModelSummary` — cross-run mean ± std for one model config

Also includes:
- `load_chat_responses(csv_path)` — type-cleans ChatResponse data, converts ns → seconds
- `AggregationConfig` — tunable thresholds for collapse/recovery detection (default: PSR < 10% = collapse, > 50% = recovery)

**`aggregate_runs.py`** — CLI wrapper that orchestrates everything
- Discovers campaigns matching a glob
- Loads all runs, aggregates by Strategist model
- Writes CSVs (long format, runs summary, cross-run)
- Writes JSON audit dump
- Renders two HTML dashboards from a single embedded payload

### Sample Outputs

Six files showing the expected output format:

- **`iterations_long.csv`** — One row per (model, campaign_tag, iteration). ~700 cols including all outcomes, terminal distribution, component flags, cognition summaries. For plotting, filtering, detailed analysis.
- **`runs_summary.csv`** — One row per run. Peak PSR, collapses, recoveries, proposal-type totals, validator-verdict histogram.
- **`cross_run_summary.csv`** — One row per model configuration. Mean ± std across all runs: peak PSR/centered, final PSR/centered, collapse/recovery counts, proposal types, excisions. **This is the headline table for the paper.**
- **`aggregated_data.json`** — Nested structure with full per-iteration details, run summaries, and model aggregates. Audit trail if numbers look wrong.
- **`pipeline_performance.html`** — Interactive dashboard: RL outcomes, terminal distributions, Validator verdicts, proposal types, component flags, optimization metrics. ~60 KB self-contained file.
- **`compute_cost.html`** — Interactive dashboard: per-phase cost breakdown, prompt size growth, gen tokens/sec by phase. ~50 KB self-contained file.

---

## Quick Start

### 1. Prerequisites

- Python 3.9+
- No external dependencies (pure stdlib for the library; the CLI uses only `argparse`, `csv`, `json`)
- A modern web browser (for the HTML dashboards; tested with recent Chrome, Firefox, Safari)

### 2. Setup

Copy the two scripts into your RL agent loop repo:

```bash
mkdir -p ~/Projects/RL-Lab/rl_agent_loop/post_hoc_analysis
cp extract_cognition.py ~/Projects/RL-Lab/rl_agent_loop/post_hoc_analysis/
cp aggregate_runs.py ~/Projects/RL-Lab/rl_agent_loop/post_hoc_analysis/
```

### 3. Run the aggregator

From the repo root:

```bash
cd ~/Projects/RL-Lab/rl_agent_loop

python3 post_hoc_analysis/aggregate_runs.py \
    --experiments-root experiments \
    --campaign-glob '*spin_crash_10cycles_1MSteps*reorderedOldValPrompt*' \
    --label spin_crash_reorderedOldValPrompt
```

**Arguments:**
- `--experiments-root` — Path to your `experiments/` folder (default: `experiments`)
- `--campaign-glob` — Glob (relative to experiments-root) matching campaigns to aggregate. Example: `'*spin_crash*remote*'` matches all campaigns whose tag contains `spin_crash` and `remote`. **Omit the `_runN` suffix; the glob should match all run folders of the same training configuration together.**
- `--label` — Label for output files and dashboard titles (default: sanitized version of the glob)
- `--output-dir` — Output directory (default: `post_hoc_analysis/outputs/{label}/`)
- `--collapse-threshold` — Fraction 0-1, PSR below which = collapse (default: 0.10)
- `--recovery-threshold` — Fraction 0-1, PSR above which = recovery (default: 0.50)
- `--recovery-window` — Max iterations to count recovery after collapse; 0 = unbounded (default: 0)
- `--primary-landing-metric` — Which metric drives collapse/recovery detection: `psr` or `centered` (default: `psr`)

### 4. Outputs

Writes to `post_hoc_analysis/outputs/{label}/`:

```
├── iterations_long.csv          (one row per iter)
├── runs_summary.csv             (one row per run)
├── cross_run_summary.csv        (one row per model, mean±std) ← HEADLINE TABLE
├── aggregated_data.json         (full nested audit)
├── pipeline_performance.html    (RL + cognition dashboard)
└── compute_cost.html            (LLM compute dashboard)
```

### 5. View dashboards

Open the HTML files in your browser:

```bash
open post_hoc_analysis/outputs/spin_crash_reorderedOldValPrompt/pipeline_performance.html
open post_hoc_analysis/outputs/spin_crash_reorderedOldValPrompt/compute_cost.html
```

All data is embedded in the HTML — no server, no internet required. Charts render client-side using Chart.js loaded from CDN (requires internet only on first load).

---

## Understanding the Data Flow

### Per-Iteration Assembly

For each iteration, **three structured sources** are stitched together:

```
iter07_metric_payload.json
├─ multi_seed_optimization_health
│  ├─ population_metrics: {cross_seed_snr, mean_final_reward, ...}
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
│  ├─ {phase: "strategist", response_content: "...[Proposal 1]...[Proposal 2]..."}
│  ├─ {phase: "research_lead", response_content: "...**Selected Proposal:** Proposal 1..."}
│  └─ ...5 other phases...
└─ ...

experiment_ledger.json (one file for the whole run)
├─ experiments: [
│  ├─ {id: 1, hypothesis_payload: "...", validation_post_mortem: "**Status:** Regressed\n..."}
│  ├─ {id: 7, hypothesis_payload: "...", validation_post_mortem: "**Status:** Regressed\n..."}
│  └─ ...
└─ ...

ChatResponse_data.csv (one file for the whole run, 60 rows for a 10-iter run × 6 phases)
├─ iteration,phase,model_name,prompt_eval_count,eval_count,total_duration_ns,...
├─ 1,strategist,gemma3:27b,3335,1237,93000000000,...
└─ ...
```

**Extraction logic:**
1. Load **payload** → `OutcomeMetrics` with PSR, ρ, SNR, terminal distribution, component flags, etc.
2. Load **cognition record** → `CognitionRecord` with proposal types (modification/addition/cluster), excision count, selected proposal
3. Load **ledger** → look up iteration 7 → extract status from `**Status:**` field in post-mortem
4. Load **chat rows** for this iteration → timestamp them for plotting

**Why three sources?**
- The payload is deterministic, machine-readable, and already exists on disk. It IS the ground truth for outcomes.
- The cognition record is text (LLM responses), so regex is necessary for proposal types and RL selection — but we skip the outcome metrics parsing that the old code did, which caused an off-by-one bug (the Validator prompt embeds two diagnostics: prior iter's baseline + current results; regex from the top grabbed the wrong one).
- The ledger has structured verdicts, not markdown parsing.

### Per-Run Aggregation

All iterations for one run are combined:

```
IterationRecord[iter1, iter2, ..., iter10]
    ↓
aggregate_run(cfg: AggregationConfig)
    ├─ Peak PSR / peak centered (max across iters)
    ├─ Final PSR / final centered (last iter)
    ├─ Collapse count (how many iters had PSR < threshold?)
    ├─ Recovery count (after a collapse, did PSR bounce back above recovery_threshold?)
    ├─ Stability score (σ of PSR across iters)
    ├─ Proposal type distributions (total modifications, additions, clusters, unknowns)
    ├─ Validator verdict histogram ({Validated: 2, Regressed: 5, ...})
    └─ Proposal type mean per iter (for averaging across runs)
    ↓
RunSummary
```

### Cross-Run Aggregation

All runs of the same model configuration:

```
RunSummary[run1, run2, run3]
    ↓
aggregate_across_runs()
    ├─ peak_psr_mean / peak_psr_std (mean ± std of each run's peak)
    ├─ collapse_count_mean / collapse_count_std
    ├─ recovery_count_mean / recovery_count_std
    ├─ stability_score_mean / stability_score_std (σ of run-level σ's)
    ├─ proposal_type_mean_per_iter (mean modifications per iter, averaged across runs)
    └─ All run summaries (for detailed drill-down)
    ↓
ModelSummary ← This is one row in cross_run_summary.csv
```

---

## CSV Column Reference

### `iterations_long.csv`

One row per (model, campaign, iteration). Suitable for plotting, filtering, statistical tests.

**Outcome Metrics (all fractions 0–1 unless noted):**
- `psr` — Population success rate (= `population_mean_success_rate` from payload)
- `centered_rate` — `landed_centered` from terminal distribution
- `objective_alignment_rho`, `survival_hacking_rho` — ρ values from topology analysis
- `cross_seed_snr` — Signal-to-noise ratio (can be very large)
- `critic_saturation_index`, `trajectory_isomorphism_rho`, `intra_rollout_cv`, `terminal_entropy_norm` — Optimization/fragility metrics
- `mean_descent_efficiency`, `actuator_chatter_rate`, `macro_oscillations` — Kinematic metrics
- Terminal distribution: `term_landed_centered`, `term_landed_off_centered`, `term_landed_but_slid_into_valley`, `term_crashed`, `term_out_of_bounds`, `term_hover_timeout`
- Component rollups: `n_components`, `n_optimal`, `n_traitor`, `n_dead_weight`, `n_hidden_dependency`
- Flags: `is_lottery_ticket`, `survival_hacking_detected`, `is_initialization_sensitive`, `is_universally_converged`

**Cognition (LLM behavior):**
- `validator_status` — Extracted from ledger (e.g., `Validated`, `Regressed`, `Goodhart Trap`)
- `excision_count` — # of components the Strategist excised in PART 1
- `prop_modification`, `prop_addition`, `prop_cluster`, `prop_unknown` — # of proposals of each type
- `selected_proposal_index` — Which proposal the Research Lead chose
- `parse_warnings` — Semicolon-separated list of parsing issues (e.g., `no_proposals_parsed`, `ledger_post_mortem_pending`)

### `runs_summary.csv`

One row per run. Suitable for comparing runs of the same model.

**Per-run aggregates:**
- `iteration_count` — Total iterations in this run
- `peak_psr`, `peak_centered` — Best PSR/centered across all iters
- `iter_final_psr`, `iter_final_centered` — PSR/centered in the last iteration
- `collapse_count`, `recovery_count` — # of collapse/recovery events (using thresholds from cfg)
- `stability_score` — σ of PSR across iters (how volatile was the run?)
- `total_excisions`, `mean_excisions_per_iter` — Total excisions and mean per iter
- `prop_*_total` — Total proposals of each type across all iters
- `validator_verdicts` — JSON dict of {status: count}, e.g., `{"Regressed": 5, "Mixed": 3, "Validated": 2}`
- `iterations_with_warnings` — # of iters with parsing warnings

### `cross_run_summary.csv`

One row per model configuration (one Strategist model, one campaign signature). **This is the headline table for your paper.**

**Cross-run statistics (mean ± std across N runs):**
- `model` — Strategist model name (e.g., `gemma3:27b`)
- `campaign_signature` — The glob you passed (useful for filters, e.g., `*spin_crash*`)
- `n_runs` — Number of runs aggregated
- `peak_psr`, `peak_centered` — `mean ± std` of each run's peak
- `iter_final_psr`, `iter_final_centered` — `mean ± std` of final PSR/centered
- `collapse_count`, `recovery_count` — `mean ± std` counts
- `stability_score` — `mean ± std` of run-level σ's (σ of σ's)
- `mean_excisions_per_iter` — Average across runs (single number, no std)
- `mean_modifications_per_iter`, `mean_additions_per_iter`, `mean_clusters_per_iter` — Average proposal type rates per iter

---

## HTML Dashboards

### `pipeline_performance.html`

**RL outcomes + LLM cognition in one view.**

**Sections:**

1. **Cross-run Summary Table** — Mean ± std for peak PSR, peak centered, final metrics, collapse/recovery counts, stability. One-glance view of model performance.

2. **Outcome Trajectories** — Two side-by-side charts:
   - **Population Success Rate** — One line per run, overlaid with cross-run mean band
   - **Centered Landing Rate** — Same layout
   - X-axis: iteration; Y-axis: fraction 0–1

3. **Terminal Mode Distribution** — Small-multiple stacked bar charts (one per run):
   - Each bar = one iteration
   - Stacks: landed_centered (green), landed_off_centered (blue), landed_slid (cyan), crashed (red), out_of_bounds (purple), hover_timeout (orange)
   - Useful for seeing if the policy is shifting failure modes

4. **Validator Verdict Timeline** — Grid of colored pills:
   - Rows: one per run
   - Cols: one per iteration
   - Colors: Validated/Confirmed (green), Mixed/Pyrrhic/Productive (yellow), Inconclusive (gray), Refuted/Regressed/Goodhart (red)

5. **Proposal Types** — Stacked bar chart of mean proposals per iteration across all runs:
   - Modification (blue), Addition (green), Cluster (purple), Unknown (gray)

6. **Excisions Per Iteration** — Line chart, one line per run:
   - Y-axis: # of components excised
   - Useful for tracking if the Strategist is getting more aggressive

7. **Component Flags** — Stacked bar chart:
   - One bar per iteration (mean across runs)
   - Stacks: 🟢 Optimal, 🟡 Dead weight, 🟣 Hidden dependency, 🔴 Traitor
   - Useful for tracking if the reward function is getting cleaner or more problematic

8. **Optimization Metrics** — Three charts side-by-side:
   - **Objective Alignment ρ** — Should increase toward 1.0
   - **SNR** — Log scale, shows signal-to-noise in cross-seed reward
   - **Intra-rollout CV** — Coefficient of variation of actions (policy stability)

9. **Per-Iteration Detail (Collapsible)** — Table for each run with every iteration's data:
   - PSR, centered rate, ρ, SNR, validator status, excisions, proposal breakdown, selected proposal, warnings
   - Useful for debugging when a number looks odd

### `compute_cost.html`

**LLM cost analysis.**

**Sections:**

1. **Per-Phase Cost Summary Table** — Rows are phases (validator, strategist, organizer, research_lead, dispatcher, coder):
   - Calls — # of LLM calls in this phase
   - Total time — Wall-clock seconds summed across all calls
   - Prompt tok, Gen tok — Token counts
   - Gen tok/s — Throughput (= gen tok / eval time in seconds)
   - % of total time — Fraction of overall campaign runtime

2. **Per-Iteration Phase-Stacked Time** — Stacked bar chart:
   - X-axis: iteration (1–10)
   - Y-axis: total seconds
   - Stacks: time spent in each phase (colored)
   - Shows if any phase is becoming a bottleneck as the run progresses

3. **Prompt Size Growth** — Line chart, one line per phase:
   - X-axis: iteration
   - Y-axis: mean prompt tokens (averaged across runs)
   - Useful for detecting if the Strategist's ledger (examples of past proposals) is bloating

4. **Gen Tokens / Second (Scatter)** — Scatter plot by phase:
   - X-axis: phase (with jitter)
   - Y-axis: gen tokens per second for each call
   - Shows throughput distribution — e.g., is the Research Lead faster than the Strategist?

---

## Troubleshooting

### "No campaigns matched glob"

**Error:** `No campaigns matched glob '*spin_crash*' under experiments/`

**Cause:** The glob didn't match any folders under `experiments/`. 

**Fix:** 
1. Check your campaign folder names: `ls experiments/`
2. Verify the glob pattern is a valid shell glob (remember: globbing is case-sensitive)
3. Example: if your campaigns are named `2026-05-13_spin_crash_10cycles_1MSteps_remote_reorderedOldValPrompt_run1`, the glob `'*spin_crash*'` should work. But `'*SpinCrash*'` won't.

### "Missing payload" or "Missing cognition record"

**Error:** `FileNotFoundError: Missing payload: ...iter07_metric_payload.json`

**Cause:** The discovered iteration doesn't have both a payload and a cognition record.

**Fix:**
1. Check that both files exist: `ls experiments/CAMPAIGN/MODEL/telemetry/metric_payloads/iter07_metric_payload.json` and `...cognition/json_cognition_records/iter07_cognition_record.json`
2. The aggregator requires BOTH for each iteration. If one iteration is missing either file, that iteration is skipped.
3. Run with `--discover-iterations` (future feature) to see which iterations were found.

### Dashboard shows "—" or "NaN" for many values

**Cause:** Missing or None values in the payload.

**Fix:**
1. This is usually OK — outcomes metrics can be None if they weren't computed. The CSV will have empty cells; the dashboard renders them as "—".
2. If a metric is consistently None across all iterations, the payload generation may have failed silently.
3. Check `aggregated_data.json` for the full per-iteration values — that's the audit trail.

### Dashboard charts don't render

**Cause:** Chart.js didn't load from CDN, or the data JSON is malformed.

**Fix:**
1. Check browser console (F12 → Console tab) for errors
2. Verify you're online (Chart.js loads from CDN)
3. Try opening one of the sample dashboards — if those render, your browser is OK and the issue is with your generated HTML
4. Check that `aggregated_data.json` is valid JSON: `python3 -m json.tool aggregated_data.json > /dev/null`

### Proposal types show as "unknown"

**Cause:** The Strategist's response format doesn't match the regex patterns.

**Fix:**
1. Check `iterations_long.csv` for the `parse_warnings` column — entries like `proposal_2_type_unknown` indicate which proposals couldn't be classified
2. Look at the actual Strategist response in the cognition record JSON
3. Report the proposal text and I'll add a new pattern to `_infer_proposal_type()`

### Validator status is "Unparsed"

**Cause:** The post-mortem text doesn't start with `**Status:**` in the expected format.

**Fix:**
1. Check the ledger JSON directly: `experiments/CAMPAIGN/MODEL/cognition/experiment_ledger.json`
2. Look at the `validation_post_mortem` field for that iteration
3. The regex looks for `**Status:**` followed by a word in backticks or bare. If the Validator uses a different format, report it and I'll update the regex.

---

## Advanced Usage

### Custom Aggregation Config

Change collapse/recovery thresholds:

```bash
python3 post_hoc_analysis/aggregate_runs.py \
    --campaign-glob '*spin_crash*' \
    --collapse-threshold 0.05 \
    --recovery-threshold 0.60 \
    --recovery-window 2
```

**Interpretation:**
- `collapse_threshold=0.05` — PSR < 5% counts as a collapse
- `recovery_threshold=0.60` — PSR ≥ 60% counts as recovery
- `recovery_window=2` — Only count recovery if it happens within 2 iterations of the collapse (0 = unbounded)

### Use the library directly (Python)

```python
from pathlib import Path
from post_hoc_analysis.extract_cognition import load_run, aggregate_across_runs

# Load one campaign folder
run = load_run(Path("experiments/2026-05-13_spin_crash_10cycles_1MSteps_remote_run1"))
print(f"Peak PSR: {run.peak_psr}")
print(f"Iterations with warnings: {run.iterations_with_warnings}")

# Iterate over every iteration
for it in run.iterations:
    print(f"Iter {it.iteration}: PSR={it.outcomes.population_success_rate}, "
          f"ρ={it.outcomes.objective_alignment_rho}, "
          f"validator={it.validator_status}")

# Load and aggregate multiple runs
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

Loads sample data from `/mnt/user-data/uploads/` (iter 1-10 payloads, cognition records, ledger, ChatResponse CSV) and prints per-iteration extraction results. Useful for verifying the library works before running on your full data.

---

## Architecture Notes

### Why This Design?

**Problem with the old code:**
- Parsed outcome metrics from the Validator's post-mortem markdown via regex
- The prompt embeds TWO diagnostics: prior iteration's baseline (Section 1) + current iteration's results (Section 2)
- A first-match regex would grab Section 1 → off-by-one bug (iter 7 got iter 6's PSR)

**Solution:**
- Load metrics directly from the payload JSON (they're already computed, deterministic, structured)
- Use the cognition record only for unstructured LLM behavior (proposal types, RL selection)
- Use the ledger for Validator verdicts (structured `**Status:**` field, not markdown parsing)

**Result:**
- No more off-by-one bugs
- Audit trail is clear: trace any number back to its source JSON file
- Regex is isolated to exactly where it's needed (proposal-type classification, RL selection)

### Data Immutability

- The payloads and ledger are written by the training loop; the tools never modify them
- Outputs (CSVs, JSON, HTML) can be regenerated from the same input at any time
- If you rerun `aggregate_runs.py` on the same campaigns, outputs are identical (deterministic)

### Scaling

- The library loads one iteration at a time; memory usage is O(iteration count), not O(dataset size)
- All computations are simple statistics (mean, std, count) — no matrix operations
- For 100 runs × 10 iters: ~20 seconds to load + aggregate, ~5 seconds to render dashboards
- HTML files are self-contained; no server needed to view or share

---

## File Manifest

```
post_hoc_analysis/
├── extract_cognition.py              ← Core library (no dependencies)
├── aggregate_runs.py                 ← CLI wrapper
├── README.md                         ← This file
└── outputs/                          ← Generated by aggregate_runs.py
    └── {label}/
        ├── iterations_long.csv       ← Per-iteration details
        ├── runs_summary.csv          ← Per-run aggregates
        ├── cross_run_summary.csv     ← Paper headline table (mean ± std)
        ├── aggregated_data.json      ← Audit dump
        ├── pipeline_performance.html ← Dashboard 1
        └── compute_cost.html         ← Dashboard 2
```

---

## Citation

If you use these tools in a paper, cite the session where they were developed. The design is optimized for the ARD pipeline but generalizes to any LLM-in-the-loop training framework with structured payloads.

---

## Questions / Feedback

- **Dashboards look crowded?** → Split into three by editing `write_dashboards()` in `aggregate_runs.py` (trivial change, just separate the sections into different HTML files)
- **Need different metrics plotted?** → Metrics exist in `iterations_long.csv`; open with Pandas/R for custom analysis. Or ask and I can add them to the dashboard.
- **Proposal type regex doesn't match your format?** → Report the text and I'll add a pattern to `_infer_proposal_type()`
- **Want time-series training dynamics (entropy, KL divergence)?** → Create a separate `dashboard_training_dynamics.py` that reads `progress_*.csv` files. Current design focuses on outcomes + LLM cost.

Enjoy! 📊
