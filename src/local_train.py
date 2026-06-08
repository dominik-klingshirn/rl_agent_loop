import argparse
import os
import subprocess
import sys

from src.utils import get_parallel_training_config

def run_local_cycle(iteration: int, num_seeds: int):
    print(f"💻 [Local-Manager] Executing Local Training for Iteration {iteration}")
    try:
        concurrency, ccx_groups, threads = get_parallel_training_config()
        pin_mode = "ccx" if ccx_groups else "none"
        print(f"   Parallel config: concurrency={concurrency}, "
              f"pinning={pin_mode}, threads_per_run={threads}")

        seeds_remaining = list(range(num_seeds))
        while seeds_remaining:
            batch = seeds_remaining[:concurrency]
            seeds_remaining = seeds_remaining[concurrency:]
            procs = []
            for slot, seed_id in enumerate(batch):
                env = os.environ.copy()
                env["TORCH_NUM_THREADS"] = str(threads)
                for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                          "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
                    env[k] = str(threads)
                cmd = f"{sys.executable} src/train.py --iteration {iteration} --seed_id {seed_id}"
                if ccx_groups and slot < len(ccx_groups):
                    cmd = f"taskset -c {ccx_groups[slot]} " + cmd
                procs.append(subprocess.Popen(cmd, shell=True, env=env))

            for p in procs:
                if p.wait() != 0:
                    raise subprocess.CalledProcessError(p.returncode, p.args)

        subprocess.run(
            f"{sys.executable} src/analysis.py --iteration {iteration} --num_seeds {num_seeds}",
            shell=True, check=True)
        print(f"✅ Local Cycle {iteration} Complete.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Critical Failure during local execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--num_seeds", type=int, default=4)
    args = parser.parse_args()

    run_local_cycle(args.iteration, args.num_seeds)
