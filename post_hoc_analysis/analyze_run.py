#!/usr/bin/env python3
"""
analyze_run.py
--------------
CLI entry point for ARD cognition analysis.
Called automatically by outer_loop.sh after each campaign completes.

Single run:
    python3 analyze_run.py --campaign 2025-05-10_spin_crash_10cycles_500kSteps

Cross-run comparison:
    python3 analyze_run.py --compare \
        2025-05-10_spin_crash_10cycles_500kSteps \
        2025-05-11_spin_crash_10cycles_500kSteps

The script resolves paths as:
    experiments/{CAMPAIGN_TAG}/{MODEL}/cognition/json_cognition_records/
"""

from __future__ import annotations
import argparse
import json
import sys
import os
from pathlib import Path

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).parent))
from cognition_analysis import (
    load_run,
    build_report,
    build_summary,
    floor_rule_summary,
)

EXPERIMENTS_DIR = Path("experiments")


def resolve_cognition_dir(campaign: str, model: str | None = None) -> Path:
    """
    Find the cognition records directory for a campaign.
    If model is not specified, uses the first model directory found.
    """
    base = EXPERIMENTS_DIR / campaign

    if not base.exists():
        raise FileNotFoundError(f"Campaign directory not found: {base}")

    if model:
        sanitized = model.replace(":", "-")
        candidate = base / sanitized / "cognition" / "json_cognition_records"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Cognition records not found: {candidate}")

    # Auto-detect: find first model directory containing cognition records
    for child in sorted(base.iterdir()):
        candidate = child / "cognition" / "json_cognition_records"
        if candidate.exists() and any(candidate.glob("iter*_cognition_record.json")):
            return candidate

    raise FileNotFoundError(
        f"No cognition records found anywhere under {base}"
    )


def analyze_single(campaign: str, model: str | None = None, verbose: bool = True) -> dict:
    """Run analysis for a single campaign. Returns the summary dict."""
    cognition_dir = resolve_cognition_dir(campaign, model)
    run_label     = f"{campaign} / {cognition_dir.parent.parent.name}"

    if verbose:
        print(f"\n📊 Analyzing: {cognition_dir}")

    data    = load_run(cognition_dir)
    summary = build_summary(data)

    # Output directory: same level as cognition/
    out_dir = cognition_dir.parent.parent / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    # HTML report
    html_path = out_dir / "cognition_report.html"
    build_report(data, html_path, run_label=run_label)

    # JSON summary
    json_path = out_dir / "cognition_summary.json"
    json_path.write_text(json.dumps(summary, indent=2))

    if verbose:
        _print_summary(summary, run_label)
        print(f"\n✅ Report saved: {html_path}")
        print(f"✅ Summary saved: {json_path}")

    return summary


def _print_summary(summary: dict, label: str = "") -> None:
    """Print a concise terminal summary."""
    meta  = summary["run_meta"]
    floor = summary["floor_rule_summary"]

    print(f"\n{'='*60}")
    print(f"  ARD COGNITION SUMMARY  {label}")
    print(f"{'='*60}")
    print(f"  Iterations : {meta['n_iterations']}")
    print(f"  Wall time  : {meta['total_dur_min']} min")
    print(f"  In tokens  : {meta['total_in']:,}")
    print(f"  Out tokens : {meta['total_out']:,}")
    print(f"  Thinking   : {meta['total_think']:,} chars")
    print()
    print(f"  Validator Floor Rule compliance:")
    print(f"    Hard violations : {floor['hard_violations']} / {floor['total']}")
    print(f"    Soft violations : {floor['soft_violations']} / {floor['total']}")
    print(f"    Hard compliance : {floor['hard_pct']}%")
    if floor['violations']:
        print(f"    ⚠  Violations:")
        for v in floor['violations']:
            print(f"       iter {v['iteration']}: {v['floor']['label']}")
    print()
    print(f"  Validator verdicts:")
    for v in summary["validator_verdicts"]:
        if not v["present"]:
            continue
        sr_b = f"{v['baseline_sr']:.1f}%" if v['baseline_sr'] is not None else "?"
        sr_a = f"{v['actual_sr']:.1f}%"   if v['actual_sr']   is not None else "?"
        flag = " ⚠" if v['floor']['status'] != 'ok' else ""
        print(f"    iter {v['iteration']:02d}: {v['verdict']:22s} {sr_b} → {sr_a}{flag}")
    print()
    print(f"  Proposal selection:")
    counts = {1: 0, 2: 0, 3: 0}
    for p in summary["proposal_selection"]:
        if p["chosen"]:
            counts[p["chosen"]] = counts.get(p["chosen"], 0) + 1
    for k, cnt in counts.items():
        bar = "█" * cnt
        print(f"    P{k}: {bar} {cnt}")
    print()

    # Coder retries
    retries = [r for r in summary["coder_retries"] if r["retries"] > 0]
    if retries:
        print(f"  Code validation retries:")
        for r in retries:
            print(f"    iter {r['iteration']:02d}: {r['coder_calls']} coder calls")
    print(f"{'='*60}\n")


