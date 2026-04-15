import time
import re
from datetime import datetime, timedelta 
import warnings
import shutil
from pathlib import Path
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

# -- PROJECT IMPORTS --
import prompts  
from src.workspace_manager import ExperimentWorkspace
from src.code_validation import CodeValidator
from src.ledger import ExperimentLedger
from src.config import Config
from src.cognitive_node import CognitiveNode
from src.utils import extract_python_code

MODEL_NAME = "gpt-oss:20b"
#MODEL_NAME = Config.LLM_MODEL


def set_inital_shaping(reward_func:str='spin_crash'):

    # Initialize Workspace & Ledger for Iteration 0
    ws = ExperimentWorkspace(iteration=0)
    # Grab where to save function to be used for training 
    save_path = ws.get_path("code", 0, "reward.py")
    # Grab the curated faulty reward function
    base_load_path = Path("/Users/dominikklingshirn/Projects/RL-Lab/rl_agent_loop/curated_reward_functions")
    reward_funcs = {
        "lunar" :          Path("lunar.py"),
        "sideways_slide" : Path("sideways_slide.py"),
        "spin_crash":      Path("spin_crash.py"),
        "vertical_bounce": Path("vertical_bounce.py"),
        "weird_reward":    Path("weird_reward.py"),
        "wild_oscillation":Path("wild_oscillation.py")
    }
    load_path = base_load_path /reward_funcs[reward_func]
    
    shutil.copy(load_path,save_path)
    print(f"Initial shaping loaded from: {load_path}\nSaved to: {save_path}")

if __name__ == "__main__":
    set_inital_shaping()