"""
evaluate_experiments.py
-----------------------
Post-training evaluation of SB3 PPO agents on the STANDARD LunarLander-v3
environment after being trained on LLM-generated reward functions.

Pass the path to a single campaign directory.  The script will:
  1. Discover every LLM sub-directory and its iteration models
  2. Evaluate each model (30 deterministic episodes, CLT-valid sample size)
  3. Per-iteration plots   → <campaign>/<llm>/artifacts/iteration<N>/plots/
  4. Per-LLM evolution     → <campaign>/<llm>/artifacts/<llm>_evolution.png
  5. Multi-LLM comparison  → <campaign>/multi_llm_comparison.png

Usage:
    python post-hoc_evaluation/evaluate_experiments.py --campaign_dir /path/to/2024-01-15_10cycles_1Msteps_run1

Expected directory layout:
    <campaign_dir>/                              ← pass this path (dynamic naming <YYYY-MM-DD_Ncycles_MSteps_tag>)
    └── <llm-name>/
        ├── telemetry/
        ├── generated_code/
        ├── cognition/
        └── artifacts/
            └── iteration<N>/
                ├── plots/                       ← per-iteration plots written here
                └── models/
                    ├── iter<N>_model0.zip       ← seed 0
                    ├── iter<N>_model1.zip       ← seed 1
                    └── ...
        <llm>_evolution.png                      ← written here (single-LLM evolution)
    multi_llm_comparison.png                     ← written here (all LLMs)

Model filename convention: iter{N}_model{seed}.zip
Aggregation notes (see conversation for full rationale):
  - Each model is evaluated for N_EVAL_EPISODES (default 30).  CLT holds at 30
    so we can safely treat the per-model mean as normally distributed and use
    mean ± std bands in all plots.
  - Per-iteration summary:  mean-of-seed-means  /  std-of-seed-means.
    Std-of-seed-means captures cross-run training variance, which is what the
    evolution band should communicate — NOT episode-level noise within one run.
  - The per-seed mean (mean of that seed's 30 episodes) is the atomic unit
    passed upward; individual episode returns are kept for the per-iteration
    left subplot only.
"""

import os
import re
import csv
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# ── Optional: suppress SB3/gym verbosity ──────────────────────────────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.evaluation import evaluate_policy
    import gymnasium as gym
except ImportError as e:
    raise ImportError(
        "Missing dependency. Run: pip install stable-baselines3 gymnasium[box2d]"
    ) from e

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
CONFIG = {
    # Matches: iter01_model0.zip  iter3_model2.zip  etc.
    "iter_filename_re": r"^iter(\d+)_model(\d+)\.zip$",

    # 30 episodes gives CLT-valid normality assumption for mean ± std plots.
    "n_eval_episodes": 30,

    # Env reset seed — deterministic, reproducible across runs.
    # Must differ from any training seeds used in the campaign.
    "eval_seed": 999,

    "render": False,

    # LunarLander-v3 conventional thresholds
    "solved_threshold": 200,
    "failure_threshold": -100,

    "style": "dark_background",

    # One colour per LLM (evolution + comparison plots)
    "llm_colors": [
        "#61afef",  # blue
        "#e06c75",  # red
        "#98c379",  # green
        "#e5c07b",  # yellow
        "#c678dd",  # purple
        "#56b6c2",  # cyan
        "#d19a66",  # orange
        "#abb2bf",  # grey
    ],

    # One colour per training seed (per-iteration plots + evolution seed dots)
    "seed_colors": [
        "#61afef", "#e06c75", "#98c379",
        "#e5c07b", "#c678dd", "#56b6c2",
    ],
}
# ══════════════════════════════════════════════════════════════════════════════


# ── Directory scanning ────────────────────────────────────────────────────────

