# ARD Run Provenance & Comparability — System Reference

The provenance machinery records, for every pipeline run, the exact configuration it executed and a single `config_fingerprint` that makes "are two runs comparable?" a string-equality check. Two runs are safely comparable if and only if their fingerprints match; campaign aggregation and cross-campaign statistics are gated and annotated on that basis.

---

## 0. Why this exists

Git tracks history but not run-level provenance, and reconstructing "what ran" from git fails three ways during active development:

1. **Dirty working tree** — runs almost never launch from a clean commit, so a recorded SHA the live files don't match cannot reconstruct what executed.
2. **Mutable prompt pointers** — `config.py` stores prompt *names*; `prompts.loader` resolves name → file → content at runtime. The bytes the model saw are the truth, not the name.
3. **Model-tag drift** — `gemma4:26b` is a tag, not an identity; a re-pull or retag points the same name at different weights.

The system replaces reconstruction with **materialization**: at run start it captures the resolved values and the actual prompt/code bytes, hashes the comparability-relevant subset into a fingerprint, and writes a human-diffable snapshot. Comparability becomes a computed property rather than a manual audit.

---

## 1. Primer: hashes

A hash function maps any input to a short fixed-length fingerprint. It is **deterministic** (same input → same output), **sensitive** (one changed character → completely different output), and **fixed-size** (`sha256` → 64 hex characters). `sha256` is a frozen NIST standard (FIPS 180-4); identical input yields byte-identical output across implementations and indefinitely.

The system **stores the full 64-character hash** everywhere and shows a **12-character prefix** only for human display. Equality checks always use the full value. A version label (`v3`) is a human-readable sticker on top of a content hash.

---

## 2. Comparability set vs. provenance set

Every run records two deliberately separate things.

- **Comparability set** — the variables whose change invalidates a comparison. These are hashed into `config_fingerprint`: experiment scalars, the resolved training regime, each agent's model + sampling + prompts, and the code that shapes LLM input.
- **Provenance set** — recorded for audit but **not** hashed: git state, environment, and the derived version labels.

**Invariant — versions are never in the fingerprint.** Version labels are *derived from* content hashes via the registry, so putting them in the hash would make the fingerprint depend on registry state and break reproducibility across machines. The fingerprint depends only on content (hashes and config values). Two runs with identical content produce the same fingerprint even if one machine's registry labels a prompt `v2` and a freshly-reset registry labels it `v1`.

---

## 3. The comparability set (what the fingerprint covers)

`config_fingerprint = sha256(canonical_json(comparability))`, stored full, where `canonical_json` is `json.dumps(obj, sort_keys=True, separators=(",", ":"))` so key order and whitespace never affect the result.

### 3.1 `experiment` — run-wide controlled conditions
`env_id`, `algorithm`, `total_timesteps`, `total_iterations`, `num_seeds`, `eval_episodes`, `initial_func`, and `initial_reward_hash` — a **raw** hash of the iteration-0 reward *as the Strategist receives it* (header stripped exactly as `standard.py` strips it). Raw because the initial reward is fed to the Strategist as text, comments included, so a comment change is a real change to the experiment.

### 3.2 `training` — the RL regime
The resolved PPO/training configuration:

- **Hardware-resolved (vary by machine):** `n_envs`, and the values derived from it — `n_steps` and `batch_size` (from `get_optimized_ppo_params(n_envs)`). `n_envs` comes from `get_hardware_config(system)`, where `system` is taken from the `TRAIN_PLATFORM` env var (exported by `outer_loop.sh` on the remote branch) and defaults to the local platform when unset. The manifest writer runs on the orchestration node (Mac) while training may run on the remote node (Linux), so `TRAIN_PLATFORM` tells the manifest which platform to resolve the hardware profile for, guaranteeing the recorded value matches what `train.py` resolved on the training machine.
- **Fixed (sourced from `Config`):** `vec_env_cls`, `n_epochs`, `gamma`, `gae_lambda`, `clip_range`, `vf_coef`, `max_grad_norm`, `target_kl`, `normalize_advantage`, `policy`, `net_arch`, `activation_fn`.
- **Schedules (kernel hash + parameters):** `learning_rate` and `ent_coef` are each stored as `{"type": <shape>, "initial": <x>, "final": <y>, "fn_hash": <64-hex>}`. `type` is the resolved shape selection from `Config.LR_SCHEDULE_TYPE` / `Config.ENT_SCHEDULE_TYPE`; `fn_hash` is the AST-normalized hash of the selected shape kernel in `schedules.py` (`SHAPES[type]`), computed via `inspect.getsource`. The live decayed value is never read. Schedules sharing a shape (e.g., both `learning_rate` and `ent_coef` set to `"linear"`) resolve to the same kernel and record identical `fn_hash` values — this is correct.

