import argparse
import os
import sys
from src.remote_ops import RemoteManager
from src.config import Config
from src.workspace_manager import ExperimentWorkspace

try:
    import src.config_local 
except ImportError:
    pass
def run_remote_cycle(iteration: int, num_seeds: int):
        # 1. Initialize Local Workspace (Mac side)
    # We need this to find the generated reward file to upload
    ws = ExperimentWorkspace(iteration=iteration)
    print(f"📡 [Remote-Manager] Initializing Remote Training for Iteration {iteration}")

    # 2. Setup Manager
    manager = RemoteManager(
        Config.LINUX_IP, 
        Config.LINUX_USER, 
        Config.SSH_KEY_PATH, 
        Config.REMOTE_PROJECT_ROOT
    )

    # 3. UPLOAD: Send the generated reward code to Linux
    # Source: experiments/Campaign/Model/generated_code/iterXX_reward.py (Mac)
    local_reward_path = ws.get_path("code", iteration, "reward.py")
    # Dest: experiments/Campaign/Model/generated_code/iterXX_reward.py (Linux)
    # We use get_relative_path so we don't accidentally send Mac absolute paths (/Users/...) to Linux
    relative_path = ws.get_relative_path("code", iteration, "reward.py")
    
    print(f"📤 Uploading Reward Function: {local_reward_path}")
    manager.sync_file(str(local_reward_path), str(relative_path))

    # 3. EXECUTE: Trigger Training & Analysis on Linux
    print(f"🚀 Triggering Remote Execution (Iter {iteration}) across {num_seeds} seeds")

    omp = Config.OMP_NUM_THREADS
    env_vars = {
        "CAMPAIGN_TAG": os.environ.get("CAMPAIGN_TAG", ws.campaign_tag),
        "LLM_MODEL": os.environ.get("LLM_MODEL", ws.raw_model_name),
        "TOTAL_TIMESTEPS": os.environ.get("TOTAL_TIMESTEPS", "50000"),
        "OMP_NUM_THREADS": omp,
        "MKL_NUM_THREADS": omp,
        "OPENBLAS_NUM_THREADS": omp,
    }
    # Build remote bash script: detect CCX topology, launch seeds in parallel
    # with taskset, wait for all, then run analysis. Falls back to sequential
    # if the remote machine lacks multi-CCX topology.
    compound_cmd = f"""
set -o pipefail
cd {Config.REMOTE_PROJECT_ROOT}
export PYTHONPATH={Config.REMOTE_PROJECT_ROOT}

mapfile -t CCX < <(cat /sys/devices/system/cpu/cpu[0-9]*/cache/index3/shared_cpu_list 2>/dev/null | sort -u)
NUM_CCX=${{#CCX[@]}}
echo "📡 [Remote-Dispatch] Detected $NUM_CCX CCX groups for {num_seeds} seeds"

if [ $NUM_CCX -lt 2 ]; then
    echo "   Single CCX or detection failed → sequential dispatch"
    for seed_id in $(seq 0 $(({num_seeds} - 1))); do
        {Config.REMOTE_PYTHON_BIN} -u src/train.py --iteration {iteration} --seed_id $seed_id || exit 1
    done
else
    echo "   Multi-CCX → parallel dispatch with taskset pinning"
    declare -a PIDS
    for seed_id in $(seq 0 $(({num_seeds} - 1))); do
        CCX_IDX=$((seed_id % NUM_CCX))
        echo "   → seed $seed_id pinned to CCX ${{CCX[$CCX_IDX]}}"
        LOG=/tmp/ard_iter{iteration}_seed$seed_id.log
        taskset -c "${{CCX[$CCX_IDX]}}" {Config.REMOTE_PYTHON_BIN} -u src/train.py --iteration {iteration} --seed_id $seed_id > "$LOG" 2>&1 &
        PIDS+=($!)
    done
    EXIT_CODE=0
    for pid in "${{PIDS[@]}}"; do
        if ! wait $pid; then EXIT_CODE=1; fi
    done
    for seed_id in $(seq 0 $(({num_seeds} - 1))); do
        echo "--- Seed $seed_id ---"
        cat /tmp/ard_iter{iteration}_seed$seed_id.log 2>/dev/null || true
    done
    if [ $EXIT_CODE -ne 0 ]; then
        echo "❌ One or more seeds failed"
        exit 1
    fi
fi

{Config.REMOTE_PYTHON_BIN} -u -m src.analysis --iteration {iteration} --num_seeds {num_seeds}
"""

    success = manager.stream_command(compound_cmd, env_vars=env_vars)
    
    if not success:
        print("❌ Critical Failure: Remote training crashed.")
        sys.exit(1)

    # 5. DOWNLOAD: Retrieve the Metrics Payload
    # Linux saved it to: experiments/Campaign/Model/telemetry/metric_payloads/iterXX_metrics.json
    metrics_rel_path = ws.get_relative_path("telemetry_payloads", iteration, "metric_payload.json")
    local_metrics_dest = ws.get_path("telemetry_payloads", iteration, "metric_payload.json")
    
    # Ensure the local folder exists before downloading
    local_metrics_dest.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📥 Downloading Aggregated Metrics: {metrics_rel_path}")
    success = manager.retrieve_file(str(metrics_rel_path), str(local_metrics_dest))
    
    if not success:
        print("❌ Failed to retrieve metrics. Controller will crash.")
        sys.exit(1)

    print(f"✅ Remote Cycle {iteration} Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--num_seeds", type=int, default=4)
    args = parser.parse_args()
    
    run_remote_cycle(args.iteration, args.num_seeds)