def find_models(campaign_dir: Path) -> dict:
    """
    Recursively scan campaign_dir for model files and return:

        { llm_name: { iteration_int: { seed_int: Path } } }

    First level under campaign_dir is taken as the LLM name.
    Layout:
        <experiments_dir>/
        └── <Campaign_Tag>/
            └── <llm-name>/
                └── artifacts/
                    └── iteration<N>/
                        └── models/
                            └── iter<N>_model<seed>.zip
    """
    iter_re   = re.compile(CONFIG["iter_filename_re"], re.IGNORECASE)
    structure: dict = defaultdict(lambda: defaultdict(dict))

    for model_path in sorted(campaign_dir.rglob("*.zip")):
        m = iter_re.match(model_path.name)
        if not m:
            continue

        iteration = int(m.group(1))
        seed      = int(m.group(2))

        try:
            rel_parts = model_path.relative_to(campaign_dir).parts
            llm_name  = rel_parts[0]
        except ValueError:
            continue

        structure[llm_name][iteration][seed] = model_path

    return {
        llm: dict(sorted(iters.items()))
        for llm, iters in structure.items()
    }


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_model(model_path: Path) -> list[float]:
    """
    Run one model for CONFIG['n_eval_episodes'] deterministic episodes.
    Returns a list of per-episode returns (length = n_eval_episodes).
    """
    env = gym.make("LunarLander-v3")
    env.reset(seed=CONFIG["eval_seed"])
    try:
        model = PPO.load(
            str(model_path),
            env=env,
            device="cpu",
            custom_objects={"lr_schedule": lambda _: 3e-4} # a value required since callable passed to PPO constructor during training
            )

        ep_rewards, _ = evaluate_policy(
            model, env,
            n_eval_episodes=CONFIG["n_eval_episodes"],
            deterministic=True,
            render=CONFIG["render"],
            warn=False,
            return_episode_rewards=True,
        )
    finally:
        env.close()
    return list(ep_rewards)


def collect_results(structure: dict) -> dict:
    """
    Evaluate every model in structure and return:

        {
            llm_name: {
                iteration_int: {
                    seed_int: {
                        "episode_returns": [float, ...],  # n_eval_episodes values
                        "mean": float,                    # mean  of episode returns
                        "std":  float,                    # std   of episode returns
                    }
                }
            }
        }

    The per-seed "mean" is the key scalar used for all higher-level aggregation.
    """
    results = {}
    n_eps   = CONFIG["n_eval_episodes"]

    for llm_name, iter_map in structure.items():
        total_models = sum(len(s) for s in iter_map.values())
        print(f"\n{'═'*62}")
        print(f"  LLM : {llm_name}")
        print(f"  Iters: {len(iter_map)}   Models: {total_models}   "
              f"Episodes/model: {n_eps}")
        print(f"{'═'*62}")

        results[llm_name] = {}

        for iteration, seed_map in iter_map.items():
            results[llm_name][iteration] = {}
            for seed, model_path in sorted(seed_map.items()):
                print(
                    f"  → Iter {iteration:>3}  seed {seed}  evaluating ...",
                    end="", flush=True,
                )
                try:
                    ep_returns = evaluate_model(model_path)
                    mean_val   = float(np.mean(ep_returns))
                    std_val    = float(np.std(ep_returns))
                    results[llm_name][iteration][seed] = {
                        "episode_returns": ep_returns,
                        "mean": mean_val,
                        "std":  std_val,
                    }
                    print(f"  mean={mean_val:+.1f}  std={std_val:.1f}")
                except Exception as ex:
                    print(f"  FAILED ({ex})")

    return results


# ── Aggregation helper ────────────────────────────────────────────────────────

def iter_aggregate(seed_data: dict) -> tuple[float, float, list[float]]:
    """
    Collapse one iteration's seed results into iteration-level statistics.

    Returns (mean_of_means, std_of_means, [seed_means]).

    Using std-of-seed-means (NOT mean-of-individual-stds) because:
      - The std band on the evolution plot should show cross-run training
        variance, i.e. how differently seeds converged.
      - Per-seed std reflects within-run episode noise — a separate quantity
        that belongs only on the per-iteration subplot.
    """
    seed_means = [seed_data[s]["mean"] for s in sorted(seed_data.keys())]
    return float(np.mean(seed_means)), float(np.std(seed_means)), seed_means


# ── Plot helpers ──────────────────────────────────────────────────────────────

def _threshold_lines(ax, solved: float, failure: float, label: bool = True):
    """Add solved / zero / failure horizontal reference lines."""
    kw_s = dict(color="#98c379", linestyle="--", linewidth=0.9, alpha=0.65)
    kw_f = dict(color="#e06c75", linestyle="--", linewidth=0.9, alpha=0.65)
    kw_z = dict(color="#abb2bf", linestyle=":",  linewidth=0.6, alpha=0.40)
    if label:
        kw_s["label"] = f"Solved  ({int(solved)})"
        kw_f["label"] = f"Failure ({int(failure)})"
    ax.axhline(solved,  **kw_s)
    ax.axhline(0,       **kw_z)
    ax.axhline(failure, **kw_f)


def _set_ylim(ax, values: np.ndarray, solved: float, failure: float, pad: float = 25.0):
    """Y-limits that always include both reference thresholds plus padding."""
    ax.set_ylim(
        min(float(values.min()), failure) - pad,
        max(float(values.max()), solved)  + pad,
    )


# ── Plot 1: per-iteration ─────────────────────────────────────────────────────