Because `n_envs` is recorded truthfully, **runs on different hardware receive different fingerprints — and that is correct.** An 8-env local debug run and a 16-env remote campaign run are genuinely different training regimes (different buffer structure and `n_steps`) and must never be pooled; the fingerprint distinguishing them is the system working. A cloned repo run on a single machine resolves that machine's profile and produces runs comparable among themselves.

### 3.3 `agents` — per-role model, sampling, and prompts
One entry per role (`strategist`, `organizer`, `research_lead`, `dispatcher`, `coder`, `validator`):

- `model` — the resolved model for that role. The per-role map comes from a single resolver, `Config.role_model_overrides(model_name)`, with the Strategist (and any unlisted role) falling through to `Config.LLM_MODEL`. This resolver is the one place the mapping lives, so a future move to YAML changes only its internals.
- `model_digest` — the model's content digest from Ollama's `/api/tags`, matched on the model name with a `:latest` fallback for names stored without a tag. If the lookup fails it records the fixed sentinel `"UNAVAILABLE"` (deterministic, so two failed lookups still compare equal). The digest captures weight identity, so a re-pull that changes weights under the same tag is flagged.
- `sampling` — the **full resolved output** of `Config.get_inference_options(model, role)`, verbatim (keys vary by model type — reasoning vs. standard — and include temperature, top_p, top_k, num_ctx, num_predict, stop, etc.). This captures temperature and the inference regime directly; an edit to `get_inference_options` is captured via the changed resolved values.
- `prompt_system_hash`, `prompt_user_hash` — **raw** hashes of the unformatted templates as returned by `prompts.loader.load_template` (before any variable substitution). The template text is what the model receives.

### 3.4 `code` — the LLM-input-shaping surface
- `analysis_hash` — **AST-normalized** hash of `analysis.py` (the entire Deterministic Translation Layer: per-seed analysis, cross-seed aggregation, metrics → Diagnostic Report).
- `ledger_hash` — **AST-normalized** hash of `ledger.py` (formats the historical ledger and validator responses fed back to the agents).

Both are AST-normalized (`sha256(ast.unparse(ast.parse(src)))`) because they only *execute* to produce LLM-facing text — their source comments reach no model, so comment/format edits must not flag while logic, structure, or name changes must.

Schedule hashes live in the `training` block (§3.2), not here, because schedules carry a shape *selection* dimension that the single-purpose `analysis.py` / `ledger.py` files do not.

---

## 4. The provenance set (recorded, not hashed)

