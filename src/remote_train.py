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

    # 2. EXECUTE: Trigger Sequential Training & Analysis on Linux
    print(f"🚀 Triggering Remote Execution (Iter {iteration}) across {num_seeds} seeds")

    # 🔧 Pin training to CCD0 (cores 0-7 + their hyperthreads 16-23) for L3 cache locality.
    # Sequential seeds reuse the same cache-warmed CCD across runs.
 # 🔧 Use Config values — populated by config_local.py if present, safe defaults otherwise
    cores = Config.REMOTE_TASKSET_CORES
    TASKSET = f"taskset -c {cores}" if cores else ""

    omp = Config.OMP_NUM_THREADS

    env_vars = {
        "CAMPAIGN_TAG": os.environ.get("CAMPAIGN_TAG", ws.campaign_tag),
        "LLM_MODEL": os.environ.get("LLM_MODEL", ws.raw_model_name),
        "TOTAL_TIMESTEPS": os.environ.get("TOTAL_TIMESTEPS", "50000"),
        "OMP_NUM_THREADS": omp,
        "MKL_NUM_THREADS": omp,
        "OPENBLAS_NUM_THREADS": omp,
    }
    # Build a sequential command chain using '&&'
    # If any step fails, the chain stops immediately.
    remote_commands = []

    # A. Train each seed (pinned to CCD0)
    for seed_id in range(num_seeds):
        remote_commands.append(
            f"{TASKSET} {Config.REMOTE_PYTHON_BIN} -u train.py "
            f"--iteration {iteration} --seed_id {seed_id}"
        )

    # B. Analysis (also pinned — keeps the chain on one CCD end-to-end)
    remote_commands.append(
        f"PYTHONPATH={Config.REMOTE_PROJECT_ROOT} {TASKSET} "
        f"{Config.REMOTE_PYTHON_BIN} -u -m src.analysis --iteration {iteration}"
    )
    # Join them together: train 0 && train 1 && train 2 && analyze
    compound_cmd = " && ".join(remote_commands)
    #for command in remote_commands:
     #   success = manager.stream_command(command, env_vars=env_vars)
    # This blocks on the Mac until Linux finishes all training and aggregation

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
    parser.add_argument("--num_seeds", type=int, default=3)
    args = parser.parse_args()
    
    run_remote_cycle(args.iteration, args.num_seeds)