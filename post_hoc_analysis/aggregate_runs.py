""" Aggregator CLI for ARD ablation runs.
Inputs:
  --experiments-root   Path to experiments/ directory
  --campaign-glob      Glob (relative to experiments-root) that matches the N
                       campaign folders to aggregate together.
                       Typical: tag without the _runN suffix, plus a *.
                       Example: '2026-05-13_spin_crash_10cycles_*reorderedOldValPrompt*'
  --label              Label for output files & dashboards
                       (defaults to a sanitized version of the glob)
  --output-dir         Output dir (default: post_hoc_analysis/reports/single_campaign/{label})

Outputs (under output-dir):
  iterations_long.csv         one row per (run, iter)
  runs_summary.csv            one row per run
  cross_run_summary.csv       one row per model configuration, mean±std
  aggregated_data.json        full nested audit dump
  pipeline_performance.html   dashboard 1 (RL + LLM cognition)
  compute_cost.html           dashboard 2 (LLM compute)
  code_evolution.html         dashboard 3 (Evolution of Code)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # project root for src imports
from extract_cognition import (  # noqa: E402
    AggregationConfig,
    LEDGER_STATUS_VOCAB,
    ModelSummary,
    PROP_TYPES,
    RunSummary,
    aggregate_across_runs,
    load_chat_responses,
    load_run,
)

# All terminal modes the diagnostic produces.  Stable column order for CSVs.
ALL_TERMINAL_MODES = (
    "landed_centered",
    "landed_off_centered",
    "landed_but_slid_into_valley",
    "landed_off_centered_timeout",   
    "crashed",
    "out_of_bounds",
    "hover_timeout",
)

# ===========================================================================
# Campaign discovery
# ===========================================================================

def discover_campaigns(experiments_root: Path, campaign_glob: str) -> list[Path]:
    """Return campaign folders matching the glob, sorted alphabetically.
    Each match must be a directory containing exactly one model_dir; others
    are skipped with a warning.
    """
    out = []
    for c in sorted(experiments_root.glob(campaign_glob)):
        if not c.is_dir():
            continue
        subdirs = [p for p in c.iterdir() if p.is_dir()]
        if len(subdirs) != 1:
            print(f"  skipping {c.name}: contains {len(subdirs)} model dirs",
                  file=sys.stderr)
            continue
        out.append(c)
    return out


def _load_regression_stats(campaign_path: Path) -> dict:
    """
    Read regression/recovery counts from triage_summary.json (written by analyze_run.py).
    Returns zeros with no error if the file doesn't exist — aggregate_runs may be run
    before analyze_run on a given campaign.
    """
    _zero = {"sharp_regression_count": 0, "recovery_count": 0, "unrecovered_count": 0}
    try:
        from extract_cognition import RunPaths
        paths = RunPaths(campaign_path)
        summary_path = paths.model_dir / "reports" / "triage_summary.json"
        if not summary_path.is_file():
            return _zero
        with summary_path.open() as f:
            s = json.load(f)
        return {
            "sharp_regression_count": s.get("sharp_regression_count", 0),
            "recovery_count":         s.get("recovery_count", 0),
            "unrecovered_count":      s.get("unrecovered_count", 0),
        }
    except Exception:
        return _zero

# ===========================================================================
# CSV writers
# ===========================================================================

def write_iterations_csv(model_summaries, path: Path):
    """Long-format CSV: one row per (model, run, iter)."""
    fieldnames = [
        "model", "campaign_tag", "iteration",
        # outcomes — fractions 0-1 from the payload (not percent)
        "psr", "centered_rate",
        "objective_alignment_rho", "survival_hacking_rho",
        "cross_seed_cv", "critic_saturation_index",
        "trajectory_isomorphism_rho", "intra_rollout_cv",
        "terminal_entropy_norm", "mean_descent_efficiency",
        "actuator_chatter_rate", "macro_oscillations",
        # flags
        "is_lottery_ticket", "survival_hacking_detected",
        "is_initialization_sensitive", "is_universally_converged",
        "within_seed_terminal_cv", "is_terminal_unstable",
        # terminal distribution
        *[f"term_{m}" for m in ALL_TERMINAL_MODES],
        # component rollups
        "n_components", "n_optimal", "n_traitor",
        "n_dead_weight", "n_hidden_dependency", "n_neutral_noisy",
        "n_hidden_traitor", "n_hidden_helper", "n_high_magnitude_neutral",
        "optimal_noise_ratio", "optimal_delta",
        # cognition
        "validator_status", "excision_count",
        "prop_modification", "prop_addition", "prop_cluster", "prop_unknown",
        "selected_proposal_index", "parse_warnings",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for ms in model_summaries:
            for run in ms.run_summaries:
                prev_n_optimal = None
                for it in run.iterations:
                    o = it.outcomes
                    c = it.cognition
                    row = {
                        "model": ms.strategist_model,
                        "campaign_tag": run.campaign_tag,
                        "iteration": it.iteration,
                        "psr": o.population_success_rate,
                        "centered_rate": o.landed_centered_rate,
                        "objective_alignment_rho": o.objective_alignment_rho,
                        "survival_hacking_rho": o.survival_hacking_rho,
                        "cross_seed_cv": o.cross_seed_cv,
                        "critic_saturation_index": o.critic_saturation_index,
                        "trajectory_isomorphism_rho": o.trajectory_isomorphism_rho,
                        "intra_rollout_cv": o.intra_rollout_cv,
                        "terminal_entropy_norm": o.terminal_entropy_norm,
                        "mean_descent_efficiency": o.mean_descent_efficiency,
                        "actuator_chatter_rate": o.actuator_chatter_rate,
                        "macro_oscillations": o.macro_oscillations,
                        "is_lottery_ticket": o.is_lottery_ticket,
                        "survival_hacking_detected": o.survival_hacking_detected,
                        "is_initialization_sensitive": o.is_initialization_sensitive,
                        "is_universally_converged": o.is_universally_converged,
                        "within_seed_terminal_cv": o.within_seed_terminal_cv,
                        "is_terminal_unstable": o.is_terminal_unstable,
                        "n_components": o.n_components,
                        "n_optimal": o.n_optimal,
                        "n_traitor": o.n_traitor,
                        "n_dead_weight": o.n_dead_weight,
                        "n_hidden_dependency": o.n_hidden_dependency,
                        "n_neutral_noisy": o.n_neutral_noisy,
                        "n_hidden_traitor": o.n_hidden_traitor,
                        "n_hidden_helper": o.n_hidden_helper,
                        "n_high_magnitude_neutral": o.n_high_magnitude_neutral,
                        "optimal_noise_ratio": round(o.n_optimal / (o.n_neutral_noisy + 1), 3),
                        "validator_status": it.validator_status,
                        "excision_count": c.excision_count,
                        "prop_modification": c.proposal_type_counts.get("modification", 0),
                        "prop_addition": c.proposal_type_counts.get("addition", 0),
                        "prop_cluster": c.proposal_type_counts.get("cluster", 0),
                        "prop_unknown": c.proposal_type_counts.get("unknown", 0),
                        "selected_proposal_index": c.selected_proposal_index,
                        "parse_warnings": ";".join(it.parse_warnings),
                    }
                    row["optimal_delta"] = (
                        (o.n_optimal - prev_n_optimal) if prev_n_optimal is not None else None
                    )
                    prev_n_optimal = o.n_optimal
                    for m in ALL_TERMINAL_MODES:
                        row[f"term_{m}"] = o.terminal_distribution.get(m)
                    w.writerow(row)


def write_runs_csv(model_summaries, path: Path, regression_by_tag: dict):
    fieldnames = [
        "model", "campaign_tag", "iteration_count",
        "peak_psr", "peak_centered",
        "iter_final_psr", "iter_final_centered",
        "regression_count", "recovery_count", "stability_score",
        "total_excisions", "mean_excisions_per_iter",
        "prop_modification_total", "prop_addition_total",
        "prop_cluster_total", "prop_unknown_total",
        "validator_verdicts", "iterations_with_warnings",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for ms in model_summaries:
            for run in ms.run_summaries:
                w.writerow({
                    "model": ms.strategist_model,
                    "campaign_tag": run.campaign_tag,
                    "iteration_count": run.iteration_count,
                    "peak_psr": run.peak_psr,
                    "peak_centered": run.peak_centered,
                    "iter_final_psr": run.iter_final_psr,
                    "iter_final_centered": run.iter_final_centered,
                    "regression_count": regression_by_tag.get(run.campaign_tag, {}).get("sharp_regression_count", 0),
                    "recovery_count":   regression_by_tag.get(run.campaign_tag, {}).get("recovery_count", 0),
                    "stability_score": run.stability_score,
                    "total_excisions": run.total_excisions,
                    "mean_excisions_per_iter": round(run.mean_excisions_per_iter, 3),
                    "prop_modification_total": run.total_proposals_by_type.get("modification", 0),
                    "prop_addition_total": run.total_proposals_by_type.get("addition", 0),
                    "prop_cluster_total": run.total_proposals_by_type.get("cluster", 0),
                    "prop_unknown_total": run.total_proposals_by_type.get("unknown", 0),
                    "validator_verdicts": json.dumps(run.validator_verdicts),
                    "iterations_with_warnings": run.iterations_with_warnings,
                })


def write_cross_run_summary_csv(model_summaries, path: Path, regression_by_tag: dict):
    """The headline table: mean ± std across N runs, per model configuration."""
    def fmt(mean, std, digits=3):
        if mean is None: return ""
        if std is None: return f"{mean:.{digits}f}"
        return f"{mean:.{digits}f} ± {std:.{digits}f}"

    fieldnames = [
        "model", "campaign_signature", "n_runs",
        "peak_psr", "peak_centered",
        "iter_final_psr", "iter_final_centered",
        "regression_count", "recovery_count", "stability_score",
        "mean_excisions_per_iter",
        "mean_modifications_per_iter",
        "mean_additions_per_iter",
        "mean_clusters_per_iter",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for ms in model_summaries:
            # Compute mean±std from sidecar because RunSummary.collapse_count is always 0
            _reg  = [regression_by_tag.get(r.campaign_tag, {}).get("sharp_regression_count", 0)
                     for r in ms.run_summaries]
            _rec  = [regression_by_tag.get(r.campaign_tag, {}).get("recovery_count", 0)
                     for r in ms.run_summaries]
            _reg_mean  = sum(_reg) / len(_reg) if _reg else 0.0
            _rec_mean  = sum(_rec) / len(_rec) if _rec else 0.0
            _reg_std   = (sum((v - _reg_mean)**2 for v in _reg) / len(_reg))**0.5 if len(_reg) > 1 else None
            _rec_std   = (sum((v - _rec_mean)**2 for v in _rec) / len(_rec))**0.5 if len(_rec) > 1 else None
            w.writerow({
                "model": ms.strategist_model,
                "campaign_signature": ms.campaign_signature,
                "n_runs": ms.n_runs,
                "peak_psr": fmt(ms.peak_psr_mean, ms.peak_psr_std),
                "peak_centered": fmt(ms.peak_centered_mean, ms.peak_centered_std),
                "iter_final_psr": fmt(ms.iter_final_psr_mean, ms.iter_final_psr_std),
                "iter_final_centered": fmt(ms.iter_final_centered_mean, ms.iter_final_centered_std),
                "regression_count": fmt(_reg_mean, _reg_std, 1),
                "recovery_count":   fmt(_rec_mean, _rec_std, 1),
                "stability_score": fmt(ms.stability_score_mean, ms.stability_score_std),
                "mean_excisions_per_iter": f"{ms.mean_excisions_per_iter_across_runs:.2f}",
                "mean_modifications_per_iter": f"{ms.proposal_type_mean_per_iter.get('modification', 0) or 0:.2f}",
                "mean_additions_per_iter": f"{ms.proposal_type_mean_per_iter.get('addition', 0) or 0:.2f}",
                "mean_clusters_per_iter": f"{ms.proposal_type_mean_per_iter.get('cluster', 0) or 0:.2f}",
            })

# ===========================================================================
# JSON audit
# ===========================================================================

def _to_dict(obj):
    try:
        return asdict(obj)
    except TypeError:
        return obj


def write_audit_json(model_summaries, path: Path):
    payload = {
        "schema_version": 2,
        "models": [_to_dict(ms) for ms in model_summaries],
    }
    with path.open("w") as f:
        json.dump(payload, f, indent=2, default=str)

# ===========================================================================
# Dashboard payload: shape data for plotting in the browser
# ===========================================================================

def build_dashboard_payload(model_summaries, chat_rows_by_run, regression_by_tag: dict) -> dict:
    """
    Build a single JSON object that both dashboards consume.
    Shape:
    {
      "models": [
        {
          "name": "gemma3:27b",
          "signature": "...",
          "runs": [
            {
              "tag": "...run1",
              "iterations": [
                {"iter": 1, "psr": 0.13, "centered": 0.07, ...},
                ...
              ],
              "verdicts": {"Regressed": 4, ...},
              ...
            },
            ...
          ],
          "summary": {peak_psr_mean, peak_psr_std, ...},
          "chat_rows": [
            {iteration, phase, model, total_s, prompt_eval_count, eval_count, ...},
            ...
          ]
        }
      ]
    }
    """
    out_models = []
    for ms in model_summaries:
        out_runs = []
        for run in ms.run_summaries:
            iters = []
            for it in run.iterations:
                o = it.outcomes
                c = it.cognition
                cc = it.code_change
                # ── Code-change sub-dict ──
                code_entry = None
                if cc is not None:
                    code_entry = {
                        "lines_added":        cc.lines_added,
                        "lines_removed":      cc.lines_removed,
                        "n_hunks":            cc.n_hunks,
                        "patch_available":    cc.patch_available,
                        "excised":            cc.excised_components,
                        "added":              cc.added_components,
                        "n_excised":          cc.n_excised,
                        "n_added":            cc.n_added,
                        "component_names":    cc.component_names,
                        "n_components":       cc.n_components,
                        "n_double_count":     len(cc.double_count_flags),
                        "double_count_flags": cc.double_count_flags,
                        "n_ghost":            len(cc.ghost_vars),
                        "ghost_vars":         cc.ghost_vars,
                        "ast_available":      cc.ast_available,
                        "code_warnings":      cc.warnings
                        }
                iters.append({
                    "iter": it.iteration,
                    "psr": o.population_success_rate,
                    "centered": o.landed_centered_rate,
                    "off_centered": o.landed_off_centered_rate,
                    "slid": o.landed_slid_rate,
                    "off_centered_timeout": o.terminal_distribution.get("landed_off_centered_timeout"),
                    "crashed": o.crashed_rate,
                    "oob": o.out_of_bounds_rate,
                    "hover_timeout": o.hover_timeout_rate,
                    "rho": o.objective_alignment_rho,
                    "cross_seed_cv": o.cross_seed_cv,
                    "within_seed_terminal_cv": o.within_seed_terminal_cv,
                    "is_terminal_unstable": o.is_terminal_unstable,
                    "csi": o.critic_saturation_index,
                    "isomorphism": o.trajectory_isomorphism_rho,
                    "intra_cv": o.intra_rollout_cv,
                    "term_entropy": o.terminal_entropy_norm,
                    "chatter": o.actuator_chatter_rate,
                    "macro_osc": o.macro_oscillations,
                    "survival_hacking": o.survival_hacking_detected,
                    "lottery_ticket": o.is_lottery_ticket,
                    "n_components": o.n_components,
                    "n_optimal": o.n_optimal,
                    "n_traitor": o.n_traitor,
                    "n_dead_weight": o.n_dead_weight,
                    "n_hidden_dependency": o.n_hidden_dependency,
                    "n_neutral_noisy": o.n_neutral_noisy,
                    "validator_status": it.validator_status,
                    "excision_count": c.excision_count,
                    "prop_modification": c.proposal_type_counts.get("modification", 0),
                    "prop_addition": c.proposal_type_counts.get("addition", 0),
                    "prop_cluster": c.proposal_type_counts.get("cluster", 0),
                    "prop_unknown": c.proposal_type_counts.get("unknown", 0),
                    "selected_proposal_index": c.selected_proposal_index,
                    "warnings": it.parse_warnings,
                    "code": code_entry, 
                })

            # Attempt to load pre-computed RunScore
            run_score_data = None
            if run.model_dir_path is not None:
                rs_path = run.model_dir_path / "reports" / "run_score.json"
                ts_path = run.model_dir_path / "reports" / "triage_summary.json"
                if ts_path.exists() and ts_path.is_file():
                    try:
                        import json as _json
                        with ts_path.open() as _f:
                            _ts = _json.load(_f)
                        run_score_data = {
                            "score": _ts.get("run_score"),
                            "ppv": _ts["sub_scores"].get("ppv"),
                            "policy_retention": _ts["sub_scores"].get("policy_retention"),
                            "tr": _ts["sub_scores"].get("tr"),
                        }
                    except Exception:
                        run_score_data = None

                elif rs_path.exists() and rs_path.is_file():
                    try:
                        import json as _json
                        with rs_path.open() as _f:
                            _rs = _json.load(_f)
                        run_score_data = {
                            "score": _rs.get("run_score"),
                            "ppv": _rs["components"].get("ppv"),
                            "policy_retention": _rs["components"].get("policy_retention"),
                            "tr": _rs["components"].get("tr"),
                        }
                    except Exception:
                        run_score_data = None

            chat_rows = chat_rows_by_run.get(run.campaign_tag, [])
            # Slim the chat rows for dashboard payload — full csv is on disk.
            # MOD: include response_content for gen token output breakdown
            slim_chat = [{
                "iteration": r["iteration"],
                "phase": r["phase"],
                "model": r["model_name"],
                "total_s": r.get("total_duration_s"),
                "load_s": r.get("load_duration_s"),
                "prompt_eval_s": r.get("prompt_eval_duration_s"),
                "eval_s": r.get("eval_duration_s"),
                "prompt_tokens": r.get("prompt_eval_count"),
                "gen_tokens": r.get("eval_count"),
                # For thinking/response breakdown: include response_content
                "response_content": r.get("response_content") or "",
                "thinking_trace": r.get("thinking_trace") or ""
            } for r in chat_rows]

            out_runs.append({
                "tag": run.campaign_tag,
                "iterations": iters,
                "iteration_count": run.iteration_count,
                "peak_psr": run.peak_psr,
                "peak_centered": run.peak_centered,
                "iter_final_psr": run.iter_final_psr,
                "iter_final_centered": run.iter_final_centered,
                "collapse_count": regression_by_tag.get(run.campaign_tag, {}).get("sharp_regression_count", 0),
                "regression_count": regression_by_tag.get(run.campaign_tag, {}).get("sharp_regression_count", 0),
                "recovery_count":   regression_by_tag.get(run.campaign_tag, {}).get("recovery_count", 0),
                "stability_score": run.stability_score,
                "verdicts": run.validator_verdicts,
                "warnings": run.iterations_with_warnings,
                "chat_rows": slim_chat,
                "run_score": run_score_data,
            })

        _reg_s = [regression_by_tag.get(r.campaign_tag, {}).get("sharp_regression_count", 0)
                  for r in ms.run_summaries]
        _rec_s = [regression_by_tag.get(r.campaign_tag, {}).get("recovery_count", 0)
                  for r in ms.run_summaries]
        _reg_s_mean = sum(_reg_s) / len(_reg_s) if _reg_s else 0.0
        _rec_s_mean = sum(_rec_s) / len(_rec_s) if _rec_s else 0.0
        _reg_s_std  = (sum((v - _reg_s_mean)**2 for v in _reg_s) / len(_reg_s))**0.5 if len(_reg_s) > 1 else None
        _rec_s_std  = (sum((v - _rec_s_mean)**2 for v in _rec_s) / len(_rec_s))**0.5 if len(_rec_s) > 1 else None
        out_models.append({
            "name": ms.strategist_model,
            "signature": ms.campaign_signature,
            "n_runs": ms.n_runs,
            "summary": {
                "peak_psr_mean": ms.peak_psr_mean,
                "peak_psr_std": ms.peak_psr_std,
                "peak_centered_mean": ms.peak_centered_mean,
                "peak_centered_std": ms.peak_centered_std,
                "iter_final_psr_mean": ms.iter_final_psr_mean,
                "iter_final_psr_std": ms.iter_final_psr_std,
                "regression_count_mean": _reg_s_mean,
                "regression_count_std":  _reg_s_std,
                "recovery_count_mean":   _rec_s_mean,
                "recovery_count_std":    _rec_s_std,
                "stability_score_mean": ms.stability_score_mean,
                "stability_score_std": ms.stability_score_std,
                "proposal_type_mean_per_iter": ms.proposal_type_mean_per_iter,
            },
            "runs": out_runs,
        })

    return {
        "schema_version": 2,
        "models": out_models,
        "terminal_modes": list(ALL_TERMINAL_MODES),
        "status_vocab": LEDGER_STATUS_VOCAB,
        "proposal_types": PROP_TYPES,
    }

# ===========================================================================
# Dashboards — self-contained HTML, no external deps
# ===========================================================================
CODE_EVOLUTION_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Code Evolution — {LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body  { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
          background: #0f1115; color: #e6e6e6; margin: 0; padding: 24px; font-size: 14px; }
  h1   { font-size: 22px; margin: 0 0 6px 0; }
  h2   { font-size: 16px; margin: 26px 0 8px 0; color: #a8c5f0;
         border-bottom: 1px solid #2a2d35; padding-bottom: 4px; }
  h3   { font-size: 13px; margin: 14px 0 6px 0; color: #d0d0d0; }
  .meta { color: #888; font-size: 12px; margin-bottom: 18px; }
  .card { background: #181a20; border: 1px solid #262931; border-radius: 8px;
          padding: 14px; margin: 8px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .chart-box { position: relative; height: 240px; }
  /* Tables */
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 5px 9px; text-align: left; border-bottom: 1px solid #22252d; }
  th     { color: #a8c5f0; font-weight: 600; white-space: nowrap; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.mono { font-family: monospace; font-size: 11px; }
  /* Component lifecycle cell states */
  .lc-new     { background: #163320; color: #6ee093; font-weight: 700; text-align: center; }
  .lc-stable  { background: #141619; color: #555;    text-align: center; }
  .lc-excised { background: #331414; color: #e66e6e; font-weight: 700; text-align: center; }
  .lc-dc      { background: #2e2108; color: #e6c46e; font-weight: 700; text-align: center; }
  .lc-absent  { background: #0f1115; color: #2a2d35; text-align: center; }
  /* Inline tags */
  .tag { display: inline-block; padding: 1px 6px; border-radius: 3px;
         font-size: 10px; font-weight: 600; margin: 1px; white-space: nowrap; }
  .tag-ex    { background: #331414; color: #e66e6e; }
  .tag-add   { background: #163320; color: #6ee093; }
  .tag-dc    { background: #2e2108; color: #e6c46e; }
  .tag-ghost { background: #252512; color: #c8c860; }
  .tag-warn  { background: #222; color: #888; }
  /* Legend */
  .legend { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; font-size: 11px; }
  .legend-item { display: flex; align-items: center; gap: 5px; }
  .swatch { width: 13px; height: 13px; border-radius: 2px; flex-shrink: 0; }
  .small { color: #888; font-size: 11px; }
  .warn  { color: #e6c46e; }
  details > summary { cursor: pointer; padding: 4px 0; color: #a8c5f0; font-size: 13px; }
  .caveat { color: #888; font-size: 11px; font-style: italic; margin-top: 4px; }
</style>
</head>
<body>
<h1>ARD Code Evolution</h1>
<div class="meta">
  Campaign: <code>{LABEL}</code> &nbsp;•&nbsp; Generated: <code id="ts"></code>
</div>
<div id="root"></div>

<script>
const DATA = {DATA_JSON};
document.getElementById('ts').textContent =
  new Date().toISOString().replace('T',' ').slice(0,19);
const root = document.getElementById('root');

// ── Palette (matches Pipeline Performance) ──
const RUN_COLORS = ['#4e79a7','#f28e2b','#59a14f','#e15759',
                    '#76b7b2','#edc948','#b07aa1','#ff9da7'];
function runColor(i) { return RUN_COLORS[i % RUN_COLORS.length]; }

// ── Stats helpers ──
function mean(arr)  { const v = arr.filter(x => x != null); return v.length ? v.reduce((a,b)=>a+b,0)/v.length : null; }
function std(arr)   {
  const v = arr.filter(x => x != null);
  if (v.length < 2) return null;
  const m = mean(v);
  return Math.sqrt(v.reduce((a,b) => a + (b-m)**2, 0) / v.length);
}
function fmt(v, d=2) { return (v == null) ? '—' : (+v).toFixed(d); }
function fmtPct(v)   { return (v == null) ? '—' : (v*100).toFixed(1)+'%'; }
function getCode(it) { return it.code || {}; }

// ── Build per-iteration aggregates (mean / std across runs) ──
// Returns arrays indexed 0..maxIter-1 (position i → iteration i+1).
function buildAggArrays(runs, maxIter, extractor) {
  const means = [], stds = [];
  for (let i = 1; i <= maxIter; i++) {
    const vals = runs.map(r => {
      const it = r.iterations.find(x => x.iter === i);
      return it ? extractor(it) : null;
    }).filter(x => x != null);
    means.push(vals.length ? mean(vals) : null);
    stds.push(vals.length > 1 ? std(vals) : null);
  }
  return { means, stds };
}

// ── Render one model block ──
DATA.models.forEach((model, mi) => {
  const block = document.createElement('div');
  root.appendChild(block);

  const h2 = document.createElement('h2');
  h2.textContent = model.name + '  ·  ' + model.n_runs + ' run' + (model.n_runs===1?'':'s');
  block.appendChild(h2);

  const maxIter = Math.max(...model.runs.flatMap(r => r.iterations.map(it => it.iter)));
  const itLabels = Array.from({length: maxIter}, (_, i) => String(i+1));

  // ════════════════════════════════════════════════════════
  // CARD 1 — Component Count Trajectory  +  Churn
  // ════════════════════════════════════════════════════════
  const card1 = document.createElement('div');
  card1.className = 'card grid2';
  block.appendChild(card1);

  // ── 1a: Component count trajectory ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = '<h3>Component Count per Iteration</h3><div class="chart-box"><canvas></canvas></div>';
    card1.appendChild(box);

    const { means, stds } = buildAggArrays(model.runs, maxIter, it => getCode(it).n_components ?? null);
    const upperData = means.map((m,i) => (m!=null && stds[i]!=null) ? m+stds[i] : m);
    const lowerData = means.map((m,i) => (m!=null && stds[i]!=null) ? Math.max(0,m-stds[i]) : m);

    const col = runColor(mi);

    // Per-run lines (faint), then CI band + mean on top
    const perRunDatasets = model.runs.map((r, ri) => ({
      label: r.tag.split('_').slice(-1)[0],
      data: itLabels.map((_, i) => {
        const it = r.iterations.find(x => x.iter === i+1);
        return it ? (getCode(it).n_components ?? null) : null;
      }),
      borderColor: runColor(ri) + '66',
      backgroundColor: 'transparent',
      borderWidth: 1, pointRadius: 2, tension: 0.2,
      spanGaps: true,
    }));

    const ciDatasets = [
      // Upper CI boundary (fills down to lower)
      { label: '_upper', data: upperData, borderWidth: 0, pointRadius: 0,
        fill: '+1', backgroundColor: col + '28', tension: 0.2, spanGaps: true },
      // Lower CI boundary
      { label: '_lower', data: lowerData, borderWidth: 0, pointRadius: 0,
        fill: false, tension: 0.2, spanGaps: true },
      // Mean line
      { label: 'mean', data: means, borderColor: col, borderWidth: 2.5,
        pointRadius: 3, tension: 0.2, fill: false, spanGaps: true },
    ];

    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: { labels: itLabels, datasets: [...perRunDatasets, ...ciDatasets] },
      options: {
        scales: {
          x: { title: { display: true, text: 'Iteration' } },
          y: { title: { display: true, text: 'N Components' }, min: 0,
               ticks: { stepSize: 1 } },
        },
        plugins: {
          legend: {
            labels: {
              color: '#ccc', boxWidth: 10, font: { size: 10 },
              // Hide the CI helper datasets from legend
              filter: item => !item.text.startsWith('_'),
            }
          }
        },
        animation: false,
      }
    });
  })();

  // ── 1b: Component churn (per-run lines) ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = '<h3>Component Churn per Iteration (per run)</h3><div class="chart-box"><canvas></canvas></div>';
    card1.appendChild(box);

    // Per-run added lines (solid) and excised lines (dashed), same run color
    const datasets = [];
    model.runs.forEach((run, ri) => {
      const color = runColor(ri);
      const shortTag = run.tag.split('_').slice(-1)[0];
      datasets.push({
        label: shortTag + ' +added',
        data: itLabels.map((_, i) => {
          const it = run.iterations.find(x => x.iter === i + 1);
          return it ? (getCode(it).n_added ?? null) : null;
        }),
        borderColor: color, backgroundColor: color + '33',
        borderWidth: 2, pointRadius: 3, tension: 0.1,
        fill: false, spanGaps: true,
      });
      datasets.push({
        label: shortTag + ' ×excised',
        data: itLabels.map((_, i) => {
          const it = run.iterations.find(x => x.iter === i + 1);
          return it ? (getCode(it).n_excised ?? null) : null;
        }),
        borderColor: color, backgroundColor: 'transparent',
        borderWidth: 1.5, borderDash: [4, 3], pointRadius: 2,
        fill: false, spanGaps: true,
      });
    });

    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: { labels: itLabels, datasets },
      options: {
        scales: {
          x: { title: { display: true, text: 'Iteration' } },
          y: { title: { display: true, text: 'Components' }, min: 0, ticks: { stepSize: 1 } },
        },
        plugins: {
          legend: { labels: { color: '#ccc', boxWidth: 10, font: { size: 10 } } },
          tooltip: { callbacks: {
            title: ctx => `Iteration ${+itLabels[ctx[0].dataIndex] + 1}`,
          }},
        },
        animation: false,
      }
    });
  })();

  // ════════════════════════════════════════════════════════
  // CARD 2 — Code Change Volume  +  Structural Integrity Rates
  // ════════════════════════════════════════════════════════
  const card2 = document.createElement('div');
  card2.className = 'card grid2';
  block.appendChild(card2);

  // ── 2a: Code change volume (per-run lines) ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = '<h3>Diff Size per Iteration (per run)</h3><div class="chart-box"><canvas></canvas></div>';
    card2.appendChild(box);

    const datasets = [];
    model.runs.forEach((run, ri) => {
      const color = runColor(ri);
      const shortTag = run.tag.split('_').slice(-1)[0];
      datasets.push({
        label: shortTag + ' +lines',
        data: itLabels.map((_, i) => {
          const it = run.iterations.find(x => x.iter === i + 1);
          return it ? (getCode(it).lines_added ?? null) : null;
        }),
        borderColor: color, fill: false,
        borderWidth: 2, pointRadius: 3, tension: 0.1, spanGaps: true,
      });
      datasets.push({
        label: shortTag + ' −lines',
        data: itLabels.map((_, i) => {
          const it = run.iterations.find(x => x.iter === i + 1);
          return it ? (getCode(it).lines_removed ?? null) : null;
        }),
        borderColor: color, borderDash: [4, 3], fill: false,
        borderWidth: 1.5, pointRadius: 2, tension: 0.1, spanGaps: true,
      });
    });

    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: { labels: itLabels, datasets },
      options: {
        scales: {
          x: { title: { display: true, text: 'Iteration' } },
          y: { title: { display: true, text: 'Lines' }, min: 0 },
        },
        plugins: {
          legend: { labels: { color: '#ccc', boxWidth: 10, font: { size: 10 } } },
        },
        animation: false,
      }
    });
  })();

  // ── 2b: Structural flag rates per iteration (AST-only) ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = `
      <h3>Structural Flag Rates per Iteration (AST)</h3>
      <div class="chart-box"><canvas></canvas></div>`;
    card2.appendChild(box);

    const dcRates = [], ghostRates = [];
    for (let i = 1; i <= maxIter; i++) {
      // Double-count rate: fraction of runs with ≥1 double-count pair at iter i
      const dcVals = model.runs.map(r => {
        const it = r.iterations.find(x => x.iter===i);
        return it ? ((getCode(it).n_double_count ?? 0) > 0 ? 1 : 0) : null;
      }).filter(x => x != null);
      dcRates.push(dcVals.length ? mean(dcVals) : null);

      // Ghost rate: fraction of runs with ≥1 untracked r_* var at iter i
      const ghostVals = model.runs.map(r => {
        const it = r.iterations.find(x => x.iter===i);
        return it ? ((getCode(it).n_ghost ?? 0) > 0 ? 1 : 0) : null;
      }).filter(x => x != null);
      ghostRates.push(ghostVals.length ? mean(ghostVals) : null);
    }

    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: {
        labels: itLabels,
        datasets: [
          { label: 'Double-count rate', data: dcRates,
            borderColor: '#e6c46e', backgroundColor: '#e6c46e22',
            borderWidth: 2, pointRadius: 3, tension: 0.2, spanGaps: true },
          { label: 'Ghost var rate', data: ghostRates,
            borderColor: '#c8c860', backgroundColor: '#c8c86022',
            borderWidth: 2, pointRadius: 3, tension: 0.2, spanGaps: true },
        ]
      },
      options: {
        scales: {
          x: { title: { display: true, text: 'Iteration' } },
          y: { title: { display: true, text: 'Rate (0–1)' }, min: 0, max: 1 },
        },
        plugins: { legend: { labels: { color: '#ccc', boxWidth: 12 } } },
        animation: false,
      }
    });
  })();

  // ════════════════════════════════════════════════════════
  // CARD 3 — Cross-run Summary Table
  // ════════════════════════════════════════════════════════
  (function() {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = '<h3>Cross-run Summary</h3>';

    const tbl = document.createElement('table');
    tbl.innerHTML = `<thead><tr>
      <th>Run</th>
      <th title="Total unique components ever in dict">Peak N Comp</th>
      <th title="Total components excised across all iterations">Total Excised</th>
      <th title="Total components added across all iterations">Total Added</th>
      <th title="Mean (excised + added) per iteration">Mean Churn/Iter</th>
      <th title="Iterations with ≥1 double-count pair">Double-count Iters</th>
      <th title="Iterations with ≥1 ghost r_* var">Ghost Iters</th>
      <th title="Sum of lines_added + lines_removed across all iterations">Total Lines Changed</th>
      <th title="Mean lines changed per iteration">Mean Lines/Iter</th>
    </tr></thead>`;
    const tbody = document.createElement('tbody');

    model.runs.forEach((run, ri) => {
      const iters = run.iterations;
      const nIter = iters.length;

      const allComps = new Set();
      iters.forEach(it => (getCode(it).component_names || []).forEach(c => allComps.add(c)));
      const peakN = allComps.size;

      const totalEx   = iters.reduce((s,it) => s + (getCode(it).n_excised ?? 0), 0);
      const totalAdd  = iters.reduce((s,it) => s + (getCode(it).n_added ?? 0), 0);
      const meanChurn = nIter ? ((totalEx + totalAdd) / nIter).toFixed(2) : '—';
      const dcIters   = iters.filter(it => (getCode(it).n_double_count ?? 0) > 0).length;
      const ghostIters= iters.filter(it => (getCode(it).n_ghost ?? 0) > 0).length;
      const totalLines= iters.reduce((s,it) => s + (getCode(it).lines_added??0) + (getCode(it).lines_removed??0), 0);
      const meanLines = nIter ? (totalLines / nIter).toFixed(1) : '—';
      const shortTag  = run.tag.split('_').slice(-1)[0];

      tbody.innerHTML += `<tr>
        <td class="mono">${shortTag}</td>
        <td class="num">${peakN}</td>
        <td class="num">${totalEx}</td>
        <td class="num">${totalAdd}</td>
        <td class="num">${meanChurn}</td>
        <td class="num ${dcIters>0?'warn':''}">${dcIters} / ${nIter}</td>
        <td class="num">${ghostIters} / ${nIter}</td>
        <td class="num">${totalLines}</td>
        <td class="num">${meanLines}</td>
      </tr>`;
    });
    tbl.appendChild(tbody);
    card.appendChild(tbl);
    block.appendChild(card);
  })();

  // ════════════════════════════════════════════════════════
  // CARD 3b — Jaccard Convergence Matrix
  // ════════════════════════════════════════════════════════
  (function() {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h3>Cross-run Convergence — Jaccard Similarity of Final Component Sets
        <span class="small" style="margin-left:8px">
          (1.0 = identical final sets · 0.0 = no shared components)
        </span>
      </h3>`;

    // Final component set per run = component_names at the last iteration
    const finalSets = model.runs.map(run => {
      const lastIt = run.iterations.reduce((a, b) => a.iter > b.iter ? a : b, run.iterations[0]);
      return new Set(getCode(lastIt).component_names || []);
    });
    const runTags = model.runs.map(r => r.tag.split('_').slice(-1)[0]);

    function jaccard(setA, setB) {
      const intersection = [...setA].filter(x => setB.has(x)).length;
      const union = new Set([...setA, ...setB]).size;
      return union === 0 ? 1 : intersection / union;
    }

    // Color: 0=red, 0.5=yellow, 1=green (diagonal = white)
    function jaccardColor(v, isDiag) {
      if (isDiag) return '#2a2d35';
      if (v >= 0.66) return `rgba(89,161,79,${0.3 + v * 0.5})`;   // green
      if (v >= 0.33) return `rgba(230,196,110,${0.3 + v * 0.5})`; // yellow
      return `rgba(225,87,89,${0.3 + (1-v) * 0.5})`;              // red
    }

    // Add CSS for matrix cells
    const style = document.createElement('style');
    style.textContent = `
      .jac-table td { text-align: center; width: 70px; height: 36px;
                      font-variant-numeric: tabular-nums; font-size: 12px; }
      .jac-table th { text-align: center; color: #a8c5f0; padding: 4px 9px; }`;
    card.appendChild(style);

    const tbl = document.createElement('table');
    tbl.className = 'jac-table';
    let thead = '<thead><tr><th></th>';
    runTags.forEach(t => { thead += `<th>${t}</th>`; });
    thead += '</tr></thead>';
    tbl.innerHTML = thead;
    const tbody = document.createElement('tbody');

    model.runs.forEach((runA, ri) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<th style="text-align:right;color:${runColor(ri)}">${runTags[ri]}</th>`;
      model.runs.forEach((runB, ci) => {
        const isDiag = ri === ci;
        const j = isDiag ? 1 : jaccard(finalSets[ri], finalSets[ci]);
        tr.innerHTML += `<td style="background:${jaccardColor(j, isDiag)};color:#e6e6e6">
          ${isDiag ? '—' : j.toFixed(2)}</td>`;
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    card.appendChild(tbl);

    // Summary: mean off-diagonal Jaccard
    const offDiag = [];
    model.runs.forEach((_, ri) =>
      model.runs.forEach((_, ci) => { if (ri < ci) offDiag.push(jaccard(finalSets[ri], finalSets[ci])); }));
    const meanJ = offDiag.length ? offDiag.reduce((a,b)=>a+b,0)/offDiag.length : null;
    const note = document.createElement('div');
    note.className = 'small';
    note.style.marginTop = '8px';
    note.textContent = meanJ !== null
      ? `Mean cross-run Jaccard: ${meanJ.toFixed(3)} — ${
          meanJ >= 0.5 ? 'strong convergence (consistent reward structure across seeds)' :
          meanJ >= 0.25 ? 'moderate convergence' :
          'low convergence (reward structures diverge across seeds)'}`
      : '—';
    card.appendChild(note);
    block.appendChild(card);
  })();

  // ════════════════════════════════════════════════════════
  // CARD 3c — Productive Churn Ratio  +  Component Survival Curve
  // ════════════════════════════════════════════════════════
  const card3c = document.createElement('div');
  card3c.className = 'card grid2';
  block.appendChild(card3c);

  // ── Left: Productive churn ratio (horizontal bar, one bar per run) ──
  (function() {
    const POSITIVE = new Set(['Validated','Confirmed','ProductiveDeviation','Mixed']);
    const box = document.createElement('div');
    box.innerHTML = `
      <h3>Productive Churn Ratio
        <span class="small" style="margin-left:6px">
          (excisions + additions in positively-verdicted iterations / total)
        </span>
      </h3>
      <div class="chart-box" style="height:180px"><canvas></canvas></div>`;
    card3c.appendChild(box);

    const labels = [], values = [], colors = [];
    model.runs.forEach((run, ri) => {
      let productiveChurn = 0, totalChurn = 0;
      run.iterations.forEach(it => {
        const cc = getCode(it);
        const churn = (cc.n_excised ?? 0) + (cc.n_added ?? 0);
        totalChurn += churn;
        if (POSITIVE.has(it.validator_status)) productiveChurn += churn;
      });
      const ratio = totalChurn > 0 ? productiveChurn / totalChurn : null;
      labels.push(run.tag.split('_').slice(-1)[0]);
      values.push(ratio != null ? +(ratio * 100).toFixed(1) : null);
      colors.push(ratio == null ? '#444'
        : ratio >= 0.5 ? '#59a14f'
        : ratio >= 0.3 ? '#e6c46e'
        : '#e15759');
    });

    new Chart(box.querySelector('canvas'), {
      type: 'bar',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3 }] },
      options: {
        indexAxis: 'y',
        scales: {
          x: { min: 0, max: 100, title: { display: true, text: '% of total churn' },
               ticks: { callback: v => v + '%' } },
          y: { ticks: { color: labels.map((_, i) => runColor(i)) } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.raw ?? '—'}% of churn was in productive iterations` } },
        },
        animation: false,
      }
    });
  })();

  // ── Right: Component survival curve ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = `
      <h3>Component Survival Curve
        <span class="small" style="margin-left:6px">
          (fraction of components surviving ≥ k iterations after introduction)
        </span>
      </h3>
      <div class="chart-box" style="height:180px"><canvas></canvas></div>`;
    card3c.appendChild(box);

    // Determine max possible survival span
    const maxSpan = maxIter;

    const datasets = model.runs.map((run, ri) => {
      // For each component, compute how many iterations it survived after birth.
      // Birth = first iter where state = 'new'; death = first iter where state = 'excised'
      // (or maxIter + 1 if never excised = survived to end of run).
      const allComps = new Set();
      run.iterations.forEach(it => {
        (getCode(it).component_names || []).forEach(c => allComps.add(c));
        (getCode(it).excised || []).forEach(c => allComps.add(c));
      });

      const survivalLengths = [];
      allComps.forEach(comp => {
        let birth = null, death = null;
        for (let i = 1; i <= maxIter; i++) {
          const it = run.iterations.find(x => x.iter === i);
          if (!it) continue;
          const cc = getCode(it);
          const addSet  = new Set(cc.added || []);
          const excSet  = new Set(cc.excised || []);
          if (birth === null && addSet.has(comp)) birth = i;
          if (birth !== null && death === null && excSet.has(comp)) death = i;
        }
        if (birth !== null) {
          const survived = death !== null ? (death - birth) : (maxIter - birth + 1);
          survivalLengths.push(survived);
        }
      });

      const n = survivalLengths.length;
      if (n === 0) return null;

      // S(k) = fraction surviving >= k iterations
      const survData = [];
      for (let k = 0; k <= maxSpan; k++) {
        survData.push({ x: k, y: survivalLengths.filter(s => s >= k).length / n });
      }

      return {
        label: run.tag.split('_').slice(-1)[0],
        data: survData,
        borderColor: runColor(ri),
        backgroundColor: 'transparent',
        borderWidth: 2, pointRadius: 0,
        fill: false, stepped: true,
      };
    }).filter(Boolean);

    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: { datasets },
      options: {
        scales: {
          x: { type: 'linear', title: { display: true, text: 'Iterations after introduction (k)' },
               min: 0, ticks: { stepSize: 1 } },
          y: { title: { display: true, text: 'Survival fraction' }, min: 0, max: 1 },
        },
        plugins: { legend: { labels: { color: '#ccc', boxWidth: 10 } } },
        animation: false,
      }
    });
  })();

  // ════════════════════════════════════════════════════════
  // CARD 4 — Component Lifecycle (one sub-table per run)
  // ════════════════════════════════════════════════════════
  const lifecycleDetails = document.createElement('details');
  lifecycleDetails.className = 'card';
  lifecycleDetails.innerHTML = '<summary style="font-size:13px;color:#a8c5f0">Component Lifecycle (per-run heatmap)</summary>';
  block.appendChild(lifecycleDetails);

  const lifecycleCard = document.createElement('div');
  lifecycleCard.style.marginTop = '10px';
  lifecycleDetails.appendChild(lifecycleCard);

  // Legend
  const legendDiv = document.createElement('div');
  legendDiv.className = 'legend';
  [
    ['#163320','#6ee093','✦  New'],
    ['#141619','#555',   '·  Stable'],
    ['#331414','#e66e6e','✕  Excised'],
    ['#2e2108','#e6c46e','⚠  Double-count'],
    ['#0f1115','#2a2d35','—  Absent'],
  ].forEach(([bg, fg, label]) => {
    legendDiv.innerHTML += `<div class="legend-item">
      <div class="swatch" style="background:${bg};border:1px solid ${fg}66"></div>
      <span style="color:${fg}">${label}</span></div>`;
  });
  lifecycleCard.appendChild(legendDiv);

  model.runs.forEach((run, ri) => {
    const iters = Array.from({length: maxIter}, (_, i) => i+1);

    // All component names seen across this run, in first-appearance order
    const allComps = [], seenSet = new Set();
    iters.forEach(i => {
      const it = run.iterations.find(x => x.iter===i);
      (it ? getCode(it).component_names || [] : []).forEach(c => {
        if (!seenSet.has(c)) { seenSet.add(c); allComps.push(c); }
      });
      // Also include excised-only (appeared in prev but never in curr)
      (it ? getCode(it).excised || [] : []).forEach(c => {
        if (!seenSet.has(c)) { seenSet.add(c); allComps.push(c); }
      });
    });
    if (!allComps.length) return;

    // Per-component, per-iteration state
    const stateOf = (comp, iter) => {
      const it = run.iterations.find(x => x.iter===iter);
      if (!it) return 'absent';
      const cc = getCode(it);
      const currSet  = new Set(cc.component_names || []);
      const excSet   = new Set(cc.excised || []);
      const addSet   = new Set(cc.added || []);
      const dcComps  = new Set();
      (cc.double_count_flags || []).forEach(f => {
        dcComps.add(f.component_a); dcComps.add(f.component_b);
      });
      if (excSet.has(comp))   return 'excised';
      if (!currSet.has(comp)) return 'absent';
      if (dcComps.has(comp))  return 'dc';
      if (addSet.has(comp))   return 'new';
      return 'stable';
    };

    const CLASS = {new:'lc-new', stable:'lc-stable', excised:'lc-excised', dc:'lc-dc', absent:'lc-absent'};
    const LABEL = {new:'✦', stable:'·', excised:'✕', dc:'⚠', absent:'—'};
    const TITLE = {
      new:'First appeared this iteration', stable:'Present, no flags',
      excised:'Removed from components dict', dc:'In a double-count pair this iteration',
      absent:'Not in components dict',
    };

    const runLabel = document.createElement('div');
    runLabel.className = 'small';
    runLabel.style.cssText = 'margin: 10px 0 4px; color:#a8c5f0;';
    runLabel.textContent = run.tag.split('_').slice(-1)[0];
    lifecycleCard.appendChild(runLabel);

    const tbl = document.createElement('table');
    let thead = '<thead><tr><th style="min-width:180px">Component</th>';
    iters.forEach(i => { thead += `<th style="text-align:center;width:52px">Iter ${i}</th>`; });
    thead += '</tr></thead>';
    tbl.innerHTML = thead;
    const tbody = document.createElement('tbody');
    allComps.forEach(comp => {
      let row = `<tr><td class="mono">${comp}</td>`;
      iters.forEach(i => {
        const s = stateOf(comp, i);
        row += `<td class="${CLASS[s]}" title="${TITLE[s]}">${LABEL[s]}</td>`;
      });
      row += '</tr>';
      tbody.innerHTML += row;
    });
    // Ghost vars row (if any across this run)
    const ghostsByIter = {};
    iters.forEach(i => {
      const it = run.iterations.find(x => x.iter===i);
      if (it) (getCode(it).ghost_vars || []).forEach(g => {
        (ghostsByIter[i] = ghostsByIter[i] || []).push(g);
      });
    });
    if (Object.keys(ghostsByIter).length) {
      let ghostRow = `<tr><td class="mono" style="color:#c8c860">ghost r_* vars</td>`;
      iters.forEach(i => {
        const gs = ghostsByIter[i];
        ghostRow += gs
          ? `<td style="text-align:center;font-size:10px;color:#c8c860" title="${gs.join(', ')}">⊘${gs.length}</td>`
          : `<td class="lc-absent">—</td>`;
      });
      ghostRow += '</tr>';
      tbody.innerHTML += ghostRow;
    }
    tbl.appendChild(tbody);
    lifecycleCard.appendChild(tbl);
  });

  // ════════════════════════════════════════════════════════
  // CARD 5 — Per-iteration detail (expandable)
  // ════════════════════════════════════════════════════════
  const drill = document.createElement('details');
  drill.className = 'card';
  drill.innerHTML = '<summary>Per-iteration Code Detail (all runs)</summary>';
  block.appendChild(drill);

  model.runs.forEach(run => {
    const sec = document.createElement('div');
    sec.style.marginTop = '10px';
    const shortTag = run.tag.split('_').slice(-1)[0];
    sec.innerHTML = `<div class="small" style="margin-bottom:4px;color:#a8c5f0">${shortTag}</div>`;

    const tbl = document.createElement('table');
    tbl.innerHTML = `<thead><tr>
      <th>Iter</th><th>N Comp</th>
      <th>Excised</th><th>Added</th>
      <th>+Lines</th><th>−Lines</th><th>Hunks</th>
      <th>Double-count</th><th>Ghost vars</th><th>Warnings</th>
    </tr></thead>`;
    const tbody = document.createElement('tbody');

    run.iterations.forEach(it => {
      const cc = getCode(it);
      const exTags  = (cc.excised || []).map(e  => `<span class="tag tag-ex">${e}</span>`).join('');
      const addTags = (cc.added   || []).map(a  => `<span class="tag tag-add">${a}</span>`).join('');
      const dcTags  = (cc.double_count_flags || []).map(f =>
        `<span class="tag tag-dc" title="Shared: ${(f.shared_r_vars||[]).join(', ')}">${f.component_a} ↔ ${f.component_b}</span>`
      ).join('');
      const ghostTags = (cc.ghost_vars || []).map(g => `<span class="tag tag-ghost">${g}</span>`).join('');
      const warnText  = (cc.code_warnings || [])
        .filter(w => !w.startsWith('iter1_no_prev'))
        .map(w => `<span class="tag tag-warn">${w}</span>`).join('');

      tbody.innerHTML += `<tr>
        <td>${it.iter}</td>
        <td class="num">${cc.n_components ?? '—'}</td>
        <td>${exTags  || '<span class="small">—</span>'}</td>
        <td>${addTags || '<span class="small">—</span>'}</td>
        <td class="num" style="color:#59a14f">${cc.lines_added   ?? '—'}</td>
        <td class="num" style="color:#e15759">${cc.lines_removed ?? '—'}</td>
        <td class="num">${cc.n_hunks ?? '—'}</td>
        <td>${dcTags    || '<span class="small">—</span>'}</td>
        <td>${ghostTags || '<span class="small">—</span>'}</td>
        <td>${warnText  || '<span class="small">—</span>'}</td>
      </tr>`;
    });
    tbl.appendChild(tbody);
    sec.appendChild(tbl);
    drill.appendChild(sec);
  });
});
</script>
</body>
</html>
"""

