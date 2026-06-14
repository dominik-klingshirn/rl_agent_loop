"""
extractor_schema.py  —  lives in src/schemas.py

The minimal Extractor surface, serving exactly two consumers:

  (1) DASHBOARD COMPLETENESS — replaces the fragile regex in
      extract_cognition.py (_infer_proposal_type + the Selected-Proposal regex)
      that currently mislabels proposals and silently misses the selected one.
  (2) ORCHESTRATION CONTEXT FLAGS — supplies the two prose facts the
      deterministic AST/regex layer cannot get, each backing one named flag:
        - the Strategist's PART 1 excision names  -> "deletion never transited"
        - handoff.code_change_present             -> "RL paraphrased the code away"

------------------------------------------------------------------------------
DESIGN INVARIANTS (locked; changing one is a schema-version bump, not an edit)
------------------------------------------------------------------------------
I1. The Extractor returns FACTS, never judgments. Proposal *type* is DERIVED in
    Python (derive_proposal_type / derive_display_bucket) from term_count +
    touches_existing. The model never classifies. This mirrors spec section 6.1
    and removes the label-flapping the regex cascade suffers from.

I2. One semantic distinction is intentionally ABSENT: delete-vs-modify-vs-replace
    intent. The current Strategist prompt (system_prompts/strategist) already
    decomposes this at the source — PART 1 is removal-only, and anything whose
    input or behavioral purpose changes is routed to PART 2 as excision + addition
    (the prompt's functional-identity rule). A PART 1 name is therefore a deletion
    by construction. The replace pattern re-emerges only as a Coder *implementation*
    tactic, which is an AST fact (realized formula), not Strategist prose — so it
    belongs to the deterministic layer, never the Extractor. (Verified against real
    records: iter09 deletes `upright_bonus` in PART 1 and adds `r_center` in PART 2
    — the prompt's split working as designed.)

I3. CONTEXT-GRADE, not GATE-GRADE. These outputs annotate dashboards and raise
    soft flags. A wrong field costs a second glance, never a corrupted score. The
    Tier-2 scorer (del_honored gate, INDETERMINATE, E1-E19) is a SEPARATE, higher-
    bar consumer and is frozen/backlogged. Do not let this schema absorb its rigor.

Field names mirror TIER2_ORCHESTRATION_SPEC_v4 section 6.2 (orch_v4) so wiring
this into prompts/builders.py later is a rename-free drop-in.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


SCHEMA_VERSION = "extractor_v1"


# ---------------------------------------------------------------------------
# Closed vocabulary
# ---------------------------------------------------------------------------

class ProposalKind(str, Enum):
    """The kind tag the Strategist writes in a proposal header parenthetical,
    e.g. 'Attitude Smoothing (Modification)'. REFERENCE SIGNAL ONLY — empirically
    unreliable (verified: iter01 tags a proposal '(Modification)' whose handoff
    both deletes four components and adds a new term). The canonical type is
    derived from facts, never from this. Captured only so disagreements between
    the author's label and the derived type are visible in instrument-health.
    """
    ADDITION = "addition"
    MODIFICATION = "modification"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Leaf models
# ---------------------------------------------------------------------------

class ProposalExtract(BaseModel):
    """One Strategist proposal (PART 2). The two load-bearing fields are
    term_count and touches_existing; everything else is descriptive."""

    ordinal: int = Field(
        ...,
        ge=1,
        description="1-indexed proposal number as labeled (Proposal 1/2/3).",
    )
    title: str = Field(
        ...,
        description="Proposal title verbatim, WITHOUT the kind parenthetical. "
                    "'Attitude Smoothing (Modification)' -> 'Attitude Smoothing'.",
    )
    author_declared_kind: ProposalKind = Field(
        ProposalKind.UNKNOWN,
        description="Kind from the header parenthetical if present, else unknown. "
                    "Reference only — never used to derive the canonical type.",
    )

    # --- the two factual fields the type is derived from ---
    touches_existing: bool = Field(
        ...,
        description="True iff the proposal changes the formula of an EXISTING "
                    "component (an in-place modification). False if it only "
                    "introduces brand-new term(s). A delete-old-add-new proposal "
                    "is False here (the new term is new) — the deletion lives in "
                    "PART 1, captured separately in IterationExtract.excision_names.",
    )
    term_count: int = Field(
        ...,
        ge=0,
        description="Count of DISTINCT NEW reward terms introduced. Pure in-place "
                    "modification = 0. One new r_* term = 1. Synergistic multi-term "
                    "addition = 2+. A safety-variant rewrite of the SAME term "
                    "(`r_x = ...` then `r_x = max(0, ...)`) counts as 1, not 2.",
    )

    target_component: str | None = Field(
        None,
        description="For a modification (touches_existing=True): the existing "
                    "component being changed, as written ('upright_bonus' or "
                    "'r_upright'). Null for a pure addition.",
    )
    new_term_names: list[str] = Field(
        default_factory=list,
        description="Names of new r_* terms introduced, verbatim (['r_v_descent']). "
                    "Empty for a pure modification. len should equal term_count when "
                    "the prose names the terms; a mismatch is fine and is noted.",
    )

    @model_validator(mode="after")
    def _coherence(self):
        # Soft self-consistency only: a pure modification adds no new terms.
        # We do NOT raise — context-grade (I3). An incoherent combination is,
        # however, the single most useful thing to surface for prompt-tuning, so
        # both labeler and Extractor should avoid it. Enforcement (if any) is the
        # harness's job, not the model's. Documented here, intentionally a no-op.
        return self


class RoleHandoffExtract(BaseModel):
    """The Research Lead's selection + verbatim 'Execution Hand-off' to the Coder.

    Carries the orchestration fact regex misses most: did a concrete code change
    survive the handoff (code_change_present), and which proposal was chosen
    (selected_ordinal). Verified across records, the selected-proposal line is
    FORMAT-UNSTABLE — 'Proposal 1: X', '[3. X]', 'Proposal 3: X' all occur — which
    is exactly why the dashboard regex drops it and why the Extractor earns its keep.
    """

    selected_ordinal: int | None = Field(
        None,
        ge=1,
        description="Proposal number the RL selected (1-indexed). Read it from "
                    "ANY of: 'Selected Proposal: Proposal N', a leading '[N. ...]', "
                    "or 'Proposal N:' in the decision block. Null only if truly "
                    "unstated. Do NOT infer from content similarity — read the label.",
    )
    selected_title: str | None = Field(
        None,
        description="Title of the selected proposal, verbatim (brackets/kind tag "
                    "stripped). May differ in wording from the PART 2 title; record "
                    "what the RL wrote.",
    )
    code_change_present: bool = Field(
        ...,
        description="THE flag-driving field. True iff the handoff forwards an "
                    "explicit code change — a formula or an r_* = ... line under "
                    "'Code Additions' (or an equivalent concrete change). False iff "
                    "the proposal was restated as PROSE ONLY with no concrete code "
                    "surviving. False is the 'paraphrased-away the code' signal.",
    )
    handoff_additions: list[str] = Field(
        default_factory=list,
        description="Code-addition line(s) as forwarded, verbatim, incl. LaTeX/"
                    "fenced forms ('R_well = -(5.0*angle**2 + 2.0*vx**2)'). "
                    "May be empty when code_change_present is False.",
    )
    handoff_deletions: list[str] = Field(
        default_factory=list,
        description="Deletion names forwarded in the handoff's 'Code Deletions' "
                    "field, verbatim, one per entry. EMPTY LIST if the field is "
                    "empty or holds a null marker ('[None]', 'None', '-'). Never "
                    "put a null marker token in this list.",
    )


# ---------------------------------------------------------------------------
# Top-level per-iteration model
# ---------------------------------------------------------------------------

class IterationExtract(BaseModel):
    """Everything the Extractor returns for ONE cognition record.

    Sourced from STRATEGIST and RESEARCH_LEAD prose only. Pairs with the
    deterministic CodeChangeRecord (AST) in analyze_run.py; the dashboard and the
    flags consume both. The Organizer/Dispatcher/Coder phases are NOT read here —
    they are what the deterministic layer and the eventual scorer compare against.
    """

    schema_version: Literal["extractor_v1"] = SCHEMA_VERSION
    iteration: int = Field(..., ge=1)

    # --- Strategist PART 1 (origin of all deletion intent) ---
    excision_names: list[str] = Field(
        default_factory=list,
        description="Component names listed in PART 1 (SURGICAL EXCISION), VERBATIM "
                    "and UNCORRECTED — including any spacing/bracket/garble "
                    "corruption (the deterministic resolver normalizes; labels must "
                    "preserve the raw token). EMPTY LIST when PART 1 states nothing "
                    "is excised. (Verified shapes: backticked single names, "
                    "backticked multi-name bullet lists.)",
    )

    # --- Strategist PART 2 ---
    proposals: list[ProposalExtract] = Field(
        default_factory=list,
        description="All proposals authored (typically exactly 3).",
    )

    # --- Research Lead ---
    handoff: RoleHandoffExtract = Field(
        ...,
        description="The RL's selection + verbatim execution handoff.",
    )

    # --- non-scoring instrument-health note channel ---
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="One free-text note per ambiguity/malformation encountered. "
                    "Surfaced in instrument-health; never fed to any score. These "
                    "notes are what make a fixture valuable for prompt-tuning.",
    )

    @property
    def excision_count(self) -> int:
        """Direct feed for the dashboard's CognitionRecord.excision_count."""
        return len(self.excision_names)