def compare_runs(campaigns: list[str], model: str | None = None) -> None:
    """
    Compare multiple runs side by side.
    Prints a cross-run comparison table and saves a JSON comparison file.
    """
    print(f"\n🔀 Cross-run comparison: {len(campaigns)} campaigns\n")
    all_summaries = []
    for camp in campaigns:
        try:
            s = analyze_single(camp, model, verbose=False)
            s["_campaign"] = camp
            all_summaries.append(s)
        except FileNotFoundError as e:
            print(f"  ⚠  Skipping {camp}: {e}")

    if not all_summaries:
        print("No campaigns could be loaded.")
        return

    # Print comparison table
    print(f"\n{'Campaign':<55} {'Iters':>5} {'Time':>6} {'In-K':>6} "
          f"{'Out-K':>6} {'Think-K':>8} {'HardViol':>9} {'StrictPct':>10}")
    print("-" * 115)
    for s in all_summaries:
        m   = s["run_meta"]
        fl  = s["floor_rule_summary"]
        camp = s["_campaign"][:54]
        print(f"{camp:<55} {m['n_iterations']:>5} {m['total_dur_min']:>5.1f}m "
              f"{m['total_in']//1000:>5}K {m['total_out']//1000:>5}K "
              f"{m['total_think']//1000:>7}K "
              f"{fl['hard_violations']:>9} {fl['strict_pct']:>9}%")

    # Success rate peak comparison
    print(f"\n{'Campaign':<55} {'Peak SR':>8} {'Peak Iter':>10} {'Proposal Bias'}")
    print("-" * 90)
    for s in all_summaries:
        camp   = s["_campaign"][:54]
        sr_pts = [(t["iteration"], t["sr"]) for t in s["terminal_sr"] if t["sr"] is not None]
        if sr_pts:
            peak_iter, peak_sr = max(sr_pts, key=lambda x: x[1])
            peak_str = f"{peak_sr:.1f}%"
        else:
            peak_iter, peak_str = "?", "?"
        # Proposal bias
        counts = {1: 0, 2: 0, 3: 0}
        for p in s["proposal_selection"]:
            if p["chosen"]:
                counts[p["chosen"]] = counts.get(p["chosen"], 0) + 1
        bias = "  ".join(f"P{k}:{v}" for k, v in sorted(counts.items()))
        print(f"{camp:<55} {peak_str:>8} {'iter '+str(peak_iter):>10}  {bias}")

    # Save comparison JSON
    out_path = EXPERIMENTS_DIR / "cross_run_comparison.json"
    out_path.write_text(json.dumps(all_summaries, indent=2))
    print(f"\n✅ Comparison saved: {out_path}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze ARD pipeline cognition records."
    )
    parser.add_argument(
        "--campaign", "-c",
        type=str,
        help="Campaign tag (experiments/{CAMPAIGN_TAG}/). "
             "Also accepts a direct path to a cognition records directory.",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Model name (optional, auto-detected if omitted).",
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="CAMPAIGN",
        help="Compare multiple campaigns side by side.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress terminal summary (still writes files).",
    )

    args = parser.parse_args()

    if args.compare:
        compare_runs(args.compare, model=args.model)
    elif args.campaign:
        analyze_single(args.campaign, model=args.model, verbose=not args.quiet)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
