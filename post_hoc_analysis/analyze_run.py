#!/usr/bin/env python3
"""
analyze_run.py
--------------
Per-run triage analysis for the ARD pipeline.
Called automatically by outer_loop.sh after each campaign completes.

Outputs (under {campaign}/{model_dir}/reports/):
  triage_report.html   — self-contained HTML dashboard
  triage_summary.json  — machine-readable headline stats

Data sources (via extract_cognition.py — structured only):
  RL outcomes       : iter{NN}_metric_payload.json
  Validator verdicts: experiment_ledger.json
  Code evolution    : iter{NN}_reward.py (AST) + iter{NN}_changes.patch
  LLM behaviour     : iter{NN}_cognition_record.json
  Token / timing    : ChatResponse_data.csv

Coder retry count:
 ChatResponse_data.csv   - coder-phase call count − 1  

Thinking-token estimate:
  Word-count ratio apportionment of gen_tokens between response_content and
  thinking_trace — same method as apportionTokens() in the compute_cost
  dashboard of aggregate_runs.py.

Usage:
  python3 analyze_run.py --campaign 2025-05-10_spin_crash_10cycles_500kSteps
  python3 analyze_run.py --campaign-path /abs/path/to/campaign/dir
  python3 analyze_run.py --campaign 2025-05-10_... --quiet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_cognition import (
    AggregationConfig,
    RunPaths,
    load_ledger,
    load_run,
    load_chat_responses,
)

_DEFAULT_EXPERIMENTS_DIR = Path(__file__).parent.parent / "experiments"

# Floor-rule thresholds expressed in percentage-points (applied after × 100)
_FLOOR_UP_PP   = 20.0   # ≥ +20pp → verdict must be DEV / Validated
_FLOOR_DOWN_PP = 20.0   # ≤ −20pp → verdict must be Regressed / GoodhartTrap
_VERDICTS_DEV  = {"Validated", "Productive Deviation"}
_VERDICTS_BAD  = {"Regressed", "Goodhart Trap"}


# ===========================================================================
# Helpers
# ===========================================================================

def _apportion_tokens(
    response_content: str,
    thinking_trace: str,
    gen_tokens: int | None,
) -> tuple[int, int]:
    """
    Apportion gen_tokens into (thinking_tokens, response_tokens) by word-count
    ratio.  Mirrors apportionTokens() in the Compute Cost dashboard so the
    per-run and per-campaign estimates are computed identically.
    """
    think_words = len(thinking_trace.split()) if thinking_trace else 0
    resp_words  = len(response_content.split()) if response_content else 0
    total_words = think_words + resp_words
    gt = gen_tokens or 0
    if total_words == 0 or gt == 0:
        return 0, gt
    think_tok = round(gt * think_words / total_words)
    return think_tok, gt - think_tok


def _floor_rule_check(
    baseline_psr: float | None,
    actual_psr:   float | None,
    verdict:      str   | None,
) -> dict:
    """
    Return a floor-rule compliance dict for one iteration.
    PSR inputs are fractions 0-1; delta is converted to pp internally.
    """
    if baseline_psr is None or actual_psr is None:
        return {"status": "unknown", "delta_pp": None,
                "label": "unknown (missing baseline PSR)"}

    delta = (actual_psr - baseline_psr) * 100.0
    v     = verdict or "Unparsed"

    if delta >= _FLOOR_UP_PP:
        if v == "Regressed":
            return {"status": "hard_violation", "delta_pp": round(delta, 1),
                    "label": f"HARD: +{delta:.1f}pp → cannot be Regressed"}
        if v not in _VERDICTS_DEV:
            return {"status": "soft_violation", "delta_pp": round(delta, 1),
                    "label": f"SOFT: +{delta:.1f}pp → should be DEV/Validated (got {v})"}

    if delta <= -_FLOOR_DOWN_PP:
        if v not in _VERDICTS_BAD:
            return {"status": "hard_violation", "delta_pp": round(delta, 1),
                    "label": f"HARD: {delta:.1f}pp → must be Regressed/GoodhartTrap (got {v})"}

    sign = "+" if delta >= 0 else ""
    return {"status": "ok", "delta_pp": round(delta, 1),
            "label": f"ok ({sign}{delta:.1f}pp)"}


def _count_coder_retries(
    iteration:  int,
    chat_rows:  list,
) -> tuple[int, str]:
    """
    Returns (retry_count, source).

    ChatResponse CSV coder-phase call count − 1.
    Zero here means no retries were observed by either method.
    """
    coder_calls = sum(
        1 for r in chat_rows
        if r.get("iteration") == iteration and r.get("phase") == "coder"
    )
    if coder_calls > 0:
        return max(0, coder_calls - 1)

    return 0


# ===========================================================================
# Data assembly
# ===========================================================================

def build_triage_data(
    campaign_path: Path,
    cfg: AggregationConfig | None = None,
) -> dict:
    """
    Load all structured sources for one campaign run and return a single
    dict that both the HTML template and the JSON summary consume.
    """
    paths       = RunPaths(campaign_path)
    run_summary = load_run(campaign_path, cfg)
    chat_rows   = load_chat_responses(
        paths.chat_response_path,
        cognition_json_dir=paths.cognition_json_dir,
    )

    # Aggregate wall time from ChatResponse timing
    total_wall_s = sum(r.get("total_duration_s") or 0.0 for r in chat_rows)

    # PSR lookup by iteration number (fraction 0-1, authoritative from payload)
    psr_by_iter: dict[int, float | None] = {
        it.iteration: it.outcomes.population_success_rate
        for it in run_summary.iterations
    }

    # Slim chat rows — pre-compute thinking/response split; drop raw text
    slim_chat = []
    for r in chat_rows:
        think_tok, resp_tok = _apportion_tokens(
            r.get("response_content") or "",
            r.get("thinking_trace")   or "",
            r.get("eval_count"),
        )
        slim_chat.append({
            "iteration":     r.get("iteration"),
            "phase":         r.get("phase"),
            "model":         r.get("model_name"),
            "total_s":       r.get("total_duration_s"),
            "eval_s":        r.get("eval_duration_s"),
            "prompt_tokens": r.get("prompt_eval_count"),
            "gen_tokens":    r.get("eval_count"),
            "think_tokens":  think_tok,
            "resp_tokens":   resp_tok,
        })

    # Per-iteration rows
    iter_rows = []
    for it in run_summary.iterations:
        n       = it.iteration
        o       = it.outcomes
        cog     = it.cognition
        cc      = it.code_change

        baseline_psr = psr_by_iter.get(n - 1)          # None for iter 1 (expected)
        floor        = _floor_rule_check(baseline_psr, o.population_success_rate,
                                         it.validator_status)
        retries= _count_coder_retries(n, chat_rows)

        iter_rows.append({
            "iter":             n,
            # RL outcomes (metric payload — authoritative)
            "psr":              o.population_success_rate,
            "centered":         o.landed_centered_rate,
            "baseline_psr":     baseline_psr,
            # Validator (ledger — authoritative)
            "validator_status": it.validator_status,
            "floor":            floor,
            # Code evolution (AST — authoritative)
            "n_components":       cc.n_components       if cc else None,
            "n_excised":          cc.n_excised           if cc else None,
            "n_added":            cc.n_added             if cc else None,
            "excised_components": cc.excised_components  if cc else [],
            "added_components":   cc.added_components    if cc else [],
            "n_double_count":     len(cc.double_count_flags) if cc else 0,
            "double_count_flags": cc.double_count_flags  if cc else [],
            "n_ghost":            len(cc.ghost_vars)     if cc else 0,
            "ghost_vars":         cc.ghost_vars          if cc else [],
            "lines_added":        cc.lines_added         if cc else None,
            "lines_removed":      cc.lines_removed       if cc else None,
            "patch_available":    cc.patch_available     if cc else False,
            # LLM behaviour (cognition record — authoritative)
            "excision_count":     cog.excision_count,
            "selected_proposal":  cog.selected_proposal_index,
            "prop_modification":  cog.proposal_type_counts.get("modification", 0),
            "prop_addition":      cog.proposal_type_counts.get("addition", 0),
            "prop_cluster":       cog.proposal_type_counts.get("cluster", 0),
            # Coder retries 
            "coder_retries":  retries,
            # Parse / code warnings
            "parse_warnings": it.parse_warnings,
        })

    return {
        "campaign_tag":             paths.campaign_tag,
        "model":                    run_summary.strategist_model,
        "iteration_count":          run_summary.iteration_count,
        "total_wall_s":             round(total_wall_s, 1),
        "peak_psr":                 run_summary.peak_psr,
        "final_psr":                run_summary.iter_final_psr,
        "collapse_count":           run_summary.collapse_count,
        "recovery_count":           run_summary.recovery_count,
        "stability_score":          run_summary.stability_score,
        "validator_verdicts":       run_summary.validator_verdicts,
        "iterations_with_warnings": run_summary.iterations_with_warnings,
        "iterations":               iter_rows,
        "chat_rows":                slim_chat,
    }


# ===========================================================================
# HTML template  (raw string — Python does not interpolate braces inside)
# Placeholders replaced at render time:  {LABEL}  {DATA_JSON}
# ===========================================================================

TRIAGE_REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Triage — {LABEL}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg:   #0f1115; --bg2: #181a20; --bdr: #262931;
    --txt:  #e6e6e6; --txt2: #a8c5f0; --txt3: #888; --txt4: #555;
    --grn:  #6ee093; --red:  #e66e6e; --ylw: #e6c46e; --blu: #76b7b2;
    --gc:   rgba(255,255,255,0.05);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body   { font-family: ui-monospace, "JetBrains Mono", "Fira Code", monospace;
           background: var(--bg); color: var(--txt); padding: 28px;
           font-size: 13px; line-height: 1.5; }
  h1     { font-size: 20px; font-weight: 700; letter-spacing: .03em;
           color: #fff; margin-bottom: 4px; }
  h2     { font-size: 12px; font-weight: 600; letter-spacing: .1em;
           text-transform: uppercase; color: var(--txt2);
           border-bottom: 1px solid var(--bdr); padding-bottom: 5px;
           margin: 22px 0 10px; }
  .meta  { font-size: 11px; color: var(--txt3); margin-bottom: 20px; }
  .meta code { color: var(--txt); }
  /* ── headline cards ── */
  .cards { display: grid; grid-template-columns: repeat(6, 1fr);
           gap: 8px; margin-bottom: 20px; }
  .card  { background: var(--bg2); border: 1px solid var(--bdr);
           border-radius: 6px; padding: 12px 14px; }
  .card .lbl { font-size: 10px; color: var(--txt3); letter-spacing: .06em;
               text-transform: uppercase; margin-bottom: 5px; }
  .card .val { font-size: 22px; font-weight: 700; color: #fff; }
  .card .sub { font-size: 10px; color: var(--txt4); margin-top: 3px; }
  /* ── chart cards ── */
  .cc     { background: var(--bg2); border: 1px solid var(--bdr);
            border-radius: 6px; padding: 14px; margin-bottom: 12px; }
  .grid2  { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
  .cbox   { position: relative; height: 200px; }
  /* ── tables ── */
  table   { width: 100%; border-collapse: collapse; font-size: 11px; }
  th, td  { padding: 5px 8px; text-align: left;
            border-bottom: 1px solid var(--bdr); }
  th      { color: var(--txt2); font-weight: 600; font-size: 10px;
            letter-spacing: .05em; text-transform: uppercase; }
  td.num  { text-align: right; font-variant-numeric: tabular-nums; }
  tr.fl-hard td { background: #200f0f; color: var(--red); }
  tr.fl-soft td { background: #1e1800; color: var(--ylw); }
  tr.fl-ok   td { color: var(--txt4); }
  tr.fl-unk  td { color: var(--txt4); opacity: .6; }
  /* ── verdict chips ── */
  .chip-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }
  .chip  { display: inline-flex; flex-direction: column; align-items: center;
           width: 44px; padding: 4px 2px; border-radius: 4px;
           font-size: 9px; font-weight: 700; line-height: 1.4;
           cursor: default; }
  .chip .n { font-size: 10px; font-weight: 400; color: #666; margin-top: 1px; }
  .chip-Validated,.chip-Confirmed       { background:#0e2318; color:var(--grn); }
  .chip-ProductiveDeviation             { background:#0b1e26; color:var(--blu); }
  .chip-Mixed,.chip-PyrrhicVictory      { background:#241b00; color:var(--ylw); }
  .chip-Inconclusive                    { background:#1c1f26; color:#888; }
  .chip-Regressed,.chip-Refuted,
  .chip-GoodhartTrap                    { background:#200f0f; color:var(--red); }
  .chip-Unparsed                        { background:#22252d; color:#555; }
  /* ── inline tags ── */
  .tag { display:inline-block; padding:1px 5px; border-radius:3px;
         font-size:10px; font-weight:600; margin:1px; white-space:nowrap; }
  .t-ex    { background:#200f0f; color:var(--red); }
  .t-add   { background:#0e2318; color:var(--grn); }
  .t-dc    { background:#241b00; color:var(--ylw); }
  .t-gh    { background:#1e1e10; color:#c8c860; }
  .t-warn  { background:#1a1a2e; color:#9898c8; }
  .t-retry { background:#22102a; color:#d080d0; }
  .dim     { color:var(--txt4); }
</style>
</head>
<body>

<h1>ARD Pipeline — Triage Report</h1>
<div class="meta">
  Campaign: <code>{LABEL}</code> &nbsp;·&nbsp;
  Generated: <code id="ts"></code>
</div>

<div id="root"></div>

<script>
const D    = {DATA_JSON};
const root = document.getElementById('root');

document.getElementById('ts').textContent =
  new Date().toISOString().replace('T',' ').slice(0,19);

// ── formatting helpers ──────────────────────────────────────────────────────
function fmt(v, d=3)   { if (v==null) return '—'; return (+v).toFixed(d); }
function pct(v)        { if (v==null) return '—'; return (v*100).toFixed(1)+'%'; }
function dpp(v)        { if (v==null) return '—';
                          return (v>=0?'+':'')+v.toFixed(1)+'pp'; }
function dash(x)       { return x || '<span class="dim">—</span>'; }

// ── verdict helpers ─────────────────────────────────────────────────────────
function chipClass(s)  { return 'chip chip-'+(s||'Unparsed').replace(/[^A-Za-z]/g,''); }
function short(s) {
  return ({Validated:'VAL',Confirmed:'CON','Productive Deviation':'DEV',
           Mixed:'MIX','Pyrrhic Victory':'PYR',Regressed:'REG',
           Refuted:'REF','Goodhart Trap':'GHT',Inconclusive:'INC'})[s]
    || (s||'?').slice(0,3).toUpperCase();
}

const PHASES = ['validator','strategist','organizer','research_lead','dispatcher','coder'];
const PC = { validator:'#e15759', strategist:'#f28e2b', organizer:'#edc948',
             research_lead:'#76b7b2', dispatcher:'#b07aa1', coder:'#4e79a7' };
const gc = 'rgba(255,255,255,0.05)';
const tc = '#555';

function baseOpts(xLabel, yLabel) {
  return {
    animation: false,
    scales: {
      x: { title:{display:true,text:xLabel,color:tc}, ticks:{color:tc}, grid:{color:gc} },
      y: { title:{display:true,text:yLabel,color:tc}, ticks:{color:tc}, grid:{color:gc} },
    },
    plugins: { legend:{ labels:{color:'#aaa',boxWidth:10,font:{size:10}} } },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// HEADLINE CARDS
// ─────────────────────────────────────────────────────────────────────────────
{
  const wrap = document.createElement('div');
  wrap.className = 'cards';
  const wall = D.total_wall_s ? (D.total_wall_s/60).toFixed(1)+' min' : '—';
  const hardViol = D.iterations.filter(i=>i.floor&&i.floor.status==='hard_violation').length;
  [
    { lbl:'Iterations',  val:D.iteration_count,         sub:'' },
    { lbl:'Wall time',   val:wall,                      sub:'' },
    { lbl:'Peak PSR',    val:pct(D.peak_psr),           sub:'population success rate' },
    { lbl:'Final PSR',   val:pct(D.final_psr),          sub:'last iteration' },
    { lbl:'Collapses',   val:D.collapse_count,          sub:'PSR < threshold' },
    { lbl:'Floor Viol.', val:hardViol,
      sub: hardViol > 0 ? 'hard violations' : 'all compliant' },
  ].forEach(c => {
    wrap.innerHTML += `<div class="card">
      <div class="lbl">${c.lbl}</div>
      <div class="val" style="${c.lbl==='Floor Viol.'&&hardViol>0?'color:#e66e6e':''}">${c.val}</div>
      <div class="sub">${c.sub}</div>
    </div>`;
  });
  root.appendChild(wrap);
}

// ─────────────────────────────────────────────────────────────────────────────
// PSR TRAJECTORY
// ─────────────────────────────────────────────────────────────────────────────
{
  const cc = document.createElement('div');
  cc.className = 'cc';
  cc.innerHTML = '<h2>PSR Trajectory</h2><div class="cbox"><canvas id="cPSR"></canvas></div>';
  root.appendChild(cc);

  const iters   = D.iterations.map(i => i.iter);
  const psrPct  = D.iterations.map(i => i.psr     != null ? i.psr*100     : null);
  const centPct = D.iterations.map(i => i.centered != null ? i.centered*100 : null);

  // Point colour encodes verdict
  const ptCol = D.iterations.map(i => {
    const s = i.validator_status;
    if (!s||s==='Unparsed')                              return '#444';
    if (s==='Validated'||s==='Confirmed')                return '#6ee093';
    if (s==='Productive Deviation')                      return '#76b7b2';
    if (s==='Mixed'||s==='Pyrrhic Victory')              return '#e6c46e';
    if (s==='Regressed'||s==='Refuted'||s==='Goodhart Trap') return '#e66e6e';
    return '#888';
  });

  new Chart(document.getElementById('cPSR'), {
    type: 'line',
    data: { labels: iters, datasets: [
      { label:'PSR (%)', data:psrPct,
        borderColor:'#4e79a7', backgroundColor:'rgba(78,121,167,.12)',
        tension:.2, fill:true, spanGaps:false,
        pointRadius:5, pointBackgroundColor:ptCol, pointBorderColor:ptCol },
      { label:'Centered (%)', data:centPct,
        borderColor:'#59a14f', borderDash:[4,3],
        tension:.2, fill:false, spanGaps:false, pointRadius:3 },
    ]},
    options: {
      ...baseOpts('Iteration','Success rate (%)'),
      scales: {
        x: { title:{display:true,text:'Iteration',color:tc}, ticks:{color:tc},
             grid:{color:gc} },
        y: { min:0, max:105, title:{display:true,text:'% success',color:tc},
             ticks:{color:tc, callback:v=>v+'%'}, grid:{color:gc} },
      },
      plugins: {
        legend:{ labels:{color:'#aaa',boxWidth:10,font:{size:10}} },
        tooltip:{ callbacks:{
          afterLabel: ctx => {
            const it = D.iterations[ctx.dataIndex];
            const v  = it.validator_status || '—';
            const f  = it.floor ? it.floor.label : '';
            return [`  verdict: ${v}`, f ? `  floor: ${f}` : ''].filter(Boolean);
          }
        }}
      },
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// VERDICT TIMELINE  (chip row)
// ─────────────────────────────────────────────────────────────────────────────
{
  const cc = document.createElement('div');
  cc.className = 'cc';
  cc.innerHTML = '<h2>Validator Verdict Timeline</h2><div class="chip-row" id="vchips"></div>';
  root.appendChild(cc);
  const row = document.getElementById('vchips');
  D.iterations.forEach(it => {
    const s    = it.validator_status || 'Unparsed';
    const star = (it.floor && it.floor.status === 'hard_violation') ? '★' : '';
    row.innerHTML += `<div class="${chipClass(s)}"
        title="${s}&#10;${it.floor ? it.floor.label : ''}">
      ${short(s)}${star}
      <span class="n">${it.iter}</span>
    </div>`;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// FLOOR RULE COMPLIANCE TABLE
// ─────────────────────────────────────────────────────────────────────────────
{
  const hard = D.iterations.filter(i=>i.floor&&i.floor.status==='hard_violation').length;
  const soft = D.iterations.filter(i=>i.floor&&i.floor.status==='soft_violation').length;
  const cc = document.createElement('div');
  cc.className = 'cc';
  cc.innerHTML = `<h2>Floor Rule Compliance
    <span style="font-size:11px;margin-left:10px;
      color:${hard>0?'#e66e6e':'#6ee093'}">${hard} hard</span>
    <span style="font-size:11px;margin-left:6px;
      color:${soft>0?'#e6c46e':'#888'}">${soft} soft</span>
  </h2>`;
  const tbl = document.createElement('table');
  tbl.innerHTML = `<thead><tr>
    <th>Iter</th><th>Baseline PSR</th><th>Actual PSR</th><th>Δ pp</th>
    <th>Verdict</th><th>Assessment</th>
  </tr></thead>`;
  const tb = document.createElement('tbody');
  D.iterations.forEach(it => {
    const fl = it.floor || {};
    const rc = fl.status==='hard_violation' ? 'fl-hard'
             : fl.status==='soft_violation' ? 'fl-soft'
             : fl.status==='ok'             ? 'fl-ok'
             : 'fl-unk';
    tb.innerHTML += `<tr class="${rc}">
      <td>${it.iter}</td>
      <td class="num">${pct(it.baseline_psr)}</td>
      <td class="num">${pct(it.psr)}</td>
      <td class="num">${dpp(fl.delta_pp)}</td>
      <td>${it.validator_status || '—'}</td>
      <td>${fl.label || '—'}</td>
    </tr>`;
  });
  tbl.appendChild(tb);
  cc.appendChild(tbl);
  root.appendChild(cc);
}

// ─────────────────────────────────────────────────────────────────────────────
// CODE INTEGRITY TABLE
// ─────────────────────────────────────────────────────────────────────────────
{
  const cc = document.createElement('div');
  cc.className = 'cc';
  cc.innerHTML = '<h2>Code Integrity per Iteration</h2>';
  const tbl = document.createElement('table');
  tbl.innerHTML = `<thead><tr>
    <th>Iter</th><th>Comps</th>
    <th>Excised</th><th>Added</th>
    <th style="color:#59a14f">+Lines</th><th style="color:#e15759">−Lines</th>
    <th>Double-count</th><th>Ghost vars</th>
    <th>Retries</th><th>Warnings</th>
  </tr></thead>`;
  const tb = document.createElement('tbody');
  D.iterations.forEach(it => {
    const ex = (it.excised_components||[]).map(e=>`<span class="tag t-ex">${e}</span>`).join('');
    const ad = (it.added_components||[]).map(a=>`<span class="tag t-add">${a}</span>`).join('');
    const dc = (it.double_count_flags||[]).map(f=>
      `<span class="tag t-dc" title="Shared: ${(f.shared_r_vars||[]).join(', ')}">
        ${f.component_a}↔${f.component_b}</span>`).join('');
    const gh = (it.ghost_vars||[]).map(g=>`<span class="tag t-gh">${g}</span>`).join('');
    const wr = (it.parse_warnings||[])
      .filter(w=>!w.startsWith('iter1_no_prev')&&w!=='ledger_post_mortem_pending')
      .map(w=>`<span class="tag t-warn">${w}</span>`).join('');
    const rt = it.coder_retries > 0
      ? `<span class="tag t-retry">${it.coder_retries}✗ <span style="opacity:.6;font-size:9px">${it.retry_src}</span></span>`
      : '';

    tb.innerHTML += `<tr>
      <td>${it.iter}</td>
      <td class="num">${it.n_components ?? '—'}</td>
      <td>${dash(ex)}</td><td>${dash(ad)}</td>
      <td class="num" style="color:#59a14f">${it.lines_added  ?? '—'}</td>
      <td class="num" style="color:#e15759">${it.lines_removed ?? '—'}</td>
      <td>${dash(dc)}</td><td>${dash(gh)}</td>
      <td>${dash(rt)}</td><td>${dash(wr)}</td>
    </tr>`;
  });
  tbl.appendChild(tb);
  cc.appendChild(tbl);
  root.appendChild(cc);
}

// ─────────────────────────────────────────────────────────────────────────────
// TOKEN CONSUMPTION + STRATEGIST THINKING DEPTH
// ─────────────────────────────────────────────────────────────────────────────
if (D.chat_rows && D.chat_rows.length) {
  const maxIter = Math.max(...D.chat_rows.map(r=>r.iteration||0));
  const iterLabels = Array.from({length:maxIter}, (_,i)=>i+1);

  const grid = document.createElement('div');
  grid.className = 'grid2';
  root.appendChild(grid);

  // ── Left: gen tokens stacked by phase ───────────────────────────────────
  const tokCard = document.createElement('div');
  tokCard.className = 'cc';
  tokCard.innerHTML = '<h2>Gen Tokens per Iteration (by phase)</h2>'
                    + '<div class="cbox"><canvas id="cTok"></canvas></div>';
  grid.appendChild(tokCard);

  const tokDs = PHASES.map(p => ({
    label: p,
    data: iterLabels.map(i => {
      const rows = D.chat_rows.filter(r=>r.iteration===i&&r.phase===p);
      return rows.reduce((s,r)=>s+(r.gen_tokens||0),0);
    }),
    backgroundColor: PC[p],
  }));

  new Chart(document.getElementById('cTok'), {
    type:'bar',
    data:{ labels:iterLabels, datasets:tokDs },
    options:{
      ...baseOpts('Iteration','Gen tokens'),
      scales:{
        x:{ stacked:true, title:{display:true,text:'Iteration',color:tc},
            ticks:{color:tc}, grid:{color:gc} },
        y:{ stacked:true, title:{display:true,text:'Gen tokens',color:tc},
            ticks:{color:tc}, grid:{color:gc} },
      },
      animation:false,
    }
  });

  // ── Right: strategist thinking depth (apportioned estimate) ─────────────
  const thinkCard = document.createElement('div');
  thinkCard.className = 'cc';
  thinkCard.innerHTML = '<h2>Strategist Thinking Depth (est. tokens)</h2>'
                      + '<div class="cbox"><canvas id="cThink"></canvas></div>';
  grid.appendChild(thinkCard);

  const thinkVals = iterLabels.map(i => {
    const rows = D.chat_rows.filter(r=>r.iteration===i&&r.phase==='strategist');
    return rows.reduce((s,r)=>s+(r.think_tokens||0),0);
  });
  // Red bar when gen tokens > 0 but thinking estimate is 0 (no thinking trace)
  const thinkColors = iterLabels.map(i => {
    const rows = D.chat_rows.filter(r=>r.iteration===i&&r.phase==='strategist');
    const gen   = rows.reduce((s,r)=>s+(r.gen_tokens||0),0);
    const think = rows.reduce((s,r)=>s+(r.think_tokens||0),0);
    return (gen>0 && think===0) ? '#e15759' : '#f28e2b';
  });

  new Chart(document.getElementById('cThink'), {
    type:'bar',
    data:{
      labels: iterLabels,
      datasets:[{
        label:'Thinking (est.)',
        data: thinkVals,
        backgroundColor: thinkColors,
        borderRadius: 3,
      }]
    },
    options:{
      ...baseOpts('Iteration','Est. thinking tokens'),
      animation:false,
    }
  });
}
</script>
</body>
</html>
"""


