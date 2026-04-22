import time
import re
from datetime import datetime, timedelta 
import warnings
import shutil
from pathlib import Path
import argparse
# -- PROJECT IMPORTS --
from src.workspace_manager import ExperimentWorkspace
from src.analysis import *
def set_inital_shaping(reward_func:str='spin_crash'):

    # Initialize Workspace & Ledger for Iteration 0
    ws = ExperimentWorkspace(iteration=0)

    # Grab the curated faulty reward function
    base_code_load_path = Path("/Users/dominikklingshirn/Projects/RL-Lab/rl_agent_loop/curated_reward_functions")
    reward_funcs = {
        "lunar" :          Path("lunar.py"),
        "sideways_slide" : Path("sideways_slide.py"),
        "spin_crash":      Path("spin_crash.py"),
        "vertical_bounce": Path("vertical_bounce.py"),
        "weird_reward":    Path("weird_reward.py"),
        "wild_oscillation":Path("wild_oscillation.py")
    }
    code_load_path = base_code_load_path /reward_funcs[reward_func]
    # Path to save code
    code_save_path = ws.get_path("code", 0, "reward.py")
    # Copy to current experiment directory
    shutil.copy(code_load_path,code_save_path)

    # Paths to the CSVs related to that reward function
    eval_paths = [base_code_load_path / 'telemetry'/ f"{reward_func}_seed{seed_id}_eval.csv"
                  for seed_id in range(3)]
    train_paths = [base_code_load_path / 'telemetry'/ f"{reward_func}_seed{seed_id}_train.csv"
                  for seed_id in range(3)]
    progress_paths = [base_code_load_path / 'telemetry'/ f"progress_{reward_func}_seed{seed_id}.csv"
                  for seed_id in range(3)]
 
    # Analyze each progress.csv
    single_progress_results = [analyze_single_seed_progress(path, idx) for idx, path in enumerate(progress_paths)]
    # Analyzing progress.csv across seeds
    progress_payload= aggregate_progress_seeds(single_progress_results)

    # Analyze each train_eps.csv
    train_results = [analyze_single_seed_stochastic(path, idx) for idx, path in enumerate(train_paths)]
    # Analyzing train_eps.csv across seeds
    train_payload = aggregate_stochastic_seeds(train_results)

    # Analyze each eval.csv
    eval_results = [analyze_single_seed_eval(path, idx) for idx, path in enumerate(eval_paths)]
    # Analyzing eval.csv across seeds
    eval_payload = aggregate_eval_seeds(eval_results)
 
    metrics = {
        "multi_seed_optimization_health" : progress_payload,
        "multi_seed_stochastic_health" : train_payload,
        "multi_seed_evaluation_health" : eval_payload
        }
    # Save metric payload, it will be picked up and translated as Diagnostic Report during LLM orchestration
    ws.save_metrics(0,metrics)

    print(f"Initial shaping script loaded from: {code_load_path}\nSaved to: {code_save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reward', type=str, default="spin_crash")
    args = parser.parse_args()
    set_inital_shaping(args.reward)