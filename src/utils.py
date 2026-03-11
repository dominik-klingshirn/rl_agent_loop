
import re
import json
import difflib
import torch
import platform
import importlib.util
import sys
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
# Testing out new training data formating function that goes with new summarize_training_log()
# ==============================================================================
def format_diagnostician_input(training_summary: dict) -> str:
    """
    Format training summary into structured markdown for diagnostician prompt.
    
    Args:
        training_summary: Output from summarize_training_log()
    
    Returns:
        Formatted markdown string with:
        - Raw metrics table
        - Relational features
        - Coupling indicators
        - Trend patterns
    """
    
    # ========================================================================
    # SECTION 1: Raw Metrics Table
    # ========================================================================
    
    metric_order = [
        'policy_gradient_loss',
        'approx_kl',
        'loss',
        'explained_variance',
        'entropy_loss',
        'value_loss',
        'clip_fraction'
    ]
    
    table_lines = [
        "## Training Metrics Table",
        "",
        "| metric | first_third_mean | middle_third_mean | final_third_mean | overall_median |",
        "|--------|------------------|-------------------|------------------|----------------|"
    ]
    
    for metric in metric_order:
        if metric in training_summary:
            data = training_summary[metric]
            line = (
                f"| {metric} | "
                f"{data['first_third_mean']} | "
                f"{data['middle_third_mean']} | "
                f"{data['final_third_mean']} | "
                f"{data['overall_median']} |"
            )
            table_lines.append(line)
    
    raw_table = "\n".join(table_lines)
    
    # ========================================================================
    # SECTION 2: Relational Features
    # ========================================================================
    
    relational = training_summary.get("_relational", {})
    
    relational_section = [
        "",
        "## Derived Features",
        "",
        "### Relational Features (Scale-Invariant)",
        ""
    ]
    
    relational_items = [
        ("EV improvement factor", relational.get("ev_improvement_factor", "N/A")),
        ("Value loss reduction factor", relational.get("value_loss_reduction_factor", "N/A")),
        ("Entropy decay rate", relational.get("entropy_decay_rate", "N/A")),
        ("Critic vs policy learning ratio", relational.get("critic_vs_policy_learning_ratio", "N/A")),
        ("KL coefficient of variation", relational.get("kl_coefficient_of_variation", "N/A")),
        ("EV coefficient of variation", relational.get("ev_coefficient_of_variation", "N/A"))
    ]
    
    for label, value in relational_items:
        relational_section.append(f"- **{label}**: {value}")
    
    relational_text = "\n".join(relational_section)
    
    # ========================================================================
    # SECTION 3: Coupling Indicators
    # ========================================================================
    
    coupling = training_summary.get("_coupling", {})
    
    coupling_section = [
        "",
        "### Coupling Indicators (Diagnostic Patterns)",
        ""
    ]
    
    coupling_items = [
        ("Updates conservative", coupling.get("updates_conservative", False)),
        ("Updates aggressive", coupling.get("updates_aggressive", False)),
        ("Late phase EV breakthrough", coupling.get("late_phase_ev_breakthrough", False)),
        ("Early phase EV plateau", coupling.get("early_phase_ev_plateau", False)),
        ("Critic bottleneck", coupling.get("critic_bottleneck", False)),
        ("Weak gradients despite good critic", coupling.get("weak_gradients_despite_good_critic", False)),
        ("Premature convergence", coupling.get("premature_convergence", False)),
        ("Maintained exploration", coupling.get("maintained_exploration", False))
    ]
    
    for label, value in coupling_items:
        status = "✓ **TRUE**" if value else "✗ false"
        coupling_section.append(f"- {label}: {status}")
    
    coupling_text = "\n".join(coupling_section)
    
    # ========================================================================
    # SECTION 4: Trend Patterns
    # ========================================================================
    
    trends = training_summary.get("_trends", {})
    
    trends_section = [
        "",
        "### Trend Patterns (Stability Analysis)",
        ""
    ]
    
    trend_items = [
        ("Explained variance", trends.get("explained_variance_pattern", "unknown")),
        ("Value loss", trends.get("value_loss_pattern", "unknown")),
        ("Approx KL", trends.get("approx_kl_pattern", "unknown")),
        ("Entropy", trends.get("entropy_pattern", "unknown"))
    ]
    
    for label, pattern in trend_items:
        trends_section.append(f"- **{label}**: `{pattern}`")
    
    trends_text = "\n".join(trends_section)
    
    # ========================================================================
    # SECTION 5: Metadata (Optional Context)
    # ========================================================================
    
    metadata = training_summary.get("_metadata", {})
    
    metadata_section = [
        "",
        "### Training Context",
        "",
        f"- **Total updates**: {metadata.get('n_updates', 'N/A')}",
        f"- **Total steps logged**: {metadata.get('n_steps', 'N/A')}",
        f"- **Steps per phase**: First={metadata.get('first_third_steps', 'N/A')}, "
        f"Middle={metadata.get('middle_third_steps', 'N/A')}, "
        f"Final={metadata.get('final_third_steps', 'N/A')}",
        ""
    ]
    
    metadata_text = "\n".join(metadata_section)
    
    # ========================================================================
    # COMBINE ALL SECTIONS
    # ========================================================================
    
    full_output = "\n".join([
        raw_table,
        relational_text,
        coupling_text,
        trends_text,
        metadata_text
    ])
    
    return full_output
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
# Agent's Hyperparameters
# ---------------------------------------------------------
def linear_schedule(initial_value: float, final_value: float):
    """
    Linear learning rate schedule.
    :param initial_value: Starting learning rate.
    :param final_value: Ending learning rate.
    :return: schedule that computes current lr based on remaining progress
    """
    def func(progress_remaining: float) -> float:
        """
        Progress will decrease from 1 (beginning) to 0 (end).
        """
        lr = final_value + (initial_value - final_value) * progress_remaining
        #print(f"Progress: {progress_remaining:.3f} → LR: {lr:.6f}")
        return lr

    return func