PIPELINE_PERFORMANCE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Pipeline Performance — {LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        background: #0f1115; color: #e6e6e6; margin: 0; padding: 24px;
        font-size: 14px; }
  h1 { font-size: 22px; margin: 0 0 6px 0; }
  h2 { font-size: 16px; margin: 26px 0 8px 0; color: #a8c5f0;
        border-bottom: 1px solid #2a2d35; padding-bottom: 4px; }
  h3 { font-size: 14px; margin: 18px 0 6px 0; color: #d0d0d0; }
  .meta { color: #888; font-size: 12px; margin-bottom: 18px; }
  .card { background: #181a20; border: 1px solid #262931; border-radius: 8px;
         padding: 14px; margin: 8px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .chart-box { position: relative; height: 260px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #2a2d35; }
  th { color: #a8c5f0; font-weight: 600; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px;
         font-size: 11px; font-weight: 600; }
  .pill-Validated, .pill-Confirmed { background: #1e4a2b; color: #6ee093; }
  .pill-Mixed, .pill-PyrrhicVictory, .pill-ProductiveDeviation {
    background: #4a3e1e; color: #e6c46e; }
  .pill-Inconclusive { background: #2a2d35; color: #888; }
  .pill-Refuted, .pill-Regressed, .pill-GoodhartTrap {
    background: #4a1e1e; color: #e66e6e; }
  .pill-Unparsed { background: #333; color: #888; }
  .small { color: #888; font-size: 12px; }
  .warn { color: #e6c46e; }
  details > summary { cursor: pointer; padding: 4px 0; color: #a8c5f0; }
  .tier-header { font-size: 13px; font-weight: 700; letter-spacing: 0.08em;
                 text-transform: uppercase; padding: 6px 10px; border-radius: 4px;
                 margin: 20px 0 8px 0; display: inline-block; }
  .tier1 { background: #163320; color: #6ee093; }
  .tier2 { background: #1a1e35; color: #a8c5f0; }
  .verdict-card { display: grid; grid-template-columns: 180px 1fr 1fr 1fr; gap: 16px;
                  align-items: center; }
  .score-big { font-size: 48px; font-weight: 700; color: #e6c46e;
               font-variant-numeric: tabular-nums; }
  .score-sub { font-size: 12px; color: #888; margin-top: 2px; }
  .bar-track { background: #2a2d35; border-radius: 3px; height: 10px;
               position: relative; margin: 6px 0; }
  .bar-fill { height: 100%; border-radius: 3px; }
  .dot-row { display: flex; align-items: center; gap: 6px; margin-top: 4px;
             flex-wrap: wrap; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .no-score { color: #555; font-size: 12px; font-style: italic; }
</style>
</head>
<body>
<h1>ARD Pipeline Performance</h1>
<div class="meta">
  Campaign: <code>{LABEL}</code>  •  Generated: <code id="ts"></code>
</div>

<div id="root"></div>

<script>
const DATA = {DATA_JSON};
const root = document.getElementById('root');
document.getElementById('ts').textContent = new Date().toISOString().replace('T', ' ').slice(0, 19);

// ---------------- Helpers ----------------

function statusClass(s) { return 'pill pill-' + (s || 'Unparsed').replace(/[^A-Za-z]/g, ''); }
function fmt(v, d=3) { if (v === null || v === undefined) return '—'; if (typeof v !== 'number') return v; return v.toFixed(d); }
function fmtPct(v) { if (v === null || v === undefined) return '—'; return (v * 100).toFixed(1) + '%'; }
function fmtMeanStd(mean, std, d=3) {
  if (mean === null || mean === undefined) return '—';
  if (std === null || std === undefined) return mean.toFixed(d);
  return mean.toFixed(d) + ' ± ' + std.toFixed(d);
}
function std(arr) {
  const v = arr.filter(x => x != null);
  if (v.length < 2) return null;
  const m = v.reduce((a,b)=>a+b,0)/v.length;
  return Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/v.length);
}
function median(arr) {
  const v = arr.filter(x=>x!=null).sort((a,b)=>a-b);
  if (!v.length) return null;
  const m = Math.floor(v.length/2);
  return v.length%2 ? v[m] : (v[m-1]+v[m])/2;
}

// Stable per-run color picker (color-blind-friendly tableau-ish palette)
const RUN_COLORS = ['#4e79a7', '#f28e2b', '#59a14f', '#e15759', '#76b7b2',
                    '#edc948', '#b07aa1', '#ff9da7'];
function runColor(i) { return RUN_COLORS[i % RUN_COLORS.length]; }

// ---------------- Section 0: Campaign Verdict ----------------

(function renderVerdictCard() {
  const allRunScores = DATA.models.flatMap(m => m.runs.map(r => r.run_score));
  const hasAny = allRunScores.some(rs => rs !== null && rs !== undefined);

  const card = document.createElement('div');
  card.className = 'card';

  if (!hasAny) {
    card.innerHTML = `<div class="no-score">Run scores not computed —
      run <code>compute_run_score.py</code> for each run first.</div>`;
    root.appendChild(card);
    return;
  }

  const components = ['ppv', 'policy_retention', 'tr'];
  const compLabels = {'ppv': 'PPV — Peak Graded Value',
                      'policy_retention': 'PolicyRet — Policy Retention',
                      'tr': 'TR — Training Reliability'};
  const compColors = {'ppv': '#e6c46e', 'policy_retention': '#4e79a7', 'tr': '#59a14f'};

  DATA.models.forEach((model, mi) => {
    const scores = model.runs.map(r => r.run_score?.score).filter(v => v != null);
    const medianScore = scores.length ? scores.slice().sort((a,b)=>a-b)[Math.floor(scores.length/2)] : null;

    const grid = document.createElement('div');
    grid.className = 'verdict-card';

    const scoreDiv = document.createElement('div');
    scoreDiv.innerHTML = `
      <div class="score-big">${medianScore != null ? medianScore.toFixed(3) : '—'}</div>
      <div class="score-sub">median RunScore · N=${model.n_runs}</div>`;
    grid.appendChild(scoreDiv);

    components.forEach(comp => {
      const vals = model.runs.map(r => r.run_score?.[comp]).filter(v => v != null);
      const med = vals.length ? vals.slice().sort((a,b)=>a-b)[Math.floor(vals.length/2)] : null;
      const div = document.createElement('div');
      div.innerHTML = `<div style="font-size:12px;color:#ccc">${compLabels[comp]}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${med!=null?med*100:0}%;background:${compColors[comp]}"></div>
        </div>
        <div class="dot-row">
          ${model.runs.map((r, ri) => {
            const v = r.run_score?.[comp];
            return v != null
              ? `<div class="dot" style="background:${runColor(ri)}" title="${r.tag.split('_').slice(-1)[0]}: ${v.toFixed(3)}"></div>`
              : '';
          }).join('')}
          <span style="font-size:11px;color:#888;margin-left:4px">${med!=null?med.toFixed(3):'—'}</span>
        </div>`;
      grid.appendChild(div);
    });

    card.appendChild(grid);
  });

  root.appendChild(card);
})();

// ---------------- Section 1 header ----------------

const t1 = document.createElement('div');
t1.innerHTML = '<span class="tier-header tier1">Tier 1 — RL Outcome</span>';
root.appendChild(t1);

// ---------------- Render per-model blocks ----------------

DATA.models.forEach((model, mi) => {
  const block = document.createElement('div');
  root.appendChild(block);

  // -- Header
  const hdr = document.createElement('h2');
  hdr.textContent = model.name + '  ·  ' + model.n_runs + ' run' + (model.n_runs === 1 ? '' : 's');
  block.appendChild(hdr);

  const maxIter = Math.max(...model.runs.flatMap(r => r.iterations.map(it => it.iter)));
  const itLabels = Array.from({length: maxIter}, (_, i) => String(i+1));

  // -- Cross-run summary table (per-run rows)
  const summaryCard = document.createElement('div');
  summaryCard.className = 'card';
  summaryCard.innerHTML = `
    <h3>Cross-run summary</h3>
    <table>
      <thead><tr>
        <th>Run</th>
        <th>Peak PSR</th><th>Peak Centered</th>
        <th>Final PSR</th>
        <th>Collapses</th><th>Recoveries</th>
        <th title="σ of PSR in last 3 iterations">σ(last-3 PSR)</th>
        <th title="First iteration PSR ≥ 0.60">TtT-60</th>
        <th title="First iteration PSR ≥ 0.80">TtT-80</th>
      </tr></thead>
    </table>`;
  const summaryTbody = document.createElement('tbody');
  model.runs.forEach((run, ri) => {
    const psrs = run.iterations.map(it => it.psr);
    const last3 = psrs.slice(-3);
    const sigmaLast3 = last3.length >= 2 ? std(last3) : null;
    const ttt = thresh => {
      const idx = psrs.findIndex(v => v != null && v >= thresh);
      return idx === -1 ? '—' : String(run.iterations[idx].iter);
    };
    const shortTag = run.tag.split('_').slice(-1)[0];
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:${runColor(ri)}">${shortTag}</td>
      <td class="num">${fmtPct(run.peak_psr)}</td>
      <td class="num">${fmtPct(run.peak_centered)}</td>
      <td class="num">${fmtPct(run.iter_final_psr)}</td>
      <td class="num">${run.collapse_count ?? '—'}</td>
      <td class="num">${run.recovery_count ?? '—'}</td>
      <td class="num">${sigmaLast3 != null ? (sigmaLast3*100).toFixed(1)+'pp' : '—'}</td>
      <td class="num">${ttt(0.60)}</td>
      <td class="num">${ttt(0.80)}</td>`;
    summaryTbody.appendChild(tr);
  });
  summaryCard.querySelector('table').appendChild(summaryTbody);
  block.appendChild(summaryCard);

  // -- Outcome trajectories: PSR + Centered side-by-side (with median ribbon)
  const trajGrid = document.createElement('div');
  trajGrid.className = 'grid2';
  block.appendChild(trajGrid);

  for (const [metricKey, label, yMax] of [['psr', 'Population Success Rate', 1], ['centered', 'Centered Landing Rate', 1]]) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<h3>${label} across iterations</h3><div class="chart-box"><canvas></canvas></div>`;
    trajGrid.appendChild(card);
    const canvas = card.querySelector('canvas');

    // Build median ribbon datasets
    const ribbonDatasets = (() => {
      const uppers = [], lowers = [], meds = [];
      for (let i = 1; i <= maxIter; i++) {
        const vals = model.runs.map(r => {
          const it = r.iterations.find(x => x.iter === i);
          return it ? it[metricKey] : null;
        }).filter(v => v != null);
        const sorted = vals.slice().sort((a,b) => a-b);
        const p25 = sorted[Math.floor(sorted.length*0.25)] ?? null;
        const p75 = sorted[Math.floor(sorted.length*0.75)] ?? null;
        const med = median(vals);
        uppers.push({x:i, y:p75}); lowers.push({x:i, y:p25}); meds.push({x:i, y:med});
      }
      return [
        {label:'_p75', data:uppers, borderWidth:0, pointRadius:0, fill:'+1',
         backgroundColor:'rgba(255,255,255,0.07)', tension:0.2, spanGaps:true},
        {label:'_p25', data:lowers, borderWidth:0, pointRadius:0, fill:false, tension:0.2, spanGaps:true},
        {label:'median', data:meds, borderColor:'rgba(255,255,255,0.5)', borderWidth:2.5,
         borderDash:[5,3], pointRadius:0, fill:false, tension:0.2, spanGaps:true},
      ];
    })();

    new Chart(canvas, {
      type: 'line',
      data: {
        datasets: [
          ...model.runs.map((r, ri) => ({
            label: r.tag.split('_').slice(-1)[0],
            borderColor: runColor(ri),
            backgroundColor: runColor(ri) + '33',
            data: r.iterations.map(it => ({x: it.iter, y: it[metricKey]})),
            fill: false, tension: 0.2, pointRadius: 4, borderWidth: 2,
          })),
          ...ribbonDatasets,
        ]
      },
      options: {
        scales: {
          x: { type: 'linear', title: {display:true, text:'Iteration'}, ticks: {stepSize:1} },
          y: { title:{display:true, text:'Rate'}, min:0, max:yMax }
        },
        plugins: {
          legend: {
            labels: {
              color:'#ccc',
              filter: item => !item.text.startsWith('_'),
            }
          }
        },
        animation: false,
      }
    });
  }

  // -- Terminal mode stacked bars: one chart per run (small multiples)
  const termCard = document.createElement('div');
  termCard.className = 'card';
  termCard.innerHTML = '<h3>Terminal mode distribution per iteration</h3>';
  block.appendChild(termCard);
  const termGrid = document.createElement('div');
  termGrid.style.display = 'grid';
  termGrid.style.gridTemplateColumns = `repeat(${Math.min(model.runs.length, 2)}, 1fr)`;
  termGrid.style.gap = '14px';
  termCard.appendChild(termGrid);

  // MOD: non-centered landings use blue hue family (Option B)
  // FIX: added landed_off_centered_timeout entry
  const TERM_COLORS = {
    landed_centered:              '#2ca02c',
    landed_off_centered:          '#1f77b4',
    landed_but_slid_into_valley:  '#186499',
    landed_off_centered_timeout:  '#1A6BA4',
    crashed:                      '#d62728',
    out_of_bounds:                '#9467bd',
    hover_timeout:                '#ff7f0e',
  };

  model.runs.forEach((r, ri) => {
    const sub = document.createElement('div');
    sub.innerHTML = `<div class="small">${r.tag.split('_').slice(-1)[0]}</div>
                     <div class="chart-box"><canvas></canvas></div>`;
    termGrid.appendChild(sub);
    const c = sub.querySelector('canvas');
    new Chart(c, {
      type: 'bar',
      data: {
        labels: r.iterations.map(it => it.iter),
        datasets: DATA.terminal_modes.map(mode => ({
          label: mode,
          data: r.iterations.map(it => (it[modeKey(mode)] || 0) * 100),
          backgroundColor: TERM_COLORS[mode] || '#888',
        }))
      },
      options: {
        scales: { x: {stacked:true, title:{display:true,text:'Iteration'}},
                  y: {stacked:true, max:100, title:{display:true,text:'% of episodes'}} },
        plugins: { legend: {labels:{color:'#ccc', boxWidth:10}, position:'bottom'} },
        animation:false,
      }
    });
  });

  // ---------------- Section 2 header ----------------

  const t2 = document.createElement('div');
  t2.innerHTML = '<span class="tier-header tier2">Tier 2 — Orchestration Health</span>';
  block.appendChild(t2);

  // -- Validator verdict timeline (with ΔPSR sign row)
  const vcCard = document.createElement('div');
  vcCard.className = 'card';
  vcCard.innerHTML = '<h3>Validator verdict per iteration</h3>';
  block.appendChild(vcCard);
  const vtbl = document.createElement('table');
  let header = '<thead><tr><th>Run</th>';
  for (let i = 1; i <= maxIter; i++) header += `<th>iter ${i}</th>`;
  header += '</tr></thead>';
  vtbl.innerHTML = header;
  const tbody = document.createElement('tbody');
  model.runs.forEach(r => {
    let row = `<tr><td>${r.tag.split('_').slice(-1)[0]}</td>`;
    for (let i = 1; i <= maxIter; i++) {
      const it = r.iterations.find(x => x.iter === i);
      const status = it ? (it.validator_status || 'Unparsed') : '';
      row += `<td>${status ? `<span class="${statusClass(status)}">${status}</span>` : '—'}</td>`;
    }
    row += '</tr>';
    tbody.innerHTML += row;
  });

  // ΔPSR sign row
  const signRow = document.createElement('tr');
  signRow.innerHTML = `<td style="color:#888;font-size:11px">Δ PSR</td>`;
  for (let i = 1; i <= maxIter; i++) {
    const signs = model.runs.map(r => {
      const cur  = r.iterations.find(x => x.iter === i);
      const prev = r.iterations.find(x => x.iter === i-1);
      if (!cur || !prev || cur.psr == null || prev.psr == null) return null;
      return cur.psr > prev.psr + 0.005 ? '↑' : cur.psr < prev.psr - 0.005 ? '↓' : '~';
    }).filter(Boolean);
    const up = signs.filter(s => s==='↑').length;
    const dn = signs.filter(s => s==='↓').length;
    const cell = i===1 ? '—'
      : up > dn ? `<span style="color:#59a14f">↑${up}</span>`
      : dn > up ? `<span style="color:#e15759">↓${dn}</span>`
      : `<span style="color:#888">~</span>`;
    signRow.innerHTML += `<td style="text-align:center;font-size:12px">${cell}</td>`;
  }
  tbody.appendChild(signRow);

  vtbl.appendChild(tbody);
  vcCard.appendChild(vtbl);

  // -- Verdict–Outcome alignment chart
  (function renderAlignmentChart() {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = '<h3>Verdict–Outcome Alignment <span class="small">(% iterations where verdict sign matched ΔPSR sign)</span></h3><div class="chart-box" style="height:160px"><canvas></canvas></div>';
    block.appendChild(card);

    const POSITIVE = new Set(['Validated','Confirmed','ProductiveDeviation','Mixed']);
    const NEGATIVE = new Set(['Regressed','Refuted','GoodhartTrap']);

    const labels = [], values = [], colors = [];
    model.runs.forEach((run, ri) => {
      let correct = 0, total = 0;
      run.iterations.forEach(it => {
        const prev = run.iterations.find(x => x.iter === it.iter-1);
        if (!prev || it.psr == null || prev.psr == null) return;
        const deltaUp = it.psr > prev.psr + 0.005;
        const v = it.validator_status;
        if (!POSITIVE.has(v) && !NEGATIVE.has(v)) return;
        total++;
        const verdictPos = POSITIVE.has(v);
        if (verdictPos === deltaUp) correct++;
      });
      const pct = total > 0 ? correct/total : null;
      labels.push(run.tag.split('_').slice(-1)[0]);
      values.push(pct != null ? Math.round(pct*100) : null);
      colors.push(pct==null?'#444': pct>=0.6?'#59a14f': pct>=0.4?'#e6c46e':'#e15759');
    });

    new Chart(card.querySelector('canvas'), {
      type: 'bar',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3 }] },
      options: {
        indexAxis: 'y',
        scales: {
          x: { min:0, max:100, title:{display:true,text:'% aligned'},
               ticks:{callback:v=>v+'%'},
               grid: { color: ctx => ctx.tick.value===50?'#555':'#1f2229' } },
          y: { ticks: { color: labels.map((_,i)=>runColor(i)) } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.raw ?? '—'}% aligned` } },
        },
        animation: false,
      }
    });
  })();

  // -- Strategist behaviour: proposal types per iter, stacked
  const stratGrid = document.createElement('div');
  stratGrid.className = 'grid2';
  block.appendChild(stratGrid);

  const propCard = document.createElement('div');
  propCard.className = 'card';
  propCard.innerHTML = '<h3>Proposal types per iteration (mean across runs)</h3><div class="chart-box"><canvas></canvas></div>';
  stratGrid.appendChild(propCard);
  const propData = {modification:[], addition:[], cluster:[], unknown:[]};
  for (let i = 1; i <= maxIter; i++) {
    for (const t of DATA.proposal_types) {
      const vals = model.runs.map(r => {
        const x = r.iterations.find(y => y.iter === i);
        return x ? x['prop_' + t] : 0;
      });
      propData[t].push(vals.reduce((a,b) => a+b, 0) / vals.length);
    }
  }
  new Chart(propCard.querySelector('canvas'), {
    type:'bar',
    data:{
      labels: itLabels,
      datasets:[
        {label:'modification', data:propData.modification, backgroundColor:'#4e79a7'},
        {label:'addition',     data:propData.addition,     backgroundColor:'#59a14f'},
        {label:'cluster',      data:propData.cluster,      backgroundColor:'#edc948'},
        {label:'unknown',      data:propData.unknown,      backgroundColor:'#888'},
      ]
    },
    options:{
      scales:{x:{stacked:true, title:{display:true,text:'Iteration'}},
               y:{stacked:true, title:{display:true,text:'Count (mean)'}}},
      plugins:{legend:{labels:{color:'#ccc'}}},
      animation:false,
    }
  });

  // Excisions scatter
  const exCard = document.createElement('div');
  exCard.className = 'card';
  exCard.innerHTML = '<h3>Excisions per iteration (AST-verified)</h3><div class="chart-box"><canvas></canvas></div>';
  stratGrid.appendChild(exCard);

  const collisionMap = {};
  model.runs.forEach((r, ri) => {
    r.iterations.forEach(it => {
      const key = `${it.iter},${it.code?.n_excised ?? null}`;
      if (!collisionMap[key]) collisionMap[key] = [];
      collisionMap[key].push(ri);
    });
  });

  const exDatasets = model.runs.map((r, ri) => ({
    label: r.tag.split('_').slice(-1)[0],
    borderColor: runColor(ri),
    backgroundColor: runColor(ri),
    data: r.iterations.map(it => {
      const nEx = it.code?.n_excised ?? null;
      const key = `${it.iter},${nEx}`;
      const runsAtThisPoint = collisionMap[key];
      const n = runsAtThisPoint.length;
      let xOffset = 0;
      if (n > 1) {
        const posInGroup = runsAtThisPoint.indexOf(ri);
        xOffset = (posInGroup - (n - 1) / 2) * 0.18;
      }
      return { x: it.iter + xOffset, y: nEx };
    }),
    pointRadius: 6,
  }));

  new Chart(exCard.querySelector('canvas'), {
    type: 'scatter',
    data: { datasets: exDatasets },
    options: {
      scales: {
        x: { type: 'linear', title: {display: true, text: 'Iteration'}, ticks: {stepSize: 1} },
        y: { title: {display: true, text: 'Excisions'}, min: 0 }
      },
      plugins: { legend: { labels: { color: '#ccc' } } },
      animation: false,
    }
  });

  // -- Component flags: per-run line charts for n_optimal and n_traitor
  const flagGrid = document.createElement('div');
  flagGrid.className = 'card grid2';
  block.appendChild(flagGrid);

  for (const [key, label, color] of [
    ['n_optimal','Optimal Components per Iteration','#59a14f'],
    ['n_traitor','Traitor Components per Iteration','#e15759'],
  ]) {
    const box = document.createElement('div');
    box.innerHTML = `<h3>${label}</h3><div class="chart-box"><canvas></canvas></div>`;
    flagGrid.appendChild(box);
    new Chart(box.querySelector('canvas'), {
      type: 'line',
      data: { datasets: model.runs.map((r, ri) => ({
        label: r.tag.split('_').slice(-1)[0],
        borderColor: runColor(ri), backgroundColor: runColor(ri)+'33',
        data: r.iterations.map(it => ({x:it.iter, y:it[key] ?? null})),
        fill:false, tension:0.1, pointRadius:4, borderWidth:2, spanGaps:true,
      }))},
      options: {
        scales: {
          x:{type:'linear',title:{display:true,text:'Iteration'},ticks:{stepSize:1}},
          y:{title:{display:true,text:'Count'},min:0,ticks:{stepSize:1}},
        },
        plugins: { legend: { labels: {color:'#ccc', boxWidth:10} } },
        animation:false,
      }
    });
  }

  // -- Objective Alignment ρ scatter (with weak-alignment reference line)
  const rhoCard = document.createElement('div');
  rhoCard.className = 'card';
  rhoCard.innerHTML = '<h3>Objective Alignment ρ <span class="small">(point-biserial corr of reward with success)</span></h3><div class="chart-box"><canvas></canvas></div>';
  block.appendChild(rhoCard);
  new Chart(rhoCard.querySelector('canvas'), {
    type: 'scatter',
    data: { datasets: [
      ...model.runs.map((r, ri) => ({
        label: r.tag.split('_').slice(-1)[0],
        backgroundColor: runColor(ri),
        data: r.iterations.map(it => ({x:it.iter, y:it.rho})),
        pointRadius: 4,
      })),
      {
        label:'weak alignment (0.3)',
        data: [{x:1,y:0.3},{x:maxIter,y:0.3}],
        type:'line', borderColor:'#e6c46e', borderWidth:1, borderDash:[4,4],
        pointRadius:0, fill:false,
      },
    ]},
    options: {
      scales: {
        x: { type:'linear', title:{display:true,text:'Iteration'}, ticks:{stepSize:1} },
        y: { title:{display:true,text:'ρ'} }
      },
      plugins: { legend: { labels: { color:'#ccc', boxWidth:10 } } },
      animation: false,
    }
  });

  // -- Per-iteration detail (all runs) — collapsible
  const drill = document.createElement('details');
  drill.className = 'card';
  drill.innerHTML = '<summary>Per-iteration detail (all runs)</summary>';
  block.appendChild(drill);
  model.runs.forEach(run => {
    const sec = document.createElement('div');
    sec.style.marginTop = '10px';
    sec.innerHTML = `<div class="small" style="margin-bottom:4px">${run.tag.split('_').slice(-1)[0]}</div>`;
    const tbl = document.createElement('table');
    tbl.innerHTML = '<thead><tr><th>Iter</th><th>PSR</th><th>Centered</th><th>ρ</th><th>Cross-Seed CV</th><th>Validator</th><th>Excisions</th><th>Intra-CV</th><th>DeadWt</th><th>HidDep</th><th>Noisy</th><th>Warnings</th></tr></thead>';
    const tb2 = document.createElement('tbody');
    run.iterations.forEach(it => {
      const w = it.warnings && it.warnings.length ? `<span class="warn">${it.warnings.join(', ')}</span>` : '—';
      tb2.innerHTML += `<tr>
        <td>${it.iter}</td>
        <td class="num">${fmt(it.psr)}</td>
        <td class="num">${fmt(it.centered)}</td>
        <td class="num">${fmt(it.rho)}</td>
        <td class="num">${fmt(it.cross_seed_cv)}</td>
        <td>${it.validator_status ? `<span class="${statusClass(it.validator_status)}">${it.validator_status}</span>` : '—'}</td>
        <td class="num">${it.code?.n_excised != null ? it.code.n_excised : '—'}</td>
        <td class="num">${fmt(it.intra_cv)}</td>
        <td class="num">${it.n_dead_weight ?? '—'}</td>
        <td class="num">${it.n_hidden_dependency ?? '—'}</td>
        <td class="num">${it.n_neutral_noisy ?? '—'}</td>
        <td class="small">${w}</td>
      </tr>`;
    });
    tbl.appendChild(tb2);
    sec.appendChild(tbl);
    drill.appendChild(sec);
  });
});

// FIX: modeKey updated to include landed_off_centered_timeout
function modeKey(termMode) {
  return {
    'landed_centered':             'centered',
    'landed_off_centered':         'off_centered',
    'landed_but_slid_into_valley': 'slid',
    'landed_off_centered_timeout': 'off_centered_timeout',
    'crashed':                     'crashed',
    'out_of_bounds':               'oob',
    'hover_timeout':               'hover_timeout',
  }[termMode];
}
</script>
</body>
</html>
"""

COMPUTE_COST_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Compute Cost — {LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        background: #0f1115; color: #e6e6e6; margin: 0; padding: 24px;
        font-size: 14px; }
  h1 { font-size: 22px; margin: 0 0 6px 0; }
  h2 { font-size: 16px; margin: 26px 0 8px 0; color: #a8c5f0;
        border-bottom: 1px solid #2a2d35; padding-bottom: 4px; }
  h3 { font-size: 14px; margin: 18px 0 6px 0; color: #d0d0d0; }
  .meta { color: #888; font-size: 12px; margin-bottom: 18px; }
  .card { background: #181a20; border: 1px solid #262931; border-radius: 8px;
         padding: 14px; margin: 8px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
  .chart-box { position: relative; height: 280px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #2a2d35; }
  th { color: #a8c5f0; font-weight: 600; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .small { color: #888; font-size: 12px; }
</style>
</head>
<body>
<h1>ARD Compute Cost</h1>
<div class="meta">
  Campaign: <code>{LABEL}</code>  •  Generated: <code id="ts"></code>
</div>
<div id="root"></div>

<script>
const DATA = {DATA_JSON};
const root = document.getElementById('root');
document.getElementById('ts').textContent = new Date().toISOString().replace('T', ' ').slice(0, 19);

const PHASE_ORDER = ['validator', 'strategist', 'organizer', 'research_lead', 'dispatcher', 'coder'];
const PHASE_COLORS = {
  validator:    '#e15759',
  strategist:   '#f28e2b',
  organizer:    '#edc948',
  research_lead:'#76b7b2',
  dispatcher:   '#b07aa1',
  coder:        '#4e79a7',
};

const RUN_COLORS = ['#4e79a7','#f28e2b','#59a14f','#e15759',
                    '#76b7b2','#edc948','#b07aa1','#ff9da7'];
function runColor(i) { return RUN_COLORS[i % RUN_COLORS.length]; }

function fmt(v, d=2) { if (v === null || v === undefined) return '—'; if (typeof v !== 'number') return v; return v.toFixed(d); }
function sum(arr) { return arr.reduce((a,b) => a + (b || 0), 0); }

// MOD: helper — split response_content into thinking_words vs response_words
// Uses word count (len(text.split())) as token estimate.
function apportionTokens(responseContent, thinkingTrace, genTokens) {
  // Use word-count ratios to apportion the real eval_count token budget.
  // This is more accurate than raw word counts because the tokenizer's
  // compression ratio is consistent within a single response.
  const thinkWords = thinkingTrace ? String(thinkingTrace).trim().split(/\s+/).filter(Boolean).length : 0;
  const respWords  = responseContent ? String(responseContent).trim().split(/\s+/).filter(Boolean).length : 0;
  const totalWords = thinkWords + respWords;
  if (totalWords === 0 || !genTokens) return {thinking: 0, response: genTokens || 0};
  const thinkRatio = thinkWords / totalWords;
  const thinkTokens = Math.round(genTokens * thinkRatio);
  const respTokens  = genTokens - thinkTokens;  // subtract so they sum exactly
  return {thinking: thinkTokens, response: respTokens};
}

DATA.models.forEach(model => {
  const block = document.createElement('div');
  root.appendChild(block);
  block.innerHTML = `<h2>${model.name} · ${model.n_runs} run${model.n_runs===1?'':'s'}</h2>`;

  const allRows = model.runs.flatMap(r => r.chat_rows);
  if (!allRows.length) {
    block.innerHTML += '<div class="card small">No ChatResponse_data.csv found for these runs.</div>';
    return;
  }

  // Per-phase totals across the whole campaign
  const phaseTotals = {};
  for (const p of PHASE_ORDER) {
    const rows = allRows.filter(r => r.phase === p);
    phaseTotals[p] = {
      n_calls: rows.length,
      total_s: sum(rows.map(r => r.total_s)),
      prompt_tokens: sum(rows.map(r => r.prompt_tokens)),
      gen_tokens: sum(rows.map(r => r.gen_tokens)),
      eval_s: sum(rows.map(r => r.eval_s)),
      prompt_eval_s: sum(rows.map(r => r.prompt_eval_s)),
    };
  }
  const grandTotal = {
    total_s: sum(Object.values(phaseTotals).map(p => p.total_s)),
    prompt_tokens: sum(Object.values(phaseTotals).map(p => p.prompt_tokens)),
    gen_tokens: sum(Object.values(phaseTotals).map(p => p.gen_tokens)),
  };

  // ---- Cost table per phase
  const tableCard = document.createElement('div');
  tableCard.className = 'card';
  tableCard.innerHTML = `<h3>Per-phase totals (sum across all runs &amp; iterations)</h3>`;
  const tbl = document.createElement('table');
  tbl.innerHTML = `<thead><tr>
    <th>Phase</th><th>Model</th><th>Calls</th>
    <th>Total time (s)</th><th>Prompt tok</th><th>Gen tok</th>
    <th>Gen tok/s</th><th>% of total time</th>
  </tr></thead>`;
  const tb = document.createElement('tbody');
  for (const p of PHASE_ORDER) {
    const t = phaseTotals[p];
    const rows = allRows.filter(r => r.phase === p);
    const phaseModel = rows.length ? rows[0].model : '—';
    const tokPerS = t.eval_s > 0 ? t.gen_tokens / t.eval_s : null;
    const pctTime = grandTotal.total_s > 0 ? (t.total_s / grandTotal.total_s * 100) : 0;
    tb.innerHTML += `<tr>
      <td>${p}</td>
      <td>${phaseModel}</td>
      <td class="num">${t.n_calls}</td>
      <td class="num">${fmt(t.total_s, 1)}</td>
      <td class="num">${t.prompt_tokens}</td>
      <td class="num">${t.gen_tokens}</td>
      <td class="num">${tokPerS !== null ? fmt(tokPerS, 1) : '—'}</td>
      <td class="num">${fmt(pctTime, 1)}%</td>
    </tr>`;
  }
  tb.innerHTML += `<tr style="border-top: 2px solid #2a2d35; font-weight:600">
    <td colspan="2">TOTAL</td>
    <td class="num">${allRows.length}</td>
    <td class="num">${fmt(grandTotal.total_s, 1)}</td>
    <td class="num">${grandTotal.prompt_tokens}</td>
    <td class="num">${grandTotal.gen_tokens}</td>
    <td></td><td></td>
  </tr>`;
  tbl.appendChild(tb);
  tableCard.appendChild(tbl);
  block.appendChild(tableCard);

  // ── Per-run cost summary ──────────────────────────────────────────────────
  const perRunCard = document.createElement('div');
  perRunCard.className = 'card';
  perRunCard.innerHTML = '<h3>Per-run cost summary</h3>';
  const prTbl = document.createElement('table');
  prTbl.innerHTML = `<thead><tr>
    <th>Run</th>
    <th>Total time (s)</th>
    <th>Prompt tok</th>
    <th>Gen tok</th>
    <th>Avg tok/s</th>
    <th>% of campaign wall time</th>
  </tr></thead>`;
  const prTb = document.createElement('tbody');

  const campaignTotalS = sum(model.runs.map(r => sum(r.chat_rows.map(x => x.total_s || 0))));

  model.runs.forEach((run, ri) => {
    const rows = run.chat_rows;
    const totalS    = sum(rows.map(x => x.total_s    || 0));
    const evalS     = sum(rows.map(x => x.eval_s     || 0));
    const promptTok = sum(rows.map(x => x.prompt_tokens || 0));
    const genTok    = sum(rows.map(x => x.gen_tokens  || 0));
    const tokPerS   = evalS > 0 ? genTok / evalS : null;
    const pct       = campaignTotalS > 0 ? (totalS / campaignTotalS * 100) : 0;
    const shortTag  = run.tag.split('_').slice(-1)[0];
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:${runColor(ri)}">${shortTag}</td>
      <td class="num">${fmt(totalS, 1)}</td>
      <td class="num">${promptTok.toLocaleString()}</td>
      <td class="num">${genTok.toLocaleString()}</td>
      <td class="num">${tokPerS !== null ? fmt(tokPerS, 1) : '—'}</td>
      <td class="num">${fmt(pct, 1)}%</td>`;
    prTb.appendChild(tr);
  });

  prTbl.appendChild(prTb);
  perRunCard.appendChild(prTbl);
  block.appendChild(perRunCard);

  // ── Cost-per-outcome ──────────────────────────────────────────────────────
  const coGrid = document.createElement('div');
  coGrid.className = 'card grid2';
  block.appendChild(coGrid);

  // ── Left: seconds per PSR-pp (horizontal bar, one bar per run) ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = '<h3>Wall time per PSR-pp delivered <span style="font-size:11px;color:#888">(lower = more efficient)</span></h3><div class="chart-box" style="height:180px"><canvas></canvas></div>';
    coGrid.appendChild(box);

    const labels = [], values = [], colors = [];
    model.runs.forEach((run, ri) => {
      const totalS  = sum(run.chat_rows.map(x => x.total_s || 0));
      const finalPSR = run.iter_final_psr;
      const psrPP   = finalPSR != null ? finalPSR * 100 : null;
      const secPerPP = (psrPP != null && psrPP > 0) ? totalS / psrPP : null;
      labels.push(run.tag.split('_').slice(-1)[0]);
      values.push(secPerPP != null ? +secPerPP.toFixed(1) : null);
      colors.push(secPerPP == null ? '#444'
        : secPerPP < 10  ? '#59a14f'
        : secPerPP < 20  ? '#e6c46e'
        : '#e15759');
    });

    new Chart(box.querySelector('canvas'), {
      type: 'bar',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3 }] },
      options: {
        indexAxis: 'y',
        scales: {
          x: { title: { display: true, text: 's / PSR-pp' }, min: 0 },
          y: { ticks: { color: labels.map((_,i) => runColor(i)) } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.raw ?? '—'} s per PSR percentage-point` } },
        },
        animation: false,
      }
    });
  })();

  // ── Right: PSR vs total wall time scatter (one dot per run) ──
  (function() {
    const box = document.createElement('div');
    box.innerHTML = '<h3>Final PSR vs total wall time <span style="font-size:11px;color:#888">(top-left = best)</span></h3><div class="chart-box" style="height:180px"><canvas></canvas></div>';
    coGrid.appendChild(box);

    const points = model.runs.map((run, ri) => ({
      x: sum(run.chat_rows.map(x => x.total_s || 0)),
      y: (run.iter_final_psr ?? 0) * 100,
      label: run.tag.split('_').slice(-1)[0],
      color: runColor(ri),
    }));

    new Chart(box.querySelector('canvas'), {
      type: 'scatter',
      data: {
        datasets: points.map(pt => ({
          label: pt.label,
          data: [{ x: pt.x, y: pt.y }],
          backgroundColor: pt.color,
          pointRadius: 8,
          pointHoverRadius: 10,
        }))
      },
      options: {
        scales: {
          x: { title: { display: true, text: 'Total wall time (s)' } },
          y: { title: { display: true, text: 'Final PSR (%)' }, min: 0, max: 100 },
        },
        plugins: {
          legend: { labels: { color: '#ccc', boxWidth: 10, font: { size: 11 } } },
          tooltip: { callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}% PSR in ${ctx.parsed.x.toFixed(0)}s`
          }},
        },
        animation: false,
      }
    });
  })();

  // ---- Row 1: Total time (left) + Gen tok/s scatter (right)
  // MOD: swapped positions — Gen tok/s now sits to the right of Total time
  const row1Grid = document.createElement('div');
  row1Grid.className = 'grid2';
  block.appendChild(row1Grid);

  // ── Per-run total wall time per iteration (line chart) ──
  const timeCard = document.createElement('div');
  timeCard.className = 'card';
  timeCard.innerHTML = '<h3>Total wall time per iteration (per run + median)</h3><div class="chart-box"><canvas></canvas></div>';
  row1Grid.appendChild(timeCard);

  const maxIter = Math.max(...allRows.map(r => r.iteration));

  const timeDatasets = model.runs.map((run, ri) => ({
    label: run.tag.split('_').slice(-1)[0],
    borderColor: runColor(ri),
    backgroundColor: runColor(ri) + '33',
    data: Array.from({length: maxIter}, (_, i) => {
      const iter = i + 1;
      const iterRows = run.chat_rows.filter(x => x.iteration === iter);
      const t = sum(iterRows.map(x => x.total_s || 0));
      return { x: iter, y: iterRows.length ? t : null };
    }),
    fill: false, tension: 0.2, pointRadius: 4, borderWidth: 2, spanGaps: true,
  }));

  const medianData = Array.from({length: maxIter}, (_, i) => {
    const iter = i + 1;
    const vals = model.runs.map(run => {
      const iterRows = run.chat_rows.filter(x => x.iteration === iter);
      return iterRows.length ? sum(iterRows.map(x => x.total_s || 0)) : null;
    }).filter(v => v != null).sort((a, b) => a - b);
    if (!vals.length) return { x: iter, y: null };
    const m = Math.floor(vals.length / 2);
    return { x: iter, y: vals.length % 2 ? vals[m] : (vals[m-1] + vals[m]) / 2 };
  });
  timeDatasets.push({
    label: 'median',
    borderColor: 'rgba(255,255,255,0.55)',
    backgroundColor: 'transparent',
    data: medianData,
    fill: false, tension: 0.2, pointRadius: 0, borderWidth: 2.5,
    borderDash: [5, 3], spanGaps: true,
  });

  new Chart(timeCard.querySelector('canvas'), {
    type: 'line',
    data: { datasets: timeDatasets },
    options: {
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Iteration' }, ticks: { stepSize: 1 } },
        y: { title: { display: true, text: 'Total time (s)' }, min: 0 },
      },
      plugins: { legend: { labels: { color: '#ccc', boxWidth: 10 } } },
      animation: false,
    }
  });

  // ---- MOD: Gen-tokens-per-second scatter moved here (right of time chart)
  const tpsCard = document.createElement('div');
  tpsCard.className = 'card';
  tpsCard.innerHTML = '<h3>Gen tokens / second per phase (all calls, scatter)</h3><div class="chart-box"><canvas></canvas></div>';
  row1Grid.appendChild(tpsCard);
  const tpsData = PHASE_ORDER.map((p, pi) => {
    const points = allRows
      .filter(r => r.phase === p && r.eval_s > 0)
      .map(r => ({x: pi + 1 + (Math.random() - 0.5) * 0.4, y: r.gen_tokens / r.eval_s}));
    return {label:p, data:points, backgroundColor:PHASE_COLORS[p], pointRadius:5};
  });
  new Chart(tpsCard.querySelector('canvas'), {
    type:'scatter',
    data:{datasets: tpsData},
    options:{
      scales:{
        x:{ min:0.5, max:6.5, ticks:{
              callback: (v) => PHASE_ORDER[Math.round(v)-1] || '',
              stepSize:1
            }, title:{display:true,text:'Phase'} },
        y:{title:{display:true,text:'tokens / sec'}}
      },
      plugins:{legend:{display:false}}, animation:false,
    }
  });

  // ── Phase time per run (mean seconds per iteration) ──────────────────────
  const phaseRunCard = document.createElement('div');
  phaseRunCard.className = 'card';
  phaseRunCard.innerHTML = '<h3>Phase avg time per iteration (seconds) — per run</h3>';
  const prtTbl = document.createElement('table');

  const runTags = model.runs.map(r => r.tag.split('_').slice(-1)[0]);
  prtTbl.innerHTML = `<thead><tr>
    <th>Phase</th>
    ${runTags.map((t, i) => `<th style="color:${runColor(i)}">${t}</th>`).join('')}
    <th style="color:#888">median</th>
  </tr></thead>`;

  const prtTb = document.createElement('tbody');
  PHASE_ORDER.forEach(phase => {
    const avgPerRun = model.runs.map(run => {
      const rows = run.chat_rows.filter(x => x.phase === phase);
      if (!rows.length) return null;
      const byIter = {};
      rows.forEach(x => { byIter[x.iteration] = (byIter[x.iteration] || 0) + (x.total_s || 0); });
      const iterTotals = Object.values(byIter);
      return iterTotals.length ? sum(iterTotals) / iterTotals.length : null;
    });

    const validVals = avgPerRun.filter(v => v != null).sort((a, b) => a - b);
    const med = validVals.length
      ? (validVals.length % 2
        ? validVals[Math.floor(validVals.length / 2)]
        : (validVals[Math.floor(validVals.length/2)-1] + validVals[Math.floor(validVals.length/2)]) / 2)
      : null;

    const maxV = validVals.length ? validVals[validVals.length - 1] : 0;
    const minV = validVals.length ? validVals[0] : 0;
    const highVariance = minV > 0 && (maxV / minV) > 1.5;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:${PHASE_COLORS[phase] || '#ccc'}">${phase}</td>
      ${avgPerRun.map(v =>
        `<td class="num" style="${highVariance ? 'color:#e6c46e' : ''}">${v != null ? fmt(v, 1) : '—'}</td>`
      ).join('')}
      <td class="num" style="color:#888">${med != null ? fmt(med, 1) : '—'}</td>`;
    prtTb.appendChild(tr);
  });

  prtTbl.appendChild(prtTb);
  phaseRunCard.appendChild(prtTbl);
  const phaseVarNote = document.createElement('div');
  phaseVarNote.className = 'small';
  phaseVarNote.style.marginTop = '6px';
  phaseVarNote.textContent = 'Yellow = max/min ratio > 1.5× across runs (high phase-level variance)';
  phaseRunCard.appendChild(phaseVarNote);
  block.appendChild(phaseRunCard);

  // ---- Row 2: Prompt size growth (left) + Response/Thinking output size (right)
  // MOD: Prompt size now full-width row below, paired with new Response size chart
  const row2Grid = document.createElement('div');
  row2Grid.className = 'grid2';
  block.appendChild(row2Grid);

  // ---- Prompt size growth per phase, per iteration (line per phase)
  const promptCard = document.createElement('div');
  promptCard.className = 'card';
  promptCard.innerHTML = '<h3>Prompt size growth (mean across runs, tokens)</h3><div class="chart-box"><canvas></canvas></div>';
  row2Grid.appendChild(promptCard);
  const promptDatasets = PHASE_ORDER.map(p => {
    const data = [];
    for (let i = 1; i <= maxIter; i++) {
      const vals = model.runs.map(r => {
        const row = r.chat_rows.find(x => x.iteration === i && x.phase === p);
        return row ? row.prompt_tokens : null;
      }).filter(v => v !== null);
      // FIX: use {x,y} points + type:'linear' on x-axis to prevent axis drop
      data.push({x:i, y: vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : null});
    }
    return {label:p, data, borderColor:PHASE_COLORS[p], tension:0.2, pointRadius:3, fill:false, borderWidth:2};
  });

  // Add faint per-run lines (sum of prompt tokens across all phases per iteration)
  const promptPerRunDatasets = model.runs.map((run, ri) => {
    const data = [];
    for (let i = 1; i <= maxIter; i++) {
      const rows = run.chat_rows.filter(x => x.iteration === i);
      const total = sum(rows.map(x => x.prompt_tokens || 0));
      data.push({ x: i, y: rows.length ? total : null });
    }
    return {
      label: `_run${ri}`,
      data,
      borderColor: runColor(ri) + '44',
      borderWidth: 1,
      pointRadius: 0,
      fill: false,
      tension: 0.2,
      spanGaps: true,
    };
  });

  new Chart(promptCard.querySelector('canvas'), {
    type:'line',
    data:{datasets: [...promptPerRunDatasets, ...promptDatasets]},
    options:{
      scales:{
        x:{ type:'linear', title:{display:true,text:'Iteration'}, ticks:{stepSize:1} },
        y:{ title:{display:true,text:'Prompt tokens'} }
      },
      plugins:{
        legend:{
          labels:{
            color:'#ccc',
            filter: item => !item.text.startsWith('_'),
          }
        }
      },
      animation:false,
    }
  });

  // ---- MOD: New — Response/Thinking output size growth per phase
  // Single line per phase for total gen_tokens (like Prompt size chart).
  // Tooltip shows estimated response_words vs thinking_words breakdown.
  const responseCard = document.createElement('div');
  responseCard.className = 'card';
  responseCard.innerHTML = '<h3>Response output size growth (mean across runs, gen tokens)</h3><div class="chart-box"><canvas></canvas></div>';
  row2Grid.appendChild(responseCard);

  // Pre-compute per-iteration, per-phase: mean gen_tokens, mean thinking_words, mean response_words
  const responseDatasets = PHASE_ORDER.map(p => {
    const data = [];
    const thinkingByIter = [];
    const responseByIter = [];
    const thinkMultByIter = [];
    for (let i = 1; i <= maxIter; i++) {
      const rows = model.runs.flatMap(r =>
        r.chat_rows.filter(x => x.iteration === i && x.phase === p)
      );

      // mean generated tokens
      const genVals = rows.map(r => r.gen_tokens).filter(v => v != null);
      const meanGen = genVals.length ? genVals.reduce((a,b)=>a+b,0)/genVals.length : null;

      // estimated thinking & response tokens
      const thinkVals = rows.map(r => apportionTokens(r.response_content, r.thinking_trace, r.gen_tokens).thinking);
      const respVals  = rows.map(r => apportionTokens(r.response_content, r.thinking_trace, r.gen_tokens).response);
      const meanThink = thinkVals.length ? thinkVals.reduce((a,b)=>a+b,0)/thinkVals.length : 0;
      const meanResp  = respVals.length  ? respVals.reduce((a,b)=>a+b,0)/respVals.length   : 0;

      // --- compute multiple for this iteration (no lag) ---
      const multiple = (meanResp > 0) ? (meanThink / meanResp) : null;


      data.push({x: i, y: meanGen});
      thinkingByIter.push(meanThink);
      responseByIter.push(meanResp);
      thinkMultByIter.push(multiple);
    }
    return {
      label: p,
      data,
      borderColor: PHASE_COLORS[p],
      backgroundColor: PHASE_COLORS[p] + '22',
      tension: 0.2,
      pointRadius: 4,
      fill: false,
      borderWidth: 2,
      // Store breakdown for tooltip access
      _thinkingEst: thinkingByIter,
      _responseEst: responseByIter,
      _thinkMult: thinkMultByIter
    };
  });

  // Add faint per-run lines (sum of gen tokens across all phases per iteration)
  const responsePerRunDatasets = model.runs.map((run, ri) => {
    const data = [];
    for (let i = 1; i <= maxIter; i++) {
      const rows = run.chat_rows.filter(x => x.iteration === i);
      const total = sum(rows.map(x => x.gen_tokens || 0));
      data.push({ x: i, y: rows.length ? total : null });
    }
    return {
      label: `_run${ri}`,
      data,
      borderColor: runColor(ri) + '44',
      borderWidth: 1,
      pointRadius: 0,
      fill: false,
      tension: 0.2,
      spanGaps: true,
    };
  });

  new Chart(responseCard.querySelector('canvas'), {
    type:'line',
    data:{datasets: [...responsePerRunDatasets, ...responseDatasets]},
    options:{
      // FIX: add type:'linear' to x-axis so axis labels are rendered
      scales:{
        x:{ type:'linear', title:{display:true,text:'Iteration'}, ticks:{stepSize:1} },
        y:{ title:{display:true,text:'Gen tokens (total)'} }
      },
      plugins:{
        legend:{
          labels:{
            color:'#ccc',
            filter: item => !item.text.startsWith('_'),
          }
        },
        tooltip:{
          callbacks:{
            // MOD: show thinking vs response word-count estimates on hover
            afterBody: function(items) {
                const lines = [];
                items.forEach(item => {
                    const ds = item.dataset;
                    const idx = item.dataIndex;
                    const thinkEst = ds._thinkingEst ? Math.round(ds._thinkingEst[idx]) : null;
                    const respEst  = ds._responseEst  ? Math.round(ds._responseEst[idx])  : null;
                    const mult     = ds._thinkMult    ? ds._thinkMult[idx] : null;
                    if (thinkEst !== null) {
                        lines.push(`  ↳ thinking ~${thinkEst} tok`);
                        lines.push(`  ↳ response ~${respEst} tok`);
                        // Only show multiple if there's actually thinking content
                        if (mult !== null && thinkEst > 0) {
                            lines.push(`  ↳ think/resp ${mult.toFixed(1)}×`);
                        } else if (thinkEst === 0) {
                            lines.push(`  ↳ no thinking trace`);
                        }
                    }
                });
                return lines;
            }
          }
        }
      },
      animation:false,
    }
  });
});
</script>
</body>
</html>
"""


def write_dashboards(payload: dict, label: str, output_dir: Path):
    """Render all three HTML dashboards from a single payload."""
    data_json = json.dumps(payload, default=str)

    pp = (output_dir / "pipeline_performance.html")
    pp.write_text(
        PIPELINE_PERFORMANCE_TEMPLATE
        .replace("{LABEL}", label)
        .replace("{DATA_JSON}", data_json)
    )

    cc = (output_dir / "compute_cost.html")
    cc.write_text(
        COMPUTE_COST_TEMPLATE
        .replace("{LABEL}", label)
        .replace("{DATA_JSON}", data_json)
    )

    ce = (output_dir / "code_evolution.html")
    ce.write_text(
        CODE_EVOLUTION_TEMPLATE
        .replace("{LABEL}", label)
        .replace("{DATA_JSON}", data_json)
    )

    return pp, cc, ce

# ===========================================================================
# CLI
# ===========================================================================

def main():
    _DEFAULT_EXPERIMENT_DIR = Path(__file__).parent.parent / 'experiments'
    ap = argparse.ArgumentParser(description="Aggregate ARD ablation runs → dashboards + CSVs")
    ap.add_argument("--experiments-root", type=Path, default=_DEFAULT_EXPERIMENT_DIR,
                    help="Path to the experiments/ directory")
    ap.add_argument("--campaign-glob", required=True,
                    help="Glob relative to experiments-root matching campaign folders")
    ap.add_argument("--label", default="",
                    help="Human-readable label (used in filenames + dashboards)")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Output directory (default: post_hoc_analysis/reports/single_campaign/{label})")
    # Values for AggregationConfig init
    ap.add_argument("--established_floor", type=float, default=0.4)
    ap.add_argument("--regression_k", type=float, default=2.0)
    ap.add_argument("--regression_min_floor_pp", type=float, default=10.0)
    ap.add_argument("--recovery_window", type=int, default=0)
    ap.add_argument("--primary-metric", default="psr",
                    choices=["psr", "centered"])
    ap.add_argument("--force", action="store_true", default=False,
                    help="Proceed even if runs have mismatched config fingerprints")
    args = ap.parse_args()

    label = args.label or args.campaign_glob.replace("*", "X").replace("/", "_")[:60]
    output_dir = args.output_dir or (
        Path("post_hoc_analysis") / "reports" / "single_campaign" / label
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = AggregationConfig(
        established_floor=args.established_floor,
        regression_k=args.regression_k,
        regression_min_floor_pp=args.regression_min_floor_pp,
        recovery_window=args.recovery_window,
        primary_landing_metric=args.primary_metric,
    )

    print(f"Discovering campaigns under {args.experiments_root} matching '{args.campaign_glob}'...")
    campaigns = discover_campaigns(args.experiments_root, args.campaign_glob)
    if not campaigns:
        print("  ERROR: no matching campaign directories found.", file=sys.stderr)
        sys.exit(1)
    print(f"  Found {len(campaigns)} campaign(s)")

    run_summaries = []
    chat_rows_by_run: dict = {}
    regression_by_tag: dict[str, dict] = {}
    _run_manifests: list[dict] = []

    for c in campaigns:
        try:
            from extract_cognition import RunPaths
            paths = RunPaths(c)
            summary = load_run(c, cfg)
            run_summaries.append(summary)
            regression_by_tag[c.name] = _load_regression_stats(c)
            chat_rows_by_run[c.name] = load_chat_responses(
                paths.chat_response_path,
                cognition_json_dir=paths.cognition_json_dir)

            print(f"  loaded {c.name}: "
                  f"(iters={summary.iteration_count}, peak_psr={summary.peak_psr}, "
                  f"warnings={summary.iterations_with_warnings})")
        except Exception as exc:
            print(f"  WARNING: skipping {c.name}: {exc}", file=sys.stderr)

        # Read run manifest independently — a missing/broken manifest never skips the run
        _mdata: dict = {"campaign": c.name, "fingerprint": None, "comparability": None, "labels": None}
        try:
            _subdirs = [p for p in c.iterdir() if p.is_dir()]
            if len(_subdirs) == 1:
                _mp = _subdirs[0] / "config_snapshot" / "run_manifest.json"
                if _mp.is_file():
                    with _mp.open() as _mf:
                        _m = json.load(_mf)
                    _mdata = {
                        "campaign":      c.name,
                        "fingerprint":   _m.get("config_fingerprint"),
                        "comparability": _m.get("comparability"),
                        "labels":        _m.get("labels"),
                    }
        except Exception:
            pass
        _run_manifests.append(_mdata)

    if not run_summaries:
        print("ERROR: no runs loaded successfully.", file=sys.stderr)
        sys.exit(1)

    # --- Comparability gate (Tier 2) ---
    try:
        from src.run_manifest import diff_comparability as _diff_comp, short as _short_fp
        _fingerprints = [m["fingerprint"] for m in _run_manifests]
        _distinct_fps = set(fp for fp in _fingerprints if fp is not None)
        _has_none = any(fp is None for fp in _fingerprints)
        _config_fp_output = None
        _comparability_output = None
        _labels_output = None

        if _has_none or len(_distinct_fps) > 1:
            print("\nERROR: Runs have mismatched or missing config fingerprints!", file=sys.stderr)
            _ref = next((m for m in _run_manifests if m["comparability"] is not None), None)
            print(f"  {'Campaign':<45}  {'Fingerprint':>14}  Diff fields", file=sys.stderr)
            for _m in _run_manifests:
                _fp_str = _short_fp(_m["fingerprint"]) if _m["fingerprint"] else "MISSING"
                _diffs = []
                if _ref and _m["comparability"] is not None and _m is not _ref:
                    _diffs = _diff_comp(_ref["comparability"], _m["comparability"])
                _diff_str = ", ".join(d[0] for d in _diffs) if _diffs else ""
                print(f"  {_m['campaign']:<45}  {_fp_str:>14}  {_diff_str}", file=sys.stderr)

            if not args.force:
                sys.exit(1)
            else:
                print("\nWARNING: --force specified; proceeding with mixed fingerprints.", file=sys.stderr)
                _config_fp_output = "FORCED_MIXED"
                _comparability_output = "FORCED_MIXED"
        else:
            _config_fp_output = list(_distinct_fps)[0] if _distinct_fps else None
            _ref = next((m for m in _run_manifests if m["comparability"] is not None), None)
            if _ref:
                _comparability_output = _ref["comparability"]
                _labels_output = _ref["labels"]
    except ImportError:
        _config_fp_output = None
        _comparability_output = None
        _labels_output = None

    # Group by strategist model + campaign signature
    from collections import defaultdict
    groups: dict[str, list] = defaultdict(list)
    for run in run_summaries:
        groups[run.strategist_model].append(run)

    model_summaries = [
        aggregate_across_runs(runs, campaign_signature=label)
        for runs in groups.values()
    ]

    # Write CSVs
    iter_path = output_dir / "iterations_long.csv"
    runs_path = output_dir / "runs_summary.csv"
    cross_path = output_dir / "cross_run_summary.csv"
    audit_path = output_dir / "aggregated_data.json"

    write_iterations_csv(model_summaries, iter_path)
    write_runs_csv(model_summaries, runs_path, regression_by_tag)
    write_cross_run_summary_csv(model_summaries, cross_path, regression_by_tag)
    write_audit_json(model_summaries, audit_path)

    # Stamp comparability fingerprint into the audit JSON for downstream consumers
    if _config_fp_output is not None:
        try:
            with audit_path.open() as _af:
                _audit = json.load(_af)
            _audit["config_fingerprint"] = _config_fp_output
            if _comparability_output is not None:
                _audit["comparability"] = _comparability_output
            if _labels_output is not None:
                _audit["labels"] = _labels_output
            with audit_path.open("w") as _af:
                json.dump(_audit, _af, indent=2, default=str)
        except Exception as _stamp_exc:
            print(f"WARNING: could not stamp fingerprint into audit JSON: {_stamp_exc}", file=sys.stderr)

    # Build payload and write dashboards
    payload = build_dashboard_payload(model_summaries, chat_rows_by_run, regression_by_tag)
    pp, cc, ce = write_dashboards(payload, label, output_dir)

    print(f"\nOutputs written to {output_dir}/")
    print(f"  {iter_path.name}")
    print(f"  {runs_path.name}")
    print(f"  {cross_path.name}")
    print(f"  {audit_path.name}")
    print(f"  {pp.name}")
    print(f"  {cc.name}")
    print(f"  {ce.name}")


if __name__ == "__main__":
    main()