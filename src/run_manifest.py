"""
run_manifest.py — Run provenance and comparability machinery.

Writes <model_dir>/run_manifest.json once per run (idempotent via skip-if-exists).
Downstream tools import compute_fingerprint and diff_comparability from here.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import inspect
import json
import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import Config
from src.prompts.loader import load_template
from src.utils import get_hardware_config, get_optimized_ppo_params
from src.schedules import SHAPES

ROLES = ["strategist", "organizer", "research_lead", "dispatcher", "coder", "validator"]

_REPO_ROOT = Path(__file__).parent.parent
_REGISTRY_PATH = _REPO_ROOT / "prompts" / "version_registry.json"

# slot → (load_template category, subcategory, Config attribute holding the filename)
# Attributes and subcategories discovered from src/config.py and prompts/ directory layout.
_SLOT_MAP: dict[str, tuple[str, str, str]] = {
    "strategist_system":    ("system_prompts", "strategist",    "strategist_role"),
    "strategist_user":      ("user_prompts",   "strategist",    "strategist_task"),
    "organizer_system":     ("system_prompts", "organizer",     "organizer_role"),
    "organizer_user":       ("user_prompts",   "organizer",     "organizer_task"),
    "research_lead_system": ("system_prompts", "research_lead", "lead_role"),
    "research_lead_user":   ("user_prompts",   "research_lead", "lead_task"),
    "dispatcher_system":    ("system_prompts", "dispatcher",    "dispatcher_role"),
    "dispatcher_user":      ("user_prompts",   "dispatcher",    "dispatcher_task"),
    "coder_system":         ("system_prompts", "coder",         "coder_role"),
    "coder_user":           ("user_prompts",   "coder",         "coder_task"),
    "validator_system":     ("system_prompts", "validator",     "validator_role"),
    "validator_user":       ("user_prompts",   "validator",     "validator_task"),
}

# ---------------------------------------------------------------------------
# Hashing primitives
# ---------------------------------------------------------------------------

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()  # full 64-hex

class _StripDocstrings(ast.NodeTransformer):
    """Remove docstring nodes before hashing — docstrings don't affect behaviour."""
    def _strip(self, node):
        self.generic_visit(node)
        if (node.body and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:] or [ast.Pass()]
        return node
    visit_Module           = _strip
    visit_FunctionDef      = _strip
    visit_AsyncFunctionDef = _strip
    visit_ClassDef         = _strip

def _ast_norm(src: str) -> str:
    tree = _StripDocstrings().visit(ast.parse(src))
    return sha256_text(ast.unparse(tree))          # strips comments, normalises formatting

def ast_normalized_hash(path: str) -> str:
    return _ast_norm(open(path, encoding="utf-8").read())

def _schedule_fn_hash(shape_type: str) -> str:
    """AST-normalized hash of the SELECTED shape kernel (not the whole schedules.py file)."""
    return _ast_norm(inspect.getsource(SHAPES[shape_type]))

def short(h: str) -> str:
    return h[:12]

