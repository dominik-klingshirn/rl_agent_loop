#!/usr/bin/env python3
"""
verify_orchestration.py  —  deterministic, no-cloud orchestration check for one run.

Reproduces the checks validated in the design session. Point it at a directory that
contains a run's  iter{NN}_reward.py  (00..N)  and  iter{NN}_cognition_record.json (01..N):

    python post_hoc_analysis/verify_orchestration.py \
        --campaign /path/to/campagin_dir \
        --model <model_name>          # sanitized version of name, i.e. with ':' replaced with '-'

It is the deterministic precursor to the spec's orchestration_score.py — it uses ONLY the
reward-file AST and the cognition records, makes ZERO cloud calls, and does no scoring.
Its purpose tonight is to tell you whether the Dispatcher prompt change reduced the
coder's dishonored deletions.

RELIABILITY (read this):
  * SOLID  (pure AST, no text parsing): added / excised / modified components, ghost
    variables, double-counts, truncation, missing roles. Trust these.
  * SEAM   (Disp->Coder del_honored): parses the dispatcher's "Code Deletions" field
    (backticked component names by contract — clean) and checks them against the AST.
    This is the right measurement for "did the coder honor the now-unambiguous field".
  * APPROX (Strat manifest): regex over the Strategist PART-1 excision list. KNOWN
    UNRELIABLE (un-backticked names -> false-empty; modify/context names -> false-positive).
    Shown for context only and flagged low-confidence. The production path replaces this
    with the cloud Extractor.
"""
import ast, hashlib, json, re, sys, glob, os, argparse, unicodedata, difflib
from pathlib import Path
from collections import Counter

PARAMS = {"obs", "prev_obs", "info"}
MODS = {"np", "math"}
SINKS = {"components", "total_reward"}

_STRUCTURAL_STOPLIST = {
    "components", "total_reward", "obs", "info", "prev_obs",
    "prev_angle", "prev_v_ang", "action", "calculate_reward",
}
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def normalize_deletion_name(raw: str, vocab: dict):
    """
    Resolve one candidate deletion token against the prior-iteration vocabulary.

    raw   : candidate name as it appeared in the dispatcher field (one logical name).
    vocab : {alias_or_key -> canonical_key}; MUST also map each canonical key to itself.

    Returns (canonical_or_None, status):
      'exact'      matched a known alias/key verbatim
      'normalized' matched only after unicode/whitespace cleanup  (rescued)
      'fuzzy'      matched by edit-distance after cleanup          (rescued, low-confidence)
      'stoplisted' structural identifier -> drop, not a deletion target
      'unresolved' no match -> excluded from gate denominator, forces INDETERMINATE
    """
    if raw in vocab:
        return vocab[raw], "exact"
    c = unicodedata.normalize("NFKC", raw)
    c = c.translate(_ZERO_WIDTH)
    c = c.replace(" ", " ").replace(" ", " ").replace("‑", "-")
    c = c.strip().strip("`*-• ").strip()
    c_ws = "".join(c.split())
    if c_ws in vocab:
        return vocab[c_ws], "normalized"
    if c_ws in _STRUCTURAL_STOPLIST:
        return None, "stoplisted"
    hit = difflib.get_close_matches(c_ws, list(vocab.keys()), n=1, cutoff=0.85)
    if hit:
        return vocab[hit[0]], "fuzzy"
    return None, "unresolved"


# ----------------------------- AST layer (SOLID) -----------------------------
def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def analyze(path):
    """Generalized intermediate tracking (convention-independent: r_*, R_*, Term_*, G_y...)."""
    tree = ast.parse(open(path).read())
    func = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "calculate_reward")
    assigns = {}
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id] = n.value
                elif isinstance(t, ast.Tuple):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            assigns[e.id] = n.value
    # leaf = RHS references only params/modules (obs-unpacking etc.); else intermediate
    inter = {v for v, r in assigns.items() if not ((_names(r) - {v}) <= (PARAMS | MODS))}
    # components dict: key -> value-expr node
    comp = {}
    for n in ast.walk(func):
        if (isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "components" for t in n.targets)
                and isinstance(n.value, ast.Dict)):
            for k, val in zip(n.value.keys, n.value.values):
                comp[k.value] = val
    # alias map: dict key <-> primary internal var (value is float(r_X) or r_X)
    alias = {}
    for k, val in comp.items():
        a = {k}
        v0 = val.args[0] if (isinstance(val, ast.Call) and val.args) else val
        if isinstance(v0, ast.Name):
            a.add(v0.id)
        alias[k] = a

    def cone(node):
        seen, st = set(), list(_names(node))
        while st:
            nm = st.pop()
            if nm in seen or nm not in inter:
                continue
            seen.add(nm)
            st += list(_names(assigns[nm]) - {nm})
        return seen

    ccone = {k: cone(v) for k, v in comp.items()}
    used = set().union(*ccone.values()) if ccone else set()
    ghosts = sorted(inter - used - SINKS)
    keys = list(comp)
    dbl = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            x = ccone[keys[i]] & ccone[keys[j]]
            if x:
                dbl.append((keys[i], keys[j], sorted(x)))

    def fp(k):
        parts = [ast.dump(comp[k])] + [v + "=" + ast.dump(assigns[v]) for v in sorted(cone(comp[k]))]
        return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]

    return dict(keys=set(comp), alias=alias, ghosts=ghosts, dbl=dbl,
                fps={k: fp(k) for k in comp})


