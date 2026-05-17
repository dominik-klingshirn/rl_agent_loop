"""
build_demo_remote.py
====================
Orchestrates the full demo-video pipeline on the remote Linux PC:

    1. For each iteration 1..num_iterations: runs record_clips.py
    2. Runs build_demo_video.py across all iterations
    3. SCPs the finished video back to this Mac

Usage
-----
python build_demo_remote.py \
    --campaign_tag  "2025-01-15_baseline_10cycles_500kSteps" \
    --model_name    "gemma4:26b" \
    --num_iterations 5 \
    [--num_seeds     3] \
    [--output_name   "demo.mp4"] \
    [--local_dest    "~/Desktop"]

SSH Configuration
-----------------
Edit the SSH_CONFIG block below to match your Linux PC.
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# SSH / PATH CONFIGURATION  — edit these to match your setup
# ---------------------------------------------------------------------------
SSH_CONFIG = {
    "hostname":           "YOUR_LINUX_PC_HOSTNAME_OR_IP",
    "username":           "YOUR_USERNAME",
    "ssh_key_path":       "~/.ssh/id_rsa",
    "remote_project_root": "/home/YOUR_USERNAME/rl_agent_loop",
}

# Directory (relative to remote_project_root) where the analysis scripts live
ANALYSIS_DIR = "post_hoc_analysis"

# Python interpreter to use on the remote machine
REMOTE_PYTHON = "python3"
# ---------------------------------------------------------------------------


# Import RemoteManager from the local src directory so this script can live
# anywhere in the project tree.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from src.remote_ops import RemoteManager


def parse_args():
    p = argparse.ArgumentParser(
        description="Record clips + build demo video on Linux PC, then fetch result."
    )
    p.add_argument(
        "--campaign_tag", required=True,
        help='Campaign folder name, e.g. "2025-01-15_baseline_10cycles_500kSteps"',
    )
    p.add_argument(
        "--model_name", required=True,
        help='Model name as used by the pipeline, e.g. "gemma4:26b"',
    )
    p.add_argument(
        "--num_iterations", type=int, required=True,
        help="Total number of iterations to include (will record clips for 1..N).",
    )
    p.add_argument(
        "--num_seeds", type=int, default=3,
        help="Seeds per iteration (default: 3).",
    )
    p.add_argument(
        "--output_name", default="demo.mp4",
        help='Filename for the final video (default: "demo.mp4").',
    )
    p.add_argument(
        "--local_dest", default="~/Desktop",
        help="Local directory on this Mac to save the finished video (default: ~/Desktop).",
    )
    return p.parse_args()


def derive_remote_video_path(campaign_tag: str, model_name: str, output_name: str) -> str:
    """
    Mirrors ExperimentWorkspace path logic:
        experiments/{campaign_tag}/{model_dir_name}/artifacts/Videos/{output_name}
    
    model_dir_name sanitises colons (gemma4:26b -> gemma4-26b) to match
    what ExperimentWorkspace does on the Linux side.
    """
    model_dir_name = model_name.replace(":", "-")
    return f"experiments/{campaign_tag}/{model_dir_name}/artifacts/Videos/{output_name}"


def main():
    args = parse_args()

    iterations = list(range(1, args.num_iterations + 1))
    iterations_str = " ".join(str(i) for i in iterations)

    print("\n" + "=" * 60)
    print("  ARD Demo Video — Remote Build")
    print("=" * 60)
    print(f"  Campaign    : {args.campaign_tag}")
    print(f"  Model       : {args.model_name}")
    print(f"  Iterations  : {iterations}")
    print(f"  Seeds/iter  : {args.num_seeds}")
    print(f"  Output file : {args.output_name}")
    print(f"  Local dest  : {args.local_dest}")
    print("=" * 60 + "\n")

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------
    rm = RemoteManager(
        hostname=SSH_CONFIG["hostname"],
        username=SSH_CONFIG["username"],
        ssh_key_path=SSH_CONFIG["ssh_key_path"],
        remote_project_root=SSH_CONFIG["remote_project_root"],
    )

    # Quick connectivity check
    print("🔌 Checking SSH connectivity...")
    code, out, err = rm.run_command("echo OK")
    if code != 0 or out != "OK":
        print(f"❌ SSH check failed (exit {code}): {err}")
        sys.exit(1)
    print("   Connected.\n")

    # ------------------------------------------------------------------
    # Step 1 — Record clips for each iteration
    # ------------------------------------------------------------------
    print(f"🎬 Step 1/2 — Recording clips ({args.num_iterations} iteration(s))\n")

    for iteration in iterations:
        print(f"  ▶  Iteration {iteration:02d} / {args.num_iterations:02d}")
        cmd = (
            f"{REMOTE_PYTHON} {ANALYSIS_DIR}/record_clips.py "
            f"--campaign_tag \"{args.campaign_tag}\" "
            f"--model_name   \"{args.model_name}\" "
            f"--iteration    {iteration} "
            f"--num_seeds    {args.num_seeds}"
        )
        ok = rm.stream_command(cmd)
        if not ok:
            print(f"\n❌ record_clips.py failed on iteration {iteration}. Aborting.")
            sys.exit(1)
        print()

    # ------------------------------------------------------------------
    # Step 2 — Build composite demo video
    # ------------------------------------------------------------------
    print(f"🎞️  Step 2/2 — Building demo video\n")

    cmd = (
        f"{REMOTE_PYTHON} {ANALYSIS_DIR}/build_demo_video.py "
        f"--campaign_tag \"{args.campaign_tag}\" "
        f"--model_name   \"{args.model_name}\" "
        f"--iterations   {iterations_str} "
        f"--num_seeds    {args.num_seeds} "
        f"--output_name  \"{args.output_name}\""
    )
    ok = rm.stream_command(cmd)
    if not ok:
        print("\n❌ build_demo_video.py failed. Aborting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3 — SCP the finished video back to Mac
    # ------------------------------------------------------------------
    print(f"\n📥 Step 3/2 — Fetching video from Linux PC\n")  # 3/2 is intentional humour

    remote_video_path = derive_remote_video_path(
        args.campaign_tag, args.model_name, args.output_name
    )

    # Expand ~ and resolve the final local path
    local_dir = Path(args.local_dest).expanduser().resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    local_video_path = str(local_dir / args.output_name)

    print(f"  Remote : {SSH_CONFIG['remote_project_root']}/{remote_video_path}")
    print(f"  Local  : {local_video_path}\n")

    ok = rm.retrieve_file(remote_video_path, local_video_path)
    if not ok:
        print("❌ SCP download failed.")
        sys.exit(1)

    print(f"\n✅ Done!  Video saved to: {local_video_path}\n")


if __name__ == "__main__":
    main()
