import argparse
import os
import sys
from pathlib import Path


# -- project imports --
from src.remote_ops import RemoteManager
from src.config import Config
from src.workspace_manager import ExperimentWorkspace

def remote_campaign_summary():

    # Setup Manager
    manager = RemoteManager(
        Config.LINUX_IP, 
        Config.LINUX_USER, 
        Config.SSH_KEY_PATH, 
        Config.REMOTE_PROJECT_ROOT
    )

    print(f"🔬 Generating Campaign Summary Plot")
    # Grab neccesary environment variables
    env_vars = {
        "CAMPAIGN_TAG":     Config.CAMPAIGN_TAG,
        "LLM_MODEL":        Config.LLM_MODEL,
        "TOTAL_ITERATIONS": Config.TOTAL_ITERATIONS
    }

    # Build a sequential command chain using '&&'
    # If any step fails, the chain stops immediately.
    remote_commands = []

    # Plotting summary capaign on LINUX BOX
    remote_commands.append(f"PYTHONPATH={Config.REMOTE_PROJECT_ROOT} {Config.REMOTE_PYTHON_BIN} -u -m src.plot_campaign_summary")
    
    # If you want to run multiple visualizations/post-hoc evaluations
    # Append additional commands to remote_commands above
    compound_cmd = " && ".join(remote_commands)

    success = manager.stream_command(compound_cmd, env_vars=env_vars)
    
    if not success:
        print("❌ Critical Failure: Plotting Campaign Summary Failed.") 
        sys.exit(1)

    model_name = Config.LLM_MODEL.replace(":", "-")
    plot_file = Path(f"experiments/{env_vars['CAMPAIGN_TAG']}/{model_name}/all_iterations_{model_name}.png")
    print(f"📥 Downloading Campaign Summary Plot: {plot_file}")

    plot_file.parent.mkdir(parents=True, exist_ok=True)

    success = manager.retrieve_file(str(plot_file), str(plot_file))
    if not success:
        print("❌ Failed to retrieve campaign summary plot.")
        sys.exit(1)

if __name__ == "__main__":
    remote_campaign_summary()