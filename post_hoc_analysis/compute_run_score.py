"""
compute_run_score.py

Computes the composite Tier 1 RunScore for a completed ARD run.
Reads per-iteration metric_payload.json files from the standard workspace
directory structure. No dependencies on live pipeline components.

Usage:
    python compute_run_score.py --run_dir experiments/CampaignTag/ModelName
    python compute_run_score.py --run_dir experiments/CampaignTag/ModelName --gs_w 0.35 --lambda2 0.5 --eps 0.001
"""

import json
import math
import argparse
import numpy as np
from pathlib import Path


# ===========================================================================
# Core computation
# ===========================================================================

def load_iteration_payloads(run_dir: Path) -> list[dict]:
    """
    Auto-detects and loads all iter*_metric_payload.json files in sorted order.
    Returns a list of payload dicts ordered by iteration number.
    """
    payloads_dir = run_dir / "telemetry" / "metric_payloads"
    if not payloads_dir.exists():
        raise FileNotFoundError(f"No metric_payloads directory found at {payloads_dir}")

    payload_files = sorted(payloads_dir.glob("iter*_metric_payload.json"))
    if not payload_files:
        raise FileNotFoundError(f"No metric_payload.json files found in {payloads_dir}")

    payloads = []
    for f in payload_files:
        with open(f) as fp:
            payloads.append(json.load(fp))

    print(f"Loaded {len(payloads)} iteration payloads from {payloads_dir}")
    return payloads


def extract_iteration_scalars(payloads: list[dict], e_pen_key: str = "population_mean_chatter_rate") -> dict:
    """
    Extracts per-iteration scalar arrays from the loaded payloads.

    e_pen_key: the key inside multi_seed_evaluation_health.kinematic_stability
               that represents the environment-specific efficiency penalty.
               Default: "population_mean_chatter_rate" (LunarLander).
               Set to None to disable E_pen (defaults all values to 0.0).
    """
    psr_list = []
    s_cen_list = []
    sigma_norm_list = []
    e_pen_list = []
    snr_list = []
    diverged_list = []

    for i, p in enumerate(payloads):
        stoch = p.get("multi_seed_stochastic_health", {})
        eval_ = p.get("multi_seed_evaluation_health", {})
        prog = p.get("multi_seed_optimization_health", {})

        # --- PSR_i: sum of landed_* fractions from population terminal distribution ---
        term_dist = stoch.get("population_terminal_distribution", {})
        psr_i = float(sum(v for k, v in term_dist.items() if "landed" in k))
        psr_list.append(psr_i)

        # --- s_cen_i: centered-landing rate (micro/precision goal) ---
        s_cen_i = float(term_dist.get("landed_centered", 0.0))
        s_cen_list.append(s_cen_i)

        # --- σ_norm_i: cross-seed std of per-seed success rates, normalized by 0.5 ---
        seed_rates = stoch.get("global_reward_topology", {}).get("seed_success_rates", [])
        if len(seed_rates) >= 2:
            sigma_i = float(np.std(seed_rates)) / 0.5
        else:
            # Single seed or missing field: no dispersion penalty
            sigma_i = 0.0
        sigma_norm_list.append(sigma_i)

        # --- E_pen_i: environment-specific efficiency penalty ---
        if e_pen_key is not None:
            kin = eval_.get("kinematic_stability", {})
            e_pen_i = float(kin.get(e_pen_key, 0.0))
        else:
            e_pen_i = 0.0
        e_pen_list.append(e_pen_i)

        # --- SNR_i: cross-seed signal-to-noise ratio from progress payload ---
        pop = prog.get("population_metrics", {})
        snr_i = float(pop.get("cross_seed_snr", 0.0))
        snr_list.append(snr_i)

        # --- Divergence flag ---
        crit = prog.get("critic_robustness", {})
        diverged_list.append(bool(crit.get("systemic_critic_divergence_flag", False)))

    return {
        "psr": psr_list,
        "s_cen": s_cen_list,
        "sigma_norm": sigma_norm_list,
        "e_pen": e_pen_list,
        "snr": snr_list,
        "diverged": diverged_list,
        "n_iterations": len(payloads),
    }


def compute_ppv(gs: list[float], e_pen: list[float], lambda2: float) -> float:
    """
    PPV = max_i ( GS_i * max(0, 1 - λ2*E_pen_i) )
    Peak graded value, efficiency-penalized. Dispersion penalty removed —
    cross-seed reliability is now owned solely by TR (orthogonality).
    """
    best = 0.0
    for gs_i, e_pen_i in zip(gs, e_pen):
        efficiency_factor = max(0.0, 1.0 - lambda2 * e_pen_i)
        ppv_i = gs_i * efficiency_factor
        if ppv_i > best:
            best = ppv_i
    return best


def compute_policy_retention(gs: list[float]) -> float:
    """
    Trapezoidal mean of GS over the iteration horizon.
    Returns 0.0 if fewer than 2 iterations.
    """
    n = len(gs)
    if n < 2:
        return 0.0
    total = sum((gs[i] + gs[i + 1]) / 2.0 for i in range(n - 1))
    return total / (n - 1)


def compute_tr(gs: list[float], sigma_norm: list[float], diverged: list[bool]) -> tuple[float, bool, list[int]]:
    """
    TR = (1/|K|) * sum( 1 - min(1, σ_norm_i) ) for i in K
    K = top-ceil(N/3) iterations by GS_i (graded success).

    Reliability = cross-seed success dispersion (replaces reward-SNR);
    σ_norm_i = std(seed_success_rates_i) / 0.5, clamped to [0,1].

    Divergence validity unchanged:
    - diverged_run = True if systemic_critic_divergence_flag is True in >50% of K.
    Returns: (tr_score, diverged_run, K_indices)
    """
    n = len(gs)
    k_size = math.ceil(n / 3)

    ranked = sorted(range(n), key=lambda i: gs[i], reverse=True)
    k_indices = ranked[:k_size]

    k_diverged_count = sum(1 for i in k_indices if diverged[i])
    diverged_run = (k_diverged_count > k_size / 2)

    tr = float(np.mean([1.0 - min(1.0, sigma_norm[i]) for i in k_indices]))

    return tr, diverged_run, k_indices