# ------------------------- cognition-record parsing --------------------------
def load_record(path):
    d = json.load(open(path))
    return d.get("iteration"), {c["phase"]: c for c in d["calls"]}


def truncations(by):
    out = []
    for ph, c in by.items():
        ec = c.get("runtime", {}).get("eval_count")
        npd = c.get("options", {}).get("num_predict")
        if ec is not None and npd is not None and ec >= npd:
            out.append(f"{ph}({ec}>={npd})")
    return out


def disp_code_deletions(by):
    """SEAM source: dispatcher CODER_PAYLOAD 'Code Deletions' field (tolerant to old name)."""
    if "dispatcher" not in by:
        return None
    m = re.search(r"<CODER_PAYLOAD>(.*?)</CODER_PAYLOAD>",
                  by["dispatcher"]["response_content"], re.DOTALL)
    if not m:
        return None
    dm = re.search(r"Code Deletions(?:/Modifications)?:\*\*\s*(.*?)\n\*\*Code Additions",
                   m.group(1), re.DOTALL)
    if not dm:
        return None
    t = dm.group(1).strip()
    if re.fullmatch(r"(?i)\s*none\s*", t):
        return []
    candidates = []
    for line in t.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*•∙‣◦]\s*", "", line).strip()
        line = line.strip("`* ").strip()
        if not line or line.lower() == "none":
            continue
        parts = [p.strip().strip("`").strip() for p in line.split(",")]
        parts = [p for p in parts if p and p.lower() != "none"]
        if len(parts) > 1 and all(len(p.split()) <= 1 for p in parts):
            candidates.extend(parts)
        else:
            candidates.append(line)
    return candidates


def strat_manifest(by):
    """APPROX source: Strategist PART-1 excision names. Returns (names, low_confidence)."""
    if "strategist" not in by:
        return None, True
    r = by["strategist"]["response_content"]
    m = re.search(r"(?:PART\s*1|SURGICAL EXCISION)(.*?)(?:PART\s*2|PROPOSAL|\Z)", r, re.DOTALL | re.I)
    seg = m.group(1) if m else r[:1500]
    ticked = sorted(set(re.findall(r"`([A-Za-z_]\w*)`", seg)))
    if re.search(r"no\s+components?\s+(?:are\s+|being\s+|were\s+)?(?:excised|removed)", seg, re.I) and not ticked:
        return [], False
    # low confidence if PART-1 has descriptive prose but no backticked names
    low = (len(ticked) == 0)
    return ticked, low


