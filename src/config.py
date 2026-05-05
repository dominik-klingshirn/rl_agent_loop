import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()

class Config:
    # 1. Experiment Settings ###################################################################
    ENV_ID = "LunarLander-v3"
    TOTAL_TIMESTEPS = int(os.getenv("TOTAL_TIMESTEPS", 1000000))
    TOTAL_ITERATIONS = int(os.getenv("TOTAL_ITERATIONS", 10))
    ALGORITHM = "PPO"
    
    # 2. Dynamic Experiment Directory Name ####################################################
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder")
    CAMPAIGN_TAG = os.getenv("CAMPAIGN_TAG", "Debug_Run")
    INITIAL_FUNC=os.getenv("INITIAL_FUNC", "spin_crash")
    
    # 3. LLM Prompt Templates ###################################################################
    strategist_role = "strategist_system_prompt"
    strategist_task = "strategist_user_prompt"
    strategist_template = (strategist_role,strategist_task)

    organizer_role = "organizer_system_prompt"
    organizer_task = "organizer_user_prompt"
    organizer_template = (organizer_role,organizer_task)

    lead_role = "lead_system_prompt"
    lead_task = "lead_user_prompt"
    lead_template = (lead_role,lead_task)

    dispatcher_role = "dispatcher_system_prompt"
    dispatcher_task = "dispatcher_user_prompt"
    dispatcher_template = (dispatcher_role,dispatcher_task)

    coder_role = "coder_system_prompt"
    coder_task = "coder_user_prompt"
    coder_template = (coder_role,coder_task)

    validator_role = "validator_system_prompt"
    validator_task = "validator_user_prompt"
    validator_template = (validator_role,validator_task)


    # 4. Code Generation Settings ###############################################################
    # Standard/Non-thinking Models Options
    standard_options={                       
        "temperature": 0.85,       
        "repeat_penalty": 1.1,     
        "num_predict": 8192,
        "num_ctx": 16384
    }

    # Thinking- Model Options
    think_options={
        "temperature": 0.7,        
        "top_p": 0.95,             
        "repeat_penalty": 1.0,     
        "num_predict": 8192,       
        "num_ctx": 16384
        }
    # gpt_oss has 3 thinking levels : low, medium, high
    gpt_think_level = "low"


    def get_inference_options(model_name: str, role: str):
        """
        Returns optimal inference parameters based on Model Architecture AND Cognitive Role.
        Target Hardware: Mac Studio/Pro M4 Max (36GB Unified Memory), fully local via Ollama.

        Pipeline Roles (6-stage Chain-of-Agents):
            - validator:     Critical post-mortem analysis against diagnostic report
            - strategist:    Divergent mathematical hypothesis generation
            - organizer:     Strict deterministic format enforcement
            - research_lead: Convergent executive selection via Occam's Razor
            - dispatcher:    Deterministic payload routing/splitting (no creativity)
            - coder:         Precise Python syntax translation from math spec

        Context Sizing Philosophy:
            Each role receives only the data it needs (zero-shot, structured prompts).
            This is what prevents KV cache accumulation across the 20-iteration loop.
            Organizer and Dispatcher get the smallest windows because their inputs
            are already the cleaned outputs of the prior stage.

        Notes on Reasoning Models (DeepSeek-R1, etc.):
            - Never set repeat_penalty > 1.0: breaks Chain-of-Thought loops
            - Never drop Coder temp below 0.5: causes stuttering/token repetition
            - Organizer/Dispatcher on reasoning models is wasteful but supported
        """
        model_id = model_name.lower()
        role = role.lower()

        is_reasoning = any(k in model_id for k in ["deepseek-r1", "thinking", "openthinker", "gpt-oss"])

        # Shared baseline — overridden per role below
        options = {
            "num_ctx": 16384,
            "num_predict": 4096,
            "stop": ["<|end_of_text|>", "<|user|>", "User:", "Observation:"]
        }

        # ==============================================================================
        # SCENARIO A: THINKING / REASONING MODELS (DeepSeek-R1, etc.)
        # Global constraint: repeat_penalty must stay at 1.0 to preserve CoT integrity.
        # ==============================================================================
        if is_reasoning:
            options.update({
                "repeat_penalty": 1.0,  # CRITICAL: Do not touch — breaks CoT loops
                "top_k": 40,
            })

            if role == "validator":
                # Goal: Detect Goodhart's Law and reward hacking against a prior hypothesis.
                # Needs reliable pattern-matching, not creative divergence.
                # Context: Diagnostic Report + 1 ledger entry (targeted, not full history).
                # Low temp keeps the post-mortem grounded; slight top_p room for nuanced language.
                options["temperature"] = 0.5
                options["top_p"] = 0.9
                options["num_ctx"] = 16384
                options["num_predict"] = 4096   # Post-mortem is an essay, not a treatise

            elif role == "strategist":
                # Goal: Generate 3 mathematically DISTINCT reward topologies.
                # Must escape prior failure modes logged in the full Experiment Ledger.
                # Highest entropy in the pipeline — needs to diverge from its own history.
                # Context: Full ledger + diagnostic report = largest window justified.
                options["temperature"] = 1.0
                options["top_p"] = 0.95
                options["top_k"]=64
                options["num_ctx"] = 24576      # Max safe for 36GB — ledger grows over iterations
                options["num_predict"] = 8192   # 3 detailed mathematical proposals with rationale

            elif role == "organizer":
                # Goal: Reformat the Strategist's output into a strict, machine-parseable schema.
                # Zero creativity required — this is pure structural enforcement.
                # Context: Just the Strategist's output (smallest meaningful window).
                # Lower temp than any other role to prevent schema drift.
                options["temperature"] = 0.4
                options["top_p"] = 0.85
                options["num_ctx"] = 12288      # Strategist output only — no history needed
                options["num_predict"] = 8192   # Bounded by the schema structure itself

            elif role == "research_lead":
                # Goal: Apply Occam's Razor and select the single most viable hypothesis.
                # Convergent reasoning — must commit to one choice, not hedge.
                # Context: Organized proposals + ledger (to avoid repeating prior failures).
                options["temperature"] = 0.55
                options["top_p"] = 0.9
                options["num_ctx"] = 20480      # Proposals + relevant ledger context
                options["num_predict"] = 2048   # Selection + rationale, not a full essay

            elif role == "dispatcher":
                # Goal: Split the selected hypothesis into <CODER_PAYLOAD> and <VALIDATOR_PAYLOAD>.
                # Pure deterministic routing — output is a strict schema split, not generation.
                # Context: Just the Research Lead's single selected output.
                options["temperature"] = 0.4
                options["top_p"] = 0.85
                options["num_ctx"] = 8192       # Single hypothesis only — smallest window
                options["num_predict"] = 2048   # Two structured payload blocks, nothing more

            elif role == "coder":
                # Goal: Translate a mathematical spec into a valid Python reward function.
                # WARNING: Do not drop below 0.5 for R1 models — causes token stutter.
                # The model's internal verification handles correctness; we handle fluency.
                # Context: CODER_PAYLOAD only (math spec, no reasoning history).
                options["temperature"] = 0.55
                options["top_p"] = 0.9
                options["num_ctx"] = 16384      # Payload + room for full function output
                options["num_predict"] = 10000  # Max — complex reward functions can be long

        # ==============================================================================
        # SCENARIO B: STANDARD MODELS (Llama 3, Mistral, Command R, etc.)
        # "Cognitive Thermodynamics" — Temperature and penalties as direct control levers.
        # Seed is set on deterministic roles to lock reproducibility within an iteration.
        # ==============================================================================
        else:
            options.update({
                "num_predict": 4096,
            })

            if role == "validator":
                # Goal: Reliable, repeatable detection of reward hacking.
                # Deterministic enough to produce consistent post-mortems across re-runs.
                options["temperature"] = 0.2
                options["top_p"] = 0.9
                options["top_k"] = 40
                options["repeat_penalty"] = 1.05
                options["num_ctx"] = 16384
                options["num_predict"] = 4096
                options["seed"] = 42

            elif role == "strategist":
                # Goal: Maximally diverse mathematical proposals.
                # presence_penalty forces topical escape — prevents rehashing prior iterations.
                # No seed — we explicitly want variance here.
                options["temperature"] = 0.8
                options["top_p"] = 0.95
                options["top_k"] = 60
                options["repeat_penalty"] = 1.1
                options["presence_penalty"] = 0.3  # Forces mathematical novelty
                options["num_ctx"] = 24576
                options["num_predict"] = 8192

            elif role == "organizer":
                # Goal: Rigid schema enforcement. Effectively a deterministic formatter.
                # Lowest temperature in the pipeline outside of Dispatcher.
                # High repeat_penalty prevents schema elements from leaking into content fields.
                options["temperature"] = 0.05
                options["top_p"] = 0.8
                options["top_k"] = 20
                options["repeat_penalty"] = 1.1
                options["num_ctx"] = 12288
                options["num_predict"] = 4096
                options["seed"] = 42

            elif role == "research_lead":
                # Goal: Rational, reproducible selection. Balanced against creative lock-in.
                # Slightly warmer than Organizer to allow natural justification language.
                options["temperature"] = 0.25
                options["top_p"] = 0.9
                options["top_k"] = 40
                options["repeat_penalty"] = 1.05
                options["num_ctx"] = 20480
                options["num_predict"] = 2048
                options["seed"] = 42

            elif role == "dispatcher":
                # Goal: Clean deterministic payload split. Output is two labeled blocks.
                # Near-greedy — this is a parsing task, not a generation task.
                options["temperature"] = 0.05
                options["top_p"] = 0.8
                options["top_k"] = 20
                options["repeat_penalty"] = 1.05
                options["num_ctx"] = 8192
                options["num_predict"] = 2048
                options["seed"] = 42

            elif role == "coder":
                # Goal: Deterministic Python translation from math spec.
                # Greedy decoding — correctness is the only objective here.
                # Low repeat_penalty (not zero) prevents line-duplication bugs in loops/dicts.
                options["temperature"] = 0.1
                options["top_p"] = 0.85
                options["top_k"] = 30
                options["repeat_penalty"] = 1.02
                options["num_ctx"] = 16384
                options["num_predict"] = 10000
                options["seed"] = 42

        return options

    # 5. Network Credentials ################################################
    # Saved in .env, raw IPs never see github

    # NETWORK CONFIGURATION
    LINUX_IP = os.getenv("LINUX_IP", "127.0.0.1")
    LINUX_USER = os.getenv("LINUX_USER", "user")
    ssh_env = os.getenv("SSH_KEY_PATH", "") 
    SSH_KEY_PATH = os.path.expanduser(ssh_env)
    REMOTE_PROJECT_ROOT = os.getenv("REMOTE_PROJECT_ROOT", "")
    REMOTE_PYTHON_BIN = os.getenv("REMOTE_PYTHON_BIN", "")

    # Validation (Optional but recommended)
    @classmethod
    def validate_network_config(cls):
        if not cls.REMOTE_PROJECT_ROOT or not cls.REMOTE_PYTHON_BIN:
            raise ValueError("❌ Missing Remote Configs! Please set REMOTE_PROJECT_ROOT in your .env file.")