def compute_run_score(
    run_dir: str | Path,
    gs_w: float = 0.5,
    lambda2: float = 0.5,
    eps: float = 0.001,
    e_pen_key: str = "population_mean_chatter_rate",
) -> dict:
    """
    Main entry point. Loads payloads, computes RunScore and all components.

    Returns a results dict containing:
    - run_score: float
    - components: {ppv, policy_retention, tr}
    - validity: {is_diverged, diverged_k_iterations}
    - per_iteration: {s_any, s_cen, gs, sigma_norm, e_pen, snr, diverged}
    - metadata: {n_iterations, gs_w, lambda2, eps, e_pen_key, run_dir}
    """
    run_dir = Path(run_dir)
    payloads = load_iteration_payloads(run_dir)
    scalars = extract_iteration_scalars(payloads, e_pen_key=e_pen_key)

    # Graded success: GS_i = w·s_any_i + (1-w)·s_cen_i  (nested macro/micro goal)
    gs = [gs_w * a + (1.0 - gs_w) * c
          for a, c in zip(scalars["psr"], scalars["s_cen"])]

    ppv = compute_ppv(gs, scalars["e_pen"], lambda2)
    policy_retention = compute_policy_retention(gs)
    tr, is_diverged, k_indices = compute_tr(gs, scalars["sigma_norm"], scalars["diverged"])

    # Clamp all bases to [eps, 1.0]
    ppv_c = max(eps, min(1.0, ppv))
    pr_c = max(eps, min(1.0, policy_retention))
    tr_c = max(eps, min(1.0, tr))

    run_score = (ppv_c ** 0.4) * (pr_c ** 0.4) * (tr_c ** 0.2)

    results = {
        "run_score": round(run_score, 6),
        "components": {
            "ppv": round(ppv, 6),
            "policy_retention": round(policy_retention, 6),
            "tr": round(tr, 6),
        },
        "validity": {
            "is_diverged": is_diverged,
            "diverged_k_iterations": [int(i + 1) for i in k_indices if scalars["diverged"][i]],
        },
        "per_iteration": {
            "s_any": [round(v, 4) for v in scalars["psr"]],
            "s_cen": [round(v, 4) for v in scalars["s_cen"]],
            "gs":    [round(v, 4) for v in gs],
            "sigma_norm": [round(v, 4) for v in scalars["sigma_norm"]],
            "e_pen": [round(v, 4) for v in scalars["e_pen"]],
            "snr": [round(v, 4) for v in scalars["snr"]],
            "diverged": scalars["diverged"],
        },
        "metadata": {
            "n_iterations": scalars["n_iterations"],
            "gs_w": gs_w,
            "lambda2": lambda2,
            "eps": eps,
            "e_pen_key": e_pen_key,
            "run_dir": str(run_dir),
        },
    }

    return results


def save_run_score(results: dict, run_dir: Path) -> Path:
    """Saves the RunScore results JSON alongside the metric_payloads."""
    output_path = run_dir / "reports" / "run_score.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"RunScore saved to {output_path}")
    return output_path


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Tier 1 RunScore for a completed ARD run.")
    parser.add_argument("--run_dir", type=str, required=True,
                        help="Path to the model run root (e.g. experiments/CampaignTag/ModelName)")
    parser.add_argument("--gs_w", type=float, default=0.35,
                        help="Graded-success weight: GS = w*any_landing + (1-w)*centered. "
                             "w=1.0 → pure any-landing; w=0.0 → pure centered (default: 0.35)")
    parser.add_argument("--lambda2", type=float, default=0.5,
                        help="Efficiency penalty weight (default: 0.5)")
    parser.add_argument("--eps", type=float, default=0.001,
                        help="Epsilon floor for geometric mean bases (default: 0.001)")
    parser.add_argument("--e_pen_key", type=str, default="population_mean_chatter_rate",
                        help="Key in kinematic_stability payload for E_pen (default: population_mean_chatter_rate). Pass 'none' to disable.")
    parser.add_argument("--save", action="store_true",
                        help="Save run_score.json to the metric_payloads directory")
    args = parser.parse_args()

    e_pen_key = None if args.e_pen_key.lower() == "none" else args.e_pen_key

    results = compute_run_score(
        run_dir=args.run_dir,
        gs_w=args.gs_w,
        lambda2=args.lambda2,
        eps=args.eps,
        e_pen_key=e_pen_key,
    )

    # Print summary
    validity_tag = " ⚠️  DIVERGED — excluded from MWU" if results["validity"]["is_diverged"] else ""
    print(f"\n{'='*50}")
    print(f"RunScore: {results['run_score']:.4f}{validity_tag}")
    print(f"  PPV:              {results['components']['ppv']:.4f}")
    print(f"  PolicyRetention:  {results['components']['policy_retention']:.4f}")
    print(f"  TR:               {results['components']['tr']:.4f}")
    print(f"  N iterations:     {results['metadata']['n_iterations']}")
    print(f"{'='*50}\n")
    print("Per-iteration PSR:", results["per_iteration"]["s_any"])
    print("Per-iteration GS:", results["per_iteration"]["gs"])

    if args.save:
        save_run_score(results, Path(args.run_dir))