# ----------------------------------- record discovery, and file parsing orchestration ------------------------------------
def run(model_root: Path):
    rew_dir = model_root / "generated_code"
    rec_dir = model_root / "cognition" / "json_cognition_records"

    if not model_root.exists():
        print(f"model_root not found: {model_root}"); return

    rew, recs = {}, {}
    for f in glob.glob(str(rew_dir / "iter*_reward.py")):
        i = int(re.search(r"iter(\d+)_reward", f).group(1))
        rew[i] = f
    for f in glob.glob(str(rec_dir / "iter*_cognition_record.json")):
        i = int(re.search(r"iter(\d+)_cognition", f).group(1))
        recs[i] = f

    if not rew:
        print(f"No iter*_reward.py found in {rew_dir}"); return
    R = {i: analyze(p) for i, p in rew.items()}
    iters = sorted(i for i in recs if i >= 1 and i in R and (i - 1) in R)

    dishonored_tally = Counter()
    ghost_iters, dbl_iters, trunc_events, missing_events = [], [], [], []
    indeterminate_iters = []
    name_normalization_rescued = 0
    deletion_name_unresolved = 0
    ALLROLES = ["validator", "strategist", "organizer", "research_lead", "dispatcher", "coder"]

    print("=" * 100)
    print(f"RUN: {model_root}")
    print("=" * 100)
    for i in iters:
        prev, cur = R[i - 1], R[i]
        _, by = load_record(recs[i])
        added = sorted(cur["keys"] - prev["keys"])
        excised = sorted(prev["keys"] - cur["keys"])
        modified = sorted(k for k in (prev["keys"] & cur["keys"]) if prev["fps"][k] != cur["fps"][k])

        # SEAM del_honored (dispatcher Code Deletions field, alias-resolved vs AST)
        a2k = {a: k for k, al in prev["alias"].items() for a in al}
        vocab = {**a2k, **{k: k for k in prev["keys"]}}
        reqs = disp_code_deletions(by)
        honored = dishonored = rescued = unresolved = None
        if reqs is not None:
            honored, dishonored, rescued, unresolved = [], [], [], []
            for raw in reqs:
                canon, status = normalize_deletion_name(raw, vocab)
                if status == "stoplisted":
                    continue
                if status == "unresolved":
                    unresolved.append(raw)
                else:
                    k = canon
                    if status in ("normalized", "fuzzy"):
                        rescued.append(f"{raw}->{k}({status})")
                    if k not in cur["keys"]:
                        honored.append(f"{raw}->{k}")
                    else:
                        dishonored.append(f"{raw}->{k}"); dishonored_tally[k] += 1
            name_normalization_rescued += len(rescued)
            deletion_name_unresolved += len(unresolved)

        # APPROX strat manifest (context only)
        man, low = strat_manifest(by)

        trunc = truncations(by)
        missing = [r for r in ALLROLES if r not in by]

        print(f"\n--- iter{i:02d} ---")
        print(f"  [AST]   added={added or '-'}  excised={excised or '-'}  modified={modified or '-'}")
        if cur["ghosts"]:
            print(f"  [AST]   GHOST vars (computed, unused): {cur['ghosts']}"); ghost_iters.append(i)
        if cur["dbl"]:
            print(f"  [AST]   DOUBLE-COUNT: {[(a,b,s) for a,b,s in cur['dbl']]}"); dbl_iters.append(i)
        if reqs is not None:
            if dishonored:
                gate = "FAIL"
            elif unresolved:
                gate = "INDETERMINATE"
                indeterminate_iters.append(i)
            else:
                gate = "PASS"
            seam_line = (f"  [SEAM]  dispatcher Code Deletions -> coder:  honored={honored or '-'}  "
                         f"DISHONORED={dishonored or '-'}  GATE={gate}")
            if rescued:
                seam_line += f"  rescued={rescued}"
            if unresolved:
                seam_line += f"  unresolved={unresolved}"
            print(seam_line)
        else:
            print(f"  [SEAM]  no dispatcher Code Deletions field (missing/malformed)")
        flag = "  (LOW CONFIDENCE: no backticked names in PART-1)" if low and man != [] else ""
        print(f"  [APPROX] strat PART-1 manifest (context only): {man}{flag}")
        if trunc:
            print(f"  [HEALTH] TRUNCATED calls: {trunc}"); trunc_events += [(i, trunc)]
        if missing:
            print(f"  [HEALTH] MISSING roles: {missing}"); missing_events += [(i, missing)]

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"  iterations analyzed: {iters}")
    print(f"  ghost-var iterations: {ghost_iters or 'none'}")
    print(f"  double-count iterations: {dbl_iters or 'none'}")
    print(f"  indeterminate iterations: {indeterminate_iters or 'none'}")
    print(f"  truncation events: {trunc_events or 'none'}")
    print(f"  missing-role events: {missing_events or 'none'}")
    if dishonored_tally:
        print("  DISHONORED DELETIONS (component -> times the coder ignored a Code-Deletions request):")
        for k, n in dishonored_tally.most_common():
            print(f"      {k}: {n}")
    else:
        print("  DISHONORED DELETIONS: none  <-- this is the target state after the prompt fix")
    print(f"  name_normalization_rescued: {name_normalization_rescued}")
    print(f"  deletion_name_unresolved: {deletion_name_unresolved}")
    print("\n  Headline check: compare the dishonored-deletions list above against the prior run.")
    print("  If it drops to none under a healthy num_predict, the field-name fix resolved it.")
    print("  If a component (e.g. action_spin_bonus) still recurs, the cause is the coder model, not the prompt.")

# ----------------------------------- main ------------------------------------
def main():

    p = argparse.ArgumentParser()
    p.add_argument("--campaign", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--experiments-dir", default="experiments")
    args = p.parse_args()
    model_root = Path(args.experiments_dir) / args.campaign / args.model
    run(model_root)



if __name__ == "__main__":
    main()
