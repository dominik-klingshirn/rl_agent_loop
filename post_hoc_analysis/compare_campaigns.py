#!/usr/bin/env python3
"""
compare_campaigns.py — Cross-campaign comparison dashboard for ARD ablations.

Consumes the aggregated_data.json produced by aggregate_runs.py for two or
more campaigns and produces a self-contained comparison.html with:
  - Headline metric table with Mann-Whitney U significance and Cliff's delta
  - PSR trajectory overlay with ±1σ CI bands
  - Peak PSR strip plot (honest small-N distribution visualization)
  - Validator verdict distribution
  - Proposal type distribution
  - Code structural integrity rates (AST-derived)
  - Pairwise statistical details table

Statistical layer:
  - Mann-Whitney U (non-parametric, appropriate for N ≥ 3, no normality assumption)
  - Cliff's delta (effect size, range −1 to +1)
  - scipy.stats required; install with: pip install scipy

Usage:
    python3 compare_campaigns.py \\
        --campaign-dirs post_hoc_analysis/outputs/campaign_A \\
                        post_hoc_analysis/outputs/campaign_B \\
        --labels "Old Val Prompt" "Reordered Val Prompt" \\
        --baseline 0 \\
        --output-dir post_hoc_analysis/comparisons/A_vs_B

    # Baseline defaults to index 0 if not specified.
    # Labels default to directory names if not specified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scipy import stats as _scipy_stats
except ImportError:
    print("ERROR: scipy is required.  pip install scipy", file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Statistical helpers
# ===========================================================================

def _mean(vals: list) -> float | None:
    vs = [v for v in vals if v is not None]
    return sum(vs) / len(vs) if vs else None


def _std(vals: list) -> float | None:
    vs = [v for v in vals if v is not None]
    if len(vs) < 2:
        return None
    m = sum(vs) / len(vs)
    return (sum((v - m) ** 2 for v in vs) / len(vs)) ** 0.5


def cliffs_delta(a: list, b: list) -> float | None:
    """
    Cliff's delta: proportion of (a,b) pairs where a > b minus proportion
    where a < b.  Range: −1 (b dominates) to +1 (a dominates).
    Positive = a > b on average.
    """
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if not a or not b:
        return None
    n = len(a) * len(b)
    dom  = sum(1 for x in a for y in b if x > y)
    domd = sum(1 for x in a for y in b if x < y)
    return (dom - domd) / n


def interpret_delta(d: float | None) -> str:
    """Return magnitude label per standard thresholds."""
    if d is None:
        return "—"
    ad = abs(d)
    if   ad < 0.147: return "negligible"
    elif ad < 0.330: return "small"
    elif ad < 0.474: return "medium"
    else:            return "large"


def mann_whitney(a: list, b: list) -> tuple[float | None, float | None]:
    """Mann-Whitney U, two-sided.  Returns (U, p)."""
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if len(a) < 2 or len(b) < 2:
        return None, None
    try:
        res = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
        return float(res.statistic), float(res.pvalue)
    except Exception:
        return None, None


def fmt_p(p: float | None) -> str:
    if p is None:
        return "—"
    if p < 0.001:
        return "< 0.001"
    return f"{p:.3f}"


def fmt_delta(d: float | None) -> str:
    if d is None:
        return "—"
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "·")
    return f"{arrow} {abs(d):.3f}"


# ===========================================================================
# Data loading
# ===========================================================================

def _safe(d: dict | None, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is None:
            return default
    return cur

def _extract_model_data(model_data: dict, campaign_label: str) -> dict:
    """
    Build a self-contained metrics dict for one ModelSummary entry.
    Extracted from load_campaign so it can be called once per (campaign, model).
    """
    run_summaries = model_data.get("run_summaries", [])

    # ── Per-run headline metrics ──
    runs = []
    for rs in run_summaries:
        iters = rs.get("iterations", [])
        n_iters = len(iters)

        # Code integrity rates (AST-derived)
        n_dc = sum(
            1 for it in iters
            if len((_safe(it, "code_change", "double_count_flags") or [])) > 0
        )
        n_ghost = sum(
            1 for it in iters
            if len((_safe(it, "code_change", "ghost_vars") or [])) > 0
        )
        n_excised_total = sum(
            _safe(it, "code_change", "n_excised") or 0 for it in iters
        )

        # Proposal type totals (from CognitionRecord.proposal_type_counts per iter)
        prop_counts: dict = {}
        for it in iters:
            for ptype, cnt in (_safe(it, "cognition", "proposal_type_counts") or {}).items():
                prop_counts[ptype] = prop_counts.get(ptype, 0) + cnt
        prop_total = sum(prop_counts.values()) or 1

        runs.append({
            "tag":          rs.get("campaign_tag", ""),
            "peak_psr":     rs.get("peak_psr"),
            "peak_centered":rs.get("peak_centered"),
            "final_psr":    rs.get("iter_final_psr"),
            "stability":    rs.get("stability_score"),
            "collapses":    rs.get("collapse_count"),
            "recoveries":   rs.get("recovery_count"),
            "n_iters":      n_iters,
            "verdicts":     rs.get("validator_verdicts", {}),
            "dc_rate":      n_dc    / n_iters if n_iters else None,
            "ghost_rate":   n_ghost / n_iters if n_iters else None,
            "excision_rate":n_excised_total / n_iters if n_iters else None,
            "prop_modification": prop_counts.get("modification", 0) / prop_total,
            "prop_addition":     prop_counts.get("addition",     0) / prop_total,
            "prop_cluster":      prop_counts.get("cluster",      0) / prop_total,
            "prop_unknown":      prop_counts.get("unknown",      0) / prop_total,
        })

    # ── Per-iteration trajectory (PSR mean ± std across runs) ──
    max_iter = max((r["n_iters"] for r in runs), default=0)
    trajectory = []
    for i in range(1, max_iter + 1):
        psr_vals, centered_vals = [], []
        for rs in run_summaries:
            it = next(
                (x for x in rs.get("iterations", []) if x.get("iteration") == i),
                None
            )
            if it:
                v = _safe(it, "outcomes", "population_success_rate")
                c = _safe(it, "outcomes", "landed_centered_rate")
                if v is not None: psr_vals.append(v)
                if c is not None: centered_vals.append(c)
        trajectory.append({
            "iter":         i,
            "psr_mean":     _mean(psr_vals),
            "psr_std":      _std(psr_vals),
            "psr_upper":    (_mean(psr_vals) or 0) + (_std(psr_vals) or 0),
            "psr_lower":    max(0, (_mean(psr_vals) or 0) - (_std(psr_vals) or 0)),
            "cent_mean":    _mean(centered_vals),
            "n":            len(psr_vals),
        })

    # ── Aggregate verdict distribution across all runs ──
    verdict_totals: dict = {}
    for rs in run_summaries:
        for v, cnt in rs.get("validator_verdicts", {}).items():
            verdict_totals[v] = verdict_totals.get(v, 0) + cnt
    verdict_total_n = sum(verdict_totals.values()) or 1

    vt = sum(verdict_totals.values()) or 1
    return {
        "campaign_label": campaign_label,
        "n_runs":         len(runs),
        "runs":           runs,
        "trajectory":     trajectory,
        "max_iter":       max_iter,
        "verdict_totals": verdict_totals,
        "verdict_fracs":  {v: c / vt for v, c in verdict_totals.items()},
    }


def load_campaign(output_dir: Path, label: str) -> dict:
    """
    Load ALL ModelSummary entries from a campaign\'s aggregated_data.json.
    Returns {label, models: {model_name: entity_dict}}.
    """
    audit_path = output_dir / "aggregated_data.json"
    if not audit_path.is_file():
        raise FileNotFoundError(
            f"aggregated_data.json not found in {output_dir}\\n"
            f"Run aggregate_runs.py on this campaign first."
        )
    with audit_path.open() as f:
        audit = json.load(f)

    if not audit.get("models"):
        raise ValueError(f"No models in {audit_path}")

    models: dict = {}
    for model_data in audit["models"]:
        name = model_data.get("strategist_model", "unknown")
        models[name] = _extract_model_data(model_data, label)

    return {"label": label, "campaign_dir": str(output_dir), "models": models}


# ===========================================================================
# Comparison payload builder
# ===========================================================================

# Metrics to test — each entry: (key, label, "higher_better" | "lower_better")
METRIC_DEFS = [
    ("peak_psr",     "Peak PSR",          "higher_better"),
    ("stability",    "Stability σ",       "lower_better"),   # lower std = more stable
    ("collapses",    "Collapse count",    "lower_better"),
    ("recoveries",   "Recovery count",    "higher_better"),
    ("dc_rate",      "Double-count rate", "lower_better"),
    ("ghost_rate",   "Ghost var rate",    "lower_better"),
]

VERDICT_ORDER = [
    "Validated", "Confirmed", "Productive Deviation",
    "Mixed", "Pyrrhic Victory", "Inconclusive",
    "Refuted", "Regressed", "Goodhart Trap",
    "Unparsed",
]

VERDICT_COLORS = {
    "Validated":           "#1e4a2b",
    "Confirmed":           "#1e4a2b",
    "Productive Deviation":"#2a4a1e",
    "Mixed":               "#4a3e1e",
    "Pyrrhic Victory":     "#3e3a1e",
    "Inconclusive":        "#2a2d35",
    "Refuted":             "#4a1e1e",
    "Regressed":           "#4a1e1e",
    "Goodhart Trap":       "#3a1a2a",
    "Unparsed":            "#222",
}


def _compare_entities(baseline: dict, treatment: dict) -> dict:
    """Statistical comparison of two entity dicts (one per campaign)."""
    results = {}
    for key, label, direction in METRIC_DEFS:
        b = [r[key] for r in baseline["runs"]  if r[key] is not None]
        t = [r[key] for r in treatment["runs"] if r[key] is not None]
        U, p  = mann_whitney(t, b)
        delta = cliffs_delta(t, b)   # positive = treatment > baseline
        beneficial = (
            (delta is not None and delta  > 0 and direction == "higher_better") or
            (delta is not None and delta  < 0 and direction == "lower_better")
        )
        results[key] = {
            "label":       label,
            "direction":   direction,
            "b_mean":      _mean(b),   "b_std":  _std(b),
            "t_mean":      _mean(t),   "t_std":  _std(t),
            "U":           U,           "p":      p,
            "p_fmt":       fmt_p(p),
            "delta":       delta,       "delta_fmt": fmt_delta(delta),
            "magnitude":   interpret_delta(delta),
            "beneficial":  beneficial,
            "significant": p is not None and p < 0.05,
            "marginal":    p is not None and 0.05 <= p < 0.10,
        }
    return {
        "treatment_label": treatment["campaign_label"],
        "baseline_label":  baseline["campaign_label"],
        "metrics":         results,
    }


def build_payload(campaigns: list[dict],
                  baseline_idx: int,
                  model_filter: str | None = None) -> dict:
    """
    Group by model name across campaigns.
    Models present in 2+ campaigns get statistical comparisons.
    Models present in only 1 campaign are excluded from the dashboard.
    """
    all_model_names: set = set()
    for c in campaigns:
        all_model_names |= set(c["models"].keys())

    if model_filter:
        filtered = {m for m in all_model_names if model_filter.lower() in m.lower()}
        if not filtered:
            print(f"WARNING: --model \'{model_filter}\' matched nothing in: "
                  f"{sorted(all_model_names)}", file=sys.stderr)
        all_model_names = filtered

    all_verdicts: set = set()
    for c in campaigns:
        for md in c["models"].values():
            all_verdicts |= set(md["verdict_totals"].keys())
    verdict_order = [v for v in VERDICT_ORDER if v in all_verdicts]
    verdict_order += sorted(all_verdicts - set(VERDICT_ORDER))

    model_groups: list = []
    for model_name in sorted(all_model_names):
        entities = []
        for i, c in enumerate(campaigns):
            if model_name not in c["models"]:
                continue
            entity = dict(c["models"][model_name])
            entity["campaign_label"] = c["label"]
            entity["campaign_idx"]   = i
            entity["is_baseline"]    = (i == baseline_idx)
            entities.append(entity)

        # Skip models unique to one campaign — no counterpart for comparison
        if len(entities) < 2:
            continue

        baseline_entity = next(
            (e for e in entities if e["is_baseline"]),
            entities[0]
        )
        comparisons = [
            _compare_entities(baseline_entity, e)
            for e in entities
            if e is not baseline_entity
        ]

        model_groups.append({
            "model_name":  model_name,
            "entities":    entities,
            "comparisons": comparisons,
            "small_n":     any(e["n_runs"] < 4 for e in entities),
        })

    return {
        "campaign_labels": [c["label"] for c in campaigns],
        "baseline_idx":    baseline_idx,
        "model_groups":    model_groups,
        "verdict_order":   verdict_order,
        "verdict_colors":  VERDICT_COLORS,
        "metric_defs":     [{"key": k, "label": l, "dir": d}
                            for k, l, d in METRIC_DEFS],
    }


# ===========================================================================
# HTML template
# ===========================================================================

COMPARISON_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Campaign Comparison — {LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body  { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
          background:#0f1115; color:#e6e6e6; margin:0; padding:24px; font-size:14px; }
  h1   { font-size:22px; margin:0 0 6px 0; }
  h2   { font-size:15px; margin:22px 0 8px 0; color:#a8c5f0;
         border-bottom:1px solid #2a2d35; padding-bottom:4px; }
  .meta { color:#888; font-size:12px; margin-bottom:18px; }
  .card { background:#181a20; border:1px solid #262931; border-radius:8px;
          padding:14px; margin:8px 0; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
  .chart-box { position:relative; height:260px; }
  .chart-box-sm { position:relative; height:200px; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th,td { padding:6px 9px; text-align:left; border-bottom:1px solid #22252d; }
  th    { color:#a8c5f0; font-weight:600; white-space:nowrap; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; }
  td.mono { font-family:monospace; font-size:11px; }
  .baseline-row { background:#1a1d24; }
  .sig   { color:#6ee093; font-weight:600; }
  .marg  { color:#e6c46e; }
  .nosig { color:#555; }
  .good  { color:#6ee093; }
  .bad   { color:#e66e6e; }
  .warn-box { background:#2e2108; border:1px solid #e6c46e44; border-radius:6px;
              padding:8px 12px; font-size:12px; color:#e6c46e; margin:8px 0; }
  details > summary { cursor:pointer; padding:4px 0; color:#a8c5f0; font-size:13px; }
  .small { color:#888; font-size:11px; }
  .pill  { display:inline-block; padding:1px 7px; border-radius:10px;
           font-size:11px; font-weight:600; }
  .pill-baseline { background:#1e3a5f; color:#7ab3e0; }
  .pill-treatment { background:#1e3a2b; color:#7ae0ab; }
</style>
</head>
<body>
<h1>ARD Campaign Comparison</h1>
<div class="meta">
  Label: <code>{LABEL}</code> &nbsp;•&nbsp; Generated: <code id="ts"></code>
</div>
<div id="root"></div>

<script>
const DATA = {DATA_JSON};
document.getElementById('ts').textContent =
  new Date().toISOString().replace('T',' ').slice(0,19);
const root = document.getElementById('root');

// ── Palette — one color per campaign (distinct from run palette) ──
const CAM_COLORS = ['#4e79a7','#f28e2b','#59a14f','#e15759','#b07aa1','#76b7b2'];
function camColor(i) { return CAM_COLORS[i % CAM_COLORS.length]; }

// ── Helpers ──
function fmt(v,d=3){ return (v==null)?'—':(+v).toFixed(d); }
function fmtPct(v) { return (v==null)?'—':(v*100).toFixed(1)+'%'; }
function mean(arr) { const v=arr.filter(x=>x!=null); return v.length?v.reduce((a,b)=>a+b)/v.length:null; }
function std(arr)  {
  const v=arr.filter(x=>x!=null);
  if(v.length<2) return null;
  const m=mean(v);
  return Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/v.length);
}

const campaigns = DATA.campaigns;
const baseline  = campaigns[DATA.baseline_idx];

// ══════════════════════════════════════════════════════════════════════
// SMALL-N WARNING
// ══════════════════════════════════════════════════════════════════════
if (DATA.small_n_warning) {
  const wb = document.createElement('div');
  wb.className = 'warn-box';
  wb.innerHTML = '⚠ One or more campaigns has N&lt;4 runs. With N=3 the minimum achievable '
    + 'two-sided Mann-Whitney p-value is 0.10 — significance at α=0.05 is not attainable. '
    + 'Treat p-values and Cliff\'s δ as exploratory, not confirmatory.';
  root.appendChild(wb);
}

// ══════════════════════════════════════════════════════════════════════
// SECTION 1 — Campaign configuration chips
// ══════════════════════════════════════════════════════════════════════
(function() {
  const div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;margin:12px 0;align-items:center;';
  div.innerHTML = '<span class="small" style="color:#a8c5f0">Campaigns:</span>';
  campaigns.forEach((c,i) => {
    const chip = document.createElement('span');
    chip.className = 'pill ' + (i===DATA.baseline_idx ? 'pill-baseline':'pill-treatment');
    chip.style.borderLeft = `3px solid ${camColor(i)}`;
    chip.style.paddingLeft = '8px';
    chip.textContent = (i===DATA.baseline_idx ? '★ ' : '') + c.label
      + `  ·  ${c.model}  ·  N=${c.n_runs}`;
    div.appendChild(chip);
  });
  root.appendChild(div);
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 2 — Headline Metrics Table
// ══════════════════════════════════════════════════════════════════════
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>Headline Metrics</h2>';

  // Header row: campaign columns first, then comparison columns for each non-baseline
  const comparisons = DATA.comparisons;
  const metrics = DATA.metric_defs;

  const tbl = document.createElement('table');
  let thead = '<thead><tr><th>Metric</th>';
  campaigns.forEach((c,i) => {
    thead += `<th style="border-left:2px solid ${camColor(i)}44">${c.label}</th>`;
  });
  comparisons.forEach(cmp => {
    thead += `<th style="color:#888;font-weight:400" colspan="3">`
           + `vs baseline: ${cmp.treatment_label} — p-value / δ / magnitude</th>`;
  });
  thead += '</tr></thead>';
  tbl.innerHTML = thead;

  const tbody = document.createElement('tbody');
  metrics.forEach(({key, label, dir}) => {
    let row = `<tr><td>${label} <span class="small">${dir==='higher_better'?'↑ higher':'↓ lower'}</span></td>`;

    campaigns.forEach((c,i) => {
      const vals = c.runs.map(r => r[key]).filter(x=>x!=null);
      const m = mean(vals), s = std(vals);
      const cell = m!=null
        ? `${fmt(m)} <span class="small">±${fmt(s??0)}</span>`
        : '—';
      row += `<td class="num" style="border-left:2px solid ${camColor(i)}44">${cell}</td>`;
    });

    comparisons.forEach(cmp => {
      const res = cmp.metrics[key];
      if (!res) { row += '<td colspan="3">—</td>'; return; }
      const pClass = res.significant ? 'sig' : (res.marginal ? 'marg' : 'nosig');
      const dClass = res.beneficial  ? 'good' : (res.delta !== null && res.delta !== 0 ? 'bad' : '');
      row += `<td class="num ${pClass}">${res.p_fmt}</td>`
           + `<td class="num ${dClass}">${res.delta_fmt}</td>`
           + `<td class="num small">${res.magnitude}</td>`;
    });
    row += '</tr>';
    tbody.innerHTML += row;
  });
  tbl.appendChild(tbody);
  card.appendChild(tbl);

  // Legend for significance colouring
  const leg = document.createElement('div');
  leg.className = 'small';
  leg.style.marginTop = '8px';
  leg.innerHTML = `<span class="sig">■</span> p&lt;0.05 &nbsp;`
    + `<span class="marg">■</span> p&lt;0.10 &nbsp;`
    + `<span class="nosig">■</span> p≥0.10 &nbsp;&nbsp;`
    + `δ: <span class="good">↑/↓ beneficial</span> vs baseline`;
  card.appendChild(leg);
  root.appendChild(card);
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 3 — PSR Trajectory Overlay (full width)
// ══════════════════════════════════════════════════════════════════════
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>PSR Trajectory (mean ± 1σ across runs)</h2>'
    + '<div class="chart-box"><canvas></canvas></div>';
  root.appendChild(card);

  const maxIter = Math.max(...campaigns.map(c => c.max_iter));
  const labels  = Array.from({length: maxIter}, (_, i) => String(i+1));

  const datasets = [];
  campaigns.forEach((c, ci) => {
    const col = camColor(ci);
    const traj = c.trajectory;
    const upper = labels.map((_, i) => traj[i]?.psr_upper ?? null);
    const lower = labels.map((_, i) => traj[i]?.psr_lower ?? null);
    const mns   = labels.map((_, i) => traj[i]?.psr_mean  ?? null);

    // CI band: upper fills down to lower
    datasets.push({
      label: '_up_' + ci,
      data: upper, borderWidth:0, pointRadius:0,
      fill:'+1', backgroundColor: col+'28',
      tension:0.25, spanGaps:true,
    });
    datasets.push({
      label: '_lo_' + ci,
      data: lower, borderWidth:0, pointRadius:0,
      fill:false, tension:0.25, spanGaps:true,
    });
    datasets.push({
      label: c.label,
      data: mns,
      borderColor: col, borderWidth: 2.5, pointRadius: 3,
      fill:false, tension:0.25, spanGaps:true,
    });
  });

  new Chart(card.querySelector('canvas'), {
    type:'line',
    data:{labels, datasets},
    options:{
      scales:{
        x:{title:{display:true, text:'Iteration'}},
        y:{title:{display:true, text:'PSR'}, min:0, max:1},
      },
      plugins:{legend:{labels:{
        color:'#ccc', boxWidth:12,
        filter: item => !item.text.startsWith('_'),
      }}},
      animation:false,
    }
  });
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 4 — Peak PSR Strip Plot + Verdict Distribution
// ══════════════════════════════════════════════════════════════════════
const sec4 = document.createElement('div');
sec4.className = 'grid2';
root.appendChild(sec4);

// ── 4a: Peak PSR strip plot ──
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>Peak PSR Distribution (per run)</h2>'
    + '<div class="chart-box-sm"><canvas></canvas></div>'
    + '<div class="small" style="margin-top:4px">Each point = one run. '
    + 'Horizontal jitter separates overlapping values. '
    + 'Honest representation for small N.</div>';
  sec4.appendChild(card);

  const datasets = campaigns.map((c, ci) => {
    const col = camColor(ci);
    return {
      label: c.label,
      data: c.runs.map((r, ri) => ({
        x: ci + (ri - (c.n_runs - 1) / 2) * 0.12,
        y: r.peak_psr,
      })),
      backgroundColor: col + 'cc',
      borderColor: col,
      pointRadius: 7, borderWidth: 1.5,
    };
  });

  // Mean markers (larger diamond-ish via higher radius)
  campaigns.forEach((c, ci) => {
    const m = mean(c.runs.map(r => r.peak_psr));
    if (m == null) return;
    datasets.push({
      label: '_mean_' + ci,
      data: [{x: ci, y: m}],
      backgroundColor: camColor(ci),
      borderColor: '#fff',
      pointRadius: 10, pointStyle: 'rectRot', borderWidth: 2,
    });
  });

  new Chart(card.querySelector('canvas'), {
    type:'scatter',
    data:{datasets},
    options:{
      scales:{
        x:{
          type:'linear', min:-0.5, max:campaigns.length - 0.5,
          ticks:{
            callback: (_,i) => campaigns[i]?.label ?? '',
            stepSize:1,
          },
          title:{display:false},
        },
        y:{title:{display:true, text:'Peak PSR'}, min:0, max:1},
      },
      plugins:{legend:{labels:{
        color:'#ccc', boxWidth:10,
        filter: item => !item.text.startsWith('_'),
      }}},
      animation:false,
    }
  });
})();

// ── 4b: Validator verdict distribution ──
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>Validator Verdict Distribution</h2>'
    + '<div class="chart-box-sm"><canvas></canvas></div>';
  sec4.appendChild(card);

  const verdicts = DATA.verdict_order;
  const VCOLS = DATA.verdict_colors;

  // One stacked bar per campaign (horizontal)
  const datasets = verdicts.map(v => ({
    label: v,
    data: campaigns.map(c => {
      const tot = Object.values(c.verdict_totals).reduce((a,b)=>a+b, 0) || 1;
      return ((c.verdict_totals[v] || 0) / tot) * 100;
    }),
    backgroundColor: VCOLS[v] || '#333',
    borderColor:     (VCOLS[v] || '#333') + 'cc',
    borderWidth: 1,
  }));

  new Chart(card.querySelector('canvas'), {
    type:'bar',
    data:{
      labels: campaigns.map(c => c.label),
      datasets,
    },
    options:{
      indexAxis:'y',
      scales:{
        x:{stacked:true, title:{display:true, text:'%'}, max:100},
        y:{stacked:true},
      },
      plugins:{legend:{labels:{color:'#ccc', boxWidth:10, font:{size:10}}}},
      animation:false,
    }
  });
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 5 — Proposal Types + Code Integrity
// ══════════════════════════════════════════════════════════════════════
const sec5 = document.createElement('div');
sec5.className = 'grid2';
root.appendChild(sec5);

// ── 5a: Proposal type proportions ──
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>Proposal Type Distribution</h2>'
    + '<div class="chart-box-sm"><canvas></canvas></div>';
  sec5.appendChild(card);

  const propTypes = [
    {key:'prop_modification', label:'Modification', color:'#4e79a7'},
    {key:'prop_addition',     label:'Addition',     color:'#59a14f'},
    {key:'prop_cluster',      label:'Cluster',      color:'#edc948'},
    {key:'prop_unknown',      label:'Unknown',      color:'#888'},
  ];

  const datasets = propTypes.map(({key, label, color}) => ({
    label,
    data: campaigns.map(c => mean(c.runs.map(r => r[key])) * 100),
    backgroundColor: color + 'cc',
    borderColor: color,
    borderWidth: 1,
  }));

  new Chart(card.querySelector('canvas'), {
    type:'bar',
    data:{labels: campaigns.map(c => c.label), datasets},
    options:{
      scales:{
        x:{stacked:true},
        y:{stacked:true, title:{display:true, text:'% of proposals'}, max:100},
      },
      plugins:{legend:{labels:{color:'#ccc', boxWidth:10}}},
      animation:false,
    }
  });
})();

// ── 5b: Code structural integrity rates ──
(function() {
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = '<h2>Code Structural Integrity Rates (AST)</h2>'
    + '<div class="chart-box-sm"><canvas></canvas></div>';
  sec5.appendChild(card);

  const integrityMetrics = [
    {key:'dc_rate',       label:'Double-count rate', color:'#e6c46e'},
    {key:'ghost_rate',    label:'Ghost var rate',     color:'#c8c860'},
    {key:'excision_rate', label:'Mean excisions/iter',color:'#59a14f'},
  ];

  const datasets = integrityMetrics.map(({key, label, color}) => ({
    label,
    data: campaigns.map(c => {
      const m = mean(c.runs.map(r => r[key]).filter(x => x!=null));
      return m != null ? +(m * (key==='excision_rate' ? 1 : 100)).toFixed(3) : null;
    }),
    backgroundColor: color + 'cc',
    borderColor: color,
    borderWidth: 1,
  }));

  new Chart(card.querySelector('canvas'), {
    type:'bar',
    data:{labels: campaigns.map(c => c.label), datasets},
    options:{
      scales:{
        x:{},
        y:{
          title:{display:true, text:'Rate (%) / count'},
          min:0,
        },
      },
      plugins:{legend:{labels:{color:'#ccc', boxWidth:10}}},
      animation:false,
    }
  });
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 6 — Per-run detail table (expandable)
// ══════════════════════════════════════════════════════════════════════
(function() {
  const drill = document.createElement('details');
  drill.className = 'card';
  drill.innerHTML = '<summary>Per-run Detail (all campaigns)</summary>';
  root.appendChild(drill);

  const tbl = document.createElement('table');
  tbl.innerHTML = `<thead><tr>
    <th>Campaign</th><th>Run</th>
    <th>Peak PSR</th><th>Final PSR</th><th>Stability σ</th>
    <th>Collapses</th><th>Recoveries</th>
    <th>DC rate</th><th>Ghost rate</th><th>Iters</th>
  </tr></thead>`;
  const tbody = document.createElement('tbody');

  campaigns.forEach((c, ci) => {
    c.runs.forEach((r, ri) => {
      tbody.innerHTML += `<tr ${ri===0?`class="baseline-row"`:''}>
        <td style="color:${camColor(ci)}">${ci===DATA.baseline_idx?'★ ':''} ${c.label}</td>
        <td class="mono small">${r.tag.split('_').slice(-1)[0]}</td>
        <td class="num">${fmt(r.peak_psr)}</td>
        <td class="num">${fmt(r.final_psr)}</td>
        <td class="num">${fmt(r.stability)}</td>
        <td class="num">${r.collapses ?? '—'}</td>
        <td class="num">${r.recoveries ?? '—'}</td>
        <td class="num">${fmtPct(r.dc_rate)}</td>
        <td class="num">${fmtPct(r.ghost_rate)}</td>
        <td class="num">${r.n_iters}</td>
      </tr>`;
    });
  });

  tbl.appendChild(tbody);
  drill.appendChild(tbl);
})();

// ══════════════════════════════════════════════════════════════════════
// SECTION 7 — Pairwise statistical details (expandable)
// ══════════════════════════════════════════════════════════════════════
(function() {
  if (!DATA.comparisons.length) return;
  const drill = document.createElement('details');
  drill.className = 'card';
  drill.innerHTML = '<summary>Pairwise Statistical Details</summary>';
  root.appendChild(drill);

  DATA.comparisons.forEach(cmp => {
    const sec = document.createElement('div');
    sec.style.marginTop = '12px';
    sec.innerHTML = `<div class="small" style="color:#a8c5f0;margin-bottom:6px">
      ${cmp.treatment_label} vs baseline (${cmp.baseline_label})
    </div>`;

    const tbl = document.createElement('table');
    tbl.innerHTML = `<thead><tr>
      <th>Metric</th>
      <th>Baseline mean±σ</th><th>Treatment mean±σ</th>
      <th>U statistic</th><th>p-value</th>
      <th>Cliff's δ</th><th>Magnitude</th><th>Direction</th>
    </tr></thead>`;
    const tbody = document.createElement('tbody');

    Object.values(cmp.metrics).forEach(res => {
      const pClass = res.significant ? 'sig' : (res.marginal ? 'marg' : 'nosig');
      const dClass = res.beneficial  ? 'good' : (res.delta !== null && res.delta !== 0 ? 'bad' : '');
      const dir = res.beneficial ? '✓ favours treatment' : (res.delta ? '✗ favours baseline' : '·');
      tbody.innerHTML += `<tr>
        <td>${res.label}</td>
        <td class="num">${fmt(res.b_mean)} ± ${fmt(res.b_std)}</td>
        <td class="num">${fmt(res.t_mean)} ± ${fmt(res.t_std)}</td>
        <td class="num">${res.U != null ? fmt(res.U, 1) : '—'}</td>
        <td class="num ${pClass}">${res.p_fmt}</td>
        <td class="num ${dClass}">${res.delta_fmt}</td>
        <td class="num small">${res.magnitude}</td>
        <td class="small ${res.beneficial ? 'good' : 'bad'}">${dir}</td>
      </tr>`;
    });
    tbl.appendChild(tbody);
    sec.appendChild(tbl);
    drill.appendChild(sec);
  });
})();
</script>
</body>
</html>
"""


