# =============================================================================
# SCRIPT 1: record_clips.py
# Records one deterministic evaluation episode per seed for a given iteration.
# Saves clips to: artifacts/Videos/iter{XX}_seed{X}.mp4
#
# Usage:
#   python src/record_clips.py \
#       --campaign_tag "2025-01-15_baseline_10cycles_500kSteps" \
#       --model_name "gpt-4o" \
#       --iteration 3 \
#       --num_seeds 3
# =============================================================================

import os
import sys
import shutil
import argparse
import tempfile
from pathlib import Path

import gymnasium as gym
from gymnasium.wrappers import RecordVideo
from stable_baselines3 import PPO

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.workspace_manager import ExperimentWorkspace


def record_seed_clip(iteration: int, seed_id: int, ws: ExperimentWorkspace):
    """
    Loads saved model for (iteration, seed_id), runs one deterministic episode
    with rendering, and saves it to artifacts/videos/iter{XX}_seed{X}.mp4.
    """
    videos_dir = ws.dirs["videos"]
    videos_dir.mkdir(parents=True, exist_ok=True)

    dest_path = videos_dir / f"iter{iteration:02d}_seed{seed_id}.mp4"
    if dest_path.exists():
        print(f"  Clip already exists, skipping: {dest_path.name}")
        return

    # Load model — SB3 appends .zip automatically if missing
    model_path = ws.get_path("models", iteration, f"model{seed_id}")
    print(f"  Loading model from: {model_path}")
    model = PPO.load(str(model_path))

    # Record into a temp dir first, then rename to match our convention.
    # RecordVideo produces names like: {name_prefix}-episode-0.mp4
    with tempfile.TemporaryDirectory() as tmp:
        env = gym.make("LunarLander-v3", render_mode="rgb_array")
        env = RecordVideo(
            env,
            video_folder=tmp,
            episode_trigger=lambda ep_idx: ep_idx == 0,  # record first episode only
            name_prefix=f"iter{iteration:02d}_seed{seed_id}",
        )

        obs, _ = env.reset(seed=seed_id)
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, _, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
        env.close()

        recorded_files = list(Path(tmp).glob("*.mp4"))
        if not recorded_files:
            print(f"  WARNING: No mp4 found for iter{iteration:02d}_seed{seed_id}. Skipping.")
            return

        shutil.move(str(recorded_files[0]), str(dest_path))

    print(f"  Saved: {dest_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign_tag", type=str, required=True)
    parser.add_argument("--model_name",   type=str, required=True)
    parser.add_argument("--iteration",    type=int, required=True)
    parser.add_argument("--num_seeds",    type=int, default=3)
    args = parser.parse_args()

    # Strip any shell-quoting artifacts that can arrive when called over SSH.
    # stream_command wraps the remote cmd in double quotes, which makes single
    # quotes literal on the calling shell and can embed them in arg values.
    campaign_tag = args.campaign_tag.strip("'\"")
    model_name   = args.model_name.strip("'\"")

    # Mirror how train.py gets its campaign context — via env vars
    os.environ["CAMPAIGN_TAG"] = campaign_tag
    os.environ["LLM_MODEL"]    = model_name

    ws = ExperimentWorkspace(iteration=args.iteration)
    print(f"\n Recording clips | Iter {args.iteration:02d} | {args.num_seeds} seeds")

    for seed_id in range(args.num_seeds):
        print(f"\n  Seed {seed_id}:")
        record_seed_clip(args.iteration, seed_id, ws)
    videos_path = ws.dirs["videos"]
    print(f"\nDone. Clips saved to: {videos_path}")

if __name__ == "__main__":
    main()
