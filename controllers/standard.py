import argparse
import warnings
import time
from datetime import datetime, timedelta 
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

# -- PROJECT IMPORTS --
from src.workspace_manager import ExperimentWorkspace
from src.ledger import ExperimentLedger
from src.cognitive_node import CognitiveNode
from src.config import Config
from src import utils
from src.analysis import generate_diagnostic_report
from src.pipeline_nodes import (
    generate_proposals,
    organize_proposals,
    choose_proposal,
    generate_work_order,
    generate_code,
    generate_ledger_entry
)

MODEL_NAME = Config.LLM_MODEL

"""if MODEL_NAME == 'qwen3:8b':
    model_overrides = {
        "research_lead":"deepseek-r1:8b",
        "organizer": "deepseek-r1:8b",
        "dispatcher":"deepseek-r1:8b",
        "validator":"deepseek-r1:8b",
        "coder": "qwen3-coder:30b"
    }"""
"""
if MODEL_NAME == 'gemma3:27b':
    model_overrides = {
        "research_lead":"qwen3:30b",
        "organizer": "deepseek-r1:14b",
        "dispatcher":"deepseek-r1:14b",
        "validator":"deepseek-r1:14b",
        "coder": "qwen3-coder:30b"
    }"""



model_overrides = {
        "research_lead":"deepseek-r1:32b",
        "organizer": "deepseek-r1:14b",
        "dispatcher":"deepseek-r1:14b",
        "validator":"deepseek-r1:14b",
        "coder": "qwen3-coder:30b"
    }

def run_agentic_improvement(iteration: int):
    start_time = time.perf_counter()
    
    # =========================================================
    # 1. INITIALIZATION & STATE LOADING
    # =========================================================
    ws = ExperimentWorkspace(iteration)
    brain = CognitiveNode(iteration=iteration, workspace=ws, model=MODEL_NAME)
    ledger = ExperimentLedger(ws.model_root_path) 
    # Setting any model overrides for a MOE style run 
    val_override = model_overrides.get("validator",None)
    strat_override = model_overrides.get("strategist",None)
    organ_override = model_overrides.get("organizer",None)
    lead_override = model_overrides.get("research_lead",None)
    dispatcher_override = model_overrides.get("dispatcher",None)
    coder_override = model_overrides.get("coder",None)


    print(f"🔵 AGENT (Iter {iteration}): Active in {ws.model_root_path}")

    # Load Metrics from the recent training run
    metrics = ws.load_metrics(iteration-1)
    if not metrics:
        print(f"❌ No metrics found for Iteration {iteration-1}. Cannot proceed.")
        return
    print(f"    Iteration {iteration-1} Metrics Loaded ")
    diagnostic_report = generate_diagnostic_report(metrics) 

    # Load the code that generated these metrics
    prev_code_path = ws.get_path("code", iteration - 1, "reward.py")
    with open(prev_code_path, "r") as f:
        current_code = f.read()

    # =========================================================
    # PHASE 1: HYPOTHESIS VALIDATION (The Causal Check)
    # =========================================================
    # Validating the N-1 hypothesis using the N empirical metrics
    if iteration > 1:
        print(f"🔍 Validating Hypothesis from Experiment {iteration - 1}")
        val_payload = ledger.get_hypothesis(iteration - 1)

        ledger_entry = generate_ledger_entry(
            brain=brain, 
            iteration=iteration, 
            val_payload=val_payload, 
            diagnostic_report=diagnostic_report,
            model_override = val_override if val_override else MODEL_NAME
        )
        
        # Lock the post-mortem into the historical record
        ledger.log_validation(iteration - 1, ledger_entry)
    else:
        print(f"ℹ️ Iteration {iteration}: No history in Ledger to validate.")

    # Extract historical context for the reasoning nodes
    ledger_context = ledger.get_context_for_llm(limit=10)

    # =========================================================
    # PHASE 2: RESEARCH & DECISION PIPELINE
    # =========================================================
    print("🧠 Initiating Cognitive Pipeline")

    raw_proposals = generate_proposals(
        brain=brain, 
        iteration=iteration, 
        diagnostic_report=diagnostic_report, 
        current_code=current_code,
        expt_ledger=ledger_context,
        model_override = strat_override if strat_override else MODEL_NAME
    )
    
    proposal_report = organize_proposals(
        brain=brain, 
        proposals=raw_proposals,
        model_override = organ_override if organ_override else MODEL_NAME
    )
    
    chosen_proposal = choose_proposal(
        brain=brain, 
        iteration=iteration,
        proposal_report=proposal_report, 
        expt_ledger=ledger_context,
        model_override = lead_override if lead_override else MODEL_NAME
    )
    
    work_order = generate_work_order(
        brain=brain, 
        chosen_proposal=chosen_proposal,
        model_override = dispatcher_override if dispatcher_override else MODEL_NAME
    )

    # Extract directives for Coder, and the falsifible parameters for the Validator
    coder_payload, val_payload = utils.extract_work_order(work_order)
    
    # =========================================================
    # PHASE 3: LOG INTENT (Open New Experiment)
    # =========================================================
    print(f"📓 Logging Hypothesis for Iteration {iteration}")
    ledger.log_hypothesis(iteration=iteration, validator_payload=val_payload)

    # =========================================================
    # PHASE 4: IMPLEMENTATION (WITH SAFETY NET)
    # =========================================================
    print("💻 Passing to Coder Agent")
    
    # We rely on CodeValidator inside generate_code to catch syntax/signature bugs
    new_code = generate_code(
        brain=brain, 
        coder_payload=coder_payload, 
        current_code=current_code,
        max_retries=5,
        model_override = coder_override if coder_override else MODEL_NAME 
    )

    # =========================================================
    # FINAL SAVE & ARTIFACT GENERATION
    # =========================================================
    save_path = ws.get_path("code", iteration, "reward.py")
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Ensure generated code has necessary imports for standard matrix ops / math
    final_content = f"# Generated by {MODEL_NAME} (Iter {iteration}) on {timestamp_str}\n"
    if "import numpy" not in new_code: final_content += "import numpy as np\n"
    if "import math" not in new_code: final_content += "import math\n"
    final_content += new_code

    with open(save_path, "w") as f:
        f.write(final_content)
        
    print(f"✅ Code saved to {save_path}")

    # Save the Diff vs Previous Iteration to track trajectory of the reward surface
    patch_path = ws.get_path("code", iteration, "changes.patch")
    with open(patch_path, "w") as f:
        f.write(utils.generate_patch(current_code, final_content, "reward.py"))

    # Persist traces for offline analysis
    brain.save_report()
    
    elapsed_time = time.perf_counter() - start_time
    print(f"Execution took: {timedelta(seconds=elapsed_time)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", type=int, required=True)
    args = parser.parse_args()
    
    run_agentic_improvement(args.iteration)