# ===========================================================================
# Output
# ===========================================================================

def write_comparison_html(payload: dict, label: str, output_dir: Path) -> Path:
    data_json = json.dumps(payload, default=str)
    path = output_dir / "comparison.html"
    path.write_text(
        COMPARISON_TEMPLATE
        .replace("{LABEL}", label)
        .replace("{DATA_JSON}", data_json)
    )
    return path


def write_summary_csv(payload: dict, output_dir: Path) -> Path:
    """One row per campaign × metric with significance columns."""
    import csv
    path = output_dir / "comparison_summary.csv"
    baseline_label = payload["campaigns"][payload["baseline_idx"]]["label"]

    rows = []
    for cmp in payload["comparisons"]:
        for key, res in cmp["metrics"].items():
            rows.append({
                "treatment":   cmp["treatment_label"],
                "baseline":    cmp["baseline_label"],
                "metric_key":  key,
                "metric_label":res["label"],
                "b_mean":      res["b_mean"],
                "b_std":       res["b_std"],
                "t_mean":      res["t_mean"],
                "t_std":       res["t_std"],
                "U":           res["U"],
                "p":           res["p"],
                "cliffs_delta":res["delta"],
                "magnitude":   res["magnitude"],
                "significant": res["significant"],
                "beneficial":  res["beneficial"],
            })

    if rows:
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return path


