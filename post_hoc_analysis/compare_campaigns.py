#!/usr/bin/env python3
"""
compare_campaigns.py

Handles two comparison levels automatically by grouping on model name:

  Level 1 - Configuration ablation (same model, different pipeline config):
    Campaign A: gemma4:26b + old_val_prompt  -> 6 runs
    Campaign B: gemma4:26b + new_val_prompt  -> 6 runs
    Produces one section for gemma4:26b comparing A vs B.

  Level 2 - Model ablation (different models, equivalent conditions):
    Campaign A: [gemma4:26b, qwen3:14b]
    Campaign B: [gemma4:26b, qwen3:14b]
    Produces one section per model, each comparing A vs B.

  Models appearing in only one campaign are excluded from statistical
  comparison (no counterpart). Logged to stdout during load.

  Use --model to restrict output to a substring of the model name.

Usage:
    python3 compare_campaigns.py \
        --campaign-dirs post_hoc_analysis/outputs/campaign_A \
                        post_hoc_analysis/outputs/campaign_B \
        --labels "Config A" "Config B" \
        --baseline 0 \
        --model gemma4 \
        --output-dir post_hoc_analysis/comparisons/A_vs_B

Outputs:
    comparison.html        - self-contained dashboard
    comparison_summary.csv - one row per model x metric x campaign pair

Requires: scipy  (pip install scipy)
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # project root for src imports

try:
    from scipy import stats as _scipy_stats
except ImportError:
    print("ERROR: scipy required.  pip install scipy", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _mean(vals):
    vs = [v for v in vals if v is not None]
    return sum(vs) / len(vs) if vs else None

def _std(vals):
    vs = [v for v in vals if v is not None]
    if len(vs) < 2: return None
    m = sum(vs) / len(vs)
    return (sum((v - m) ** 2 for v in vs) / len(vs)) ** 0.5

def cliffs_delta(a, b):
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if not a or not b: return None
    n = len(a) * len(b)
    return (sum(1 for x in a for y in b if x > y)
          - sum(1 for x in a for y in b if x < y)) / n

def interpret_delta(d):
    if d is None: return "n/a"
    ad = abs(d)
    if   ad < 0.147: return "negligible"
    elif ad < 0.330: return "small"
    elif ad < 0.474: return "medium"
    else:            return "large"

def mann_whitney(a, b):
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if len(a) < 2 or len(b) < 2: return None, None
    try:
        r = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
        return float(r.statistic), float(r.pvalue)
    except Exception:
        return None, None

def fmt_p(p):
    if p is None: return "n/a"
    if p < 0.001: return "< 0.001"
    return f"{p:.3f}"

def fmt_d(d):
    if d is None: return "n/a"
    sym = "+" if d > 0 else ("-" if d < 0 else "0")
    return f"{sym}{abs(d):.3f}"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _safe(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict): return default
        cur = cur.get(k, default)
        if cur is None: return default
    return cur

def _extract_model_data(model_data, campaign_label):
    """Build a self-contained metrics dict for one ModelSummary."""
    run_summaries = model_data.get("run_summaries", [])
    runs = []

    for rs in run_summaries:
        iters   = rs.get("iterations", [])
        n_iters = len(iters)

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

        prop: dict = {}
        for it in iters:
            for k, v in (_safe(it, "cognition", "proposal_type_counts") or {}).items():
                prop[k] = prop.get(k, 0) + v
        pt = sum(prop.values()) or 1

        runs.append({
            "tag":           rs.get("campaign_tag", ""),
            "peak_psr":      rs.get("peak_psr"),
            "final_psr":     rs.get("iter_final_psr"),
            "stability":     rs.get("stability_score"),
            "collapses":     rs.get("collapse_count"),
            "recoveries":    rs.get("recovery_count"),
            "n_iters":       n_iters,
            "verdicts":      rs.get("validator_verdicts", {}),
            "dc_rate":       n_dc    / n_iters if n_iters else None,
            "ghost_rate":    n_ghost / n_iters if n_iters else None,
            "excision_rate": n_excised_total / n_iters if n_iters else None,
            "prop_modification": prop.get("modification", 0) / pt,
            "prop_addition":     prop.get("addition",     0) / pt,
            "prop_cluster":      prop.get("cluster",      0) / pt,
            "prop_unknown":      prop.get("unknown",      0) / pt,
        })

    max_iter = max((r["n_iters"] for r in runs), default=0)
    trajectory = []
    for i in range(1, max_iter + 1):
        vals = []
        for rs in run_summaries:
            it = next((x for x in rs.get("iterations", []) if x.get("iteration") == i), None)
            if it:
                v = _safe(it, "outcomes", "population_success_rate")
                if v is not None: vals.append(v)
        m = _mean(vals); s = _std(vals) or 0.0
        trajectory.append({
            "iter": i, "psr_mean": m, "psr_std": s,
            "psr_upper": (m or 0) + s,
            "psr_lower": max(0.0, (m or 0) - s),
        })

    vt_raw: dict = {}
    for rs in run_summaries:
        for v, cnt in rs.get("validator_verdicts", {}).items():
            vt_raw[v] = vt_raw.get(v, 0) + cnt
    vt_sum = sum(vt_raw.values()) or 1

    return {
        "campaign_label": campaign_label,
        "n_runs":         len(runs),
        "runs":           runs,
        "trajectory":     trajectory,
        "max_iter":       max_iter,
        "verdict_totals": vt_raw,
        "verdict_fracs":  {v: c / vt_sum for v, c in vt_raw.items()},
    }

def load_campaign(output_dir, label):
    """Load ALL models from aggregated_data.json."""
    audit_path = Path(output_dir) / "aggregated_data.json"
    if not audit_path.is_file():
        raise FileNotFoundError(
            f"aggregated_data.json not found in {output_dir}\n"
            f"Run aggregate_runs.py on this campaign first."
        )
    with audit_path.open() as f:
        audit = json.load(f)
    if not audit.get("models"):
        raise ValueError(f"No models in {audit_path}")

    models = {}
    for md in audit["models"]:
        name = md.get("strategist_model", "unknown")
        models[name] = _extract_model_data(md, label)

    return {"label": label, "campaign_dir": str(output_dir), "models": models}


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

METRIC_DEFS = [
    ("peak_psr",      "Peak PSR",          "higher_better"),
    ("stability",     "Stability sigma",   "lower_better"),
    ("collapses",     "Collapse count",    "lower_better"),
    ("recoveries",    "Recovery count",    "higher_better"),
    ("dc_rate",       "Double-count rate", "lower_better"),
    ("ghost_rate",    "Ghost var rate",    "lower_better"),
]

VERDICT_ORDER = [
    "Validated", "Confirmed", "Productive Deviation",
    "Mixed", "Pyrrhic Victory", "Inconclusive",
    "Refuted", "Regressed", "Goodhart Trap", "Unparsed",
]

VERDICT_COLORS = {
    "Validated":           "#1e4a2b", "Confirmed":           "#1e4a2b",
    "Productive Deviation":"#2a4a1e", "Mixed":               "#4a3e1e",
    "Pyrrhic Victory":     "#3e3a1e", "Inconclusive":        "#2a2d35",
    "Refuted":             "#4a1e1e", "Regressed":           "#4a1e1e",
    "Goodhart Trap":       "#3a1a2a", "Unparsed":            "#222",
}

def _compare(baseline, treatment):
    results = {}
    for key, label, direction in METRIC_DEFS:
        b = [r[key] for r in baseline["runs"] if r[key] is not None]
        t = [r[key] for r in treatment["runs"] if r[key] is not None]
        U, p  = mann_whitney(t, b)
        delta = cliffs_delta(t, b)
        beneficial = (
            (delta is not None and delta > 0 and direction == "higher_better") or
            (delta is not None and delta < 0 and direction == "lower_better")
        )
        results[key] = {
            "label":       label,     "direction":   direction,
            "b_mean":      _mean(b),  "b_std":       _std(b),
            "t_mean":      _mean(t),  "t_std":       _std(t),
            "U":           U,          "p":           p,
            "p_fmt":       fmt_p(p),   "delta":       delta,
            "delta_fmt":   fmt_d(delta),
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

def build_payload(campaigns, baseline_idx, model_filter=None):
    all_names = set()
    for c in campaigns:
        all_names |= set(c["models"].keys())

    if model_filter:
        filtered = {m for m in all_names if model_filter.lower() in m.lower()}
        if not filtered:
            print(f"WARNING: --model '{model_filter}' matched nothing in "
                  f"{sorted(all_names)}", file=sys.stderr)
        all_names = filtered

    all_verdicts = set()
    for c in campaigns:
        for md in c["models"].values():
            all_verdicts |= set(md["verdict_totals"].keys())
    verdict_order = [v for v in VERDICT_ORDER if v in all_verdicts]
    verdict_order += sorted(all_verdicts - set(VERDICT_ORDER))

    model_groups = []
    for model_name in sorted(all_names):
        entities = []
        for i, c in enumerate(campaigns):
            if model_name not in c["models"]: continue
            entity = dict(c["models"][model_name])
            entity["campaign_label"] = c["label"]
            entity["campaign_idx"]   = i
            entity["is_baseline"]    = (i == baseline_idx)
            entities.append(entity)

        if len(entities) < 2:
            continue  # no counterpart — skip

        bl = next((e for e in entities if e["is_baseline"]), entities[0])
        comparisons = [_compare(bl, e) for e in entities if e is not bl]

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


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

COMPARISON_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ARD Campaign Comparison</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
     background:#0f1115;color:#e6e6e6;margin:0;padding:24px;font-size:14px;}
h1{font-size:22px;margin:0 0 6px 0;}
h2{font-size:16px;margin:22px 0 8px 0;color:#a8c5f0;
   border-bottom:1px solid #2a2d35;padding-bottom:4px;}
h3{font-size:13px;margin:14px 0 6px 0;color:#d0d0d0;}
.meta{color:#888;font-size:12px;margin-bottom:18px;}
.card{background:#181a20;border:1px solid #262931;border-radius:8px;padding:14px;margin:8px 0;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.cb{position:relative;height:260px;} .cs{position:relative;height:200px;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th,td{padding:6px 9px;text-align:left;border-bottom:1px solid #22252d;}
th{color:#a8c5f0;font-weight:600;white-space:nowrap;}
td.r{text-align:right;font-variant-numeric:tabular-nums;}
td.m{font-family:monospace;font-size:11px;}
.sig{color:#6ee093;font-weight:600;} .marg{color:#e6c46e;} .ns{color:#555;}
.good{color:#6ee093;} .bad{color:#e66e6e;}
.wb{background:#2e2108;border:1px solid #e6c46e44;border-radius:6px;
    padding:8px 12px;font-size:12px;color:#e6c46e;margin:6px 0;}
details>summary{cursor:pointer;padding:4px 0;color:#a8c5f0;font-size:13px;}
.sm{color:#888;font-size:11px;}
.pill{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;
      font-weight:600;border-left:3px solid transparent;padding-left:8px;}
.pb{background:#1e2a3a;color:#7ab3e0;} .pt{background:#1e2e24;color:#7ae0ab;}
.ms{border-top:2px solid #2a2d35;margin-top:28px;padding-top:4px;}
</style>
</head>
<body>
<h1>ARD Campaign Comparison</h1>
<div class="meta">Generated: <code id="ts"></code></div>
<div id="root"></div>
<script>
const DATA = __DATA_JSON__;
document.getElementById('ts').textContent =
  new Date().toISOString().replace('T',' ').slice(0,19);
const root = document.getElementById('root');
const CC = ['#4e79a7','#f28e2b','#59a14f','#e15759','#b07aa1','#76b7b2'];
const cc = i => CC[i % CC.length];
const fv = (v,d=3) => v == null ? '--' : (+v).toFixed(d);
const fp = v => v == null ? '--' : (v*100).toFixed(1)+'%';
const mn = a => { const v=a.filter(x=>x!=null); return v.length?v.reduce((a,b)=>a+b)/v.length:null; };
const sd = a => {
  const v=a.filter(x=>x!=null); if(v.length<2) return null;
  const m=mn(v); return Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/v.length);
};

// Campaign legend
(()=>{
  const d=document.createElement('div');
  d.style.cssText='display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 4px;align-items:center;';
  d.innerHTML='<span class="sm" style="color:#a8c5f0">Campaigns:</span>';
  DATA.campaign_labels.forEach((lbl,i)=>{
    const c=document.createElement('span');
    c.className='pill '+(i===DATA.baseline_idx?'pb':'pt');
    c.style.borderLeftColor=cc(i);
    c.textContent=(i===DATA.baseline_idx?'\u2605 baseline  ':'')+lbl;
    d.appendChild(c);
  });
  root.appendChild(d);
})();

DATA.model_groups.forEach(group=>{
  const sec=document.createElement('div');
  sec.className='ms'; root.appendChild(sec);

  const h2=document.createElement('h2');
  h2.textContent=group.model_name; sec.appendChild(h2);

  if(group.small_n){
    const w=document.createElement('div'); w.className='wb';
    w.textContent='Warning: N<4 in at least one entity. Minimum two-sided Mann-Whitney p at N=3 is 0.10. Treat statistics as exploratory.';
    sec.appendChild(w);
  }

  // Entity chips
  (()=>{
    const d=document.createElement('div');
    d.style.cssText='display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px;';
    group.entities.forEach(e=>{
      const c=document.createElement('span');
      c.className='pill '+(e.is_baseline?'pb':'pt');
      c.style.borderLeftColor=cc(e.campaign_idx);
      c.textContent=(e.is_baseline?'\u2605 ':'')+e.campaign_label+'  N='+e.n_runs;
      d.appendChild(c);
    });
    sec.appendChild(d);
  })();

  // Headline metrics table
  if(group.comparisons.length>0)(()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>Headline Metrics</h3>';
    const tbl=document.createElement('table');
    let hdr='<thead><tr><th>Metric</th>';
    group.entities.forEach(e=>{
      hdr+=`<th style="border-left:2px solid ${cc(e.campaign_idx)}44">${e.campaign_label}</th>`;
    });
    group.comparisons.forEach(cmp=>{
      hdr+=`<th style="color:#888;font-weight:400" colspan="3">${cmp.treatment_label} vs baseline \u2014 p / \u03b4 / mag</th>`;
    });
    tbl.innerHTML=hdr+'</tr></thead>';
    const tb=document.createElement('tbody');
    DATA.metric_defs.forEach(({key,label,dir})=>{
      let row=`<tr><td>${label} <span class="sm">${dir==='higher_better'?'\u2191':'\u2193'}</span></td>`;
      group.entities.forEach(e=>{
        const v=e.runs.map(r=>r[key]).filter(x=>x!=null);
        const m=mn(v), s=sd(v);
        row+=`<td class="r" style="border-left:2px solid ${cc(e.campaign_idx)}44">`
           + `${fv(m)} <span class="sm">\u00b1${fv(s)}</span></td>`;
      });
      group.comparisons.forEach(cmp=>{
        const res=cmp.metrics[key]; if(!res){row+='<td colspan="3">--</td>';return;}
        const pc=res.significant?'sig':(res.marginal?'marg':'ns');
        const dc=res.beneficial?'good':(res.delta!=null&&res.delta!==0?'bad':'');
        row+=`<td class="r ${pc}">${res.p_fmt}</td>`
           + `<td class="r ${dc}">${res.delta_fmt}</td>`
           + `<td class="sm">${res.magnitude}</td>`;
      });
      tb.innerHTML+=row+'</tr>';
    });
    tbl.appendChild(tb); card.appendChild(tbl);
    const leg=document.createElement('div');
    leg.className='sm'; leg.style.marginTop='7px';
    leg.innerHTML='<span class="sig">\u25a0</span> p&lt;0.05 &nbsp;'
      +'<span class="marg">\u25a0</span> p&lt;0.10 &nbsp;'
      +'<span class="ns">\u25a0</span> p\u22650.10 &nbsp;&nbsp;'
      +'delta: <span class="good">+/- beneficial direction</span>';
    card.appendChild(leg); sec.appendChild(card);
  })();

  // PSR trajectory
  (()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>PSR Trajectory (mean \u00b1 1\u03c3)</h3><div class="cb"><canvas></canvas></div>';
    sec.appendChild(card);
    const maxI=Math.max(...group.entities.map(e=>e.max_iter));
    const labs=Array.from({length:maxI},(_,i)=>String(i+1));
    const ds=[];
    group.entities.forEach(e=>{
      const col=cc(e.campaign_idx);
      ds.push({label:'_u'+e.campaign_idx,
        data:labs.map((_,i)=>e.trajectory[i]?.psr_upper??null),
        borderWidth:0,pointRadius:0,fill:'+1',backgroundColor:col+'28',tension:0.25,spanGaps:true});
      ds.push({label:'_l'+e.campaign_idx,
        data:labs.map((_,i)=>e.trajectory[i]?.psr_lower??null),
        borderWidth:0,pointRadius:0,fill:false,tension:0.25,spanGaps:true});
      ds.push({label:e.campaign_label,
        data:labs.map((_,i)=>e.trajectory[i]?.psr_mean??null),
        borderColor:col,borderWidth:2.5,pointRadius:3,fill:false,tension:0.25,spanGaps:true});
    });
    new Chart(card.querySelector('canvas'),{type:'line',data:{labels:labs,datasets:ds},
      options:{scales:{x:{title:{display:true,text:'Iteration'}},y:{title:{display:true,text:'PSR'},min:0,max:1}},
        plugins:{legend:{labels:{color:'#ccc',boxWidth:12,filter:i=>!i.text.startsWith('_')}}},
        animation:false}});
  })();

  // Strip plot + verdict
  const g4=document.createElement('div'); g4.className='g2'; sec.appendChild(g4);

  (()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>Peak PSR per Run</h3><div class="cs"><canvas></canvas></div>'
      +'<div class="sm" style="margin-top:4px">Each dot = one run. Diamond = mean.</div>';
    g4.appendChild(card);
    const ds=group.entities.map(e=>({
      label:e.campaign_label,
      data:e.runs.map((r,ri)=>({x:e.campaign_idx+(ri-(e.n_runs-1)/2)*0.12,y:r.peak_psr})),
      backgroundColor:cc(e.campaign_idx)+'cc',borderColor:cc(e.campaign_idx),
      pointRadius:7,borderWidth:1.5,
    }));
    group.entities.forEach(e=>{
      const m=mn(e.runs.map(r=>r.peak_psr)); if(m==null) return;
      ds.push({label:'_m'+e.campaign_idx,data:[{x:e.campaign_idx,y:m}],
        backgroundColor:cc(e.campaign_idx),borderColor:'#fff',
        pointRadius:10,pointStyle:'rectRot',borderWidth:2});
    });
    const idxs=[...new Set(group.entities.map(e=>e.campaign_idx))].sort();
    new Chart(card.querySelector('canvas'),{type:'scatter',data:{datasets:ds},
      options:{scales:{
        x:{type:'linear',min:Math.min(...idxs)-0.5,max:Math.max(...idxs)+0.5,
          ticks:{stepSize:1,callback:v=>{const e=group.entities.find(x=>x.campaign_idx===Math.round(v));return e?e.campaign_label:''}}},
        y:{title:{display:true,text:'Peak PSR'},min:0,max:1}},
        plugins:{legend:{labels:{color:'#ccc',boxWidth:10,filter:i=>!i.text.startsWith('_')}}},
        animation:false}});
  })();

  (()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>Validator Verdict Distribution</h3><div class="cs"><canvas></canvas></div>';
    g4.appendChild(card);
    const VC=DATA.verdict_colors;
    const ds=DATA.verdict_order.map(v=>({
      label:v,
      data:group.entities.map(e=>{const t=Object.values(e.verdict_totals).reduce((a,b)=>a+b,0)||1;return((e.verdict_totals[v]||0)/t)*100;}),
      backgroundColor:VC[v]||'#333',borderColor:(VC[v]||'#333')+'cc',borderWidth:1,
    }));
    new Chart(card.querySelector('canvas'),{type:'bar',
      data:{labels:group.entities.map(e=>e.campaign_label),datasets:ds},
      options:{indexAxis:'y',scales:{x:{stacked:true,title:{display:true,text:'%'},max:100},y:{stacked:true}},
        plugins:{legend:{labels:{color:'#ccc',boxWidth:10,font:{size:10}}}},animation:false}});
  })();

  // Proposal types + code integrity
  const g5=document.createElement('div'); g5.className='g2'; sec.appendChild(g5);

  (()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>Proposal Type Distribution</h3><div class="cs"><canvas></canvas></div>';
    g5.appendChild(card);
    const pt=[{k:'prop_modification',l:'Modification',c:'#4e79a7'},
              {k:'prop_addition',    l:'Addition',    c:'#59a14f'},
              {k:'prop_cluster',     l:'Cluster',     c:'#edc948'},
              {k:'prop_unknown',     l:'Unknown',     c:'#888'}];
    const ds=pt.map(({k,l,c})=>({label:l,
      data:group.entities.map(e=>mn(e.runs.map(r=>r[k]))*100),
      backgroundColor:c+'cc',borderColor:c,borderWidth:1}));
    new Chart(card.querySelector('canvas'),{type:'bar',
      data:{labels:group.entities.map(e=>e.campaign_label),datasets:ds},
      options:{scales:{x:{stacked:true},y:{stacked:true,title:{display:true,text:'%'},max:100}},
        plugins:{legend:{labels:{color:'#ccc',boxWidth:10}}},animation:false}});
  })();

  (()=>{
    const card=document.createElement('div'); card.className='card';
    card.innerHTML='<h3>Code Structural Integrity (AST)</h3><div class="cs"><canvas></canvas></div>';
    g5.appendChild(card);
    const im=[{k:'dc_rate',   l:'Double-count %',c:'#e6c46e',s:100},
              {k:'ghost_rate',l:'Ghost var %',   c:'#c8c860',s:100},
              {k:'excision_rate',l:'Excisions/iter',c:'#59a14f',s:1}];
    const ds=im.map(({k,l,c,s})=>({label:l,
      data:group.entities.map(e=>+(mn(e.runs.map(r=>r[k]).filter(x=>x!=null))*s||0).toFixed(3)),
      backgroundColor:c+'cc',borderColor:c,borderWidth:1}));
    new Chart(card.querySelector('canvas'),{type:'bar',
      data:{labels:group.entities.map(e=>e.campaign_label),datasets:ds},
      options:{scales:{x:{},y:{title:{display:true,text:'Rate / count'},min:0}},
        plugins:{legend:{labels:{color:'#ccc',boxWidth:10}}},animation:false}});
  })();

  // Expandable detail
  const dr=document.createElement('details'); dr.className='card';
  dr.innerHTML='<summary>Per-run Detail &amp; Statistical Breakdown</summary>';
  sec.appendChild(dr);

  const rt=document.createElement('table');
  rt.innerHTML='<thead><tr><th>Campaign</th><th>Run</th><th>Peak PSR</th>'
    +'<th>Final PSR</th><th>Stability</th><th>Collapses</th><th>Recoveries</th>'
    +'<th>DC rate</th><th>Ghost rate</th><th>Iters</th></tr></thead>';
  const rb=document.createElement('tbody');
  group.entities.forEach(e=>{
    e.runs.forEach(r=>{
      rb.innerHTML+=`<tr>
        <td style="color:${cc(e.campaign_idx)}">${e.is_baseline?'\u2605 ':''}${e.campaign_label}</td>
        <td class="m sm">${r.tag.split('_').slice(-1)[0]}</td>
        <td class="r">${fv(r.peak_psr)}</td><td class="r">${fv(r.final_psr)}</td>
        <td class="r">${fv(r.stability)}</td><td class="r">${r.collapses??'--'}</td>
        <td class="r">${r.recoveries??'--'}</td>
        <td class="r">${fp(r.dc_rate)}</td><td class="r">${fp(r.ghost_rate)}</td>
        <td class="r">${r.n_iters}</td></tr>`;
    });
  });
  rt.appendChild(rb); dr.appendChild(rt);

  group.comparisons.forEach(cmp=>{
    const div=document.createElement('div'); div.style.marginTop='14px';
    div.innerHTML=`<div class="sm" style="color:#a8c5f0;margin-bottom:5px">`
      +`${cmp.treatment_label} vs baseline (${cmp.baseline_label})</div>`;
    const t=document.createElement('table');
    t.innerHTML='<thead><tr><th>Metric</th><th>Baseline</th><th>Treatment</th>'
      +'<th>U</th><th>p-value</th><th>Cliff\'s delta</th><th>Magnitude</th><th>Direction</th></tr></thead>';
    const tb=document.createElement('tbody');
    Object.values(cmp.metrics).forEach(res=>{
      const pc=res.significant?'sig':(res.marginal?'marg':'ns');
      const dc=res.beneficial?'good':(res.delta!=null&&res.delta!==0?'bad':'');
      const dir=res.beneficial?'\u2713 favours treatment':(res.delta?'\u2717 favours baseline':'\u00b7');
      tb.innerHTML+=`<tr>
        <td>${res.label}</td>
        <td class="r">${fv(res.b_mean)} \u00b1 ${fv(res.b_std??0)}</td>
        <td class="r">${fv(res.t_mean)} \u00b1 ${fv(res.t_std??0)}</td>
        <td class="r">${res.U!=null?fv(res.U,1):'--'}</td>
        <td class="r ${pc}">${res.p_fmt}</td>
        <td class="r ${dc}">${res.delta_fmt}</td>
        <td class="sm">${res.magnitude}</td>
        <td class="sm ${res.beneficial?'good':'bad'}">${dir}</td></tr>`;
    });
    t.appendChild(tb); div.appendChild(t); dr.appendChild(div);
  });
});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Configuration diff header (Tier 3)
# ---------------------------------------------------------------------------

def _print_config_diff(label_a, comp_a, labs_a, label_b, comp_b, labs_b):
    """Print a human-readable config diff and axis count between two campaigns."""
    try:
        from src.run_manifest import diff_comparability as _diff, short as _short
    except ImportError:
        print("\n  [Config diff] src.run_manifest not importable — skipping diff.", file=sys.stderr)
        return

    _UNAVAIL = {"FORCED_MIXED", None}
    if comp_a in _UNAVAIL or comp_b in _UNAVAIL:
        print(f"\n  [Config diff] {label_a} vs {label_b}: comparability data unavailable.", file=sys.stderr)
        return

    diffs = _diff(comp_a, comp_b)
    print(f"\n{'='*70}")
    print(f"  Config diff: {label_a}  vs  {label_b}")
    print(f"{'='*70}")

    if not diffs:
        print("  NO CONFIGURATION DIFFERENCES")
        if comp_a == comp_b:
            return
    else:
        # Classify diffs into axes
        roles_model_changed: set[str] = set()
        roles_sampling_changed: set[str] = set()
        prompt_slots_changed: set[str] = set()
        code_slots_changed: set[str] = set()
        experiment_fields_changed: set[str] = set()
        training_fields_changed: set[str] = set()

        rendered_lines: list[str] = []

        for path, val_a, val_b in diffs:
            parts = path.split(".")
            if len(parts) >= 3 and parts[0] == "agents":
                role, field = parts[1], parts[2]
                if field == "model":
                    roles_model_changed.add(role)
                    rendered_lines.append(f"  {role} model: {val_a}  →  {val_b}")
                elif field == "sampling":
                    roles_sampling_changed.add(role)
                elif field == "prompt_system_hash":
                    slot = f"{role}_system"
                    prompt_slots_changed.add(slot)
                    v_a = labs_a["prompt_versions"].get(slot, "?") if labs_a else "?"
                    v_b = labs_b["prompt_versions"].get(slot, "?") if labs_b else "?"
                    rendered_lines.append(f"  {slot}: v{v_a}  →  v{v_b}")
                elif field == "prompt_user_hash":
                    slot = f"{role}_user"
                    prompt_slots_changed.add(slot)
                    v_a = labs_a["prompt_versions"].get(slot, "?") if labs_a else "?"
                    v_b = labs_b["prompt_versions"].get(slot, "?") if labs_b else "?"
                    rendered_lines.append(f"  {slot}: v{v_a}  →  v{v_b}")
                # model_digest silently follows model — not an independent axis
            elif len(parts) >= 2 and parts[0] == "code":
                slot = parts[1].replace("_hash", "")
                if slot in ("analysis", "ledger"):
                    code_slots_changed.add(slot)
                    v_a = labs_a["code_versions"].get(slot, "?") if labs_a else "?"
                    v_b = labs_b["code_versions"].get(slot, "?") if labs_b else "?"
                    rendered_lines.append(f"  {slot}: v{v_a}  →  v{v_b}")
            elif len(parts) >= 2 and parts[0] == "experiment":
                field = parts[1]
                experiment_fields_changed.add(field)
                _va = _short(val_a) if isinstance(val_a, str) and len(val_a) == 64 else val_a
                _vb = _short(val_b) if isinstance(val_b, str) and len(val_b) == 64 else val_b
                rendered_lines.append(f"  {field}: {_va}  →  {_vb}")
            elif parts[0] == "training":
                if len(parts) >= 3 and parts[1] in ("learning_rate", "ent_coef"):
                    # Schedule sub-dicts map to the registry code-slots lr_schedule / ent_schedule.
                    # Whatever subfield differs (type / initial / final / fn_hash), the schedule
                    # domain counts as exactly ONE axis — the set dedupes the slot.
                    slot = "lr_schedule" if parts[1] == "learning_rate" else "ent_schedule"
                    code_slots_changed.add(slot)
                    if parts[2] == "fn_hash":
                        v_a = labs_a["code_versions"].get(slot, "?") if labs_a else "?"
                        v_b = labs_b["code_versions"].get(slot, "?") if labs_b else "?"
                        rendered_lines.append(f"  {slot}: v{v_a}  →  v{v_b}")
                    else:
                        rendered_lines.append(f"  {parts[1]}.{parts[2]}: {val_a}  →  {val_b}")
                else:
                    field = parts[1]
                    training_fields_changed.add(field)
                    rendered_lines.append(f"  {field}: {val_a}  →  {val_b}")

        # Sampling changes are independent axes only when the model did not change for that role
        independent_sampling = roles_sampling_changed - roles_model_changed
        for role in sorted(independent_sampling):
            sampling_diffs = [(p, a, b) for p, a, b in diffs
                              if p.startswith(f"agents.{role}.sampling.")]
            changed_keys = [p.split(".")[-1] for p, _, _ in sampling_diffs]
            rendered_lines.append(f"  {role} sampling: {{{', '.join(changed_keys)}}} changed")

        # Deduplicate rendered lines (path can produce multiple diff entries for nested dicts)
        seen: set[str] = set()
        unique_lines: list[str] = []
        for ln in rendered_lines:
            if ln not in seen:
                seen.add(ln)
                unique_lines.append(ln)

        for ln in unique_lines:
            print(ln)

        axis_count = (
            len(roles_model_changed)
            + len(independent_sampling)
            + len(prompt_slots_changed)
            + len(code_slots_changed)
            + len(experiment_fields_changed)
            + len(training_fields_changed)
        )

        print()
        if axis_count == 1:
            print("  ✓ CLEAN ABLATION (1 variable)")
        else:
            print(f"  ✗ CONFOUNDED ({axis_count} variables)")

    print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_html(payload, label, output_dir):
    path = output_dir / "comparison.html"
    path.write_text(
        COMPARISON_TEMPLATE.replace("__DATA_JSON__", json.dumps(payload, default=str))
    )
    return path

def write_csv(payload, output_dir):
    import csv
    path = output_dir / "comparison_summary.csv"
    rows = []
    for g in payload["model_groups"]:
        for cmp in g["comparisons"]:
            for key, res in cmp["metrics"].items():
                rows.append({
                    "model": g["model_name"],
                    "treatment": cmp["treatment_label"],
                    "baseline":  cmp["baseline_label"],
                    "metric_key": key, "metric_label": res["label"],
                    "b_mean": res["b_mean"], "b_std": res["b_std"],
                    "t_mean": res["t_mean"], "t_std": res["t_std"],
                    "U": res["U"], "p": res["p"],
                    "cliffs_delta": res["delta"], "magnitude": res["magnitude"],
                    "significant": res["significant"], "beneficial": res["beneficial"],
                })
    if rows:
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Cross-campaign ARD comparison dashboard")
    ap.add_argument("--campaign-dirs", nargs="+", required=True, type=Path)
    ap.add_argument("--labels", nargs="+", default=None)
    ap.add_argument("--baseline", type=int, default=0)
    ap.add_argument("--model", default=None,
        help="Substring filter on model name, e.g. 'gemma4'")
    ap.add_argument("--output-dir", type=Path, default=None)
    args = ap.parse_args()

    dirs   = args.campaign_dirs
    labels = args.labels or [d.name for d in dirs]

    if len(labels) != len(dirs):
        ap.error(f"--labels ({len(labels)}) must match --campaign-dirs ({len(dirs)})")
    if not (0 <= args.baseline < len(dirs)):
        ap.error(f"--baseline {args.baseline} out of range (0-{len(dirs)-1})")

    slug = (
        labels[args.baseline] + "_vs_"
        + "_".join(l for i, l in enumerate(labels) if i != args.baseline)
    )[:80].replace(" ", "_")

    output_dir = args.output_dir or Path("post_hoc_analysis") / "reports" / "campaign_comparisons" / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {len(dirs)} campaign(s)")
    campaigns = []
    _campaign_comps: list = []
    _campaign_labs: list = []
    for d, l in zip(dirs, labels):
        try:
            c = load_campaign(d, l)
            print(f"  {l}:")
            for name, md in c["models"].items():
                print(f"    {name}  ({md['n_runs']} runs, {md['max_iter']} iters)")
            campaigns.append(c)
        except Exception as exc:
            print(f"  ERROR loading {d}: {exc}", file=sys.stderr)
            sys.exit(1)

        # Load comparability stamped by aggregate_runs.py into the audit JSON
        _comp, _labs = None, None
        try:
            _audit_p = d / "aggregated_data.json"
            if _audit_p.is_file():
                with _audit_p.open() as _af:
                    _ad = json.load(_af)
                _comp = _ad.get("comparability")
                _labs = _ad.get("labels")
        except Exception:
            pass
        _campaign_comps.append(_comp)
        _campaign_labs.append(_labs)

    payload   = build_payload(campaigns, args.baseline, model_filter=args.model)
    n_groups  = len(payload["model_groups"])

    if n_groups == 0:
        all_names = set()
        for c in campaigns:
            all_names |= set(c["models"].keys())
        print(f"\nNo comparable model groups found (need same name in 2+ campaigns).",
              file=sys.stderr)
        print(f"Models seen: {sorted(all_names)}", file=sys.stderr)
        print(f"If all campaigns use the same model, verify the strategist_model "
              f"field matches across aggregated_data.json files.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{n_groups} model group(s):")
    for g in payload["model_groups"]:
        print("  " + g["model_name"] + "  ->  "
              + "  |  ".join(f"{e['campaign_label']} (N={e['n_runs']})"
                             for e in g["entities"]))

    html_path = write_html(payload, slug, output_dir)
    csv_path  = write_csv(payload, output_dir)

    print(f"\nOutputs -> {output_dir}/")
    print(f"  {html_path.name}")
    print(f"  {csv_path.name}")

    # --- Configuration diff header (Tier 3) ---
    for _ti, (_tc, _tl) in enumerate(zip(_campaign_comps, _campaign_labs)):
        if _ti == args.baseline:
            continue
        _print_config_diff(
            labels[args.baseline], _campaign_comps[args.baseline], _campaign_labs[args.baseline],
            labels[_ti],           _tc,                            _tl,
        )

    for g in payload["model_groups"]:
        for cmp in g["comparisons"]:
            sig  = [r for r in cmp["metrics"].values() if r["significant"]]
            marg = [r for r in cmp["metrics"].values() if r["marginal"]]
            print(f"\n  [{g['model_name']}]  {cmp['treatment_label']} vs {cmp['baseline_label']}:")
            if sig:
                for r in sig:
                    mark = "+" if r["beneficial"] else "!"
                    print(f"    {mark} {r['label']:22s}  p={r['p_fmt']:8s}"
                          f"  d={r['delta_fmt']}  [{r['magnitude']}]")
            elif marg:
                for r in marg:
                    print(f"    ~ {r['label']:22s}  p={r['p_fmt']:8s}"
                          f"  d={r['delta_fmt']}  [{r['magnitude']}] (marginal)")
            else:
                print("    No significant or marginal differences.")


if __name__ == "__main__":
    main()