# ===========================================================================
# Output writers
# ===========================================================================

def write_html_report(data: dict, out_path: Path) -> None:
    html = (TRIAGE_REPORT_TEMPLATE
            .replace("{LABEL}",     data["campaign_tag"])
            .replace("{DATA_JSON}", json.dumps(data, default=str)))
    out_path.write_text(html, encoding="utf-8")


def build_summary_json(data: dict) -> dict:
    """Extract machine-readable headline stats from the full triage data dict."""
    floor_hard = sum(
        1 for it in data["iterations"]
        if (it.get("floor") or {}).get("status") == "hard_violation"
    )
    floor_soft = sum(
        1 for it in data["iterations"]
        if (it.get("floor") or {}).get("status") == "soft_violation"
    )
    total_retries = sum(it.get("coder_retries", 0) for it in data["iterations"])

    return {
        "campaign_tag":             data["campaign_tag"],
        "model":                    data["model"],
        "iteration_count":          data["iteration_count"],
        "total_wall_min":           round(data["total_wall_s"] / 60, 1)
                                    if data.get("total_wall_s") else None,
        "peak_psr":                 data["peak_psr"],
        "final_psr":                data["final_psr"],
        "collapse_count":           data["collapse_count"],
        "recovery_count":           data["recovery_count"],
        "stability_score":          data["stability_score"],
        "validator_verdicts":       data["validator_verdicts"],
        "floor_hard_violations":    floor_hard,
        "floor_soft_violations":    floor_soft,
        "total_coder_retries":      total_retries,
        "iterations_with_warnings": data["iterations_with_warnings"],
    }


