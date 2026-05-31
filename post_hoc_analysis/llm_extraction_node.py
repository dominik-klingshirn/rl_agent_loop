#!/usr/bin/env python3
"""
llm_extraction_node.py
----------------------
Tier-2 post-hoc extraction node. Uses Google AI Studio (Gemini) to produce a
robust, schema-constrained reading of each iteration's cognition record where
the regex extractor in extract_cognition.py emits warnings / "unknown".

Resolves four things the regex path is brittle on:
  1. Proposal TYPE per Strategist proposal       (regex -> proposal_N_type_unknown)
  2. Research Lead's SELECTED proposal            (regex -> selection_unparsed)
  3. Chain FIDELITY of the selected proposal across
     Strategist -> Organizer -> Research Lead -> Dispatcher -> Coder
  4. Structural integrity cross-checks:
     internal contradiction, divergence origin, root cause, redundancy.

Design invariants (do not erode these when extending):
  * Anchors are deterministic. The LLM is given the regex-found proposal
    headers and the AST component delta; it classifies/judges against them.
    It does NOT define the index space or the code-delta ground truth.
  * Disagreement with regex is recorded, never hidden (see _crosscheck).
  * Counts are tallied in Python from the model's proposal list, not asked of
    the model.
  * temperature=0, pinned model, schema_version stamped, raw response cached.
    Idempotent on disk; --force to re-bill.

Boundary: NEVER import this from train.py / the inner loop. Analysis only.

Env:
  GEMINI_API_KEY   (or GOOGLE_API_KEY) — picked up by genai.Client()

Usage:
  python3 llm_extraction_node.py --campaign-path /abs/path/to/campaign --iter 7
  python3 llm_extraction_node.py --campaign-path /abs/path/to/campaign        # all iters
  python3 llm_extraction_node.py --campaign-path ... --iter 7 --force
  python3 llm_extraction_node.py --campaign-path ... --validate               # regression check
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
from extract_cognition import (
    RunPaths,
    extract_cognition_record,   # regex path, kept for cross-check
    load_code_change,           # AST anchor
)

load_dotenv()

# --- Provenance / determinism knobs -----------------------------------------
SCHEMA_VERSION = "extract-v2.1"
EXTRACTOR_MODEL = "gemini-3.5-flash"
TEMPERATURE = 0.0

CHAIN_PHASES = ("strategist", "organizer", "research_lead", "dispatcher", "coder")
PROP_TYPES = ("modification", "addition", "cluster", "unknown")


# ===========================================================================
# Output schema (Gemini response_schema)
# ===========================================================================

class ProposalClass(BaseModel):
    index: int = Field(description="Proposal number as written by the Strategist.")
    header: str
    proposal_type: str = Field(
        description=(
            "One of: modification, addition, cluster, unknown. "
            "Classify by component-dict structure (see system instructions), NOT by wording."
        )
    )
    type_basis: str = Field(
        description=(
            "'ast_delta' for the selected proposal (grounded in the actual code delta); "
            "'text_inferred' for all other proposals."
        )
    )
    rationale: str = Field(description="One sentence; cite the deciding phrase.")


class RedundancyItem(BaseModel):
    components: list[str] = Field(
        description="Exactly two component names from the current roster that share a physical quantity."
    )
    shared_quantity: str = Field(
        description="The physical quantity penalized by both (e.g. 'x²', 'angle²', 'vx²')."
    )
    detected_by: str = Field(
        description="Set to 'llm'. Python will reconcile with AST double_count_flags and may upgrade to 'both'."
    )


class HopFidelity(BaseModel):
    hop: str = Field(description="organizer | research_lead | dispatcher | coder")
    status: str = Field(
        description=(
            "preserved | altered | dropped | substituted | scope_expanded | absent. "
            "Judge against the output THIS hop RECEIVED from the previous hop."
        )
    )
    evidence: str = Field(
        description="One sentence: what the hop received vs. what it output."
    )


class IterationExtraction(BaseModel):
    iteration: int
    proposals: list[ProposalClass]
    selected_proposal_index: Optional[int]
    selected_proposal_header: Optional[str]
    selected_proposal_declared_type: str = Field(
        description=(
            "Type of the SELECTED proposal specifically. "
            "One of: modification, addition, cluster, unknown. "
            "Classify by component-dict structure against the ast_delta anchor."
        )
    )
    part1_excised_components: list[str] = Field(
        description=(
            "Component names explicitly listed in the Strategist's PART 1 surgical excision section. "
            "Empty list if PART 1 states no components are being excised."
        )
    )
    chain_fidelity: list[HopFidelity]
    chain_intact: bool = Field(
        description="True iff every hop status is 'preserved' (no altered/dropped/substituted/scope_expanded)."
    )
    coder_matches_ast: Optional[bool] = Field(
        description=(
            "True iff the code delta (added/excised_components) matches the selected proposal's intent; "
            "null if no delta was provided."
        )
    )
    internal_contradiction: bool = Field(
        description=(
            "True iff the selected proposal's declared operation requires removing or in-place-changing "
            "an existing component, BUT the proposal does not specify that removal/modification "
            "(its PART 1 excision list and its own deletion directive do not cover the affected component). "
            "A complete Old-form→New-form rewrite for the same key is NOT contradictory."
        )
    )
    contradiction_detail: str = Field(
        description="One sentence explaining the contradiction; empty string if internal_contradiction is false."
    )
    divergence_origin_hop: Optional[str] = Field(
        description=(
            "The FIRST hop whose output stops faithfully carrying the selected proposal's operation. "
            "Null if chain_intact. A hop that faithfully forwards an already-broken instruction "
            "is 'preserved', not at fault."
        )
    )
    root_cause: str = Field(
        description=(
            "Apply in order: "
            "(1) chain_intact → 'none'. "
            "(2) internal_contradiction → 'proposal_internal_contradiction'. "
            "(3) non-coder hop mutated a faithful instruction → 'upstream_hop_mutation'. "
            "(4) else → 'coder_implementation'."
        )
    )
    redundancy_introduced: list[RedundancyItem] = Field(
        default_factory=list,
        description=(
            "Component pairs in the CURRENT roster that penalize the same physical quantity. "
            "Report even when chain_intact is true. Mark detected_by as 'llm'."
        )
    )
    notes: str = Field(
        default="",
        description=(
            "Anything ambiguous or noteworthy not captured by a dedicated field. "
            "Do NOT leave empty if a redundancy, contradiction, or ghost variable is present."
        )
    )


# ===========================================================================
# System prompt
# ===========================================================================

_SYSTEM = """\
You audit a multi-agent reward-design pipeline. A reward-function change flows
through five LLM phases in order:
  Strategist  -> proposes numbered options (PROPOSAL N: or ### Proposal N)
  Organizer   -> reformats the Strategist's proposals (no new ideas)
  ResearchLead-> selects exactly one proposal
  Dispatcher  -> turns the selection into a coder work order
  Coder       -> writes the reward.py change

You are given authoritative AST anchors:
  added_components    — component keys newly present in the reward dict this iter
  excised_components  — component keys that were present last iter but are now gone
  component_roster    — ordered keys in the components dict this iteration
  ghost_vars          — r_* variables computed but not reachable from any component
  double_count_flags  — component pairs whose expanded r_* sets overlap

Do NOT invent proposals or components. Be terse; cite the deciding phrase.

─── STRUCTURAL TYPE DEFINITION ─────────────────────────────────────────────
Classify each proposal by the number and relationship of terms WITHIN that
single proposal, not by whether existing component keys are removed.
Do NOT use the ast_delta to determine the type — the ast_delta anchors the
selected proposal's coder verdict and is used only in cross-checks, not to
drive the classification itself.

  addition     = the proposal introduces ONE new term.
  modification = the proposal changes ONE existing term (rescale, sign-invert,
                 gate, change functional form, or Old Form → New Form for that
                 same logical term). Even if a new key name results, if only ONE
                 term is being acted on, it is a modification.
  cluster      = the proposal rests on TWO OR MORE cooperating terms treated as
                 one inseparable synergistic unit, where the synergy produces
                 something no single term can (e.g. a positional spring paired
                 with a velocity damper). A cluster does NOT require touching
                 existing components — two brand-new terms bundled for their
                 synergy qualify. A cluster may also bundle a modification with
                 an addition (e.g. rescale one existing term AND introduce a new
                 coupled term). The proposal boundary disambiguates intent: one
                 proposal carrying ≥2 cooperating terms is a cluster; two
                 independent terms would be two separate proposals.
  Use "unknown" only if genuinely undecidable.

─── TYPE BASIS ─────────────────────────────────────────────────────────────
For the SELECTED proposal set type_basis = "ast_delta" (classification was
verified against the actual code delta). For all other proposals set
type_basis = "text_inferred". type_basis does NOT mean the ast_delta
determined the type — it means the type was cross-checked against it.

─── PART 1 EXCISION ────────────────────────────────────────────────────────
Read part1_excised_components from the Strategist's PART 1 section only — the
bullet list of explicitly named excised components. If PART 1 states "No
components are being excised", this list is empty.

─── PREDECESSOR-RELATIVE FIDELITY ──────────────────────────────────────────
Judge each hop against the OUTPUT IT RECEIVED from the previous hop:
  Strategist → Organizer → ResearchLead → Dispatcher → Coder
Set divergence_origin_hop = the FIRST hop whose output stops faithfully
carrying the selected proposal's operation. A hop that faithfully forwards an
already-broken instruction is "preserved", not at fault. Judge semantics,
not formatting — reformatting is fine.

For CLUSTER operations: judge fidelity at the semantic level — did the hop
correctly forward the cluster concept (which components merge → one new
component)? Incomplete deletion lists in intermediate hops are acceptable if
the cluster concept is still clearly expressed. The Strategist may use old r_*
variable names (e.g. r_vel_x) that differ from current roster keys
(x_position_pressure) — use component_roster + ast_delta to resolve these;
do not treat old-name vs current-key discrepancies as fidelity breaks.

If a proposal describes a mathematical combination (R_stable = R_A + R_B) and
the coder implements the sub-components as SEPARATE component-dict keys
(e.g. angle_stability, angular_velocity_stability), this is "preserved" —
the semantic intent is maintained. Ghost variables that aggregate sub-components
(e.g. r_stable computed but not in the dict) are informational, not a break.

Hop status vocabulary:
  preserved      — semantically faithful to what it received
  altered        — target/operation/sign/intent changed
  dropped        — the selected change is missing downstream
  substituted    — a different change took its place
  scope_expanded — extra un-asked changes were added
  absent         — that phase's text was not provided

─── INTERNAL CONTRADICTION TEST ────────────────────────────────────────────
Set internal_contradiction = true iff BOTH of the following hold:
  (A) The proposal's CONCEPTUAL HYPOTHESIS says it will replace/modify/remove
      an existing component or sub-term (e.g. "replace the vx term",
      "modify component Y").
  (B) The proposal's MATHEMATICAL FORMULATION and PART 1 deletion list do NOT
      show HOW that removal/change happens — they do not give an explicit
      "delete key K", an Old Form → New Form for the affected key, or a cluster
      body that names the affected key as one of the merged sources.
      Stating the INTENT to replace is not enough; the MECHANISM must also be
      present in the proposal body.

A proposal that gives a complete in-place rewrite (Old form → New form for the
SAME key, explicitly shown) is NOT contradictory — the mechanism is specified.
A cluster proposal that explicitly names which existing keys are merged is NOT
contradictory — the cluster body IS the mechanism specification. Only mark
internal_contradiction = true if the mechanism is absent from the proposal text.

─── ROOT CAUSE DECISION ORDER ──────────────────────────────────────────────
Apply in order; stop at first match:
  1. chain_intact              → root_cause = "none"
  2. internal_contradiction    → root_cause = "proposal_internal_contradiction"
  3. non-coder hop mutated a faithfully-forwarded instruction
                               → root_cause = "upstream_hop_mutation"
  4. else                      → root_cause = "coder_implementation"

─── REDUNDANCY ─────────────────────────────────────────────────────────────
Using the provided component_roster and ast_delta, report in
redundancy_introduced any two components in the CURRENT roster that penalize
the SAME physical quantity (e.g. two terms penalizing x², two penalizing
angle²). This is distinct from a fidelity break — report it even when
chain_intact is true. Set detected_by = "llm".

─── CODER vs AST (SPECIAL RULE) ────────────────────────────────────────────
The ast_delta (added_components, excised_components) is GROUND TRUTH for the
coder hop. The coder hop is the ONE exception to pure predecessor-relative
fidelity: judge it against the SELECTED PROPOSAL'S INTENT, not just the
dispatcher's explicit instruction.
  • If the selected proposal declared a modification (replace/rewrite an
    existing component) but the ast_delta shows no excision of the targeted
    component (even if the dispatcher said "no deletions"), the coder hop is
    "altered" — the coder's implementation does not match the proposal's intent.
  • If the selected proposal declared an addition and the ast_delta matches,
    the coder hop is "preserved".
  • If an earlier hop (dispatcher, research_lead, organizer) already mutated the
    proposal's instruction, and the coder faithfully followed THAT mutated
    instruction, the EARLIER hop is the divergence origin — not the coder.
Set coder_matches_ast based on whether the ast_delta matches the selected
proposal's intent.

─── NOTES ──────────────────────────────────────────────────────────────────
Use notes whenever something is ambiguous or noteworthy and not captured by a
dedicated field. Do NOT leave it empty if a redundancy, contradiction, or ghost
variable is present.\
"""


# ===========================================================================
# Prompt assembly
# ===========================================================================

def _phase_text(record: dict, phase: str) -> str:
    for call in record.get("calls", []):
        if call.get("phase") == phase:
            return call.get("response_content") or ""
    return ""


def _build_user_payload(record: dict, regex_cog, code_change) -> str:
    headers = [f"  Proposal {p.index}: {p.header}" for p in regex_cog.proposals]
    anchor_headers = "\n".join(headers) if headers else "  (regex found none)"

    if code_change is not None:
        ast_block = (
            f"added_components:    {code_change.added_components}\n"
            f"excised_components:  {code_change.excised_components}\n"
            f"component_roster:    {code_change.component_names}\n"
            f"ghost_vars:          {code_change.ghost_vars}\n"
            f"double_count_flags:  {code_change.double_count_flags}\n"
            f"ast_available:       {code_change.ast_available}\n"
            f"patch_available:     {code_change.patch_available}"
        )
    else:
        ast_block = "(no AST delta available — coder_matches_ast should be null)"

    sections = [
        f"ITERATION {record.get('iteration')}",
        "",
        "ANCHOR — regex-found proposal headers (authoritative indices):",
        anchor_headers,
        "",
        "ANCHOR — AST code delta (ground truth; use to set type_basis for selected proposal):",
        ast_block,
        "",
    ]
    for phase in CHAIN_PHASES:
        txt = _phase_text(record, phase).strip()
        sections.append(f"===== {phase.upper()} OUTPUT =====")
        sections.append(txt if txt else "(no output recorded)")
        sections.append("")
    return "\n".join(sections)


# ===========================================================================
# Gemini call
# ===========================================================================

def _call_gemini(system: str, user: str) -> IterationExtraction:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the env.")

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=EXTRACTOR_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=TEMPERATURE,
            response_mime_type="application/json",
            response_schema=IterationExtraction,
        ),
    )
    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, IterationExtraction):
        return parsed
    return IterationExtraction.model_validate_json(resp.text)


# ===========================================================================
# Post-LLM structural checks (deterministic, Python)
# ===========================================================================

def _compute_structural_checks(
    ext: IterationExtraction,
    ast_delta: dict | None,
) -> tuple[dict, list[dict]]:
    """
    Returns (structural_checks dict, updated redundancy_introduced list).

    Reconciles the LLM's redundancy_introduced against AST double_count_flags:
    pairs in both → detected_by='both'; AST-only pairs are appended with
    detected_by='ast'; LLM-only pairs keep detected_by='llm'.
    """
    if ast_delta is None:
        null_checks = {
            "proposal_excised": None,
            "type_vs_delta_mismatch": None,
            "type_vs_delta_detail": None,
            "cluster_footprint": None,
            "redundancy_ast_only": None,
            "redundancy_llm_only": None,
        }
        return null_checks, [r.model_dump() for r in ext.redundancy_introduced]

    # ── proposal_excised: total excised minus PART 1 housekeeping ────────────
    part1_excised = set(ext.part1_excised_components)
    all_excised = set(ast_delta["excised_components"])
    proposal_excised = sorted(all_excised - part1_excised)

    # ── type_vs_delta_mismatch ────────────────────────────────────────────────
    # cluster → null (N/A; use cluster_footprint for informational delta)
    # modification / addition → bool pass/fail
    n_added = ast_delta["n_added"]
    declared = ext.selected_proposal_declared_type
    mismatch: bool | None = False
    detail = ""
    cluster_footprint: dict | None = None
    if declared == "modification":
        if n_added != 0 or len(proposal_excised) != 0:
            mismatch = True
            detail = (f"declared modification but n_added={n_added}, "
                      f"proposal_excised={proposal_excised}")
    elif declared == "addition":
        if n_added < 1 or len(proposal_excised) != 0:
            mismatch = True
            detail = (f"declared addition but n_added={n_added}, "
                      f"proposal_excised={proposal_excised}")
    elif declared == "cluster":
        mismatch = None  # N/A — cluster footprint is informational only
        cluster_footprint = {
            "added": n_added,
            "excised": proposal_excised,
        }

    # ── redundancy reconciliation ─────────────────────────────────────────────
    dc_flags = ast_delta.get("double_count_flags", [])
    ast_pairs: set[frozenset] = {
        frozenset([f["component_a"], f["component_b"]]) for f in dc_flags
    }

    llm_pair_map: dict[frozenset, dict] = {}
    updated_redundancy: list[dict] = []
    for r in ext.redundancy_introduced:
        r_dict = r.model_dump()
        if len(r.components) == 2:
            key = frozenset(r.components)
            if key in ast_pairs:
                r_dict["detected_by"] = "both"
            llm_pair_map[key] = r_dict
        updated_redundancy.append(r_dict)

    # Append AST-only pairs not reported by the LLM
    for pair in ast_pairs:
        if pair not in llm_pair_map:
            shared_vars: list[str] = []
            for f in dc_flags:
                if frozenset([f["component_a"], f["component_b"]]) == pair:
                    shared_vars = f.get("shared_r_vars", [])
                    break
            updated_redundancy.append({
                "components": sorted(pair),
                "shared_quantity": ", ".join(shared_vars) if shared_vars else "shared r_* variables",
                "detected_by": "ast",
            })

    llm_set = set(llm_pair_map.keys())
    redundancy_ast_only = [sorted(p) for p in (ast_pairs - llm_set)]
    redundancy_llm_only = [sorted(p) for p in (llm_set - ast_pairs)]

    checks = {
        "proposal_excised": proposal_excised,
        "type_vs_delta_mismatch": mismatch,
        "type_vs_delta_detail": detail,
        "cluster_footprint": cluster_footprint,
        "redundancy_ast_only": redundancy_ast_only,
        "redundancy_llm_only": redundancy_llm_only,
    }
    return checks, updated_redundancy


# ===========================================================================
# Cross-check vs regex
# ===========================================================================

def _crosscheck(
    ext: IterationExtraction,
    regex_cog,
    structural_checks: dict,
) -> dict:
    regex_blind = len(regex_cog.proposals) == 0
    count_mismatch = (
        not regex_blind
        and len(ext.proposals) > 0
        and len(ext.proposals) != len(regex_cog.proposals)
    )
    selection_disagreement = (
        ext.selected_proposal_index != regex_cog.selected_proposal_index
    )
    regex_unknown = {p.index for p in regex_cog.proposals if p.inferred_type == "unknown"}
    resolved = sorted(
        p.index for p in ext.proposals
        if p.index in regex_unknown and p.proposal_type != "unknown"
    )
    type_disagreements: list[dict] = []
    if structural_checks.get("type_vs_delta_mismatch") is True:
        type_disagreements.append({
            "selected_index": ext.selected_proposal_index,
            "declared_type": ext.selected_proposal_declared_type,
            "detail": structural_checks.get("type_vs_delta_detail", ""),
        })
    return {
        "regex_selected_index": regex_cog.selected_proposal_index,
        "regex_proposal_count": len(regex_cog.proposals),
        "regex_blind": regex_blind,
        "count_mismatch": count_mismatch,
        "selection_disagreement": selection_disagreement,
        "regex_unknown_resolved": resolved,
        "type_disagreements": type_disagreements,
    }


def _tally_types(ext: IterationExtraction) -> dict:
    counts = {t: 0 for t in PROP_TYPES}
    for p in ext.proposals:
        counts[p.proposal_type] = counts.get(p.proposal_type, 0) + 1
    return counts


# ===========================================================================
# Orchestration
# ===========================================================================

def extract_iteration(paths: RunPaths, iteration: int, force: bool = False) -> dict:
    out_dir = paths.model_dir / "cognition" / "llm_extractions"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / f"iter{iteration:02d}_extraction.json"

    if cache.is_file() and not force:
        cached = json.loads(cache.read_text())
        if (cached.get("schema_version") == SCHEMA_VERSION
                and cached.get("extractor_model") == EXTRACTOR_MODEL):
            return cached

    record = json.loads(paths.cognition_record(iteration).read_text())
    regex_cog = extract_cognition_record(paths.cognition_record(iteration))

    try:
        code_change = load_code_change(paths, iteration)
        ast_delta: dict | None = {
            "added_components":   code_change.added_components,
            "excised_components": code_change.excised_components,
            "n_added":            code_change.n_added,
            "n_excised":          code_change.n_excised,
            "component_roster":   code_change.component_names,
            "double_count_flags": code_change.double_count_flags,
            "ghost_vars":         code_change.ghost_vars,
            "ast_available":      code_change.ast_available,
            "patch_available":    code_change.patch_available,
        }
    except Exception:
        code_change = None
        ast_delta = None

    user = _build_user_payload(record, regex_cog, code_change)
    ext = _call_gemini(_SYSTEM, user)

    structural_checks, updated_redundancy = _compute_structural_checks(ext, ast_delta)

    ext_dict = ext.model_dump()
    ext_dict["redundancy_introduced"] = updated_redundancy

    payload = {
        "schema_version":    SCHEMA_VERSION,
        "extractor_model":   EXTRACTOR_MODEL,
        "extracted_at":      datetime.now(timezone.utc).isoformat(),
        "ast_delta":         ast_delta,
        "extraction":        ext_dict,
        "proposal_type_counts": _tally_types(ext),
        "structural_checks": structural_checks,
        "crosscheck":        _crosscheck(ext, regex_cog, structural_checks),
    }
    cache.write_text(json.dumps(payload, indent=2))
    return payload


# ===========================================================================
# Validation harness
# ===========================================================================

# Ground-truth expectations per iteration.
# Each value is checked against the extraction output.
# Keys not present in a row are not asserted.
_VALIDATE_ITERS = [2, 3, 6, 7, 8, 9]

_EXPECTATIONS: dict[int, dict] = {
    2: {
        # P2 may be cluster (R_angle + R_v_ang cooperating) → mismatch N/A
        "chain_intact":            True,
        "root_cause":              "none",
        "divergence_origin_hop":   None,
        "internal_contradiction":  False,
        "type_vs_delta_not_true":  True,   # null (cluster N/A) or False — never True
        "redundancy_count":        0,
        "ghost_vars_contains":     ["r_stable"],
    },
    3: {
        # internal contradiction; modification classification fires mismatch
        "chain_intact":            False,
        "root_cause":              "proposal_internal_contradiction",
        "divergence_origin_hop":   "coder",
        "internal_contradiction":  True,
        "type_vs_delta_mismatch":  True,   # exact: modification declared, must fire
        "redundancy_count":        0,
    },
    6: {
        # P3 selected; cluster acceptable (rescale + new synergy term)
        "chain_intact":            True,
        "root_cause":              "none",
        "divergence_origin_hop":   None,
        "internal_contradiction":  False,
        "type_vs_delta_not_true":  True,   # cluster → null (N/A), not a mismatch
        "redundancy_count":        0,
        "ghost_vars_contains":     ["r_stable_cluster"],
    },
    7: {
        # P1 selected; P3 cluster is correct (spring-damper)
        "chain_intact":            True,
        "root_cause":              "none",
        "divergence_origin_hop":   None,
        "internal_contradiction":  False,
        "type_vs_delta_not_true":  True,   # modification no-mismatch or cluster null — both fine
        "redundancy_count":        0,
        # p3_type_not removed: cluster is correct for P3
    },
    8: {
        # dispatcher mutated modification→addition; break caught by chain/root_cause
        # declared modification → mismatch=True; if LLM re-labels as cluster → null (also OK)
        "chain_intact":            False,
        "root_cause":              "upstream_hop_mutation",
        "divergence_origin_hop":   "dispatcher",
        "internal_contradiction":  False,
        "type_vs_delta_not_false": True,   # True (modification) or null (cluster) — never False
        "redundancy_count_min":    1,
        "redundancy_components_include": ["x_position_pressure", "x_position_penalty"],
    },
    9: {
        # P1 cluster (lateral spring-damper) → mismatch N/A
        "chain_intact":            True,
        "root_cause":              "none",
        "divergence_origin_hop":   None,
        "internal_contradiction":  False,
        "type_vs_delta_not_true":  True,   # cluster → null (N/A)
        "redundancy_count":        0,
        "selected_type":           "cluster",
    },
}


def _check_iter(it: int, p: dict) -> list[str]:
    """Return list of failure strings (empty = pass)."""
    exp = _EXPECTATIONS[it]
    ext = p["extraction"]
    sc = p.get("structural_checks", {})
    ast = p.get("ast_delta") or {}
    failures: list[str] = []

    def fail(msg: str) -> None:
        failures.append(f"iter{it:02d}: {msg}")

    for field in ("chain_intact", "root_cause", "divergence_origin_hop",
                  "internal_contradiction"):
        if field in exp:
            got = ext.get(field)
            want = exp[field]
            if got != want:
                fail(f"{field}: expected {want!r}, got {got!r}")

    if "type_vs_delta_mismatch" in exp:
        # Exact equality check (used where the value must be precisely True/False).
        got = sc.get("type_vs_delta_mismatch")
        want = exp["type_vs_delta_mismatch"]
        if got != want:
            fail(f"type_vs_delta_mismatch: expected {want!r}, got {got!r}")

    if "type_vs_delta_not_true" in exp:
        # Cluster-compatible: value must be None or False, never True.
        got = sc.get("type_vs_delta_mismatch")
        if got is True:
            fail(f"type_vs_delta_mismatch must not be True (cluster→null or no-mismatch→False), got True")

    if "type_vs_delta_not_false" in exp:
        # Modification/cluster-ambiguous: value must be True or None, never False.
        got = sc.get("type_vs_delta_mismatch")
        if got is False:
            fail(f"type_vs_delta_mismatch must not be False (expect True for modification or null for cluster), got False")

    if "redundancy_count" in exp:
        got = len(ext.get("redundancy_introduced", []))
        want = exp["redundancy_count"]
        if got != want:
            fail(f"redundancy_introduced count: expected {want}, got {got}")

    if "redundancy_count_min" in exp:
        got = len(ext.get("redundancy_introduced", []))
        want = exp["redundancy_count_min"]
        if got < want:
            fail(f"redundancy_introduced count: expected >= {want}, got {got}")

    if "redundancy_components_include" in exp:
        all_comps: set[str] = set()
        for r in ext.get("redundancy_introduced", []):
            all_comps.update(r.get("components", []))
        for c in exp["redundancy_components_include"]:
            if c not in all_comps:
                fail(f"redundancy_introduced missing component {c!r}; found {sorted(all_comps)}")

    if "selected_type" in exp:
        got = ext.get("selected_proposal_declared_type")
        want = exp["selected_type"]
        if got != want:
            fail(f"selected_proposal_declared_type: expected {want!r}, got {got!r}")

    if "ghost_vars_contains" in exp:
        ghost = ast.get("ghost_vars", [])
        for g in exp["ghost_vars_contains"]:
            if g not in ghost:
                fail(f"ast_delta.ghost_vars missing {g!r}; found {ghost}")

    return failures


def run_validate(paths: RunPaths) -> None:
    print(f"Validating {_VALIDATE_ITERS} against extract-v2 ground truth …")
    print(f"Campaign: {paths.campaign_path}")
    all_failures: list[str] = []

    for it in _VALIDATE_ITERS:
        try:
            p = extract_iteration(paths, it, force=False)
        except Exception as exc:
            all_failures.append(f"iter{it:02d}: extraction failed — {exc}")
            print(f"  iter {it:>2}: ERROR {exc}")
            continue

        failures = _check_iter(it, p)
        ext = p["extraction"]
        sc = p.get("structural_checks", {})
        status = "PASS" if not failures else "FAIL"
        print(
            f"  iter {it:>2}: [{status}] "
            f"chain_intact={ext.get('chain_intact')} "
            f"root_cause={ext.get('root_cause')} "
            f"divergence={ext.get('divergence_origin_hop')} "
            f"int_contr={ext.get('internal_contradiction')} "
            f"type_mm={sc.get('type_vs_delta_mismatch')} "
            f"redund={len(ext.get('redundancy_introduced', []))}"
        )
        for f in failures:
            print(f"    ✗ {f}")
        all_failures.extend(failures)

    if all_failures:
        print(f"\n{len(all_failures)} assertion(s) FAILED — regression detected.")
        sys.exit(1)
    else:
        print("\nAll assertions passed.")


# ===========================================================================
# CLI
# ===========================================================================

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign-path", required=True)
    ap.add_argument("--iter", type=int, default=None,
                    help="Single iteration; omit to process all discovered iters.")
    ap.add_argument("--force", action="store_true", help="Re-bill, ignore cache.")
    ap.add_argument("--validate", action="store_true",
                    help="Run regression validation on iters 2,3,6,7,8,9 and assert ground truth.")
    args = ap.parse_args()

    paths = RunPaths(Path(args.campaign_path))

    if args.validate:
        run_validate(paths)
        return

    iters = [args.iter] if args.iter is not None else paths.discover_iterations()

    for it in iters:
        try:
            p = extract_iteration(paths, it, force=args.force)
            ext = p["extraction"]
            sc = p.get("structural_checks", {})
            cc = p["crosscheck"]
            sel = ext["selected_proposal_index"]
            flags: list[str] = []
            if cc.get("selection_disagreement"):
                flags.append("selection_disagreement")
            if cc.get("count_mismatch"):
                flags.append("count_mismatch")
            if sc.get("type_vs_delta_mismatch"):
                flags.append("type_vs_delta_mismatch")
            flag_str = (" ⚠ " + ",".join(flags)) if flags else ""
            print(
                f"iter {it:>2}: sel=P{sel} "
                f"types={p['proposal_type_counts']} "
                f"chain_intact={ext['chain_intact']} "
                f"root_cause={ext['root_cause']} "
                f"divergence={ext.get('divergence_origin_hop')}"
                f"{flag_str}"
            )
        except Exception as exc:
            print(f"iter {it:>2}: ERROR {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