# ---------------------------------------------------------------------------
# Deterministic derivation — type is COMPUTED, never extracted (I1, section 6.1)
# ---------------------------------------------------------------------------

CanonicalType = Literal["modification", "addition"]
DisplayBucket = Literal["modification", "single_term_addition", "multi_term_addition"]


def derive_proposal_type(p: ProposalExtract) -> CanonicalType:
    """Canonical two-type taxonomy matching the CURRENT Strategist prompt.

    The prompt defines exactly two kinds: modification (in-place change of an
    existing term) and addition (one or more new terms). This replaces the old
    regex cascade in extract_cognition._infer_proposal_type, which guessed from
    body text and fell through to 'unknown'.
    """
    if p.touches_existing and p.term_count == 0:
        return "modification"
    return "addition"


def derive_display_bucket(p: ProposalExtract) -> DisplayBucket:
    """Three-way DISPLAY refinement for the dashboard chart, splitting additions
    by term count. This REPLACES the outdated 'cluster' verbiage:
        old 'modification' -> 'modification'
        old 'addition'     -> 'single_term_addition'
        old 'cluster'      -> 'multi_term_addition'
    Use this for the stacked proposal-type chart; use derive_proposal_type when
    the two-type canonical taxonomy is wanted (e.g. cross-campaign rollups).
    Multi-term additions are the higher-complexity intervention and worth seeing
    distinctly — the same reason 'cluster' was introduced originally.
    """
    if p.touches_existing and p.term_count == 0:
        return "modification"
    if p.term_count >= 2:
        return "multi_term_addition"
    return "single_term_addition"


def proposal_type_counts(it: IterationExtract) -> dict:
    """Drop-in replacement for CognitionRecord.proposal_type_counts, using the
    corrected three display buckets. analyze_run.py's chart keys change from
    {modification, addition, cluster} to
    {modification, single_term_addition, multi_term_addition}."""
    counts = {
        "modification": 0,
        "single_term_addition": 0,
        "multi_term_addition": 0,
    }
    for p in it.proposals:
        counts[derive_display_bucket(p)] += 1
    return counts