def plot_per_iteration(results: dict, campaign_dir: Path):
    """
    For every (LLM, iteration) pair produce a 2-subplot figure.

    Left subplot  — "Episode Returns per Seed"
        Raw episode returns for each training seed as semi-transparent lines
        (episode index on x-axis).  A horizontal dashed line marks each
        seed's mean so within-seed consistency is immediately visible.

    Right subplot — "Mean ± Std Across Seeds"
        At each episode position the mean across seeds is plotted as a bold
        line; the shaded band is ± std across seeds at that position.
        This is the cleaned-up signal extracted from the left subplot's noise.
        Faint dotted horizontals carry each seed's mean as a reference.

    Both subplots share the same y-axis limits for direct comparison.

    Output: <campaign_dir>/<llm>/artifacts/iteration<N>/plots/iter<N>_eval.png
    """
    plt.style.use(CONFIG["style"])
    seed_colors = CONFIG["seed_colors"]
    solved      = CONFIG["solved_threshold"]
    failure     = CONFIG["failure_threshold"]
    n_eps       = CONFIG["n_eval_episodes"]
    ep_idx      = np.arange(1, n_eps + 1)

    for llm_name, iter_data in results.items():
        for iteration, seed_data in iter_data.items():
            out_dir = (
                campaign_dir / llm_name / "artifacts"
                / f"iteration{iteration}" / "plots"
            )
            out_dir.mkdir(parents=True, exist_ok=True)

            seeds   = sorted(seed_data.keys())
            n_seeds = len(seeds)

            fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 5))
            fig.suptitle(
                f"{llm_name}   ·   Iteration {iteration}\n"
                "Post-Training Evaluation  —  Standard LunarLander-v3",
                fontsize=13, fontweight="bold",
            )

            # ── Left: raw episode returns per seed ────────────────────────────
            for i, seed in enumerate(seeds):
                color  = seed_colors[i % len(seed_colors)]
                ep_ret = seed_data[seed]["episode_returns"]
                s_mean = seed_data[seed]["mean"]

                ax_l.plot(
                    ep_idx, ep_ret,
                    color=color, alpha=0.45, linewidth=1.2,
                    label=f"Seed {seed}",
                )
                # Per-seed mean as a horizontal dash — same colour, clearly readable
                ax_l.axhline(
                    s_mean, color=color, linestyle="--",
                    linewidth=1.1, alpha=0.80,
                )

            _threshold_lines(ax_l, solved, failure, label=True)
            ax_l.set_title(f"Episode Returns  ({n_seeds} seeds)", fontsize=11)
            ax_l.set_xlabel("Evaluation Episode", fontsize=10)
            ax_l.set_ylabel("Episode Return", fontsize=10)
            ax_l.legend(fontsize=8, loc="upper left")
            ax_l.grid(True, alpha=0.15)

            # ── Right: mean ± std across seeds ───────────────────────────────
            # Shape (n_seeds, n_eps) — axis=0 collapses across seeds
            stacked  = np.array([seed_data[s]["episode_returns"] for s in seeds])
            ep_means = stacked.mean(axis=0)   # mean at each episode position
            ep_stds  = stacked.std(axis=0)    # spread across seeds

            ax_r.fill_between(
                ep_idx, ep_means - ep_stds, ep_means + ep_stds,
                alpha=0.20, color="#61afef", label="±1 std across seeds",
            )
            ax_r.plot(
                ep_idx, ep_means,
                color="#61afef", linewidth=2.0,
                label="Mean across seeds",
            )

            # Faint horizontal reference for each seed's overall mean
            for i, seed in enumerate(seeds):
                ax_r.axhline(
                    seed_data[seed]["mean"],
                    color=seed_colors[i % len(seed_colors)],
                    linestyle=":", linewidth=0.7, alpha=0.45,
                )

            _threshold_lines(ax_r, solved, failure, label=False)
            ax_r.set_title(f"Mean ± Std Across {n_seeds} Seeds", fontsize=11)
            ax_r.set_xlabel("Evaluation Episode", fontsize=10)
            ax_r.legend(fontsize=8, loc="upper left")
            ax_r.grid(True, alpha=0.15)

            # Shared y-limits — both axes on identical scale for easy comparison
            all_vals = stacked.flatten()
            _set_ylim(ax_l, all_vals, solved, failure)
            _set_ylim(ax_r, all_vals, solved, failure)

            fig.tight_layout()
            out_path = out_dir / f"iter{iteration}_eval.png"
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  [SAVED] {out_path}")


# ── Plot 2: single-LLM evolution ─────────────────────────────────────────────

