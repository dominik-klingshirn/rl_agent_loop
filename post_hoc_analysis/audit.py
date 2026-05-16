#!/usr/bin/env python3
"""
ARD Pipeline Cognition Audit
============================

Audits a directory of cognition records (one per iteration) and reports:
- Reward component evolution across iterations
- Coder deletion-list fidelity (was every deletion honored?)
- Coder double-count detection (combined sums included as separate components)
- Validator verdict trail
- Component count and churn summary

Usage:
    python audit.py path/to/run_dir/
    python audit.py path/to/run_dir/ --md report.md
    python audit.py path/to/run_dir/ --json report.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# Record loading
# =============================================================================

def load_record(path: Path) -> Optional[dict]:
    """Load a single iteration's cognition record. Returns None if invalid."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  Failed to load {path}: {e}", file=sys.stderr)
        return None


def find_iter_records(run_dir: Path) -> List[Tuple[int, Path]]:
    """Find all iter##_cognition_record.json files, sorted by iteration number."""
    records = []
    for p in sorted(run_dir.glob("iter*_cognition_record.json")):
        m = re.match(r"iter(\d+)", p.stem)
        if m:
            records.append((int(m.group(1)), p))
    return records


def get_call(record: dict, phase: str) -> Optional[dict]:
    """Get the first call matching a given phase name."""
    for c in record.get("calls", []):
        if c.get("phase") == phase:
            return c
    return None


# =============================================================================
# Patterns
# =============================================================================

COMPONENTS_DICT_RE = re.compile(r'components\s*=\s*\{(.*?)\}', re.DOTALL)
COMPONENT_NAME_RE = re.compile(r'"([^"]+)"\s*:')
COMPONENT_VAL_RE = re.compile(r'"([^"]+)"\s*:\s*float\(([^)]+)\)')
DELETION_SECTION_RE = re.compile(
    r'\*\*Code Deletions/Modifications:?\*\*(.*?)(?=\*\*Scaling|\*\*Integration|</CODER_PAYLOAD>|$)',
    re.DOTALL,
)
BACKTICK_RE = re.compile(r'`([^`]+)`')
VERDICT_STATUS_RE = re.compile(r'\*\*Status:?\*\*[^\n]*')
VERDICT_LABEL_RE = re.compile(
    r'(Validated|Refuted|Mixed|Pyrrhic Victory|Productive Deviation)',
    re.IGNORECASE,
)
VAR_ASSIGN_RE = re.compile(r'^\s*(\w+)\s*=\s*([^\n]+)', re.MULTILINE)


# =============================================================================
# Per-iteration extractors
# =============================================================================

def extract_components(coder_call: Optional[dict]) -> List[str]:
    """Extract reward component names from Coder output."""
    if not coder_call:
        return []
    code = coder_call.get("response_content", "")
    m = COMPONENTS_DICT_RE.search(code)
    if not m:
        return []
    return COMPONENT_NAME_RE.findall(m.group(1))


def extract_component_pairs(coder_call: Optional[dict]) -> List[Tuple[str, str]]:
    """Extract (component_name, value_expression) pairs from Coder output."""
    if not coder_call:
        return []
    code = coder_call.get("response_content", "")
    m = COMPONENTS_DICT_RE.search(code)
    if not m:
        return []
    return [(n, e.strip()) for n, e in COMPONENT_VAL_RE.findall(m.group(1))]


def extract_var_assignments(coder_call: Optional[dict]) -> Dict[str, str]:
    """Get top-level variable assignments from Coder code body."""
    if not coder_call:
        return {}
    code = coder_call.get("response_content", "")
    assigns = {}
    for m in VAR_ASSIGN_RE.finditer(code):
        var, val = m.group(1), m.group(2).strip()
        if var in ("components", "total_reward"):
            continue
        # Don't overwrite — keep first assignment (the variable's defining line)
        if var not in assigns:
            assigns[var] = val
    return assigns


def _looks_like_none(text: str) -> bool:
    """Check if deletion section explicitly says no excisions."""
    none_phrases = ['none', 'no components', 'no excisions', 'not applicable', 'n/a']
    text_lower = text.lower().strip()
    if not text_lower:
        return True
    return any(p in text_lower for p in none_phrases)