- **`git`** — `commit` (full SHA), `branch`, `is_dirty`, and `dirty_files` (parsed from `git status --porcelain`, preserving each line's two-column status prefix). `dirty_files` reveals whether the SHA is trustworthy. Git access is read-only.
- **`environment`** — `hostname` (the manifest writer's host), `python_version`, `stable_baselines3`, `gymnasium`, `ollama_version`, plus `training_platform` (the resolved training OS, disambiguating the writer's hostname) and `training_device` (resolved from the training platform's profile; currently `"cpu"`). `training_device` is provenance-only; if CUDA is ever enabled on the Linux profile it will resolve to `"cuda"` and should then be promoted into `comparability.training`, since GPU-vs-CPU training is a real regime difference.
- **`labels`** — `prompt_versions` (slot → int), `code_versions` (`analysis`, `ledger` → int), and `prompt_names` (slot → the `Config` name used). The human-readable layer, derived from the registry.

---

## 5. Hashing rules

| Artifact | Method | Rationale |
|---|---|---|
| 12 prompt templates | raw hash of the unformatted template | the template text is what the model receives |
| initial reward (iter-0 `reward.py`) | raw hash of the header-stripped text | fed to the Strategist as text, comments included |
| `analysis.py`, `ledger.py` | AST-normalized hash (comments and docstrings stripped) | execute to produce LLM-facing text; neither comments nor docstrings reach a model |
| selected schedule kernel (`learning_rate`, `ent_coef`) | AST-normalized hash via `inspect.getsource(SHAPES[type])` | executes to produce the training schedule; comments/docstrings don't affect behaviour, and only the selected shape is hashed, not the whole library |

All hashes stored full (64 hex); 12-char prefix for display only.

---

## 6. The component version registry

`prompts/version_registry.json` (git-tracked, append-only) is a content-addressed ledger that auto-versions every comparability-critical component. At run start, for each slot, its content hash is looked up; a known hash reuses its version, a new hash is assigned `max(existing) + 1` and appended with its first-seen timestamp and run id. No manual bumping; no locking (runs are strictly sequential).

- `prompt_slots` — 12 entries (`{role}_system`, `{role}_user`).
- `code_slots` — `analysis`, `ledger`, `lr_schedule`, `ent_schedule`.

The registry is also the durable record of every distinct prompt/code version the pipeline has ever executed. If deleted, content hashes are unchanged and only the friendly version numbers renumber; the fingerprint is unaffected.

---

## 7. The run manifest (full schema)

Written once per run to **`experiments/{CAMPAIGN_TAG}/{model_dir}/config_snapshot/run_manifest.json`**.

```jsonc
{
  "manifest_schema_version": 1,
  "config_fingerprint": "<full 64-hex>",
  "run": { "campaign_tag": "...", "model_dir": "...", "created_at": "<UTC ISO8601>" },

  "comparability": {
    "experiment": {
      "env_id": "LunarLander-v3", "algorithm": "PPO",
      "total_timesteps": 1000000, "total_iterations": 10,
      "num_seeds": 4, "eval_episodes": 25,
      "initial_func": "spin_crash", "initial_reward_hash": "<64-hex, RAW>"
    },
    "training": {
      "n_envs": 16, "vec_env_cls": "DummyVecEnv",
      "n_steps": 512, "batch_size": 2048,
      "n_epochs": 10, "gamma": 0.999, "gae_lambda": 0.98,
      "clip_range": 0.2, "vf_coef": 0.5, "max_grad_norm": 0.5,
      "target_kl": null, "normalize_advantage": true,
      "learning_rate": {"type": "linear", "initial": 0.001, "final": 0.0001, "fn_hash": "<64-hex, AST>"},
      "ent_coef":      {"type": "linear", "initial": 0.02,  "final": 0.001,  "fn_hash": "<64-hex, AST>"},
      "policy": "MlpPolicy", "net_arch": [256, 256], "activation_fn": "Tanh"
    },
    "agents": {
      "strategist": {
        "model": "gemma4:26b-mlx", "model_digest": "<64-hex or UNAVAILABLE>",
        "sampling": { "num_ctx": 24576, "num_predict": 16384, "temperature": 1.0, "top_p": 0.95, "top_k": 64, "repeat_penalty": 1.0, "stop": ["..."] },
        "prompt_system_hash": "<64-hex, raw>", "prompt_user_hash": "<64-hex, raw>"
      },
      "organizer":     { "model": "...", "model_digest": "...", "sampling": { }, "prompt_system_hash": "...", "prompt_user_hash": "..." },
      "research_lead": { },
      "dispatcher":    { },
      "coder":         { },
      "validator":     { }
    },
    "code": { "analysis_hash": "<64-hex, AST>", "ledger_hash": "<64-hex, AST>" }
  },

  "labels": {
    "prompt_versions": { "strategist_system": 1, "strategist_user": 1, "...": 1 },
    "code_versions":   { "analysis": 1, "ledger": 1, "lr_schedule": 1, "ent_schedule": 1 },
    "prompt_names":    { "strategist_system": "strategist_system_prompt_test", "...": "..." }
  },

  "provenance": {
    "git": { "commit": "<full SHA>", "branch": "dev", "is_dirty": true,
             "dirty_files": ["controllers/standard.py", "src/config.py", "..."] },
    "environment": { "hostname": "...", "python_version": "3.13.2",
                     "stable_baselines3": "2.7.1", "gymnasium": "1.2.2", "ollama_version": "0.24.0",
                     "training_platform": "Linux", "training_device": "cpu" }
  }
}
```

Alongside the manifest, the 12 unformatted templates are dumped to `config_snapshot/prompts/{slot}.txt` for human diffing — a deliberate decoupling of "what the prompt said" from git's mutable pointer state.

---

## 8. File & directory layout

```
prompts/
├── loader.py
├── version_registry.json           (git-tracked, append-only)
└── system_prompts/… user_prompts/…

src/run_manifest.py                  (writer + reusable helpers)

experiments/
└── {CAMPAIGN_TAG}/                            (the _runN dir)
    ├── models_metadata.csv
    └── {model_dir}/                            (one run's identity)
        ├── config_snapshot/
        │   ├── run_manifest.json
        │   └── prompts/  (12 .txt files)
        ├── cognition/  generated_code/  telemetry/  artifacts/
```

`run_manifest.py` exposes `write_run_manifest(ws)`, plus helpers imported by the consumers: `compute_fingerprint`, `diff_comparability`, and the hashing/registry utilities.

---

## 9. Execution flow

`outer_loop.sh` exports the run environment (campaign tag, model, timesteps, and `TRAIN_PLATFORM` on the remote branch), `set_initial_shaping.py` writes the iteration-0 reward, then `inner_loop.sh` invokes the controller per iteration. At the top of `run_agentic_improvement`, immediately after the workspace is created, `write_run_manifest(ws)` is called. It is idempotent — it returns immediately if the manifest already exists — so it writes once on iteration 1 and no-ops thereafter. The entire body is wrapped defensively: any failure logs a warning and writes a `run_manifest.ERROR.json`, but never aborts the training run.

On the write, it resolves the per-role models, fetches digests (deduped), resolves sampling and the training regime, hashes prompts (raw) and `analysis.py`/`ledger.py` (AST-normalized) and the initial reward (raw), updates the version registry, reads git and environment state, computes the fingerprint over the comparability set, and writes the manifest plus the prompt dump.

---

## 10. Downstream consumers

### 10.1 Per-campaign — `aggregate_runs.py` — comparability gate
Reads each member run's `config_fingerprint`. If all match, it aggregates and stamps the shared fingerprint into the output. If they differ (or any manifest is missing), it prints a per-run table of differing fields (via `diff_comparability`) and exits non-zero — aggregating runs with different configs into one mean±std is the invalid operation being prevented. `--force` overrides, proceeding while stamping the output `"comparability": "FORCED_MIXED"`.

### 10.2 Cross-campaign — `compare_campaigns.py` — independent-axis surfacing
Loads one representative manifest per campaign and prints a field-level diff as the report header, rendering hash changes via version labels (`analysis: v3 → v4`, `strategist_system: v1 → v2`, `total_timesteps: 500000 → 1000000`), before the Mann-Whitney U / Cliff's δ block.

It counts **independent axes**, treating sampling as dependent on model:
- a role whose `model` differs is **one axis** — the model carries its inference regime with it (a reasoning-vs-standard swap is a single configuration change, not a confound);
- a role whose `model` is unchanged but `sampling` differs is **one axis** (a deliberate, independent regime/temperature edit);
- each differing prompt slot, code slot, training field, or experiment scalar is one axis.

Schedule changes surface as `lr_schedule` / `ent_schedule` code-slot axes (one axis per domain even when both `type` and `fn_hash` differ — the set dedupes the slot). Other `training` scalars (e.g. `n_envs`, `gamma`) each count as one training-field axis.

Exactly one axis → `CLEAN ABLATION (1 variable)`; two or more → `CONFOUNDED (N variables)`.

---

## 11. Stability & known limitations

- **`sha256` is frozen** — recomputation is guaranteed for identical input. The real dependency is the input: identical content **and** identical canonicalization. The fixed `json.dumps(sort_keys=True, separators=(",", ":"))` defines the canonicalization; `manifest_schema_version` guards it, and fingerprints are only comparable within one schema version.
- **`ast.unparse` across Python upgrades** — its formatting is stable within a Python version but can shift across major CPython releases, so a Python upgrade can change `analysis.py`/`ledger.py` hashes with no code change. The Python version is recorded in provenance, so any such shift is explainable; re-baselining is a deliberate one-time event.
- **Captured-as-resolved-values, not source** — `get_inference_options`, `get_optimized_ppo_params`, and `get_hardware_config` are not hashed as code; their *effects* are captured as resolved values in the manifest, so any change to them flows into the fingerprint automatically. Schedule formulas are the exception: `{type, initial, final}` parameters alone cannot detect a shape change (e.g. linear → quadratic), so the **selected shape kernel** is hashed as `fn_hash` in the training block — via `inspect.getsource(SHAPES[type])`, AST-normalized. Only the kernel selected for each domain is hashed; hashing the whole `schedules.py` file would false-positive when an unused shape is added. This mirrors how prompts hash the selected template, not the entire prompt directory.
- **Delivery modality is not a comparability axis** — SB3 consumes `learning_rate` as a native callable but has no schedule hook for `ent_coef`, which is injected via a callback. This split is forced by SB3's API per scheduled parameter, not chosen; it does not change the effective schedule. No "modality", "delivery", or "callable_vs_callback" field is recorded anywhere — modality rides implicitly with the domain.