# ===========================================================================
# Top-level analysis function
# ===========================================================================

def analyze_single(
    campaign_path: Path,
    cfg:     AggregationConfig | None = None,
    verbose: bool = True,
) -> dict:
    """
    Run the full triage analysis for one campaign.
    Writes triage_report.html and triage_summary.json under
    {campaign}/{model_dir}/reports/ and returns the summary dict.
    """
    if verbose:
        print(f"\n📊  Analyzing: {campaign_path.name}")

    data    = build_triage_data(campaign_path, cfg)
    paths   = RunPaths(campaign_path)
    out_dir = paths.model_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "triage_report.html"
    json_path = out_dir / "triage_summary.json"

    write_html_report(data, html_path)
    summary = build_summary_json(data)
    json_path.write_text(json.dumps(summary, indent=2))

    if verbose:
        _print_summary(summary)
        print(f"✅  Report  : {html_path}")
        print(f"✅  Summary : {json_path}\n")

    return summary


def _print_summary(s: dict) -> None:
    wall  = f"{s['total_wall_min']} min" if s.get("total_wall_min") is not None else "?"
    peak  = f"{s['peak_psr']*100:.1f}%"  if s.get("peak_psr")  is not None else "?"
    final = f"{s['final_psr']*100:.1f}%" if s.get("final_psr") is not None else "?"

    print(f"\n{'='*62}")
    print(f"  ARD TRIAGE  —  {s['campaign_tag']}")
    print(f"{'='*62}")
    print(f"  Model         : {s.get('model', '?')}")
    print(f"  Iterations    : {s['iteration_count']}")
    print(f"  Wall time     : {wall}")
    print(f"  Peak PSR      : {peak}")
    print(f"  Final PSR     : {final}")
    print(f"  Collapses     : {s['collapse_count']}   Recoveries: {s['recovery_count']}")
    print(f"  Coder retries : {s['total_coder_retries']} total")
    if s["floor_hard_violations"] or s["floor_soft_violations"]:
        print(f"  ⚠  Floor rule : {s['floor_hard_violations']} hard  /  "
              f"{s['floor_soft_violations']} soft violations")
    else:
        print(f"  ✓  Floor rule : all compliant")
    verdicts = s.get("validator_verdicts") or {}
    if verdicts:
        vstr = "  ".join(
            f"{k}:{v}" for k, v in
            sorted(verdicts.items(), key=lambda x: -x[1])
        )
        print(f"  Verdicts      : {vstr}")
    if s["iterations_with_warnings"]:
        print(f"  ⚠  {s['iterations_with_warnings']} iteration(s) with parse/code warnings")
    print(f"{'='*62}\n")