def extract_deletions(dispatcher_call: Optional[dict]) -> Tuple[List[str], str, str]:
    """
    Extract deletion list from Dispatcher output.
    Returns (deletion_names, raw_section_text, status).
    Status is one of: 'structured', 'unstructured', 'none_marker', 'missing'.
    """
    if not dispatcher_call:
        return [], "", "missing"
    text = dispatcher_call.get("response_content", "")
    m = DELETION_SECTION_RE.search(text)
    if not m:
        return [], "", "missing"
    raw = m.group(1).strip()
    deletions = BACKTICK_RE.findall(raw)
    if deletions:
        return deletions, raw, "structured"
    if _looks_like_none(raw):
        return [], raw, "none_marker"
    return [], raw, "unstructured"


def extract_validator_verdict(validator_call: Optional[dict]) -> Tuple[str, str]:
    """Extract Validator status verdict from response."""
    if not validator_call:
        return "", ""
    text = validator_call.get("response_content", "")
    m = VERDICT_STATUS_RE.search(text)
    if not m:
        return "", ""
    line = m.group(0)
    label_match = VERDICT_LABEL_RE.search(line)
    label = label_match.group(1) if label_match else "?"
    return label, line


# =============================================================================
# Audit checks
# =============================================================================

def check_double_count(coder_call: Optional[dict]) -> List[Tuple[str, str, str]]:
    """
    Detect components whose underlying variable is a sum/product of other 
    components' underlying variables.
    
    Returns list of (component_name, full_assignment, reason).
    """
    pairs = extract_component_pairs(coder_call)
    if not pairs:
        return []
    
    var_assigns = extract_var_assignments(coder_call)
    
    # Map: dict component name -> the variable it stores
    name_to_var = {}
    for name, expr in pairs:
        # The expr is typically just a variable name like `r_damp`. 
        # Strip whitespace and check.
        if re.match(r'^[\w_]+$', expr):
            name_to_var[name] = expr
    
    # Set of all variables backing dict entries
    dict_vars = set(name_to_var.values())
    
    suspects = []
    for name, var in name_to_var.items():
        assignment = var_assigns.get(var, "")
        if not assignment:
            continue
        # Only suspect if assignment is a composite (sum or product)
        if '+' not in assignment and '*' not in assignment:
            continue
        # Find references to other dict-backing variables
        other_vars_referenced = []
        for other_var in dict_vars:
            if other_var == var:
                continue
            if re.search(rf'\b{re.escape(other_var)}\b', assignment):
                other_vars_referenced.append(other_var)
        if other_vars_referenced:
            suspects.append((
                name,
                f"{var} = {assignment}",
                f"contains other dict variable(s): {', '.join(other_vars_referenced)}",
            ))
    
    return suspects


def check_deletion_fidelity(
    coder_call: Optional[dict], 
    dispatcher_call: Optional[dict],
) -> Dict:
    """Check whether Coder honored every deletion from Dispatcher."""
    deletions, raw, status = extract_deletions(dispatcher_call)
    components = extract_components(coder_call)
    
    if status == "missing":
        return {"status": "missing", "deletions": [], "violated": [], "raw": ""}
    if status == "unstructured":
        return {
            "status": "unstructured",
            "deletions": [],
            "violated": [],
            "raw": raw[:120],
        }
    if status == "none_marker":
        return {
            "status": "none_requested",
            "deletions": [],
            "violated": [],
            "raw": raw[:120],
        }
    
    # status == 'structured'
    violated = [d for d in deletions if d in components]
    return {
        "status": "violated" if violated else "honored",
        "deletions": deletions,
        "violated": violated,
        "raw": "",
    }


# =============================================================================
# Run-level audit
# =============================================================================