def compute_fingerprint(comparability: dict) -> str:
    payload = json.dumps(comparability, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()  # full 64-hex


# ---------------------------------------------------------------------------
# Ollama digest — cached per model name, never returns None
# ---------------------------------------------------------------------------

_ollama_digest_cache: dict[str, str] = {}


def ollama_digest(model_name: str, host: str = "http://localhost:11434") -> str:
    if model_name in _ollama_digest_cache:
        return _ollama_digest_cache[model_name]
    sentinel = "UNAVAILABLE"
    try:
        import urllib.request
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        for m in data.get("models", {}):
            if (m.get("name") == model_name or \
                m.get("model") == model_name or \
                m.get("name") == f"{model_name}:latest"):
                digest = m.get("digest", sentinel)
                _ollama_digest_cache[model_name] = digest
                return digest
        # Not found in /api/tags — try /api/show
        req_body = json.dumps({"name": model_name}).encode()
        import urllib.request as _ur
        req = _ur.Request(
            f"{host}/api/show",
            data=req_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _ur.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        digest = data.get("digest", sentinel)
        _ollama_digest_cache[model_name] = digest
        return digest
    except Exception:
        _ollama_digest_cache[model_name] = sentinel
        return sentinel


# ---------------------------------------------------------------------------
# Comparability diff — used by aggregate_runs.py and compare_campaigns.py
# ---------------------------------------------------------------------------

def diff_comparability(
    a: dict, b: dict, _prefix: str = ""
) -> list[tuple[str, Any, Any]]:
    """Recursively compare two comparability dicts; return (dotted_path, val_a, val_b) for every differing leaf."""
    diffs: list[tuple[str, Any, Any]] = []
    keys = set(a) | set(b)
    for k in sorted(keys):
        path = f"{_prefix}{k}"
        if k not in a:
            diffs.append((path, "<missing>", b[k]))
        elif k not in b:
            diffs.append((path, a[k], "<missing>"))
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            diffs.extend(diff_comparability(a[k], b[k], _prefix=path + "."))
        elif a[k] != b[k]:
            diffs.append((path, a[k], b[k]))
    return diffs


# ---------------------------------------------------------------------------
# Version registry
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    if not _REGISTRY_PATH.exists() or _REGISTRY_PATH.stat().st_size == 0:
        return {"schema_version": 1, "prompt_slots": {}, "code_slots": {}}
    try:
        with _REGISTRY_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": 1, "prompt_slots": {}, "code_slots": {}}


def resolve_version(
    registry: dict,
    category: str,
    slot: str,
    content_hash: str,
    source_name: str,
    run_id: str,
) -> int:
    cat = registry.setdefault(category, {})
    entry = cat.setdefault(slot, {"versions": []})
    if category == "prompt_slots":
        entry.setdefault("current_name", source_name)
    versions: list[dict] = entry["versions"]
    for v in versions:
        if v["content_hash"] == content_hash:
            if category == "prompt_slots":
                entry["current_name"] = source_name
            return v["version"]
    new_ver = max((v["version"] for v in versions), default=0) + 1
    versions.append({
        "version":       new_ver,
        "content_hash":  content_hash,
        "source_name":   source_name,
        "first_seen":    datetime.now(timezone.utc).isoformat(),
        "first_seen_run": run_id,
    })
    if category == "prompt_slots":
        entry["current_name"] = source_name
    return new_ver


def save_registry(registry: dict) -> None:
    with _REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


# ---------------------------------------------------------------------------
# Git provenance (read-only)
# ---------------------------------------------------------------------------

def _git_provenance() -> dict:
    try:
        def _run(cmd: list[str], apply_strip: bool = True) -> str:
            result = subprocess.check_output(
                cmd, cwd=str(_REPO_ROOT), stderr=subprocess.DEVNULL
            ).decode()
            return result.strip() if apply_strip else result

        commit = _run(["git", "rev-parse", "HEAD"])
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        status_out = _run(["git", "status", "--porcelain"], apply_strip=False)
        is_dirty = bool(status_out.strip())
        dirty_files = [line[3:].rstrip() for line in status_out.splitlines() if len(line) > 3]
        return {"commit": commit, "branch": branch, "is_dirty": is_dirty, "dirty_files": dirty_files}
    except Exception:
        return {"commit": None, "branch": None, "is_dirty": None, "dirty_files": []}


# ---------------------------------------------------------------------------
# Training regime block
# ---------------------------------------------------------------------------

def _build_training_block() -> dict:
    """
    Resolve the RL training regime for the platform that actually ran training.
    TRAIN_PLATFORM env var tells us: "Linux" for remote runs, absent for local Mac runs.
    n_envs and its derived n_steps/batch_size correctly differ per machine — that is correct.
    """
    train_platform = os.environ.get("TRAIN_PLATFORM")  # None on local Mac runs
    n_envs, _device = get_hardware_config(train_platform)
    ppo = get_optimized_ppo_params(n_envs)  # use n_steps & batch_size only
    return {
        "n_envs":               n_envs,
        "vec_env_cls":          Config.VEC_ENV_CLS,
        "n_steps":              ppo["n_steps"],
        "batch_size":           ppo["batch_size"],
        "n_epochs":             Config.N_EPOCHS,
        "gamma":                Config.GAMMA,
        "gae_lambda":           Config.GAE_LAMBDA,
        "clip_range":           Config.CLIP_RANGE,
        "vf_coef":              Config.VF_COEF,
        "max_grad_norm":        Config.MAX_GRAD_NORM,
        "target_kl":            Config.TARGET_KL,
        "normalize_advantage":  Config.NORMALIZE_ADVANTAGE,
        "learning_rate":        {"type": Config.LR_SCHEDULE_TYPE,  "initial": Config.LR_INITIAL,       "final": Config.LR_FINAL,       "fn_hash": _schedule_fn_hash(Config.LR_SCHEDULE_TYPE)},
        "ent_coef":             {"type": Config.ENT_SCHEDULE_TYPE, "initial": Config.ENT_COEF_INITIAL, "final": Config.ENT_COEF_FINAL, "fn_hash": _schedule_fn_hash(Config.ENT_SCHEDULE_TYPE)},
        "policy":               Config.POLICY,
        "net_arch":             Config.NET_ARCH,
        "activation_fn":        Config.ACTIVATION_FN,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def write_run_manifest(ws) -> dict | None:
    """
    Write <model_dir>/config_snapshot/run_manifest.json once per run.

    Called unconditionally each iteration; the skip-if-exists guard makes it
    write only on the first call (iteration 1).  Never aborts the training run.
    """
    try:
        manifest_path = ws.model_root_path / "config_snapshot" / "run_manifest.json"
        if manifest_path.exists():
            return None  # idempotent

        model_name = Config.LLM_MODEL
        overrides = Config.role_model_overrides(model_name)
        role_models = {r: overrides.get(r, model_name) for r in ROLES}

        run_id = f"{ws.campaign_tag}/{ws.model_dir_name}"
        created_at = datetime.now(timezone.utc).isoformat()

        # ── Build agents map ──────────────────────────────────────────────
        agents: dict[str, dict] = {}
        for role in ROLES:
            model = role_models[role]
            model_dgst = ollama_digest(model)
            sampling = Config.get_inference_options(model, role)  # verbatim dict

            cat_sys, sub_sys, attr_sys = _SLOT_MAP[f"{role}_system"]
            cat_usr, sub_usr, attr_usr = _SLOT_MAP[f"{role}_user"]
            tpl_sys_name = getattr(Config, attr_sys)
            tpl_usr_name = getattr(Config, attr_usr)
            system_template = load_template(cat_sys, sub_sys, tpl_sys_name)
            user_template   = load_template(cat_usr, sub_usr, tpl_usr_name)

            agents[role] = {
                "model":              model,
                "model_digest":       model_dgst,
                "sampling":           sampling,
                "prompt_system_hash": sha256_text(system_template),   # raw, unformatted
                "prompt_user_hash":   sha256_text(user_template),     # raw, unformatted
            }

        # ── Experiment block ──────────────────────────────────────────────
        reward_path = ws.get_path("code", 0, "reward.py")
        if reward_path.exists():
            raw_reward = open(reward_path, "r", encoding="utf-8").read()
            # Strip the same non-deterministic header standard.py removes before feeding to LLM
            if "import" in raw_reward:
                stripped_reward = "import" + raw_reward.split("import", 1)[1]
            else:
                stripped_reward = raw_reward
            initial_reward_hash = sha256_text(stripped_reward)
        else:
            initial_reward_hash = "UNAVAILABLE"

        experiment = {
            "env_id":              Config.ENV_ID,
            "algorithm":           Config.ALGORITHM,
            "total_timesteps":     Config.TOTAL_TIMESTEPS,
            "total_iterations":    Config.TOTAL_ITERATIONS,
            "num_seeds":           Config.NUM_SEEDS,
            "eval_episodes":       Config.EVAL_EPISODES,
            "initial_func":        Config.INITIAL_FUNC,
            "initial_reward_hash": initial_reward_hash,
        }

        # ── Code block (AST-normalised hashes) ───────────────────────────
        src_dir = Path(__file__).parent
        analysis_hash = ast_normalized_hash(str(src_dir / "analysis.py"))
        ledger_hash   = ast_normalized_hash(str(src_dir / "ledger.py"))
        code = {"analysis_hash": analysis_hash, "ledger_hash": ledger_hash}

        # ── Comparability dict & fingerprint ─────────────────────────────
        comparability = {
            "experiment": experiment,
            "training":   _build_training_block(),
            "agents":     agents,
            "code":       code,
        }
        config_fingerprint = compute_fingerprint(comparability)

        # ── Version registry ──────────────────────────────────────────────
        reg = load_registry()
        prompt_versions: dict[str, int] = {}
        prompt_names: dict[str, str] = {}
        for role in ROLES:
            for side in ("system", "user"):
                slot = f"{role}_{side}"
                h = agents[role][f"prompt_{side}_hash"]
                _, _, attr = _SLOT_MAP[slot]
                src_name = getattr(Config, attr)
                v = resolve_version(reg, "prompt_slots", slot, h, src_name, run_id)
                prompt_versions[slot] = v
                prompt_names[slot] = src_name

        analysis_ver = resolve_version(reg, "code_slots", "analysis", analysis_hash, "analysis.py", run_id)
        ledger_ver   = resolve_version(reg, "code_slots", "ledger",   ledger_hash,   "ledger.py",   run_id)
        lr_fn_hash  = comparability["training"]["learning_rate"]["fn_hash"]
        ent_fn_hash = comparability["training"]["ent_coef"]["fn_hash"]
        lr_sched_ver  = resolve_version(reg, "code_slots", "lr_schedule",  lr_fn_hash,  Config.LR_SCHEDULE_TYPE,  run_id)
        ent_sched_ver = resolve_version(reg, "code_slots", "ent_schedule", ent_fn_hash, Config.ENT_SCHEDULE_TYPE, run_id)
        save_registry(reg)

        labels = {
            "prompt_versions": prompt_versions,
            "code_versions":   {"analysis": analysis_ver, "ledger": ledger_ver, "lr_schedule": lr_sched_ver, "ent_schedule": ent_sched_ver},
            "prompt_names":    prompt_names,
        }

        # ── Provenance ────────────────────────────────────────────────────
        ollama_ver = "UNAVAILABLE"
        try:
            import urllib.request as _ur
            with _ur.urlopen("http://localhost:11434/api/version", timeout=5) as resp:
                ollama_ver = json.loads(resp.read().decode()).get("version", "UNAVAILABLE")
        except Exception:
            pass

        sb3_ver = "UNAVAILABLE"
        gym_ver = "UNAVAILABLE"
        try:
            sb3_ver = importlib.metadata.version("stable_baselines3")
        except Exception:
            pass
        try:
            gym_ver = importlib.metadata.version("gymnasium")
        except Exception:
            pass

        _train_platform = os.environ.get("TRAIN_PLATFORM")
        _, _train_device = get_hardware_config(_train_platform)

        provenance = {
            "git": _git_provenance(),
            "environment": {
                "hostname":           socket.gethostname(),
                "python_version":     platform.python_version(),
                "stable_baselines3":  sb3_ver,
                "gymnasium":          gym_ver,
                "ollama_version":     ollama_ver,
                "training_platform":  _train_platform or platform.system(),
                "training_device":    _train_device,
                "created_at":         created_at,
            },
        }

        # ── Assemble & write manifest ─────────────────────────────────────
        manifest = {
            "manifest_schema_version": 1,
            "config_fingerprint":      config_fingerprint,
            "run": {
                "campaign_tag": ws.campaign_tag,
                "model_dir":    ws.model_dir_name,
                "created_at":   created_at,
            },
            "comparability": comparability,
            "labels":        labels,
            "provenance":    provenance,
        }

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # ── Snapshot raw prompt templates ─────────────────────────────────
        snapshot_dir = ws.model_root_path / "config_snapshot" / "prompts"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for role in ROLES:
            for side in ("system", "user"):
                slot = f"{role}_{side}"
                cat, sub, attr = _SLOT_MAP[slot]
                tpl_name = getattr(Config, attr)
                template_text = load_template(cat, sub, tpl_name)
                (snapshot_dir / f"{slot}.txt").write_text(template_text, encoding="utf-8")

        return manifest

    except Exception as exc:
        import traceback as _tb
        _trace = _tb.format_exc()
        print(f"\n⚠️  [run_manifest] FAILED to write run_manifest.json: {exc}", flush=True)
        print(_trace, flush=True)
        try:
            _err_path = ws.model_root_path / "run_manifest.ERROR.json"
            with _err_path.open("w", encoding="utf-8") as _f:
                json.dump({"error": str(exc), "traceback": _trace}, _f, indent=2)
        except Exception:
            pass
        return None