# ===========================================================================
# CLI
# ===========================================================================

def _resolve_campaign_path(args: argparse.Namespace) -> Path:
    if getattr(args, "campaign_path", None):
        p = Path(args.campaign_path)
        if not p.exists():
            raise FileNotFoundError(f"Campaign path not found: {p}")
        return p
    if getattr(args, "campaign", None):
        exp_root = (Path(args.experiments_root)
                    if args.experiments_root else _DEFAULT_EXPERIMENTS_DIR)
        p = exp_root / args.campaign
        if not p.exists():
            raise FileNotFoundError(
                f"Campaign '{args.campaign}' not found under {exp_root}\n"
                f"  Tried: {p}"
            )
        return p
    raise ValueError("Supply --campaign CAMPAIGN_TAG or --campaign-path PATH")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Per-run triage analysis for the ARD pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 analyze_run.py --campaign 2025-05-10_spin_crash_10cycles\n"
            "  python3 analyze_run.py --campaign-path /abs/path/to/campaign\n"
            "  python3 analyze_run.py --campaign 2025-05-10_... --quiet\n"
        ),
    )
    ap.add_argument("--campaign", "-c",
                    help="Campaign tag (looked up under --experiments-root).")
    ap.add_argument("--campaign-path",
                    help="Direct path to campaign directory (overrides --campaign).")
    ap.add_argument("--experiments-root", default=None,
                    help=f"Root experiments/ directory "
                         f"(default: {_DEFAULT_EXPERIMENTS_DIR}).")
    ap.add_argument("--collapse-threshold", type=float, default=0.10,
                    help="PSR fraction below which an iteration is a collapse "
                         "(default: 0.10).")
    ap.add_argument("--recovery-threshold", type=float, default=0.50,
                    help="PSR fraction at which a post-collapse iter counts as "
                         "recovery (default: 0.50).")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Suppress terminal summary (files still written).")
    args = ap.parse_args()

    try:
        campaign_path = _resolve_campaign_path(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        ap.print_usage(sys.stderr)
        sys.exit(1)

    cfg = AggregationConfig(
        collapse_threshold=args.collapse_threshold,
        recovery_threshold=args.recovery_threshold,
    )

    try:
        analyze_single(campaign_path, cfg=cfg, verbose=not args.quiet)
    except Exception as exc:
        print(f"Error during analysis: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