def audit_run(run_dir: Path) -> Dict:
    """Run a full audit on a single run directory."""
    record_paths = find_iter_records(run_dir)
    if not record_paths:
        return {"error": f"No iteration records found in {run_dir}"}
    
    audit = {
        "run_dir": str(run_dir),
        "n_iterations": len(record_paths),
        "iterations": [],
        "summary": {
            "double_count_iters": [],
            "deletion_violation_iters": [],
            "unstructured_dispatcher_iters": [],
            "validator_verdicts": [],
        },
    }
    
    for iter_num, path in record_paths:
        record = load_record(path)
        if not record:
            continue
        
        coder = get_call(record, "coder")
        dispatcher = get_call(record, "dispatcher")
        validator = get_call(record, "validator")
        
        components = extract_components(coder)
        double_counts = check_double_count(coder)
        deletion_check = check_deletion_fidelity(coder, dispatcher)
        verdict_label, verdict_line = extract_validator_verdict(validator)
        
        iter_audit = {
            "iter": iter_num,
            "n_components": len(components),
            "components": components,
            "double_counts": double_counts,
            "deletion_check": deletion_check,
            "validator": (
                {"verdict": verdict_label, "line": verdict_line}
                if validator else None
            ),
        }
        audit["iterations"].append(iter_audit)
        
        if double_counts:
            audit["summary"]["double_count_iters"].append((iter_num, double_counts))
        if deletion_check["status"] == "violated":
            audit["summary"]["deletion_violation_iters"].append(
                (iter_num, deletion_check["violated"])
            )
        if deletion_check["status"] == "unstructured":
            audit["summary"]["unstructured_dispatcher_iters"].append(
                (iter_num, deletion_check["raw"])
            )
        if validator:
            audit["summary"]["validator_verdicts"].append(
                (iter_num, verdict_label, verdict_line)
            )
    
    return audit


# =============================================================================
# Output formatters
# =============================================================================

def format_text(audit: Dict) -> str:
    if "error" in audit:
        return audit["error"]
    
    out = []
    out.append("=" * 70)
    out.append(f"COGNITION AUDIT — {audit['run_dir']}")
    out.append(f"Iterations: {audit['n_iterations']}")
    out.append("=" * 70)
    
    out.append("\nCOMPONENT EVOLUTION")
    out.append("-" * 70)
    for it in audit["iterations"]:
        comps_str = ", ".join(it["components"]) if it["components"] else "(none)"
        out.append(f"  iter{it['iter']:02d} ({it['n_components']}): {comps_str}")
    
    out.append("\nCODER DELETION FIDELITY")
    out.append("-" * 70)
    for it in audit["iterations"]:
        check = it["deletion_check"]
        prefix = f"  iter{it['iter']:02d}:"
        if check["status"] == "violated":
            out.append(f"{prefix} ❌ FAILED TO DELETE: {check['violated']}")
        elif check["status"] == "unstructured":
            out.append(f"{prefix} ⚠️  unstructured: '{check['raw'][:80]}'")
        elif check["status"] == "none_requested":
            out.append(f"{prefix} ✓ (no excisions requested)")
        elif check["status"] == "missing":
            out.append(f"{prefix} — (no dispatcher output)")
        else:
            out.append(f"{prefix} ✓ ({len(check['deletions'])} deletions honored)")
    
    out.append("\nDOUBLE-COUNT AUDIT")
    out.append("-" * 70)
    if not audit["summary"]["double_count_iters"]:
        out.append("  ✓ No double-count violations detected")
    else:
        for iter_num, suspects in audit["summary"]["double_count_iters"]:
            out.append(f"  iter{iter_num:02d}: ❌ DOUBLE-COUNT")
            for name, expr, reason in suspects:
                out.append(f"      component '{name}': {expr}")
                out.append(f"        → {reason}")
    
    out.append("\nVALIDATOR VERDICTS")
    out.append("-" * 70)
    for it in audit["iterations"]:
        if it["validator"]:
            v = it["validator"]
            line = v["line"][:200]
            out.append(f"  iter{it['iter']:02d} (j {it['iter']-1:02d}): {line}")
    
    out.append("\nSUMMARY")
    out.append("-" * 70)
    s = audit["summary"]
    out.append(f"  Double-count violations: {len(s['double_count_iters'])}")
    out.append(f"  Deletion-list violations: {len(s['deletion_violation_iters'])}")
    out.append(f"  Unstructured Dispatcher output: {len(s['unstructured_dispatcher_iters'])}")
    
    if s['validator_verdicts']:
        verdict_counts = {}
        for _, label, _ in s['validator_verdicts']:
            verdict_counts[label] = verdict_counts.get(label, 0) + 1
        out.append(f"  Validator verdicts: {verdict_counts}")
    
    return "\n".join(out)