def plot_evolution(results: dict, campaign_dir: Path):
    """
    For each LLM show how agent performance evolved across iterations.

      X-axis  — iteration number
      Y-axis  — mean return on standard LunarLander-v3

      • Scatter dots (one per training seed, colour-coded) — reveals whether
        seeds converged tightly or spread widely at each iteration.
      • Bold mean line — mean-of-seed-means across iterations.
      • Shaded band    — ±std-of-seed-means (cross-run training variance).
      • Dashed reference lines for solved (200) and failure (−100) thresholds.

    Aggregation uses std-of-seed-means, NOT mean-of-individual-stds.
    See iter_aggregate() docstring for the full rationale.

    Output: <campaign_dir>/<llm>/artifacts/<llm>_evolution.png
    """
    plt.style.use(CONFIG["style"])
    main_color  = CONFIG["llm_colors"][0]
    seed_colors = CONFIG["seed_colors"]
    solved      = CONFIG["solved_threshold"]
    failure     = CONFIG["failure_threshold"]

    for llm_name, iter_data in results.items():
        artifacts_dir = campaign_dir / llm_name / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        iterations              = sorted(iter_data.keys())
        ev_means: list[float]   = []
        ev_stds:  list[float]   = []

        fig, ax = plt.subplots(figsize=(12, 5))
        fig.suptitle(
            f"{llm_name}   ·   Agent Performance Evolution\n"
            "Mean Return on Standard LunarLander-v3 per Iteration",
            fontsize=13, fontweight="bold",
        )

        for iteration in iterations:
            seed_data                    = iter_data[iteration]
            seeds                        = sorted(seed_data.keys())
            mean_of_means, std_of_means, seed_means = iter_aggregate(seed_data)

            # One dot per training seed — colour matches seed index across plots
            for i, (seed, sm) in enumerate(zip(seeds, seed_means)):
                ax.scatter(
                    iteration, sm,
                    color=seed_colors[i % len(seed_colors)],
                    s=50, alpha=0.70, zorder=3,
                )

            ev_means.append(mean_of_means)
            ev_stds.append(std_of_means)

        ev_means_arr = np.array(ev_means)
        ev_stds_arr  = np.array(ev_stds)
        iters_arr    = np.array(iterations)

        # Std band
        ax.fill_between(
            iters_arr,
            ev_means_arr - ev_stds_arr,
            ev_means_arr + ev_stds_arr,
            alpha=0.20, color=main_color,
        )
        # Mean line
        ax.plot(
            iters_arr, ev_means_arr, "-o",
            color=main_color, linewidth=2.5, markersize=7,
            zorder=4, label="Mean across seeds",
        )
        # Legend proxy for seed dots
        ax.scatter(
            [], [], color="#abb2bf", s=50, alpha=0.70,
            label="Individual seed means",
        )

        _threshold_lines(ax, solved, failure, label=True)

        ax.set_xlabel("Iteration", fontsize=11)
        ax.set_ylabel("Mean Return (Standard LunarLander-v3)", fontsize=11)
        ax.set_xticks(iterations)
        ax.legend(fontsize=9, loc="upper left")
        ax.grid(True, alpha=0.15)

        fig.tight_layout()
        out_path = artifacts_dir / f"{llm_name}_evolution.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [SAVED] {out_path}")


# ── Plot 3: multi-LLM comparison ─────────────────────────────────────────────

def plot_comparison(results: dict, campaign_dir: Path):
    """
    Overlay all LLMs for direct comparison — the headline figure for the
    campaign.

    Each LLM gets a distinct colour (from CONFIG['llm_colors']).
    Seed-level dots are omitted here to avoid clutter; each LLM is represented
    by its mean-of-seed-means line and ±std-of-seed-means band only.

    The solved threshold line makes it immediately obvious which LLMs (if any)
    crossed 200 and at which iteration — this is the key story the plot tells.

    Output: <campaign_dir>/multi_llm_comparison.png
    Skipped automatically if only one LLM is present in results.
    """
    plt.style.use(CONFIG["style"])
    colors  = CONFIG["llm_colors"]
    solved  = CONFIG["solved_threshold"]
    failure = CONFIG["failure_threshold"]

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.suptitle(
        f"Multi-LLM Reward Designer Comparison   ·   {campaign_dir.name}\n"
        "Agent Performance Evolution on Standard LunarLander-v3",
        fontsize=13, fontweight="bold",
    )

    all_means: list[float] = []

    for (llm_name, iter_data), color in zip(results.items(), colors):
        iterations = sorted(iter_data.keys())
        ev_means: list[float] = []
        ev_stds:  list[float] = []

        for iteration in iterations:
            mom, sos, _ = iter_aggregate(iter_data[iteration])
            ev_means.append(mom)
            ev_stds.append(sos)

        ev_means_arr = np.array(ev_means)
        ev_stds_arr  = np.array(ev_stds)
        iters_arr    = np.array(iterations)
        all_means.extend(ev_means)

        ax.fill_between(
            iters_arr,
            ev_means_arr - ev_stds_arr,
            ev_means_arr + ev_stds_arr,
            alpha=0.12, color=color,
        )
        ax.plot(
            iters_arr, ev_means_arr, "-o",
            color=color, linewidth=2.5, markersize=7,
            label=llm_name,
        )

    _threshold_lines(ax, solved, failure, label=True)

    ax.set_xlabel("Iteration", fontsize=11)
    ax.set_ylabel("Mean Return (Standard LunarLander-v3)", fontsize=11)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, alpha=0.15)

    if all_means:
        _set_ylim(ax, np.array(all_means), solved, failure)

    fig.tight_layout()
    out_path = campaign_dir / "multi_llm_comparison.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [SAVED] {out_path}")


