"""
cognition_analysis.py
---------------------
Post-run analysis module for ARD pipeline cognition records.
Extracts token metrics, validator accuracy, strategist depth,
proposal selection, terminal distributions, and Floor Rule compliance.
Produces a self-contained HTML report and a JSON summary.

Usage (module):
    from cognition_analysis import load_run, build_report
    data = load_run(cognition_dir)
    build_report(data, output_path)

Usage (CLI):  see analyze_run.py
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FLOOR_UP_PP   = 20.0   # ≥20pp SR increase → verdict must be DEV/Validated
FLOOR_DOWN_PP = 20.0   # ≥20pp SR decrease → verdict must be at minimum Regressed
VERDICTS_DEV  = {"Validated", "Productive Deviation"}
PHASE_ORDER   = ["validator", "strategist", "organizer",
                 "research_lead", "dispatcher", "coder"]
STRAT_CEIL    = 16384   # num_predict ceiling for strategist


# ---------------------------------------------------------------------------
# 1. LOADING
# ---------------------------------------------------------------------------

def find_cognition_records(cognition_dir: Path) -> list[Path]:
    """Locate all iter{NN}_cognition_record.json files, sorted."""
    pattern = "iter*_cognition_record.json"
    records = sorted(cognition_dir.glob(pattern))
    if not records:
        # Try one level up (caller passed the campaign root)
        records = sorted(cognition_dir.rglob(pattern))
    return records


def load_run(cognition_dir: Path) -> dict:
    """
    Load all cognition records for a single run directory.
    Returns structured dict ready for report generation.
    """
    paths = find_cognition_records(cognition_dir)
    if not paths:
        raise FileNotFoundError(
            f"No cognition records found in {cognition_dir}"
        )
    records = []
    for p in paths:
        with open(p) as f:
            records.append(json.load(f))

    return {
        "records":         records,
        "iter_metrics":    _extract_iter_metrics(records),
        "phase_averages":  _extract_phase_averages(records),
        "validator":       _extract_validator_data(records),
        "strategist":      _extract_strategist_data(records),
        "proposals":       _extract_proposal_selection(records),
        "terminal":        _extract_terminal_distribution(records),
        "coder_retries":   _extract_coder_retries(records),
        "run_meta":        _extract_run_meta(records),
    }


# ---------------------------------------------------------------------------
# 2. EXTRACTION HELPERS
# ---------------------------------------------------------------------------

def _rt(call: dict, key: str, default=0) -> Any:
    rt = call.get("runtime") or {}
    return rt.get(key, default) or default


def _think(call: dict) -> int:
    return len(call.get("thinking_trace") or "")


def _resp(call: dict) -> int:
    return len(call.get("response_content") or "")


def _extract_iter_metrics(records: list) -> list[dict]:
    rows = []
    for rec in records:
        it = rec["iteration"]
        phases: dict[str, list] = {}
        for c in rec["calls"]:
            ph = c["phase"]
            phases.setdefault(ph, []).append(c)

        row = {"iteration": it, "phases": {}}
        total_in = total_out = total_think = total_dur = 0

        for ph in PHASE_ORDER:
            calls = phases.get(ph, [])
            if not calls:
                continue
            in_t  = sum(_rt(c, "prompt_eval_count") for c in calls)
            out_t = sum(_rt(c, "eval_count")         for c in calls)
            dur   = sum((_rt(c, "total_duration_ns") or 0) / 1e9 for c in calls)
            th    = sum(_think(c) for c in calls)
            count = len(calls)           # >1 means retries happened

            row["phases"][ph] = {
                "in":    in_t,
                "out":   out_t,
                "dur":   round(dur, 1),
                "think": th,
                "calls": count,
                "model": calls[0].get("model_name", "?"),
            }
            total_in    += in_t
            total_out   += out_t
            total_think += th
            total_dur   += dur

        row["total"] = {
            "in":    total_in,
            "out":   total_out,
            "think": total_think,
            "dur":   round(total_dur, 1),
            "tokens": total_in + total_out,
        }
        rows.append(row)
    return rows


def _extract_phase_averages(records: list) -> dict[str, dict]:
    buckets: dict[str, list] = {}
    for rec in records:
        for c in rec["calls"]:
            ph = c["phase"]
            buckets.setdefault(ph, []).append({
                "in":    _rt(c, "prompt_eval_count"),
                "out":   _rt(c, "eval_count"),
                "think": _think(c),
                "resp":  _resp(c),
            })

    avgs = {}
    for ph, vals in buckets.items():
        n = len(vals)
        avg_think = sum(v["think"] for v in vals) / n
        avg_resp  = sum(v["resp"]  for v in vals) / n
        avg_in    = sum(v["in"]    for v in vals) / n
        avg_out   = sum(v["out"]   for v in vals) / n
        avgs[ph] = {
            "n":           n,
            "avg_in":      round(avg_in,  0),
            "avg_out":     round(avg_out, 0),
            "avg_think":   round(avg_think, 0),
            "avg_resp":    round(avg_resp,  0),
            "think_ratio": round(avg_think / max(avg_resp, 1), 2),
        }
    return avgs


def _sr_from_section(text: str, section_header: str) -> float | None:
    """Extract Population Success Rate % from a named section."""
    idx = text.find(section_header)
    if idx == -1:
        return None
    snippet = text[idx: idx + 1500]
    m = re.search(r"Population Success Rate.*?`([\d.]+)%`", snippet)
    if m:
        return float(m.group(1))
    # Fallback: bare number pattern
    m2 = re.search(r"Population Success Rate[^\d]*([\d.]+)\s*%", snippet)
    return float(m2.group(1)) if m2 else None


def _terminal_from_section(text: str, section_header: str) -> dict[str, float]:
    """Extract terminal distribution from a named section."""
    idx = text.find(section_header)
    if idx == -1:
        return {}
    snippet = text[idx: idx + 2000]
    # Match lines like: - `landed_centered`: 46.7%
    modes = {}
    for m in re.finditer(r"`([a-z_]+)`.*?([\d.]+)\s*%", snippet):
        key = m.group(1)
        val = float(m.group(2))
        # Filter to known terminal modes
        if any(k in key for k in ("land", "crash", "hover", "bound", "slid")):
            modes[key] = val
    return modes


def _check_floor_rule(baseline_sr, actual_sr, verdict) -> dict:
    """Returns compliance assessment for a single verdict."""
    if baseline_sr is None or actual_sr is None:
        return {"status": "unknown", "delta": None, "label": "unknown (missing SR data)"}

    delta = actual_sr - baseline_sr

    if delta >= FLOOR_UP_PP:
        if verdict == "Regressed":
            return {"status": "hard_violation",
                    "delta": delta,
                    "label": f"HARD VIOLATION: +{delta:.1f}pp → cannot be Regressed"}
        if verdict not in VERDICTS_DEV:
            return {"status": "soft_violation",
                    "delta": delta,
                    "label": f"SOFT VIOLATION: +{delta:.1f}pp → Floor requires DEV/Validated (got {verdict})"}

    if delta <= -FLOOR_DOWN_PP:
        if verdict not in {"Regressed", "Goodhart Trap"}:
            return {"status": "hard_violation",
                    "delta": delta,
                    "label": f"HARD VIOLATION: {delta:.1f}pp → must be at least Regressed"}

    sign = "+" if delta >= 0 else ""
    return {"status": "ok", "delta": delta, "label": f"ok ({sign}{delta:.1f}pp)"}


def _extract_validator_data(records: list) -> list[dict]:
    rows = []
    for rec in records:
        it = rec["iteration"]
        calls = {c["phase"]: c for c in rec["calls"]}
        if "validator" not in calls:
            rows.append({"iteration": it, "present": False})
            continue

        v   = calls["validator"]
        up  = v.get("role_user", "") or ""
        resp = v.get("response_content", "") or ""
        think = v.get("thinking_trace", "") or ""
        rt  = v.get("runtime") or {}

        # Verdict
        vm = re.search(
            r"`(Validated|Regressed|Mixed|Goodhart Trap|Productive Deviation)`", resp
        )
        verdict = vm.group(1) if vm else "unknown"

        # Success rates (Section 2 = baseline, Section 3 = actual)
        baseline_sr = _sr_from_section(up, "[2. THE BASELINE STATE")
        actual_sr   = _sr_from_section(up, "[3. THE ACTUAL RESULTS")

        # Terminal distribution from actual results section
        terminal = _terminal_from_section(up, "[3. THE ACTUAL RESULTS")

        # Derived success rate from terminal if Section 3 parse failed
        if actual_sr is None and terminal:
            actual_sr = sum(
                v for k, v in terminal.items()
                if "landed" in k and "slid" not in k and "valley" not in k
            )

        floor = _check_floor_rule(baseline_sr, actual_sr, verdict)

        rows.append({
            "iteration":   it,
            "present":     True,
            "verdict":     verdict,
            "baseline_sr": baseline_sr,
            "actual_sr":   actual_sr,
            "terminal":    terminal,
            "floor":       floor,
            "think_chars": len(think),
            "out_tokens":  rt.get("eval_count", 0) or 0,
            "in_tokens":   rt.get("prompt_eval_count", 0) or 0,
            "resp_preview": resp[:300],
        })
    return rows


def _extract_strategist_data(records: list) -> list[dict]:
    rows = []
    for rec in records:
        it = rec["iteration"]
        calls = [c for c in rec["calls"] if c["phase"] == "strategist"]
        if not calls:
            rows.append({"iteration": it, "present": False})
            continue
        c = calls[0]
        rt = c.get("runtime") or {}
        resp = c.get("response_content", "") or ""
        think = c.get("thinking_trace", "") or ""
        out = rt.get("eval_count", 0) or 0

        # Extract proposal names
        props = re.findall(
            r"Proposal\s+\d+\s*[:\*]+\s*([^\n\*]{10,70})", resp
        )
        props = [p.strip()[:60] for p in props[:3]]

        rows.append({
            "iteration":   it,
            "present":     True,
            "think_chars": len(think),
            "out_tokens":  out,
            "in_tokens":   rt.get("prompt_eval_count", 0) or 0,
            "hit_ceiling": out >= STRAT_CEIL,
            "proposals":   props,
            "model":       c.get("model_name", "?"),
        })
    return rows


def _extract_proposal_selection(records: list) -> list[dict]:
    rows = []
    for rec in records:
        it = rec["iteration"]
        calls = {c["phase"]: c for c in rec["calls"]}
        rl = calls.get("research_lead", {})
        resp = rl.get("response_content", "") or ""
        think = rl.get("thinking_trace", "") or ""
        m = re.search(r"Proposal\s+(\d)", resp[:400])
        chosen = int(m.group(1)) if m else None
        rows.append({
            "iteration":   it,
            "chosen":      chosen,
            "think_chars": len(think),
        })
    return rows


def _extract_terminal_distribution(records: list) -> list[dict]:
    """
    Build the success-rate trajectory using the strategist/validator prompts.
    The iter-N strategist prompt shows the iter-N diagnostic directly.
    The validator at iter-N shows Section 3 = iter-(N-1) training result.
    We collect the ACTUAL result of each iteration's training.
    """
    # Collect: {iteration: actual_sr}
    sr_map: dict[int, float | None] = {}

    for rec in records:
        it  = rec["iteration"]
        calls = {c["phase"]: c for c in rec["calls"]}

        # From validator Section 3 (result of previous iter's code)
        if "validator" in calls:
            v  = calls["validator"]
            up = v.get("role_user", "") or ""
            sr = _sr_from_section(up, "[3. THE ACTUAL RESULTS")
            # This is the result of iter (N-1) training
            if sr is not None:
                sr_map[it - 1] = sr

        # Also try to get iter-1 (the initial state) from the strategist prompt
        if "strategist" in calls and it == 1:
            s  = calls["strategist"]
            up = s.get("role_user", "") or ""
            # Iter 1 strategist sees the initial diagnostic (iter 0 result)
            m  = re.search(r"Population Success Rate.*?`([\d.]+)%`", up)
            if m:
                sr_map[0] = float(m.group(1))

    rows = []
    for rec in records:
        it = rec["iteration"]
        rows.append({
            "iteration": it,
            "sr":        sr_map.get(it - 1),   # result of iter-N's code
        })
    return rows


def _extract_coder_retries(records: list) -> list[dict]:
    rows = []
    for rec in records:
        it    = rec["iteration"]
        count = sum(1 for c in rec["calls"] if c["phase"] == "coder")
        rows.append({"iteration": it, "coder_calls": count, "retries": max(0, count - 1)})
    return rows


def _extract_run_meta(records: list) -> dict:
    models = {}
    for rec in records:
        for c in rec["calls"]:
            ph = c["phase"]
            m  = c.get("model_name", "?")
            models[ph] = m

    total_in    = sum(
        (_rt(c, "prompt_eval_count")) for r in records for c in r["calls"]
    )
    total_out   = sum(
        (_rt(c, "eval_count"))        for r in records for c in r["calls"]
    )
    total_think = sum(
        _think(c)                     for r in records for c in r["calls"]
    )
    total_dur   = sum(
        (_rt(c, "total_duration_ns") or 0) / 1e9
        for r in records for c in r["calls"]
    )
    return {
        "n_iterations": len(records),
        "models":       models,
        "total_in":     total_in,
        "total_out":    total_out,
        "total_think":  total_think,
        "total_dur_s":  round(total_dur, 1),
        "total_dur_min": round(total_dur / 60, 1),
    }


# ---------------------------------------------------------------------------
# 3. FLOOR RULE SUMMARY
# ---------------------------------------------------------------------------

def floor_rule_summary(validator_data: list[dict]) -> dict:
    present = [v for v in validator_data if v.get("present")]
    hard    = [v for v in present if v["floor"]["status"] == "hard_violation"]
    soft    = [v for v in present if v["floor"]["status"] == "soft_violation"]
    ok      = [v for v in present if v["floor"]["status"] == "ok"]
    return {
        "total":           len(present),
        "hard_violations": len(hard),
        "soft_violations": len(soft),
        "correct":         len(ok),
        "hard_pct":        round(100 * (len(present) - len(hard)) / max(len(present), 1), 0),
        "strict_pct":      round(100 * len(ok) / max(len(present), 1), 0),
        "violations":      hard + soft,
    }


# ---------------------------------------------------------------------------
# 4. JSON SUMMARY
# ---------------------------------------------------------------------------

def build_summary(data: dict) -> dict:
    """Machine-readable summary dict — saved alongside the HTML report."""
    meta     = data["run_meta"]
    val      = data["validator"]
    strat    = data["strategist"]
    props    = data["proposals"]
    floor    = floor_rule_summary(val)

    return {
        "run_meta":           meta,
        "floor_rule_summary": floor,
        "iter_metrics":       data["iter_metrics"],
        "validator_verdicts": [
            {
                "iteration":   v["iteration"],
                "present":     v["present"],
                "verdict":     v.get("verdict"),
                "baseline_sr": v.get("baseline_sr"),
                "actual_sr":   v.get("actual_sr"),
                "floor":       v.get("floor", {"status": "unknown", "delta": None, "label": "no validator"}),
                "think_chars": v.get("think_chars", 0),
                "out_tokens":  v.get("out_tokens", 0),
            }
            for v in val
        ],
        "strategist_depth": [
            {k: v[k] for k in ("iteration","present","think_chars",
                                "out_tokens","hit_ceiling","proposals")}
            for v in strat if v.get("present")
        ],
        "proposal_selection": props,
        "terminal_sr":        data["terminal"],
        "coder_retries":      data["coder_retries"],
    }


# ---------------------------------------------------------------------------
# 5. HTML REPORT GENERATOR
# ---------------------------------------------------------------------------

def build_report(data: dict, output_path: Path, run_label: str = "") -> Path:
    """
    Generate a self-contained HTML report with embedded Chart.js charts.
    Returns the path to the written file.
    """
    meta      = data["run_meta"]
    im        = data["iter_metrics"]
    val       = data["validator"]
    strat     = data["strategist"]
    props     = data["proposals"]
    terminal  = data["terminal"]
    retries   = data["coder_retries"]
    phase_avg = data["phase_averages"]
    floor_s   = floor_rule_summary(val)
    n_iters   = meta["n_iterations"]

    # ---------- JS data arrays ----------
    iters_js      = list(range(1, n_iters + 1))
    iters_labels  = [f"I{i}" for i in iters_js]

    # Tokens per iter (stacked by phase)
    def phase_tok(ph):
        out = []
        for row in im:
            p = row["phases"].get(ph)
            out.append((p["in"] + p["out"]) if p else 0)
        return out

    strat_tok  = phase_tok("strategist")
    org_tok    = phase_tok("organizer")
    rl_tok     = phase_tok("research_lead")
    disp_tok   = phase_tok("dispatcher")
    val_tok    = phase_tok("validator")
    coder_tok  = phase_tok("coder")

    # Strategist thinking depth
    strat_think = []
    strat_ceil  = []
    for i in iters_js:
        row = next((s for s in strat if s.get("iteration") == i and s.get("present")), None)
        strat_think.append(row["think_chars"] if row else 0)
        strat_ceil.append(row["hit_ceiling"]  if row else False)

    # Success rate trajectory
    sr_vals = []
    for i in iters_js:
        row = next((t for t in terminal if t["iteration"] == i), None)
        sr  = row["sr"] if row else None
        sr_vals.append(sr)  # null stays null → gap in chart

    # Proposal selection
    prop_vals = []
    for i in iters_js:
        row = next((p for p in props if p["iteration"] == i), None)
        prop_vals.append(row["chosen"] if row else None)

    # Validator verdicts — color map
    VERDICT_COLORS = {
        "Validated":           "#3BB273",
        "Productive Deviation": "#3BB273",
        "Mixed":               "#E8922A",
        "Goodhart Trap":       "#378ADD",
        "Regressed":           "#E24B4A",
        "unknown":             "#888780",
    }
    VERDICT_SHORT = {
        "Validated":           "VAL",
        "Productive Deviation": "DEV",
        "Mixed":               "MIX",
        "Goodhart Trap":       "GHT",
        "Regressed":           "REG",
        "unknown":             "???",
    }

    # Floor rule rows for the compliance table
    def floor_row_class(status):
        return {"hard_violation": "fl-hard", "soft_violation": "fl-soft",
                "ok": "fl-ok", "unknown": "fl-unk"}.get(status, "fl-unk")

    floor_rows_html = ""
    for v in val:
        if not v.get("present"):
            continue
        it      = v["iteration"]
        verdict = v.get("verdict", "unknown")
        bsr     = v.get("baseline_sr")
        asr     = v.get("actual_sr")
        floor   = v["floor"]
        cls     = floor_row_class(floor["status"])
        delta   = floor.get("delta")
        delta_s = (f"+{delta:.1f}" if delta is not None and delta >= 0
                   else f"{delta:.1f}" if delta is not None else "?")
        floor_rows_html += \
            (f"<tr class='{cls}'>") + \
            (f"<td>{it}</td>") +     \
            (f"<td>{bsr:.1f}%</td>" if bsr is not None else "<td>—</td>") + \
            (f"<td>{asr:.1f}%</td>" if asr is not None else "<td>—</td>") + \
            (f"<td>{delta_s}pp</td>") + \
            (f"<td>{verdict}</td>") + \
            (f"<td>{floor['label']}</td>") + \
            (f"</tr>")
        

    # Phase averages table
    phase_avg_html = ""
    for ph in PHASE_ORDER:
        if ph not in phase_avg:
            continue
        pa = phase_avg[ph]
        phase_avg_html += (
            f"<tr>"
            f"<td>{ph}</td>"
            f"<td>{int(pa['avg_in']):,}</td>"
            f"<td>{int(pa['avg_out']):,}</td>"
            f"<td>{int(pa['avg_think']):,}</td>"
            f"<td>{pa['think_ratio']:.2f}×</td>"
            f"</tr>"
        )

    # Coder retry events
    retry_events = [r for r in retries if r["retries"] > 0]
    retry_note = ""
    if retry_events:
        parts = [f"iter {r['iteration']} ({r['coder_calls']}× calls)" for r in retry_events]
        retry_note = "Code validation loop triggered: " + ", ".join(parts)

    # Verdict timeline chips
    verdict_chips_html = ""
    for v in val:
        it      = v["iteration"]
        if not v.get("present"):
            verdict_chips_html += f"<div class='vchip' style='background:#1a1a1a;color:#666'>I{it}<br>—</div>"
            continue
        verdict = v.get("verdict", "unknown")
        color   = VERDICT_COLORS.get(verdict, "#888")
        short   = VERDICT_SHORT.get(verdict, "???")
        floor   = v["floor"]
        border  = "2px solid #fff" if floor["status"] == "hard_violation" else "none"
        verdict_chips_html += (
            f"<div class='vchip' style='background:{color}22;color:{color};"
            f"border:1px solid {color}44;outline:{border};outline-offset:2px'>"
            f"I{it}<br>{short}"
            f"{'★' if floor['status']=='hard_violation' else ''}"
            f"</div>"
        )

    # Proposal chips
    prop_chips_html = ""
    prop_colors = {1: "#7F77DD", 2: "#1D9E75", 3: "#E8922A", None: "#444"}
    prop_counts = {1: prop_vals.count(1), 2: prop_vals.count(2), 3: prop_vals.count(3)}
    for i, pv in enumerate(prop_vals, 1):
        col = prop_colors.get(pv, "#444")
        prop_chips_html += (
            f"<div class='pchip' style='background:{col}22;color:{col};border:1px solid {col}55'>"
            f"I{i}<br>{'P'+str(pv) if pv else '—'}</div>"
        )

    # Strat ceiling note
    ceil_iters = [s["iteration"] for s in strat if s.get("present") and s.get("hit_ceiling")]
    ceil_note  = f"Output ceiling hit at: iter {', '.join(str(i) for i in ceil_iters)}" if ceil_iters else "Output ceiling never hit"

    title = run_label or str(output_path.parent.name)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARD Cognition Report — {title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  :root {{
    --bg:   #0e0f11;
    --bg2:  #161820;
    --bg3:  #1e2128;
    --bdr:  #2a2d35;
    --txt:  #d4d2cb;
    --txt2: #8a8880;
    --txt3: #555;
    --acc:  #7F77DD;
    --grn:  #3BB273;
    --red:  #E24B4A;
    --org:  #E8922A;
    --blu:  #378ADD;
    --r:    6px;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0 }}
  body {{ background:var(--bg); color:var(--txt); font-family:'JetBrains Mono',monospace,ui-monospace;
          font-size:12px; line-height:1.6; padding:24px }}
  h1 {{ font-size:18px; font-weight:600; color:#fff; letter-spacing:.02em; margin-bottom:4px }}
  h2 {{ font-size:11px; font-weight:500; letter-spacing:.1em; text-transform:uppercase;
        color:var(--txt2); margin:20px 0 8px }}
  .meta {{ font-size:11px; color:var(--txt2); margin-bottom:20px }}
  .meta span {{ margin-right:20px }}
  .grid-4 {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:16px }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px }}
  .card {{ background:var(--bg2); border:1px solid var(--bdr); border-radius:var(--r);
           padding:12px 14px }}
  .card .lbl {{ font-size:10px; color:var(--txt2); margin-bottom:4px }}
  .card .val {{ font-size:20px; font-weight:600; color:#fff }}
  .card .sub {{ font-size:10px; color:var(--txt3); margin-top:3px }}
  .chart-wrap {{ position:relative; width:100%; }}
  .chart-wrap canvas {{ width:100% !important }}
  table {{ width:100%; border-collapse:collapse; font-size:11px }}
  th {{ text-align:left; padding:6px 10px; border-bottom:1px solid var(--bdr);
        color:var(--txt2); font-weight:500; font-size:10px; letter-spacing:.05em; text-transform:uppercase }}
  td {{ padding:6px 10px; border-bottom:1px solid var(--bdr); color:var(--txt) }}
  tr:last-child td {{ border-bottom:none }}
  .fl-hard td {{ color:var(--red) }}
  .fl-soft td {{ color:var(--org) }}
  .fl-ok   td {{ color:var(--txt2) }}
  .fl-unk  td {{ color:var(--txt3) }}
  .fl-hard td:last-child {{ font-weight:600 }}
  .chip-row {{ display:flex; gap:4px; flex-wrap:wrap; margin:4px 0 }}
  .vchip, .pchip {{ width:38px; height:38px; border-radius:5px; display:flex;
                    align-items:center; justify-content:center; font-size:8px;
                    font-weight:600; flex-direction:column; line-height:1.3; flex-shrink:0 }}
  .note {{ font-size:10px; color:var(--txt3); margin-top:6px }}
  .section {{ margin-bottom:24px }}
  .tag {{ display:inline-block; font-size:10px; padding:2px 8px; border-radius:20px;
          font-weight:600; letter-spacing:.03em }}
  .tag-ok  {{ background:#3BB27322; color:#3BB273 }}
  .tag-bad {{ background:#E24B4A22; color:#E24B4A }}
  .tag-warn{{ background:#E8922A22; color:#E8922A }}
  .divider {{ border:none; border-top:1px solid var(--bdr); margin:20px 0 }}
</style>
</head>
<body>

<h1>ARD Pipeline — Cognition Report</h1>
<div class="meta">
  <span>Run: <strong style="color:#fff">{title}</strong></span>
  <span>Iterations: <strong style="color:#fff">{n_iters}</strong></span>
  <span>Wall time: <strong style="color:#fff">{meta['total_dur_min']} min</strong></span>
  <span>Total tokens: <strong style="color:#fff">{(meta['total_in']+meta['total_out']):,}</strong></span>
</div>

<!-- HEADLINE CARDS -->
<div class="grid-4">
  <div class="card">
    <div class="lbl">Total input tokens</div>
    <div class="val">{meta['total_in']//1000}K</div>
    <div class="sub">{meta['total_in']:,} tokens</div>
  </div>
  <div class="card">
    <div class="lbl">Total output tokens</div>
    <div class="val">{meta['total_out']//1000}K</div>
    <div class="sub">{meta['total_out']:,} tokens</div>
  </div>
  <div class="card">
    <div class="lbl">Total thinking</div>
    <div class="val">{meta['total_think']//1000}K</div>
    <div class="sub">{meta['total_think']:,} chars</div>
  </div>
  <div class="card">
    <div class="lbl">Wall time</div>
    <div class="val">{meta['total_dur_min']}m</div>
    <div class="sub">≈ {round(meta['total_dur_s']/n_iters/60,1)} min/iter</div>
  </div>
</div>

<!-- VALIDATOR VERDICTS TIMELINE -->
<div class="section">
<h2>Validator verdict timeline</h2>
<div class="chip-row">{verdict_chips_html}</div>
<div class="note">★ = Floor Rule hard violation &nbsp;|&nbsp;
  DEV=Productive Deviation · GHT=Goodhart Trap · MIX=Mixed · REG=Regressed</div>
</div>

<!-- FLOOR RULE COMPLIANCE -->
<div class="section">
<h2>Floor Rule compliance
  <span class="tag {'tag-ok' if floor_s['hard_violations']==0 else 'tag-bad'}"
    style="margin-left:8px">{floor_s['hard_violations']} hard violations</span>
  <span class="tag {'tag-ok' if floor_s['soft_violations']==0 else 'tag-warn'}"
    style="margin-left:4px">{floor_s['soft_violations']} soft violations</span>
  <span style="font-size:10px;color:var(--txt2);margin-left:8px">
    {floor_s['hard_pct']}% hard compliant · {floor_s['strict_pct']}% strict compliant</span>
</h2>
<table>
  <thead><tr><th>Iter</th><th>SR Before</th><th>SR After</th><th>Δpp</th>
              <th>Verdict</th><th>Assessment</th></tr></thead>
  <tbody>{floor_rows_html}</tbody>
</table>
</div>

<!-- PROPOSAL SELECTION -->
<div class="section">
<h2>Proposal selection
  <span style="font-size:10px;color:var(--txt2);margin-left:8px">
    P1: {prop_counts[1]}× &nbsp; P2: {prop_counts[2]}× &nbsp; P3: {prop_counts[3]}×
  </span>
</h2>
<div class="chip-row">{prop_chips_html}</div>
</div>

<!-- CHARTS -->
<div class="section">
<h2>Token consumption by iteration (stacked by phase)</h2>
<div class="chart-wrap" style="height:200px">
  <canvas id="tokChart"></canvas>
</div>
</div>

<div class="grid-2">
  <div class="section">
    <h2>Success rate trajectory</h2>
    <div class="chart-wrap" style="height:180px"><canvas id="srChart"></canvas></div>
  </div>
  <div class="section">
    <h2>Strategist thinking depth &nbsp;
      <span style="font-size:10px;color:var(--txt2)">{ceil_note}</span>
    </h2>
    <div class="chart-wrap" style="height:180px"><canvas id="stratChart"></canvas></div>
  </div>
</div>

<!-- PHASE AVERAGES -->
<div class="section">
<h2>Phase averages (across run)</h2>
<table>
  <thead><tr><th>Phase</th><th>Avg In-tok</th><th>Avg Out-tok</th>
              <th>Avg Think (chars)</th><th>Think/Resp ratio</th></tr></thead>
  <tbody>{phase_avg_html}</tbody>
</table>
</div>

{f'<div class="section"><h2>Code validation events</h2><p style="color:var(--org);font-size:11px">{retry_note}</p></div>' if retry_note else ''}

<script>
const gc = 'rgba(255,255,255,0.06)';
const tc = '#6b6966';
const base = {{responsive:true, maintainAspectRatio:false,
  plugins:{{legend:{{labels:{{color:tc,font:{{size:10}},boxWidth:10,padding:10}}}}}},
  scales:{{
    x:{{ticks:{{color:tc,font:{{size:10}}}},grid:{{color:gc}}}},
    y:{{ticks:{{color:tc,font:{{size:10}},callback:v=>v>=1000?Math.round(v/1000)+'K':v}},grid:{{color:gc}}}}
  }}}};
const labels = {json.dumps(iters_labels)};

new Chart(document.getElementById('tokChart'),{{type:'bar',
  data:{{labels,datasets:[
    {{label:'strategist', data:{json.dumps(strat_tok)}, backgroundColor:'#7F77DD'}},
    {{label:'organizer',  data:{json.dumps(org_tok)},   backgroundColor:'#1D9E75'}},
    {{label:'res.lead',   data:{json.dumps(rl_tok)},    backgroundColor:'#378ADD'}},
    {{label:'dispatcher', data:{json.dumps(disp_tok)},  backgroundColor:'#BA7517'}},
    {{label:'validator',  data:{json.dumps(val_tok)},   backgroundColor:'#E24B4A'}},
    {{label:'coder',      data:{json.dumps(coder_tok)}, backgroundColor:'#555'}},
  ]}},
  options:{{...base,scales:{{
    x:{{...base.scales.x, stacked:true}},
    y:{{...base.scales.y, stacked:true}}
  }}}}
}});

const srRaw = {json.dumps(sr_vals)};
const ceilIters = {json.dumps(ceil_iters)};
new Chart(document.getElementById('srChart'),{{type:'line',
  data:{{labels,datasets:[{{
    label:'Success %', data:srRaw,
    borderColor:'#3BB273', backgroundColor:'rgba(59,178,115,0.1)',
    tension:.3, fill:true, spanGaps:false,
    pointRadius:srRaw.map((_,i)=>ceilIters.includes(i+1)?7:4),
    pointBackgroundColor:srRaw.map((_,i)=>ceilIters.includes(i+1)?'#E24B4A':'#3BB273'),
  }}]}},
  options:{{...base,scales:{{
    x:base.scales.x,
    y:{{...base.scales.y,min:0,max:105,
       ticks:{{color:tc,font:{{size:10}},callback:v=>v+'%'}}}}
  }}}}
}});

const thinkRaw = {json.dumps(strat_think)};
const thinkColors = thinkRaw.map((_,i)=>ceilIters.includes(i+1)?'#E24B4A':'#7F77DD');
new Chart(document.getElementById('stratChart'),{{type:'bar',
  data:{{labels,datasets:[{{
    label:'Think chars', data:thinkRaw,
    backgroundColor:thinkColors, borderRadius:3,
  }}]}},
  options:{{...base,scales:{{
    x:base.scales.x,
    y:{{...base.scales.y,ticks:{{color:tc,font:{{size:10}},callback:v=>v>=1000?Math.round(v/1000)+'K':v}}}}
  }}}}
}});
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path