def format_markdown(audit: Dict) -> str:
    if "error" in audit:
        return f"# Audit Error\n\n{audit['error']}\n"
    
    out = []
    out.append(f"# Cognition Audit — `{audit['run_dir']}`\n")
    out.append(f"**Iterations:** {audit['n_iterations']}\n")
    
    out.append("## Component Evolution\n")
    out.append("| iter | n | components |")
    out.append("|---|---|---|")
    for it in audit["iterations"]:
        comps_str = ", ".join(f"`{c}`" for c in it["components"]) if it["components"] else "(none)"
        out.append(f"| {it['iter']:02d} | {it['n_components']} | {comps_str} |")
    
    out.append("\n## Coder Deletion Fidelity\n")
    out.append("| iter | status | detail |")
    out.append("|---|---|---|")
    for it in audit["iterations"]:
        check = it["deletion_check"]
        if check["status"] == "violated":
            out.append(f"| {it['iter']:02d} | ❌ violated | failed to delete: `{', '.join(check['violated'])}` |")
        elif check["status"] == "unstructured":
            raw = check['raw'][:80].replace('\n', ' ').replace('|', '\\|')
            out.append(f"| {it['iter']:02d} | ⚠️ unstructured | `{raw}` |")
        elif check["status"] == "none_requested":
            out.append(f"| {it['iter']:02d} | ✓ none | no excisions requested |")
        elif check["status"] == "missing":
            out.append(f"| {it['iter']:02d} | — | no dispatcher output |")
        else:
            out.append(f"| {it['iter']:02d} | ✓ honored | {len(check['deletions'])} deletions |")
    
    out.append("\n## Double-Count Audit\n")
    if not audit["summary"]["double_count_iters"]:
        out.append("✓ No double-count violations detected\n")
    else:
        out.append("| iter | suspect | assignment | reason |")
        out.append("|---|---|---|---|")
        for iter_num, suspects in audit["summary"]["double_count_iters"]:
            for name, expr, reason in suspects:
                expr_e = expr.replace('|', '\\|')
                out.append(f"| {iter_num:02d} | `{name}` | `{expr_e}` | {reason} |")
    
    out.append("\n## Validator Verdicts\n")
    out.append("| iter (judging) | verdict | full line |")
    out.append("|---|---|---|")
    for it in audit["iterations"]:
        if it["validator"]:
            v = it["validator"]
            line = v["line"][:200].replace('\n', ' ').replace('|', '\\|')
            out.append(f"| {it['iter']:02d} (j {it['iter']-1:02d}) | {v['verdict']} | {line} |")
    
    out.append("\n## Summary\n")
    s = audit["summary"]
    out.append(f"- Double-count violations: **{len(s['double_count_iters'])}**")
    out.append(f"- Deletion-list violations: **{len(s['deletion_violation_iters'])}**")
    out.append(f"- Unstructured Dispatcher output: **{len(s['unstructured_dispatcher_iters'])}**")
    if s['validator_verdicts']:
        verdict_counts = {}
        for _, label, _ in s['validator_verdicts']:
            verdict_counts[label] = verdict_counts.get(label, 0) + 1
        out.append(f"- Validator verdicts: {verdict_counts}")
    
    return "\n".join(out)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Audit cognition records from an ARD pipeline run.",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Directory containing iter##_cognition_record.json files.",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=None,
        help="Save markdown report to this path.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Save machine-readable JSON to this path.",
    )
    args = parser.parse_args()
    
    if not args.run_dir.exists() or not args.run_dir.is_dir():
        print(f"Error: {args.run_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    audit = audit_run(args.run_dir)
    print(format_text(audit))
    
    if args.md:
        args.md.write_text(format_markdown(audit))
        print(f"\n📄 Markdown report → {args.md}")
    
    if args.json:
        args.json.write_text(json.dumps(audit, indent=2, default=str))
        print(f"\n📄 JSON report → {args.json}")


if __name__ == "__main__":
    main()