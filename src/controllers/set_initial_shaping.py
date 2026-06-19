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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

def set_inital_shaping(reward_func:str='spin_crash'):

    # Initialize Workspace & Ledger for Iteration 0
    ws = ExperimentWorkspace(iteration=0)

    # Grab the curated faulty reward function
    base_load_path = PROJECT_ROOT / "curated_reward_functions"
    reward_funcs = {
        "lunar" :          Path("lunar.py"),
        "sideways_slide" : Path("sideways_slide.py"),
        "spin_crash":      Path("spin_crash.py"),
        "vertical_bounce": Path("vertical_bounce.py"),
        "weird_reward":    Path("weird_reward.py"),
        "wild_oscillation":Path("wild_oscillation.py")
    }
    if reward_func not in reward_funcs.keys():
        print(f"{reward_func} is not recognized as a function for initialization")
        print(f"Please try again using one of the following options {reward_funcs.keys()}")
        return sys.exit(1)

    code_load_path = base_load_path /reward_funcs[reward_func]
    payload_load_path = base_load_path / f"{reward_func}_iter00_payload.json"

    # Path to save code and metric payload
    code_save_path = ws.get_path("code", 0, "reward.py")
    payload_save_path= ws.get_path("telemetry_payloads", 0, "payload.json")

    # Copy to current experiment directory
    shutil.copy(code_load_path, code_save_path)
    shutil.copy(payload_load_path, payload_save_path)

    print(f"Initial shaping script loaded from: {code_load_path}\nSaved to: {code_save_path}")
    print(f"Initial metric payload loaded from: {payload_load_path}\nSaved to: {payload_save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reward', type=str, default="spin_crash")
    args = parser.parse_args()
    set_inital_shaping(args.reward)