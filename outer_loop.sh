#!/usr/bin/env bash
set -euo pipefail
# Colors for Console 
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Define the contenders (typically for the 'Strategist' role when running 'Mixture-of-Agents' style experiment)
#MODELS=("gemma3:27b" "gemma4:26b" "qwen3:30b" "cogito:32b" "openthinker:32b") # "gemma3:27b" "deepseek-r1:32b" "openthinker:32b" "devstral:24b"
MODELS=("qwen3:8b")
#MODELS=("gemma3:27b")
# --- Defaults ---
ITERATIONS=""
TIMESTEPS=""
TAG=""
REWARD_FUNC="spin_crash" 
# Capture arguments
# i: iterations, s: steps, t: tag, r: reward
while getopts "i:s:t:r:" opt; do
  case $opt in
    i) ITERATIONS="$OPTARG" ;;       # Number of train / generate improved code cycles
    s) TIMESTEPS="$OPTARG" ;;        # number of timesteps each agent is trained on reward function
    t) TAG="$OPTARG" ;;              # optional experiment tag (e.g., testingPrompts, compareLLMs)
    r) REWARD_FUNC="$OPTARG" ;;      # the initial deliberately flawed reward function to start with
    *) echo "Usage: $0 [-i iterations] [-s steps] [-t tag] [-r reward_name]"; exit 1 ;;
  esac
done

# MANDATORY CHECK: The "Go/No-Go" Gate
# This checks if the required variables are still empty
MISSING_ARGS=()
[[ -z "$ITERATIONS" ]] && MISSING_ARGS+=("Iterations (-i)")
[[ -z "$TIMESTEPS" ]]  && MISSING_ARGS+=("Timesteps (-s)")

if [ ${#MISSING_ARGS[@]} -ne 0 ]; then
  echo -e "${RED}❌ ERROR: Missing required experiment parameters:${NC}"
  for arg in "${MISSING_ARGS[@]}"; do
    echo "  - $arg"
  done
  echo -e "\nUsage: ./outer_loop.sh -i <int> -s <int> -r <string> [-t <string>]"
  exit 1
fi

echo ""
echo "🚀 Starting experiment:"
echo "                      Iterations = $ITERATIONS"
echo "                      Timesteps  = $TIMESTEPS"
echo "         Initial Reward Function = $REWARD_FUNC"
echo ""
echo "Press Ctrl+C in the next 5 seconds to cancel."
sleep 5

# --- Export for Python ---
# Add the project root to the Python search path
export PYTHONPATH="${PYTHONPATH:-}:."
export TOTAL_TIMESTEPS=$TIMESTEPS
export TOTAL_ITERATIONS=$ITERATIONS
export INITIAL_FUNC=$REWARD_FUNC


# Validate input for iterations
if ! [[ "${ITERATIONS}" =~ ^[0-9]+$ ]]; then
  echo "Error: Please provide a valid integer for iterations."
  exit 1
fi
# 🚀 LOGIC SWITCH: Select Controller based on Tag
case "$TAG" in
  *"vision"*)
    echo "👁️  MODE DETECTED: Vision Language Experiment"
    SELECTED_CONTROLLER="controllers/vision.py"
    ;;
  *"agentic"*)
    echo "🤖 MODE DETECTED: Agentic Tools Experiment"
    SELECTED_CONTROLLER="controllers/agentic.py"
  ;;
  *)
    echo -e "\n"
    echo "📉 MODE: Standard Text Analysis"
    SELECTED_CONTROLLER="controllers/standard.py"
    ;;
esac
# 🚀 LOGIC SWITCH 2: Select Training Engine based on Tag
# We check if the tag contains the string "remote"
if [[ "$TAG" == *"remote"* ]]; then
    echo "📡 ENGINE: Distributed Training (Mac -> Linux)"
    # This script runs on Mac but talks to Linux
    TRAINING_SCRIPT="src/remote_train.py"
    PLOTTING_SCRIPT="src/remote_campaign_summary.py"
else
    echo "💻 ENGINE: Local Training"
    # This script runs the PPO math locally
    TRAINING_SCRIPT="src/local_train.py"
    PLOTTING_SCRIPT="src/local_campaign_summary.py"
fi

# Format steps for directory naming (e.g. 500000 -> 500k, 1200000 -> 1.2M)
format_steps() {
  local n="$1"
  local suffix value

  if (( n >= 1000000 )); then
    # Millions: 1 decimal place, strip trailing .0
    value=$(awk -v n="$n" 'BEGIN { printf "%.1f", n/1000000 }')
    value="${value%\.0}"
    suffix="M"
  elif (( n >= 1000 )); then
    # Thousands: integer k
    value=$(( n / 1000 ))
    suffix="k"
  else
    value="$n"
    suffix=""
  fi

  printf "%s%s" "$value" "$suffix"
}

for model in "${MODELS[@]}"; do
  echo -e "\n"
  echo "============================================"
  echo " 🥊 BENCHMARKING MODEL: $model"
  echo "============================================"

  # 1. DEFINE THE CAMPAIGN (The "Outer Loop" Context)
  TIMESTAMP=$(date +%Y-%m-%d)

  # Sanitize model name for filesystem (replace ':' with '-')
  SANITIZED_MODEL=$(echo "$model" | tr ':' '-')

  # Human-readable steps component
  STEP_STR=$(format_steps "$TIMESTEPS")

  # Optional tag suffix
  if [[ -n "$TAG" ]]; then
    TAG_PART="_${TAG}"
  else
    TAG_PART=""
  fi

  # Example final pattern:
  # 2025-12-20_10cycles_500kSteps_LLMcomparison
  CAMPAIGN_TAG="${TIMESTAMP}_${REWARD_FUNC}_${ITERATIONS}cycles_${STEP_STR}Steps${TAG_PART}"

  export CAMPAIGN_TAG
  export LLM_MODEL="$model"

  echo "📂 Target Directory: experiments/$CAMPAIGN_TAG"
  # 2. Generate Initial Reward Function
  echo -e "${GREEN}[Step 0] Populating Experiment Directory With Initial Flawed Reward Function ${NC}"
  python3 controllers/set_initial_shaping.py --reward "$REWARD_FUNC"

  # 3. RUN THE INNER LOOP
  ./inner_loop.sh "$ITERATIONS" "$SELECTED_CONTROLLER" "$TRAINING_SCRIPT"

  # 4. GENERATE SUMMARY PLOT
  python3 "$PLOTTING_SCRIPT"

  echo "✅ Campaign Complete for $model."
done

echo -e "\n🎉 BENCHMARK SUITE COMPLETE!"
echo "All data is organized in the 'experiments/' directory."