# Usage: Decay from 0.001 to 0.0001
# set when initializing the RL model:
# lr_schedule = linear_schedule(1e-3, 1e-4)

# ---------------------------------------------------------
# HARDWARE
# ---------------------------------------------------------
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

def get_hardware_config():
    system = platform.system()
    if system == "Linux": return 32, "cpu" #"cuda"
    elif system == "Darwin": return 8, "cpu" #"mps"
    return 4, "cpu"

# -----------------------------------------------------------
# Translation Layer
# Functions Focused on translating information into LLM-friendly formatting/wording
# ------------------------------------------------------------
def performance_telemetry_as_table(stats_list: list[dict]) -> str:
    """
    Converts the list of performance dicts into a Markdown table for better LLM reasoning.
    """
    if not stats_list:
        return "No telemetry data available."

    # To guaruntee the correct order of dicts, so metric values are in correct column
    for stats_dict in stats_list:
        if stats_dict["policy_behavior"] == "Deterministic":
            if stats_dict["reward_shape"] == "Base":
                det_base_stats = stats_dict
            else:
                det_shaped_stats = stats_dict
        else:
            if stats_dict["reward_shape"] == "Base":
                stoch_base_stats = stats_dict
            else:
                stoch_shaped_stats = stats_dict


    # Define the columns we want to compare
    headers = [
        "metric",
        f"Stochastic/Shaped Reward",
        f"Deterministic/Base Reward"
    ]
    
    # Create the header row
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]

    key_list = [
        "mean_reward",
        "median_reward",
        "std_reward",
        "mean_ep_length",
        "reward_success_rate",
        "position_success_rate",
        "crash_rate",
        "avg_x_position",
        "avg_descent_velocity",
        "avg_tilt_angle",
        "vertical_stability_index",
        "horizontal_stability_index"
        ]
    for key in key_list:
        # Pre-calculate/format values to reduce token noise
        row = [
            key,
            f"{stoch_shaped_stats[key]}",
            f"{det_base_stats[key]}"
        ]
        table.append("| " + " | ".join(row) + " |")

    return "\n".join(table)

def training_telemetry_as_table(stats_list: list[dict]) -> str:
    """
    Converts the list of performance dicts into a Markdown table for better LLM reasoning.
    """
    if not stats_list:
        return "No telemetry data available."

     
    # Define the columns we want to compare
    headers = [
        "metric", "start","end","median","mean",
    ]
    
    # Create the header row
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]

    key_list = [
        "policy_gradient_loss",
        "approx_kl",
        "loss",
        "explained_variance",
        "entropy_loss",
        "value_loss",
        "clip_fraction"
        ]
    for key in key_list:
        # LLMs trained a vast amount of data related to loss curves, this specific 
        # implementation of where stablebaselines3 defined entropy_loss as the negative
        # of entropy confuses LLMs when diagnosing training optimization metrics
        if key == "entropy_loss":
            stats_list['entropy'] = {k: -v for k, v in stats_list["entropy_loss"].items()}
            key = "entropy" # Rename for LLM clarity

        row = [
            key,
            f"{stats_list[key]["start"]}",
            f"{stats_list[key]["end"]}",
            f"{stats_list[key]["median"]}",
            f"{stats_list[key]["mean"]}"
        ]
        table.append("| " + " | ".join(row) + " |")

    return "\n".join(table)

# --- 2. The Spatial Context Translator ---
def tag_spatial_approach(trend_string: str) -> str:
    """Translates generic math trends into physical spatial semantics."""
    mapping = {
        "monotonic_increasing": "fleeing_target",
        "mostly_monotonic_increasing": "mostly_fleeing",
        "monotonic_decreasing": "direct_approach",
        "mostly_monotonic_decreasing": "mostly_approaching",
        "oscillating": "oscillating_around_target",
        "noisy": "noisy_thrashing",
        "insufficient_data": "insufficient_data"
    }
    return mapping.get(trend_string, "unknown_pattern")

# --- 3. The Learning Curve Context Translator ---
def tag_learning_curve(trend_string: str) -> str:
    """Translates generic math trends into RL training semantics."""
    mapping = {
        "monotonic_increasing": "consistent_improvement",
        "mostly_monotonic_increasing": "gradual_improvement",
        "monotonic_decreasing": "catastrophic_forgetting",
        "mostly_monotonic_decreasing": "performance_degradation",
        "oscillating": "unstable_learning",
        "noisy": "random_noise",
        "insufficient_data": "insufficient_data"
    }
    return mapping.get(trend_string, "unknown_pattern")