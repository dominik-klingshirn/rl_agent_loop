
import re
import json
from typing import Optional
import difflib
import torch
import platform
import importlib.util
import sys
import glob
import numpy as np
import gymnasium as gym
from stable_baselines3.common.monitor import Monitor
from typing import Tuple
import pandas as pd
from textwrap import indent
import numpy as np


# -- Custom IMPORTS --
from src.wrappers import DynamicRewardWrapper
from src.config import Config

# ---------------------------------------------------------
# FILE OPERATIONS
# ---------------------------------------------------------
def load_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def extract_python_code(llm_response):
    """Extracts code block from markdown response."""
    match = re.search(r'```python(.*?)```', llm_response, re.DOTALL)
    if match: return match.group(1).strip()
    match = re.search(r'```(.*?)```', llm_response, re.DOTALL)
    if match: return match.group(1).strip()
    return llm_response

def extract_work_order(text:str):
    coder_payload = text.split("<CODER_PAYLOAD>")[1].split("</CODER_PAYLOAD>")[0]
    val_payload = text.split("<VALIDATOR_PAYLOAD>")[1].split("</VALIDATOR_PAYLOAD>")[0]
    return coder_payload, val_payload

def extract_json(llm_response):
    """
    Robustly extracts JSON from an LLM response, handling markdown fences and stray text.
    """
    import json
    import re
    
    # 1. Try finding a markdown block first
    match = re.search(r'```json(.*?)```', llm_response, re.DOTALL)
    if match:
        clean_str = match.group(1).strip()
    else:
        # 2. If no block, try to find the first '{' and last '}'
        start = llm_response.find('{')
        end = llm_response.rfind('}')
        if start != -1 and end != -1:
            clean_str = llm_response[start:end+1]
        else:
            clean_str = llm_response.strip()

    # 3. Validation / Parsing
    try:
        return json.loads(clean_str)
    except json.JSONDecodeError:
        # Optional: Print preview for debugging, but keeping logs clean
        # print(f"⚠️ JSON Parsing Failed. Content preview: {clean_str[:50]}...")
        return None
    
def load_dynamic_module(module_name, file_path):
    """
    Loads a python file from a specific path as a module.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module 
        spec.loader.exec_module(module)
        return module
    raise ImportError(f"Could not load module {module_name} from {file_path}")


# ---------------------------------------------------------
# ENVIRONMENT
# ---------------------------------------------------------
def make_env(reward_code_path:str | None = None):
    env = gym.make(Config.ENV_ID)
    env = DynamicRewardWrapper(env, reward_code_path=reward_code_path) 
    return Monitor(env)
# ---------------------------------------------------------
# SCIENTIFIC LOGGING & ANALYSIS
# ---------------------------------------------------------

# ==============================================================================
# Testing new summarizing training log functions
# ==============================================================================


def compute_trend_consistency(values: np.ndarray) -> str:
    """Characterize trend pattern with semantic tags."""
    if len(values) < 3:
        return "insufficient_data"
    
    diffs = np.diff(values)
    
    # Check for strict monotonicity
    if np.all(diffs >= 0):
        return "monotonic_increasing"        
    elif np.all(diffs <= 0):
        return "monotonic_decreasing"       
    
    # Check for volatility
    sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
    volatility_ratio = sign_changes / len(diffs)
    net_sign_change = np.sum(np.sign(diffs))

    if volatility_ratio > 0.4:
        return "noisy"
    elif volatility_ratio > 0.2:
        return "oscillating"
    elif net_sign_change > 0: 
        return "mostly_monotonic_increasing"        
    else:
        return "mostly_monotonic_decreasing"    


# ==============================================================================
# ==============================================================================
def generate_patch(old_code: str, new_code: str, filename: str) -> str:
    """Compares two source strings and returns a Unified Diff."""
    diff = difflib.unified_diff(
        old_code.splitlines(keepends=True), 
        new_code.splitlines(keepends=True), 
        fromfile=f"prev/{filename}", 
        tofile=f"new/{filename}",
        lineterm=""
    )
    return "".join(diff)

def save_diff(old_code, new_code, iteration, attempt, base_dir):
    """Saves a delta patch between attempts to track debugging logic."""
    filename = f"iter{iteration:02d}_attempt_{attempt:02d}.patch"
    filepath = base_dir / filename
    
    diff = difflib.unified_diff(
        old_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        fromfile=f"Code Gen. Attempt {attempt-1}",
        tofile=f"Code Gen. Attempt {attempt}",
        lineterm=""
    )
    
    text = "".join(diff)
    if text:
        with open(filepath, "w") as f:
            f.write(text)
    return filepath
# ---------------------------------------------------------
# HARDWARE
# ---------------------------------------------------------
def get_parallel_training_config():
    """
    Detect the host machine and return (concurrency, ccx_groups, threads_per_run)
    for parallel seed dispatch.

    Fallback chain (each level returns safe sequential config):
      1. Non-Linux platforms (macOS, Windows) → no CCX topology accessible
      2. /sys cache topology unreadable → detection failure
      3. Single CCX detected → concurrency offers no locality benefit

    On a multi-CCX Linux box, returns concurrency = min(ccx_count, 4) with the
    per-CCX cpu_list strings ready for `taskset -c`.

    Returns:
        concurrency (int): how many seeds to run in parallel per batch
        ccx_groups (list[str]): cpu_list strings per CCX (empty list = no pinning)
        threads_per_run (int): torch + OMP/MKL/OPENBLAS/NUMEXPR thread cap
    """
    import os
    threads_per_run = min(4, os.cpu_count() or 1)

    if sys.platform != "linux":
        return 1, [], threads_per_run

    try:
        seen = {}
        for path in sorted(glob.glob(
                "/sys/devices/system/cpu/cpu[0-9]*/cache/index3/shared_cpu_list")):
            s = open(path).read().strip()
            key = tuple(sorted(
                int(x) for part in s.split(",")
                for x in ([part] if "-" not in part else
                          [str(i) for i in range(int(part.split("-")[0]),
                                                  int(part.split("-")[1]) + 1)])
            ))
            if key not in seen:
                seen[key] = s
        ccx_groups = list(seen.values())
    except Exception:
        return 1, [], threads_per_run

    if len(ccx_groups) < 2:
        return 1, [], threads_per_run

    concurrency = min(len(ccx_groups), 4)
    return concurrency, ccx_groups, threads_per_run

def get_optimized_ppo_params(n_envs, device_type="auto"):
    TARGET_BUFFER_SIZE = 8192 
    TARGET_NUM_MINIBATCHES = 4 
    n_steps = max(int(TARGET_BUFFER_SIZE // n_envs), 16)
    actual_buffer_size = n_steps * n_envs
    batch_size = int(actual_buffer_size // TARGET_NUM_MINIBATCHES)
    
    if device_type == "auto":
        if torch.cuda.is_available(): device = "cuda"
        elif torch.backends.mps.is_available(): device = "mps"
        else: device = "cpu"
    else:
        device = device_type

    return {"n_steps": n_steps, "batch_size": batch_size, "device": device}

def get_hardware_config(system:Optional[str]|None = None):
    if not system:
        system = platform.system()
    if system == "Linux": return 16, "cpu" #"cuda"
    elif system == "Darwin": return 8, "cpu" #"mps"
    return 4, "cpu"