# ── CSV export ────────────────────────────────────────────────────────────────

def save_csv(results: dict, campaign_dir: Path):
    """
    Write per-seed evaluation statistics to CSV for reproducibility.
    Columns: llm, iteration, seed, mean_return, std_return
    """
    path = campaign_dir / "eval_results.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["llm", "iteration", "seed", "mean_return", "std_return"])
        for llm_name, iter_data in results.items():
            for iteration, seed_data in iter_data.items():
                for seed, data in seed_data.items():
                    writer.writerow([
                        llm_name,
                        int(iteration),
                        int(seed),
                        round(data["mean"], 3),
                        round(data["std"],  3),
                    ])
    print(f"  [SAVED] {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate trained PPO agents from a single campaign on the "
            "standard LunarLander-v3 environment and produce publication-ready plots."
        )
    )
    parser.add_argument(
        "--campaign_dir", type=str, required=True,
        help=(
            "Path to the campaign directory "
            "(e.g. experiments/2024-01-15_10cycles_1Msteps_run1).  "
            "All LLM sub-directories inside are discovered automatically."
        ),
    )
    parser.add_argument(
        "--n_eval_episodes", type=int, default=CONFIG["n_eval_episodes"],
        help=(
            f"Evaluation episodes per model (default: {CONFIG['n_eval_episodes']}).  "
            "30 is recommended — sufficient for CLT to hold and a trustworthy mean."
        ),
    )
    parser.add_argument(
        "--eval_seed", type=int, default=CONFIG["eval_seed"],
        help=(
            f"Env reset seed for reproducible evaluation (default: {CONFIG['eval_seed']}).  "
            "Use a value that was NOT used as a training seed."
        ),
    )
    parser.add_argument(
        "--render", action="store_true",
        help="Render the environment during evaluation (slow — use for spot-checking only).",
    )
    args = parser.parse_args()

    CONFIG["n_eval_episodes"] = args.n_eval_episodes
    CONFIG["eval_seed"]       = args.eval_seed
    CONFIG["render"]          = args.render

    campaign_dir = Path(args.campaign_dir).expanduser().resolve()
    if not campaign_dir.exists():
        raise FileNotFoundError(f"campaign_dir not found: {campaign_dir}")

    print(f"\nCampaign : {campaign_dir}")
    structure = find_models(campaign_dir)

    if not structure:
        print(
            "\n[ERROR] No model files found matching iter<N>_model<seed>.zip  "
            "inside the campaign directory.  Check the directory path and "
            "model filename convention."
        )
        return

    print(f"\nFound {len(structure)} LLM(s):")
    for llm, iters in structure.items():
        total = sum(len(s) for s in iters.values())
        print(f"  • {llm}  ({len(iters)} iterations, {total} models total)")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    results = collect_results(structure)

    # ── Plot ──────────────────────────────────────────────────────────────────
    print("\nGenerating plots ...")

    plot_per_iteration(results, campaign_dir)   # one fig per (LLM × iteration)
    plot_evolution(results, campaign_dir)       # one fig per LLM

    if len(results) > 1:
        plot_comparison(results, campaign_dir)  # one fig for all LLMs
    else:
        llm = next(iter(results))
        print(
            f"  (multi-LLM comparison skipped — only '{llm}' found in campaign)"
        )

    # ── CSV ───────────────────────────────────────────────────────────────────
    save_csv(results, campaign_dir)

    print(f"\n{'═'*62}")
    print(f"  Done.  All outputs written inside: {campaign_dir}")
    print(f"{'═'*62}\n")


if __name__ == "__main__":
    main()