# ===========================================================================
# CLI
# ===========================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Cross-campaign comparison dashboard for ARD ablations"
    )
    ap.add_argument(
        "--campaign-dirs", nargs="+", required=True, type=Path,
        help="Paths to aggregate_runs.py output directories (each must contain "
             "aggregated_data.json)"
    )
    ap.add_argument(
        "--labels", nargs="+", default=None,
        help="Human-readable label for each campaign (defaults to directory name). "
             "Must match number of --campaign-dirs if provided."
    )
    ap.add_argument(
        "--baseline", type=int, default=0,
        help="Index of the baseline campaign (default: 0 = first)"
    )
    ap.add_argument(
        "--model", default=None,
        help="Substring filter on model name (e.g. 'gemma4' matches gemma4:26b)"
    )
    ap.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory (default: post_hoc_analysis/comparisons/<label>)"
    )
    args = ap.parse_args()

    dirs   = args.campaign_dirs
    labels = args.labels or [d.name for d in dirs]

    if len(labels) != len(dirs):
        ap.error(f"--labels count ({len(labels)}) must match --campaign-dirs count ({len(dirs)})")
    if not (0 <= args.baseline < len(dirs)):
        ap.error(f"--baseline {args.baseline} out of range (0–{len(dirs)-1})")

    label_str = f"{labels[args.baseline]}_vs_" + "_".join(
        l for i, l in enumerate(labels) if i != args.baseline
    )
    label_str = label_str[:80].replace(" ", "_")

    output_dir = args.output_dir or (
        Path("post_hoc_analysis") / "comparisons" / label_str
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {len(dirs)} campaign(s)...")
    campaigns = []
    for d, l in zip(dirs, labels):
        try:
            c = load_campaign(Path(d), l)
            print(f"  {l}:")
            for name, md in c["models"].items():
                print(f"    {name}  ({md['n_runs']} runs, {md['max_iter']} iters)")
            campaigns.append(c)
        except Exception as exc:
            print(f"  ERROR loading {d}: {exc}", file=sys.stderr)
            sys.exit(1)

    payload = build_payload(campaigns, args.baseline, model_filter=args.model)

    n_groups = len(payload["model_groups"])
    if n_groups == 0:
        print("\\nNo model groups with 2+ campaigns — nothing to compare.", file=sys.stderr)
        print("Check that the same model name appears across campaigns, "
              "or relax --model filter.", file=sys.stderr)
        sys.exit(1)

    print(f"\\n{n_groups} model group(s) to compare:")
    for g in payload["model_groups"]:
        print(f"  {g['model_name']}  ->  "
              + "  |  ".join(
                  f"{e['campaign_label']} (N={e['n_runs']})"
                  for e in g["entities"]
              ))
    html_path = write_comparison_html(payload, label_str, output_dir)
    csv_path  = write_summary_csv(payload, output_dir)

    print(f"\nOutputs written to {output_dir}/")
    print(f"  {html_path.name}")
    print(f"  {csv_path.name}")

    # Surface any significance findings
    for cmp in payload["comparisons"]:
        sig = [res for res in cmp["metrics"].values() if res["significant"]]
        marg = [res for res in cmp["metrics"].values() if res["marginal"]]
        print(f"\n  {cmp['treatment_label']} vs {cmp['baseline_label']}:")
        if sig:
            for res in sig:
                mark = "✓" if res["beneficial"] else "✗"
                print(f"    {mark} {res['label']:20s} p={res['p_fmt']:8s} "
                      f"δ={res['delta_fmt']}  [{res['magnitude']}]")
        elif marg:
            for res in marg:
                print(f"    ~ {res['label']:20s} p={res['p_fmt']:8s} "
                      f"δ={res['delta_fmt']}  [{res['magnitude']}] (marginal)")
        else:
            print(f"    No significant or marginal differences found.")


if __name__ == "__main__":
    main()
