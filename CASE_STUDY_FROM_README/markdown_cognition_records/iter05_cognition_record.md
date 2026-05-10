# Cognition prompts and calls: Iteration:5


# Phase: validator [System] deepseek-r1:32b
**[ROLE AND OBJECTIVE]**
You are the Post-Mortem Analyst (Validator) for an autonomous Reinforcement Learning pipeline. You act as the system's evolutionary memory.
Your objective is to evaluate a previously proposed intervention against the newly generated Diagnostic Report to determine the behavioral impact from the mathematical changes.

**[BEHAVIORAL HIERARCHY]**
Centered Landing > Off-Center Landing > Hover Timeout > Out of Bounds > Crash. 
* Moving Up Hierarchy is behavioral progress.
* Moving Down Hierarchy is behavioral regression.

**[EVALUATION DIRECTIVES]**

1. **Quantitative Check:** Look at the `Target Metric` from the Hypothesis. Did it achieve the `Expected Change` in the new Diagnostic Report?
2. **Holistic Check (Goodhart's Law):** Did the agent hack the reward? Even if the specific target metric improved, you must check the `Population Success Rate`, `Terminal Distribution`, and `Objective Alignment ($\rho$)`. 
3. **Progress-Oriented Evaluation (The Unexpected):** Physical flight dynamics are highly coupled. If the specific target metric was missed, burt the overall `Population Success Rate` or global $\rho$ improved significantly due to emergent, productive behaviors, you must recognize the physical progress. Do not rigidly refute a run that generated a superior flight policy.
4. **Compression:** Distill the entire experiment into a dense, immutable historical record for the Experiment Ledger.

**[FLOOR RULES — apply before checking metrics]**
- Success Rate Moved up ≥20pp → verdict ∈ {`Validated`, `Productive Deviation`}
- Success Rate Moved down ≥20pp → verdict at minimum `Regressed`
- Lateral OR moved up (any size) → `Regressed` prohibited
- Behavior is primary, metrics secondary. When they conflict, behavior wins.

**[OUTPUT CONSTRAINTS]**
You must output EXACTLY two bullet points formatted strictly as follows. Do not include conversational filler, introductory text, or concluding remarks.

* **Status:** [`Validated` / `Regressed` / `Mixed` / `Goodhart Trap` / `Productive Deviation`] - [Cite the exact expected metric vs. the actual metric achieved. If using Productive Deviation, explicitly state the unexpected global improvement that saved the run].
* **Behavioral Reality:** [Describe the actual physical outcome and diagnostic shifts].


# Phase: validator [User] deepseek-r1:32b
**TARGET SYSTEM:** LunarLander-v3
**ITERATION EVALUATED:** `5`

Audit the outcome of the previous reward intervention to update the Intervention Log.

### [1. THE EXPERIMENT PARAMETERS (FROM PREVIOUS ITERATION)]

This was the proposed reward intervention and its predicted effect.


**Conceptual Hypothesis:** The current `sink_penalty` is causing a deadlock where the agent hesitates to descend quickly, leading to poor `Mean Descent Efficiency`. The proposed change introduces a y-gated precision term that only penalizes lateral error and impact velocity as the agent approaches the landing pad, removing the anti-altitude bias.  
**Falsifiable Expected Outcome:** - Target Metric: `Mean Descent Efficiency`  
* Expected Change: Increase from \( 0.047 \to >0.400 \)  
* Side Effects: Reduction in `landed_off_centered` rate  


### [2. THE BASELINE STATE (BEFORE THE CHANGE)]

This is the verified diagnostic state of the agent **before** the Iteration `5` reward modifications were applied. All delta comparisons must be grounded in these values — do not estimate or recall prior states from memory.



#### A. Universal Policy Robustness
- **Population Success Rate:** `80.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.047`
- **Actuator Chatter Rate:** `0.105`

#### C. Population Terminal Distribution
- `landed_off_centered`: 43.3%
- `landed_centered`: 33.3%
- `crashed`: 20.0%
- `landed_but_slid_into_valley`: 3.3%

### [3. THE ACTUAL RESULTS (AFTER THE CHANGE)]

This is the deterministic, mathematically extracted performance data of the agent trained on that intervention.

### 1. Optimization Dynamics & Critic Health
**Status:** 🔴 **UNSTABLE/FAILED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `-23.71`
  - *Diagnosis:* The cross-seed variance exceeds the mean reward. The current reward topology is highly chaotic and fails to enforce a universal policy.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.003`
  - *Diagnosis:* The learning curves are completely uncorrelated across seeds. The reward function has created a jagged landscape with multiple competing local minima.
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `3.3%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.006`
- **Actuator Chatter Rate:** `0.322`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.

#### C. Population Terminal Distribution
- `out_of_bounds`: 93.3%
- `landed_centered`: 3.3%
- `crashed`: 3.3%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `-0.024`
  - *Diagnosis:* **CRITICAL FAILURE.** The total generated reward is NEGATIVELY correlated with successful landings. The agent is receiving mathematically higher returns for crashing/drifting than for landing safely.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `attitude_penalty` | 0.029 | 0.045 | 11.6% | ⚪ Neutral/Noisy |
| `sink_penalty` | 0.139 | 0.039 | 57.6% | ⚪ Neutral/Noisy |
| `smoothness_penalty` | -0.050 | 0.009 | 11.4% | ⚪ Neutral/Noisy |
| `precision_penalty` | -0.266 | 0.071 | 19.5% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.287` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.157`

**ACTION REQUIRED:**
Audit the intervention outcome against the Baseline and Actual Results. Output the strict 3-bullet-point Intervention Log entry to serve as the evolutionary memory for the next iteration.


# Phase: validator [Thinking Trace] deepseek-r1:32b
Okay, so I need to figure out the status and behavioral reality of the intervention based on the data provided. Let me go through each step carefully.

First, looking at the quantitative check. The target metric was Mean Descent Efficiency, expected to increase from 0.047 to above 0.400. But after the change, it's only 0.006. That's a significant decrease, so the quantitative check fails.

Next, the holistic check. The Population Success Rate dropped from 80% to 3.3%, which is a massive regression. The Terminal Distribution shows that most outcomes are now 'out_of_bounds' at 93.3%, with very few successful landings. The Objective Alignment rho is -0.024, which is negative, indicating the reward function is misaligned. The 'precision_penalty' component is negatively aligned, which is bad.

The Progress-Oriented Evaluation doesn't seem to apply here because there's no improvement in other metrics. The Population Success Rate is way down, and the overall behavior is worse.

For the Floor Rules, the Success Rate moved down by over 76pp, so the verdict can't be anything but Regressed. Also, the behavior is primary, and it's clear that the agent is failing more, so metrics don't save it.

Putting it all together, the status is Regressed because the target metric didn't improve and the success rate plummeted. The behavioral reality is that the policy is highly unstable, leading to almost all runs ending out of bounds or crashing, with the reward function actually encouraging negative behaviors.



# Phase: validator [Output] deepseek-r1:32b
* **Status:** `Regressed` - [Target Metric: Mean Descent Efficiency expected >0.400, actual 0.006].  
* **Behavioral Reality:** [The policy is highly unstable, with 93.3% of runs ending in 'out_of_bounds' and 3.3% in 'crashed'. The reward function is negatively aligned, incentivizing failure over success.]


# Phase: strategist [System] gemma4:26b
<|think|>
**[ROLE AND OBJECTIVE]**
You are the Lead Algorithmic Reward Designer (Strategist) for an autonomous Reinforcement Learning pipeline solving the LunarLander-v3 environment (an underactuated, continuous/discrete control task).
Your objective is to design dense reward functions that enforce stable, efficient, and robust physical flight dynamics.

You are part of a multi-agent system. Do not worry about formatting your output into strict JSON or perfect code blocks—an "Organizer" agent will parse your response. Your ONLY job is deep mathematical reasoning, physical deduction, and algorithmic creativity.

**[DIAGNOSTIC GLOSSARY & ANCHORS]**
You will receive a deterministic Diagnostic Report. Use these strict definitions to interpret the physical reality of the agent:

* **Critic Saturation Index (CSI):** A value $>10.0$ indicates the Value network has diverged. The reward function is injecting non-Markovian noise or contradictory gradients.

* **Objective Alignment ($\rho$):** The Pearson correlation between your reward components and actual task success (landing). Components with negative alignment are adversarial to the agent's success.

* **Mutual Information w/ Success (MI):** When the Component-Level Contribution table includes an MI column, MI captures *any* statistical dependence between a component and success — including non-linear ones that $\rho$ is mathematically blind to: thresholds (`if x > k: bonus`), quadratics around an optimum (`-(angle)²`), and saturating shapes (`tanh`, `clip`). Use the relationship between $\rho$ and MI to diagnose component structure:

  - **High |ρ| AND high MI** → linear/monotonic relationship; trust ρ's sign.
  - **Low |ρ| AND high MI** → flagged as 🟣 **HIDDEN DEPENDENCY**. The component has real influence on success that linear correlation cannot see. Do NOT infer the component is neutral or dead. Inspect the component's functional form in the code — it is likely a threshold, quadratic, or saturating term. The sign of effect cannot be read from ρ here; you must reason from the math itself.
  - **Low |ρ| AND low MI** → genuinely irrelevant; safe to excise.
  - **High |ρ| AND low MI** → rare; usually a small-sample artifact. Discount.

* **🔴 Negatively Aligned ($\rho < -0.2$):** The component's linear correlation with success is adversarial. The functional form may need sign inversion, rescaling, or replacement — but a negative ρ alone does not specify *which*. Reason from the term's mathematical form before acting. The 🟣 HIDDEN DEPENDENCY flag is **not** a negative-alignment flag; it indicates non-linearity, not adversarial direction.

* **🟡 Low Magnitude ($<1\%$ of gradient):** The component contributes negligibly to the total reward signal. This may indicate (a) a coefficient that is too small, (b) a sparse gating term that fires rarely but informatively, or (c) a genuinely irrelevant term. Cross-reference MI: low magnitude with non-trivial MI is often a gating term that should be preserved or strengthened, not excised.

* **⚪ Neutral/Noisy:** The component shows weak linear correlation and low MI. This is a finding, not a verdict — the component may be miscalibrated, mistimed, or operating in a regime the agent has not yet reached. Investigate before acting; weak signal is not the same as zero contribution.

* **Actuator Chatter Rate:** A value $>0.2$ means the agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is jagged. Smooth the penalties near zero-states.

* **Intra-Rollout Reward CV:** High values ($>0.5$) indicate extreme sensitivity to random seed initialization. The policy is mathematically fragile.


**[ENVIRONMENT & API CONSTRAINTS]**
**State Space & Variables Available:**
Time-based penalties are forbidden. To incentivize timely descent, you must encode urgency through spatial and kinematic state variables only.
You must formulate your math using ONLY these available variables:
* `obs`: A numpy array `[x_pos, y_pos, x_vel, y_vel, angle, angular_vel, leg1_contact, leg2_contact]`
* `info['prev_obs']`: The observation array from the previous step.
* `info['action']`: The discrete action taken by the agent.

**[DIRECTIVES & OUTPUT REQUIREMENTS]**
Analyze the current Python reward implementation against the Diagnostic Report. Identify the mathematical root cause of the physical failures.

You must structure your output in two distinct parts:

**PART 1: SURGICAL EXCISION**

Most components are salvageable through rescaling, sign inversion, or gating — and salvaging preserves shaping information the next iteration cannot recover. Excise only when the *functional form itself* is incoherent with the task. **No flag in the diagnostic table is by itself grounds for excision** — flags describe statistical findings, not actions. The decision to delete versus modify is yours, and must be reasoned from the component's mathematical form against the observed physical failure.

List components you are excising, with one sentence of justification per component stating why no transformation rescues the form.

**PART 2: 3 PROPOSALS (Additions, Modifications, or Synergistic Clusters)**

Output exactly **3 distinct proposals**. A proposal may:
- **Add** a novel term encoding a new physical insight
- **Modify** an existing term (rescale, invert sign, gate by state, change functional form)
- Comprise a **synergistic cluster** of cooperating terms when they are mathematically inseparable

Modification proposals are not lesser proposals. A well-reasoned sign inversion or gating condition often outperforms a novel addition. Do not artificially atomize a hypothesis into single-term proposals; do not pad a single-term hypothesis into a cluster.

For each proposal, you must clearly provide:

1. **The Conceptual Hypothesis:** Explain the physical or optimization failure and *why* your proposed math fixes it. Think about gravity, momentum, and state-space boundaries.

2. **The Mathematical Formulation:** Define the exact change in LaTeX or Python. For modifications, show the old form and the new form. For clusters, label each term's role (shaping, gating, saturation, etc.) and state what the synergy produces that no single term can. Specify coefficients and clipping boundaries.

3. **The Falsifiable Expected Outcome:** State the exact metric from the Diagnostic Report (e.g., `Mean Descent Efficiency`, `Chatter Rate`, `Population Success Rate`) that will improve, and the numerical shift you expect to see in the next iteration.

Explore the state space deeply. Do not propose the same idea three times with slightly different coefficients.


# Phase: strategist [User] gemma4:26b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT ITERATION:** `5`

Analyze the following execution data and generate your 3 distinct reward design proposals.

### [1. CURRENT REWARD IMPLEMENTATION]

This is the mathematical logic the agent just trained on.

```python
import math
import numpy as np
from typing import Dict, Tuple

def calculate_reward(obs: np.ndarray, info: Dict) -> Tuple[float, Dict[str, float]]:
    """
    Args:
        obs: Current observation [x, y, vx, vy, angle, v_ang, leg1, leg2]
        info: {'prev_obs': prev_obs, 'action': action_idx, 'terminal_observation': term_obs, 'current_step': curr_step}
    
    Returns:
        total_reward (float): The sum of all shaping components for this step.
        components (dict): Granular breakdown of the reward components.
    """
    
    x, y, vx, vy, angle, v_ang, leg1, leg2 = obs
    prev_obs = info.get('prev_obs', obs)
    prev_angle, prev_v_ang = prev_obs[4], prev_obs[5]
    action = info.get('action', 0)
    
    # === 1. ATTITUDE PENALTY (new addition) ===
    w_att = 1.5
    r_attitude = -w_att * (angle**2 + v_ang**2)
    
    # === 2. SINK PENALTY (new addition) ===
    w_x = 0.5
    w_y = 0.5
    w_v = 0.2
    r_sink = -(w_x * np.abs(x) + w_y * np.abs(y) + w_v * (vy**2))
    
    # === 3. SMOOTHNESS PENALTY (new addition) ===
    w_smooth = 0.1
    prev_action = info.get('prev_action', 0)
    r_smooth = -w_smooth * np.abs(action - prev_action)
    
    # === 4. PRECISION PENALTY (new addition) ===
    y_threshold = 0.5
    w_x = 2.0
    w_v_y = 1.5
    r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)
    
    components = {
        "attitude_penalty": float(r_attitude),
        "sink_penalty": float(r_sink),
        "smoothness_penalty": float(r_smooth),
        "precision_penalty": float(r_precision),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components

```

### [2. EXPERIMENT LEDGER (HISTORY)]

Review these past iterations to avoid repeating failed hypotheses.
### Iteration 1 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.
**Falsifiable Expected Outcome:** - Target Metric: Critic Saturation Index (CSI)

* Expected Change: Reduction from $45.74 \to < 10.0$
* Side Effects: None


**The Physical Outcome & Lesson:**
* **Status:** `Regressed` - [Cite the exact expected metric vs. the actual metric achieved. If using Productive Deviation, explicitly state the unexpected global improvement that saved the run].  
* **Behavioral Reality:** [Describe the actual physical outcome and diagnostic shifts].
----------------------------------------

### Iteration 2 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current reward landscape lacks a "gravity well" to pull the agent from the high-altitude hover state toward the landing pad. By removing the positive `survival` reward and replacing it with a multi-variable sink, we create a continuous gradient that rewards the reduction of both potential energy (altitude $y$) and lateral error ($x$), while simultaneously penalizing high-velocity impacts ($v_y$). This forces the agent to prioritize the origin $(0,0)$ as the global optimum.
**Falsifiable Expected Outcome:** - Target Metric: Objective Alignment ($\rho$)

* Expected Change: Increase from $0.000 \to >0.450$
* Side Effects: Decrease in `hover_timeout` percentage


**The Physical Outcome & Lesson:**
* **Status:** `Productive Deviation` - [Objective Alignment ($\rho$) expected >0.450 vs. actual 0.200, but Population Success Rate improved from 0.0% to 53.3%].  
* **Behavioral Reality:** [The agent now crashes (40.0%) or lands off-center (30.0%), replacing the previous hover_timeout (73.3%). Actuator chatter improved (0.265 vs. 0.755), but macro-oscillations persist].
----------------------------------------

### Iteration 3 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The `Actuator Chatter Rate` is dangerously high ($0.265$), indicating the agent is oscillating between opposing thruster commands. This suggests the policy is over-reacting to the gradients of the $x$ and $v_x$ penalties. Adding a penalty for high-frequency action changes will smooth the control signal, reducing the "jagged" landscape that causes the high `Intra-Rollout Reward CV`.  
**Falsifiable Expected Outcome:**  
* Target Metric: `Actuator Chatter Rate`  
  * Expected Change: Reduction from $0.265 \to < 0.150$  
* Target Metric: `Intra-Rollout Reward CV`  
  * Expected Change: Reduction from $0.232 \to < 0.150$  
* Side Effects: None


**The Physical Outcome & Lesson:**
* **Status:** `Goodhart Trap` - The `Actuator Chatter Rate` was reduced from 0.265 to 0.105, meeting the target, but the `Intra-Rollout Reward CV` increased from 0.232 to 0.249, and the `Objective Alignment ($\rho$)` is weak at 0.305, indicating the reward function may be exploited rather than guiding optimal behavior.
* **Behavioral Reality:** The agent exhibits smoother control actions but with increased off-center landings (43.3%) and crashes (20%), suggesting a misalignment between reward signals and desired outcomes. The reward topology is chaotic, leading to unstable optimization dynamics.
----------------------------------------

### Iteration 4 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current `sink_penalty` is causing a deadlock where the agent hesitates to descend quickly, leading to poor `Mean Descent Efficiency`. The proposed change introduces a y-gated precision term that only penalizes lateral error and impact velocity as the agent approaches the landing pad, removing the anti-altitude bias.  
**Falsifiable Expected Outcome:** - Target Metric: `Mean Descent Efficiency`  
* Expected Change: Increase from \( 0.047 \to >0.400 \)  
* Side Effects: Reduction in `landed_off_centered` rate  


**The Physical Outcome & Lesson:**
* **Status:** `Regressed` - [Target Metric: Mean Descent Efficiency expected >0.400, actual 0.006].  
* **Behavioral Reality:** [The policy is highly unstable, with 93.3% of runs ending in 'out_of_bounds' and 3.3% in 'crashed'. The reward function is negatively aligned, incentivizing failure over success.]
----------------------------------------

### [3. DIAGNOSTIC REPORT]

This is the deterministic, mathematically extracted performance data from the most recent training runs across multiple random seeds.
### 1. Optimization Dynamics & Critic Health
**Status:** 🔴 **UNSTABLE/FAILED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `-23.71`
  - *Diagnosis:* The cross-seed variance exceeds the mean reward. The current reward topology is highly chaotic and fails to enforce a universal policy.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.003`
  - *Diagnosis:* The learning curves are completely uncorrelated across seeds. The reward function has created a jagged landscape with multiple competing local minima.
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `3.3%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.006`
- **Actuator Chatter Rate:** `0.322`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.

#### C. Population Terminal Distribution
- `out_of_bounds`: 93.3%
- `landed_centered`: 3.3%
- `crashed`: 3.3%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `-0.024`
  - *Diagnosis:* **CRITICAL FAILURE.** The total generated reward is NEGATIVELY correlated with successful landings. The agent is receiving mathematically higher returns for crashing/drifting than for landing safely.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `attitude_penalty` | 0.029 | 0.045 | 11.6% | ⚪ Neutral/Noisy |
| `sink_penalty` | 0.139 | 0.039 | 57.6% | ⚪ Neutral/Noisy |
| `smoothness_penalty` | -0.050 | 0.009 | 11.4% | ⚪ Neutral/Noisy |
| `precision_penalty` | -0.266 | 0.071 | 19.5% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.287` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.157`

**ACTION REQUIRED:**
Generate your 3 distinct proposals (Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome).


# Phase: strategist [Thinking Trace] gemma4:26b
Lead Algorithmic Reward Designer.
Design dense reward functions for `LunarLander-v3`.
The current implementation (Iteration 5) has failed catastrophically.
        *   `Population Success Rate`: 3.3% (Extremely low).
        *   `Objective Alignment ($\rho$)`: -0.024 (Negative correlation with success).
        *   `Out of Bounds`: 93.3% (The agent is flying away/out of the arena).
        *   `Precision Penalty`: $\rho = -0.266$ (🔴 Negatively Aligned). This is the smoking gun.
        *   `Actuator Chatter Rate`: 0.322 (High).
        *   `Mean Descent Efficiency`: 0.006 (Near zero).

    *   `attitude_penalty`: $-1.5 \cdot (\text{angle}^2 + \text{v\_ang}^2)$. (Neutral/Noisy).
    *   `sink_penalty`: $-(0.5 \cdot |x| + 0.5 \cdot |y| + 0.2 \cdot vy^2)$. (Neutral/Noisy).
    *   `smoothness_penalty`: $-0.1 \cdot |action - prev\_action|$. (Neutral/Noisy).
    *   `precision_penalty`: $-\exp((0.5 - y) / 0.5) \cdot (2.0 \cdot x^2 + 1.5 \cdot vy^2)$. (🔴 Negatively Aligned).

    *   *The Precision Penalty Problem:* Let's look at the math: `r_precision = -exp((0.5 - y) / 0.5) * (2.0 * x^2 + 1.5 * vy^2)`.
        *   When $y$ is large (high altitude), $0.5 - y$ is a large negative number. $e^{-(\text{large})}$ approaches 0. The penalty is small.
        *   When $y$ approaches 0.5 (landing threshold), $0.5 - y \approx 0$, $e^0 = 1$. The penalty is large.
        *   *Wait, why is it negatively aligned?* If the agent is at $y=10$, the penalty is almost $0$. If the agent is at $y=0.1$, the penalty is high.
        *   *The Conflict:* The `sink_penalty` penalizes $|y|$. This means the agent is being punished for having $y > 0$. To minimize `sink_penalty`, the agent wants $y$ to be small. However, the `precision_penalty` becomes *massive* as $y$ gets small (approaching the threshold).
        *   *The "Out of Bounds" Failure:* If the agent is penalized for $y$ (sink penalty) and penalized for $x$ (sink penalty), but the `precision_penalty` explodes as it descends, the agent's best strategy to avoid huge penalties is to *flee* the landing zone entirely or stay at a high altitude where $y$ is large enough that the exponential term stays small, but $x$ is also large? No, $x$ is penalized in `sink_penalty`.
        *   *The real killer:* Look at the `sink_penalty` again: `-(0.5 * |x| + 0.5 * |y| + 0.2 * vy^2)`. This penalizes $y$. To minimize penalty, $y$ should be 0. But as $y \to 0$, the `precision_penalty` (which is negative) scales exponentially.
        *   *The Mathematical Trap:* The agent is caught in a gradient where descending towards the target ($y \to 0$) triggers an exponential explosion of negative reward. The only way to avoid this is to stay at $y \to \infty$ (where the exponential term is 0) or move to $x \to \infty$ (but $x$ is penalized).
        *   *The "Out of Bounds" Logic:* The agent is likely flying out of bounds because the `sink_penalty` for $y$ is linear, but the `precision_penalty` is exponential. If the agent stays at a very high $y$, the `precision_penalty` is near zero. However, the `sink_penalty` for $y$ is still accumulating. But wait—if the agent goes to $y = 100$, the `sink_penalty` is $-50$. If the agent goes to $y = 0.5$, the `sink_penalty` is $-0.25$. The `precision_penalty` is the deciding factor.
        *   *Crucial realization:* The `precision_penalty` is $\text{negative} \cdot \text{exponential}$. As $y$ decreases, the magnitude of the negative reward *increases* exponentially. This creates a "repulsive" force at the landing pad. The agent is literally being pushed *away* from the landing pad. This explains the 93.3% `out_of_bounds`.

    *   *Smoothness/Chatter:* The `smoothness_penalty` is too weak (0.1) to counteract the massive gradients of the `precision_penalty` and `sink_penalty`.

    *   **Proposal 1: Fix the Precision/Sink Conflict (The "Gravity Well" Restoration).**
        *   We need to remove the exponential repulsion. Instead of an exponential penalty that grows as $y \to 0$, we need a "Precision Zone" that only activates when $y$ is low, and it must be *additive* to success (or at least not subtractive in a way that outweighs the descent).
        *   Actually, the `precision_penalty` should be a *bonus* or a *low-magnitude penalty* that rewards $x \approx 0, v_y \approx 0$ ONLY when $y$ is small.
        *   Let's use a "Gated Precision" approach. When $y < \text{threshold}$, we reward low $x$ and low $v_y$.

    *   **Proposal 2: Address the Actuator Chatter and Smoothness.**
        *   The `smoothness_penalty` is currently $0.1 \cdot |action - prev\_to\_action|$. It's too small.
        *   The `actuator_chatter_rate` is $0.322$.
        *   We need to penalize the *magnitude* of the change in control signal, but also perhaps penalize the use of opposing thrusters (the "anti-vibration" approach).
        *   Let's introduce a "Control Stability" term that penalizes $\text{action\_delta}^2$ and potentially use a smoothing kernel on the $x$ and $y$ velocity penalties to prevent the "jagged" landscape.

    *   **Proposal 3: Re-establish the "Descent Drive" (The Kinetic Energy Management).**
        *   The `sink_penalty` is penalizing $y$ (altitude). This is essentially a "gravity" term, but it's forcing the agent to $y=0$ without regard for velocity.
        *   We need to manage the "Landing Impact". We need a term that rewards $v_y \to 0$ as $y \to 0$.
        *   Let's create a "Terminal State Shaping" cluster. This cluster will focus on the "Landing Window": $y \in [0, 0.5]$, $x \in [-0.5, 0.5]$, $v_y \in [-0.1, 0.1]$.

    *   *Excision:* The `precision_penalty` is mathematically repulsive. It must be excised or fundamentally inverted. I will excise it because its current form (exponentially increasing penalty as $y$ decreases) is a "repulsive barrier" that makes the target state an unstable equilibrium.

    *   *Proposal 1 (The Precision Anchor):*
        *   Replace `precision_penalty` with a "Precision Anchor".
        *   Function: A Gaussian-style reward or a gated quadratic reward that *only* activates when $y < 0.5$.
        *   $\text{Reward} = \mathbb{1}_{y < 0.5} \cdot [ w_1 \cdot \exp(-x^2/\sigma_x^2) - w_2 \cdot v_y^2 ]$.
        *   Wait, let's keep it simpler for the agent to learn: A gated quadratic penalty that is *small* but *positive* (or at least not exponentially large).
        *   Let's go with: `r_precision = - (w_x * x**2 + w_v_y * vy**2)` gated by `(y < 0.5)`. This removes the exponential repulsion.

    *   *Proposal 2 (The Smoothness/Stability Cluster):*
        *   The `smoothness_penalty` is too low.
        *   Let's increase `w_smooth` and change it to a squared penalty to penalize large jumps more heavily (reducing $\text{action\_delta}$).
        *   Also, add a "Centering Force" to the `sink_penalty` to prevent the "out of bounds" drift.
        *   Current `sink_penalty` penalizes $|x|$. Let's make it a "Lateral Stability" term: $-w_x \cdot x^2$. This provides a smoother gradient toward $x=0$ than $|x|$.

    *   *Proposal 3 (The Energy Dissipation/Impact Mitigation):*
        *   The agent is crashing or flying away. It needs to learn to dissipate energy.
        *   New term: `r_impact_mitigation`.
        *   As $y \to 0$, we need to penalize $v_y^2$ and $v_x^2$ heavily.
        *   Let's use a "Soft Landing" term: $-w_{impact} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$. This is a "damping" term that only becomes active as the agent approaches the ground.

    *   *Wait, check the `sink_penalty` again.*
    *   `r_sink = -(w_x * np.abs(x) + w_y * np.abs(y) + w_v * (vy**2))`
    *   The $w_y \cdot |y|$ term is the "anti-altitude" bias. It is actually helping the agent descend, but it's competing with the precision penalty.
    *   The main problem is the `precision_penalty`'s exponential growth.

    *   *Refined Plan:*
        1.  **Excision:** `precision_penalty`.
        2.  **Proposal 1 (The Precision Anchor):** Replace `precision_penalty` with a gated, non-exponential quadratic penalty: $-w \cdot (x^2 + v_y^/2)$ if $y < 0.5$. This removes the "repulsion" while still enforcing precision.
        3.  **Proposal 2 (The Stability Cluster):** Modify `smoothness_penalty` to be a squared-delta penalty and modify `sink_penalty` to replace $|x|$ with $x^2$ to provide a smoother, more consistent gradient toward the center, reducing the `out_of_bounds` drift.
        4.  **Proposal 3 (The Impact Damping Cluster):** Add a new term that penalizes kinetic energy ($v_x^2 + v_y^2$) specifically in the low-altitude regime ($y < 0.5$). This forces the agent to "brake" before hitting the ground, addressing the `crashed` and `landed_off_centered` issues.

    *   *Critique of Proposal 2:* If I change `sink_penalty` to $x^2$, does it fix the "Out of Bounds"? The current `sink_penalty` uses $|x|$. $|x|$ has a constant gradient. $x^2$ has a gradient that vanishes at $x=0$. This is actually *worse* for recovery if the agent is far away. Let's stick to the `sink_penalty` but focus on the "Lateral Drift" by adding a "Centering" term that is stronger.

    *   *Let's re-evaluate Proposal 2:* The `actuator_chatter_rate` is high. The `smoothness_penalty` is currently $-0.1 \cdot |action - prev\_action|$. Let's change it to a quadratic penalty on the *change* in action: $-w_{smooth} \cdot (\Delta \text{action})^2$. This is much more effective at penalizing "jitter".

    *   *Final Set of Proposals:*
        1.  **Excision:** `precision_penalty` (The "Repulsive Barrier").
        2.  **Proposal 1 (Gated Precision Anchor):** Replace `precision_penalty` with a quadratic penalty $(x^2 + v_y^2)$ that is only active when $y < 0.5$. This removes the exponential "push" away from the landing pad while maintaining the precision objective.
        3.  **Proposal 2 (Quadratic Smoothness):** Modify `smoothness_penalty` from $L1$ to $L2$ norm of the action delta: $-w \cdot (a_t - a_{t-1})^2$. This targets the `Actuator Chatter Rate` directly by penalizing large, sudden shifts in torque more aggressively.
        - **Proposal 3 (Impact Dissipation Cluster):** A new term that penalizes $v_y^2$ and $v_x^2$ with an exponential weight $\exp(-y)$. This creates a "viscous" layer near the ground, forcing the agent to decelerate as it approaches $y=0$, preventing the `crashed` state.

    *   *Check against constraints:* No time-based penalties. All use `obs` and `prev_obs`.

    *   *Final Polish of Math:*
        *   Prop 1: `r_precision = - (w_x * x**2 + w_vy * vy**2) if y < 0.5 else 0`.
        *   Prop 2: `r_smooth = -w_smooth * (action - prev_action)**2`.
        *   Prop 3: `r_damping = -w_d * exp(-y) * (vx**2 + vy**2)`.

    *   *Wait, one more look at the `precision_penalty` in the original code:*
        `r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)`
        If $y=0.1$ and $y\_threshold=0.5$, then $(0.5-0.1)/0.5 = 0.8$. $e^{0.8} \approx 2.22$.
        If $y=0.01$, then $(0.5-0.01)/0.5 = 0.98$. $e^{0.98} \approx 2.66$.
        Wait, the exponential term is *increasing* the penalty as $y$ decreases, but it's not *exploding* to infinity. It's just a scaling factor.
        *So why is $\rho$ negative?*
        Ah! If the agent is at $y=0.1$, the penalty is $-2.66 \cdot (\dots)$.
        If the agent is at $y=10$, the penalty is $-e^{-19} \cdot (\dots) \approx 0$.
        The agent is being penalized *more* for being at the target than for being far away.
        This is exactly what I thought: it's a "Repulsive Barrier". It makes the target state (low $y$) a region of high negative reward. The agent's optimal strategy to maximize reward is to stay at high $y$ (where penalty is 0) or move to high $x$ (where $x$ is large but the $y$ multiplier is small).
        This is why `out_of_bounds` is 93.3%. The agent is literally running away from the landing pad to avoid the precision penalty.

    *   *Final check on Proposal 3 (Damping):*
        The `sink_penalty` already has `w_v * vy**2`.
        If I add `r_damping = -w_d * exp(-y) * (vx**2 + vy**2)`, I am essentially making the velocity penalty much stronger as $y \to 0$. This is good.

    *   *Wait, the `smoothness_penalty` in the original code:*
        `r_smooth = -w_smooth * np.abs(action - prev_action)`
        The `prev_action` is not in the `obs` array, but it's in `info`. I must ensure my proposal uses `info`.
        The prompt says: `info: {'prev_obs': prev_obs, 'action': action_idx, ...}`.
        It doesn't explicitly say `prev_action` is in `info`, but the original code *uses* `info.get('prev_action', 0)`. I will follow that pattern.

    *   *Summary of Proposals for Output:*
        1.  **Excision:** `precision_penalty`. (Reason: Mathematical repulsion).
        2.  **Prop 1 (Gated Precision Anchor):** Replace `precision_penalty` with a gated quadratic penalty. (Target: $\rho$ and `landed_centered`).
        3.  **Prop 2 (L2 Smoothness):** Modify `smoothness_penalty` to $L2$ norm. (Target: `Actuator Chatter Rate`).
        4.  **Prop 3 (The Viscous Boundary):** Add a $y$-dependent kinetic energy penalty. (Target: `crashed` and `landed_off_centered`).


# Phase: strategist [Output] gemma4:26b
**PART 1: SURGICAL EXCISION**

*   **`precision_penalty`**: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

***

**PART 2: 3 PROPOSALS**

### Proposal 1: The Gated Precision Anchor (Modification)

**1. The Conceptual Hypothesis:**
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. The Mathematical Formulation:**
*   **Old Form:** `r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)`
*   **New Form:**
    $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$
    *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** Objective Alignment ($\rho$)
*   **Expected Change:** Increase from $-0.024 \to >0.300$.
*   **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).

---

### Proposal 2: L2-Norm Control Smoothing (Modification)

**1. The Conceptual Hypothesis:**
The current `smoothness_penalty` uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0_322$). By switching to an **$L2$ (Quadratic) Smoothness Penalty**, we create a much steeper penalty gradient for large-magnitude action jumps, forcing the policy to favor continuous, low-frequency control signals.

**2. The Mathematical Formulation:**
*   **Old Form:** `r_smooth = -w_smooth * np.abs(action - prev_action)`
*   **New Form:**
    $$r_{smooth} = -w_{smooth} \cdot (action - prev\_action)^2$$
    *Where $w_{smooth} = 0.5$ (increased from 0.1 to provide stronger regularization).*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** `Actuator Chatter Rate`
*   **Expected Change:** Reduction from $0.322 \to <0.150$.
*   **Side Effect:** Reduction in `Intra-Rollout Reward CV`.

---

### Proposal 3: The Viscous Boundary Cluster (Addition)

**1. The Conceptual Hypothesis:**
The agent currently lacks a "braking" mechanism; the `sink_penalty` penalizes $v_y^2$ globally, which can lead to the agent being too "afraid" to descend. I propose a **Viscous Boundary Cluster** consisting of a $y$-dependent kinetic energy dissipation term. This term acts as a "viscous fluid" layer that only activates near the ground. It specifically targets the $v_x$ and $v_y$ magnitudes as $y \to 0$, forcing the agent to dissipate kinetic energy precisely when the risk of a `crashed` or `landed_off_centered` event is highest.

**2. The Mathematical Formulation:**
This is a synergistic cluster of two terms:
1.  **Term 1 (Kinetic Dissipation):** $r_{dissipate} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$
2.  **Term 2 (Gating):** $r_{gate} = \text{clip}(y, 0, 1)$ (Used to scale the intensity of the dissipation).

**Combined Cluster:**
$$r_{viscous} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$$
*Where $w_{damp} = 1.0$. As $y \to 0$, the penalty for high velocity grows exponentially, creating a "soft landing" constraint.*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** `crashed` / `landed_off_centered` Rate
*   **Expected Change:** Reduction in `crashed` percentage from $3.3\% \to <1.0\%$.
*   **Side Effect:** Increase in `Mean Descent Efficiency` (as the agent will learn to use gravity to descend but must brake at the last moment).


# Phase: organizer [System] deepseek-r1:32b
**[ROLE AND OBJECTIVE]**
You are the Technical Organizer for an autonomous Reinforcement Learning pipeline. Your role is data extraction and formatting.
You sit between the "Strategist" (who generates raw mathematical proposals for reward functions) and the "Research Lead" (who evaluates them).
Your objective is to take the Strategist's raw, unformatted, or loosely formatted output and strictly map it into a pristine Markdown structure called a "Mathematical Contract."

**[DIRECTIVES]**

1. **Zero Data Loss:** You must preserve the exact mathematical formulas, Python snippets, coefficients, and physical reasoning provided by the Strategist. Do not alter the underlying logic.
2. **No Hallucination:** Do not invent new proposals. If the Strategist provided 3 proposals, you output exactly 3 formatted proposals.
3. **Extraction & Mapping:** The Strategist might blend its scaling constraints into its math formulation, or its hypothesis into its expected outcome. You must meticulously extract the information and place it into the correct sections of the template.
4. **Global Excision Routing:** The Strategist will output a "Global Excision Manifesto" at the top of its response. You must extract this list of deletions and insert it verbatim into the `Code Deletions/Modifications` bullet point for ALL THREE formatted proposals.
5. **Formatting:** You must strictly use the exact Markdown headers and sub-bullets provided in the template below.

**[TARGET OUTPUT TEMPLATE]**
For each proposal found in the Strategist's output, generate the following exact structure:

### Proposal [Number]: [Title extracted or inferred from the Strategist]

**1. Conceptual Hypothesis:** [The physical or optimization reasoning behind the change.]

**2. Mathematical Formulation:**
* **Code Additions:** [The exact LaTeX math or Python snippet proposed to be added.]
* **Code Deletions/Modifications:** [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE. You must explicitly list the manifesto items in this bullet point for every proposal. Do not write "None explicitly stated" if a manifesto exists.]

**3. Reward Scaling & Constraints:**

* **Coefficient:** [Extract the multiplier/scale used]
* **Constraint/Clipping:** [Extract any bounds or clips mentioned. If none, write "None explicitly stated."]
* **Integration:** [Extract which variables/lines this targets]

**4. Falsifiable Expected Outcome:**

* **Target Metric:** [The specific metric from the diagnostic report to be improved]
* **Expected Change:** [The numerical shift expected]


# Phase: organizer [User] deepseek-r1:32b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Format Strategist Output

Parse the following raw output from the Strategist and convert it strictly into the required Mathematical Contract Markdown format.

### [RAW STRATEGIST OUTPUT]

**PART 1: SURGICAL EXCISION**

*   **`precision_penalty`**: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

***

**PART 2: 3 PROPOSALS**

### Proposal 1: The Gated Precision Anchor (Modification)

**1. The Conceptual Hypothesis:**
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. The Mathematical Formulation:**
*   **Old Form:** `r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)`
*   **New Form:**
    $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$
    *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** Objective Alignment ($\rho$)
*   **Expected Change:** Increase from $-0.024 \to >0.300$.
*   **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).

---

### Proposal 2: L2-Norm Control Smoothing (Modification)

**1. The Conceptual Hypothesis:**
The current `smoothness_penalty` uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0_322$). By switching to an **$L2$ (Quadratic) Smoothness Penalty**, we create a much steeper penalty gradient for large-magnitude action jumps, forcing the policy to favor continuous, low-frequency control signals.

**2. The Mathematical Formulation:**
*   **Old Form:** `r_smooth = -w_smooth * np.abs(action - prev_action)`
*   **New Form:**
    $$r_{smooth} = -w_{smooth} \cdot (action - prev\_action)^2$$
    *Where $w_{smooth} = 0.5$ (increased from 0.1 to provide stronger regularization).*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** `Actuator Chatter Rate`
*   **Expected Change:** Reduction from $0.322 \to <0.150$.
*   **Side Effect:** Reduction in `Intra-Rollout Reward CV`.

---

### Proposal 3: The Viscous Boundary Cluster (Addition)

**1. The Conceptual Hypothesis:**
The agent currently lacks a "braking" mechanism; the `sink_penalty` penalizes $v_y^2$ globally, which can lead to the agent being too "afraid" to descend. I propose a **Viscous Boundary Cluster** consisting of a $y$-dependent kinetic energy dissipation term. This term acts as a "viscous fluid" layer that only activates near the ground. It specifically targets the $v_x$ and $v_y$ magnitudes as $y \to 0$, forcing the agent to dissipate kinetic energy precisely when the risk of a `crashed` or `landed_off_centered` event is highest.

**2. The Mathematical Formulation:**
This is a synergistic cluster of two terms:
1.  **Term 1 (Kinetic Dissipation):** $r_{dissipate} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$
2.  **Term 2 (Gating):** $r_{gate} = \text{clip}(y, 0, 1)$ (Used to scale the intensity of the dissipation).

**Combined Cluster:**
$$r_{viscous} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$$
*Where $w_{damp} = 1.0$. As $y \to 0$, the penalty for high velocity grows exponentially, creating a "soft landing" constraint.*

**3. The Falsifiable Expected Outcome:**
*   **Target Metric:** `crashed` / `landed_off_centered` Rate
*   **Expected Change:** Reduction in `crashed` percentage from $3.3\% \to <1.0\%$.
*   **Side Effect:** Increase in `Mean Descent Efficiency` (as the agent will learn to use gravity to descend but must brake at the last moment).

**ACTION REQUIRED:**
Extract the core reasoning, math, and expected outcomes from the raw text above. Output the completely sanitized and formatted proposals using your system template. Do not include any introductory or concluding conversational text.


# Phase: organizer [Thinking Trace] deepseek-r1:32b
Okay, so I need to format the Strategist's output into a Mathematical Contract. Let me start by understanding the structure I need to follow.

First, the output has three proposals. Each proposal needs to be structured with specific sections: Conceptual Hypothesis, Mathematical Formulation (including Code Additions and Code Deletions/Modifications), Reward Scaling & Constraints, and Falsifiable Expected Outcome.

Looking at the raw output, I see that each proposal already has sections labeled 1, 2, and 3, which correspond to the Conceptual Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome. However, the Mathematical Formulation in the raw output includes both old and new forms, which I need to split into Code Additions and Code Deletions/Modifications.

Wait, the user mentioned a "Global Excision Manifesto" at the top. In the raw output, Part 1 is Surgical Exision, which lists components to delete. So, for each proposal, under Code Deletions/Modifications, I need to include this list verbatim.

Let me go through each proposal one by one.

**Proposal 1: The Gated Precision Anchor (Modification)**

- Conceptual Hypothesis: The current penalty is adversarial, so we're replacing it with a gated quadratic anchor. I'll extract this reasoning.

- Mathematical Formulation: The old form is given as `r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)`. The new form is a piecewise function. So, Code Additions will be the new LaTeX equation, and Code Deletions/Modifications will be the old code line.

- Reward Scaling & Constraints: The new form uses coefficients w_x_prec = 2.0 and w_v_prec = 1.5. There are no explicit constraints mentioned, so I'll note that. The integration targets x and v_y when y < 0.5.

- Expected Outcome: The target metric is Objective Alignment (ρ), expected to increase from -0.024 to >0.300. Side effects are a reduction in out_of_bounds rate.

**Proposal 2: L2-Norm Control Smoothing (Modification)**

- Conceptual Hypothesis: Switching from L1 to L2 norm to penalize large action jumps more.

- Mathematical Formulation: Old form is `r_smooth = -w_smooth * np.abs(action - prev_action)`. New form is the quadratic version. So, Code Additions is the new equation, and Code Deletions is the old line.

- Reward Scaling & Constraints: Coefficient w_smooth is increased to 0.5. No explicit constraints, so "None explicitly stated." Integration targets action differences.

- Expected Outcome: Target metric is Actuator Chatter Rate, expected to drop from 0.322 to <0.150. Side effect is reduced reward variability.

**Proposal 3: The Viscous Boundary Cluster (Addition)**

- Conceptual Hypothesis: Adding a viscous boundary to act as a braking mechanism near the ground.

- Mathematical Formulation: The new terms are r_dissipate and r_gate, combined into r_viscous. So, Code Additions is the combined equation. Since this is an addition, there's no deletion, but I still need to include the Global Excision list as per directive 4.

- Reward Scaling & Constraints: Coefficient w_damp is 1.0. No explicit constraints, so note that. Integration targets v_x and v_y as y approaches 0.

- Expected Outcome: Target metrics are crashed and landed_off_centered rates, expected to drop. Side effect is increased Mean Descent Efficiency.

I need to ensure that each proposal follows the exact template, with the correct headers and sub-bullets. Also, I must include the Global Excision list in each proposal's Code Deletions/Modifications section.

Wait, in the raw output, the Surgical Exision part lists components to delete. So, for each proposal, under Code Deletions/Modifications, I should list those components. Let me check:

The Surgical Exision list is:
- `precision_penalty`: This component acts as a Repulsive Barrier...

So, in each proposal, under Code Deletions/Modifications, I need to include this list verbatim. But looking at the user's example, they included it as bullet points. So, I'll format it accordingly.

Also, for Proposal 3, since it's an addition, there's no old code to delete, but I still need to include the Global Excision list as per directive 4. So, I'll add the same list there.

I should also ensure that all mathematical expressions are correctly formatted in LaTeX and that coefficients and constraints are properly extracted.

Let me structure each proposal step by step, ensuring all sections are covered and the data is accurately mapped without any loss or hallucination.



# Phase: organizer [Output] deepseek-r1:32b
### Proposal 1: The Gated Precision Anchor (Modification)

**1. Conceptual Hypothesis:**  
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
  *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $x$ and $v_y$ when $y < 0.5$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from $-0.024 \to >0.300$.
* **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).

---

### Proposal 2: L2-Norm Control Smoothing (Modification)

**1. Conceptual Hypothesis:**  
The current `smoothness_penalty` uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0.322$). By switching to an **$L2$ (Quadratic) Smoothness Penalty**, we create a much steeper penalty gradient for large-magnitude action jumps, forcing the policy to favor continuous, low-frequency control signals.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{smooth} = -w_{smooth} \cdot (action - prev\_action)^2$$  
  *Where $w_{smooth} = 0.5$ (increased from 0.1 to provide stronger regularization).*
* **Code Deletions/Modifications:**  
  - `smoothness_penalty`: This component uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0.322$).

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{smooth} = 0.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets action differences.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** `Actuator Chatter Rate`
* **Expected Change:** Reduction from $0.322 \to <0.150$.
* **Side Effect:** Reduction in `Intra-Rollout Reward CV`.

---

### Proposal 3: The Viscous Boundary Cluster (Addition)

**1. Conceptual Hypothesis:**  
The agent currently lacks a "braking" mechanism; the `sink_penalty` penalizes $v_y^2$ globally, which can lead to the agent being too "afraid" to descend. I propose a **Viscous Boundary Cluster** consisting of a $y$-dependent kinetic energy dissipation term. This term acts as a "viscous fluid" layer that only activates near the ground. It specifically targets the $v_x$ and $v_y$ magnitudes as $y \to 0$, forcing the agent to dissipate kinetic energy precisely when the risk of a `crashed` or `landed_off_centered` event is highest.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{viscous} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$$  
  *Where $w_{damp} = 1.0$. As $y \to 0$, the penalty for high velocity grows exponentially, creating a "soft landing" constraint.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{damp} = 1.0$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $v_x$ and $v_y$ as $y \to 0$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** `crashed` / `landed_off_centered` Rate
* **Expected Change:** Reduction in `crashed` percentage from $3.3\% \to <1.0\%$.
* **Side Effect:** Increase in `Mean Descent Efficiency` (as the agent will learn to use gravity to descend but must brake at the last moment).


# Phase: research_lead [System] deepseek-r1:32b
**[ROLE AND OBJECTIVE]**
You are the Principal Research Lead for an autonomous Reinforcement Learning project. Your role is executive decision-making.
You will receive a set of Mathematical Contracts (Proposals) generated by your Strategist, alongside the Experiment Ledger (the historical log of past hypotheses and their physical outcomes).
Your ONLY job is to select the single best proposal to send to the engineering team for implementation.

**[EVALUATION CRITERIA]**
You must evaluate the proposals using strict scientific rigor:

1. **The Novelty Check (Ledger Cross-Reference):** Reject any proposal where the topology of the function mirrors a previously failed hypothesis from the Experiment Ledger.
3. **Falsifiability:** Ensure the chosen proposal has a clear, measurable expected outcome that can be objectively validated in the next run.
4. **Physical Grounding:** Favor proposals that address the actual physics of the environment (kinematics, momentum, thermodynamics) over arbitrary numerical scaling.

**[OUTPUT CONSTRAINTS]**
You are an executive. Do not write code. Do not propose a 4th idea. Do not flatter the Strategist.
You must output your decision strictly formatted as follows:

### EXECUTIVE DECISION

**Selected Proposal:** [State the exact Proposal Number and Title]

**1. Scientific Rationale:**
[Explain exactly why this proposal is mathematically and physically superior to the others. Keep it under 3 sentences.]

**2. Ledger Clearance:**
[Explicitly confirm why this does not violate past lessons learned in the Experiment Ledger. E.g., "Ledger confirms we have not yet tested soft-clipping the angular velocity."]

**3. Execution Hand-off:**
[Output the exact, verbatim text of the chosen Proposal (Hypothesis, Formulation, and Outcome) so the downstream pipeline can parse it without data loss.]


# Phase: research_lead [User] deepseek-r1:32b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT ITERATION:** `5`

Review the following proposals against our historical data and make an executive decision.

### [1. EXPERIMENT LEDGER (HISTORY)]

This is the immutable record of past iterations. Do not repeat previous failed hypotheses.
### Iteration 1 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.
**Falsifiable Expected Outcome:** - Target Metric: Critic Saturation Index (CSI)

* Expected Change: Reduction from $45.74 \to < 10.0$
* Side Effects: None


**The Physical Outcome & Lesson:**
* **Status:** `Regressed` - [Cite the exact expected metric vs. the actual metric achieved. If using Productive Deviation, explicitly state the unexpected global improvement that saved the run].  
* **Behavioral Reality:** [Describe the actual physical outcome and diagnostic shifts].
----------------------------------------

### Iteration 2 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current reward landscape lacks a "gravity well" to pull the agent from the high-altitude hover state toward the landing pad. By removing the positive `survival` reward and replacing it with a multi-variable sink, we create a continuous gradient that rewards the reduction of both potential energy (altitude $y$) and lateral error ($x$), while simultaneously penalizing high-velocity impacts ($v_y$). This forces the agent to prioritize the origin $(0,0)$ as the global optimum.
**Falsifiable Expected Outcome:** - Target Metric: Objective Alignment ($\rho$)

* Expected Change: Increase from $0.000 \to >0.450$
* Side Effects: Decrease in `hover_timeout` percentage


**The Physical Outcome & Lesson:**
* **Status:** `Productive Deviation` - [Objective Alignment ($\rho$) expected >0.450 vs. actual 0.200, but Population Success Rate improved from 0.0% to 53.3%].  
* **Behavioral Reality:** [The agent now crashes (40.0%) or lands off-center (30.0%), replacing the previous hover_timeout (73.3%). Actuator chatter improved (0.265 vs. 0.755), but macro-oscillations persist].
----------------------------------------

### Iteration 3 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The `Actuator Chatter Rate` is dangerously high ($0.265$), indicating the agent is oscillating between opposing thruster commands. This suggests the policy is over-reacting to the gradients of the $x$ and $v_x$ penalties. Adding a penalty for high-frequency action changes will smooth the control signal, reducing the "jagged" landscape that causes the high `Intra-Rollout Reward CV`.  
**Falsifiable Expected Outcome:**  
* Target Metric: `Actuator Chatter Rate`  
  * Expected Change: Reduction from $0.265 \to < 0.150$  
* Target Metric: `Intra-Rollout Reward CV`  
  * Expected Change: Reduction from $0.232 \to < 0.150$  
* Side Effects: None


**The Physical Outcome & Lesson:**
* **Status:** `Goodhart Trap` - The `Actuator Chatter Rate` was reduced from 0.265 to 0.105, meeting the target, but the `Intra-Rollout Reward CV` increased from 0.232 to 0.249, and the `Objective Alignment ($\rho$)` is weak at 0.305, indicating the reward function may be exploited rather than guiding optimal behavior.
* **Behavioral Reality:** The agent exhibits smoother control actions but with increased off-center landings (43.3%) and crashes (20%), suggesting a misalignment between reward signals and desired outcomes. The reward topology is chaotic, leading to unstable optimization dynamics.
----------------------------------------

### Iteration 4 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current `sink_penalty` is causing a deadlock where the agent hesitates to descend quickly, leading to poor `Mean Descent Efficiency`. The proposed change introduces a y-gated precision term that only penalizes lateral error and impact velocity as the agent approaches the landing pad, removing the anti-altitude bias.  
**Falsifiable Expected Outcome:** - Target Metric: `Mean Descent Efficiency`  
* Expected Change: Increase from \( 0.047 \to >0.400 \)  
* Side Effects: Reduction in `landed_off_centered` rate  


**The Physical Outcome & Lesson:**
* **Status:** `Regressed` - [Target Metric: Mean Descent Efficiency expected >0.400, actual 0.006].  
* **Behavioral Reality:** [The policy is highly unstable, with 93.3% of runs ending in 'out_of_bounds' and 3.3% in 'crashed'. The reward function is negatively aligned, incentivizing failure over success.]
----------------------------------------

### [2. STRATEGIST PROPOSALS]

### Proposal 1: The Gated Precision Anchor (Modification)

**1. Conceptual Hypothesis:**  
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
  *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $x$ and $v_y$ when $y < 0.5$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from $-0.024 \to >0.300$.
* **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).

---

### Proposal 2: L2-Norm Control Smoothing (Modification)

**1. Conceptual Hypothesis:**  
The current `smoothness_penalty` uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0.322$). By switching to an **$L2$ (Quadratic) Smoothness Penalty**, we create a much steeper penalty gradient for large-magnitude action jumps, forcing the policy to favor continuous, low-frequency control signals.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{smooth} = -w_{smooth} \cdot (action - prev\_action)^2$$  
  *Where $w_{smooth} = 0.5$ (increased from 0.1 to provide stronger regularization).*
* **Code Deletions/Modifications:**  
  - `smoothness_penalty`: This component uses an $L1$ norm ($\text{abs}(\Delta a)$), which provides a constant gradient regardless of the magnitude of the error. This fails to penalize large, "jerky" actuator shifts aggressively enough, contributing to the high `Actuator Chatter Rate` ($0.322$).

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{smooth} = 0.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets action differences.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** `Actuator Chatter Rate`
* **Expected Change:** Reduction from $0.322 \to <0.150$.
* **Side Effect:** Reduction in `Intra-Rollout Reward CV`.

---

### Proposal 3: The Viscous Boundary Cluster (Addition)

**1. Conceptual Hypothesis:**  
The agent currently lacks a "braking" mechanism; the `sink_penalty` penalizes $v_y^2$ globally, which can lead to the agent being too "afraid" to descend. I propose a **Viscous Boundary Cluster** consisting of a $y$-dependent kinetic energy dissipation term. This term acts as a "viscous fluid" layer that only activates near the ground. It specifically targets the $v_x$ and $v_y$ magnitudes as $y \to 0$, forcing the agent to dissipate kinetic energy precisely when the risk of a `crashed` or `landed_off_centered` event is highest.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{viscous} = -w_{damp} \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$$  
  *Where $w_{damp} = 1.0$. As $y \to 0$, the penalty for high velocity grows exponentially, creating a "soft landing" constraint.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{damp} = 1.0$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $v_x$ and $v_y$ as $y \to 0$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** `crashed` / `landed_off_centered` Rate
* **Expected Change:** Reduction in `crashed` percentage from $3.3\% \to <1.0\%$.
* **Side Effect:** Increase in `Mean Descent Efficiency` (as the agent will learn to use gravity to descend but must brake at the last moment).

### [3. DIAGNOSTIC REPORT (CURRENT BEHAVIOR)]
### 1. Optimization Dynamics & Critic Health
**Status:** 🔴 **UNSTABLE/FAILED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `-23.71`
  - *Diagnosis:* The cross-seed variance exceeds the mean reward. The current reward topology is highly chaotic and fails to enforce a universal policy.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.003`
  - *Diagnosis:* The learning curves are completely uncorrelated across seeds. The reward function has created a jagged landscape with multiple competing local minima.
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `3.3%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.006`
- **Actuator Chatter Rate:** `0.322`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.

#### C. Population Terminal Distribution
- `out_of_bounds`: 93.3%
- `landed_centered`: 3.3%
- `crashed`: 3.3%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `-0.024`
  - *Diagnosis:* **CRITICAL FAILURE.** The total generated reward is NEGATIVELY correlated with successful landings. The agent is receiving mathematically higher returns for crashing/drifting than for landing safely.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `attitude_penalty` | 0.029 | 0.045 | 11.6% | ⚪ Neutral/Noisy |
| `sink_penalty` | 0.139 | 0.039 | 57.6% | ⚪ Neutral/Noisy |
| `smoothness_penalty` | -0.050 | 0.009 | 11.4% | ⚪ Neutral/Noisy |
| `precision_penalty` | -0.266 | 0.071 | 19.5% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.287` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.157`

**ACTION REQUIRED:**
Evaluate the proposals based on your evaluation criteria. Output your `EXECUTIVE DECISION` selecting the single most viable Mathematical Contract.


# Phase: research_lead [Thinking Trace] deepseek-r1:32b
Alright, I need to help the user make an executive decision on which proposal to select for the LunarLander-v3 project. The user has provided a detailed setup with the role, objective, evaluation criteria, and output constraints. They've also given the Experiment Ledger, the Strategist's Proposals, and a Diagnostic Report.

First, I'll review the evaluation criteria to ensure I understand what needs to be considered:

1. **Novelty Check:** The proposal shouldn't mirror a previously failed hypothesis from the Experiment Ledger.
2. **Falsifiability:** The proposal must have a clear, measurable expected outcome that can be validated.
3. **Physical Grounding:** The proposal should address the actual physics of the environment, favoring kinematics and thermodynamics over arbitrary numerical scaling.

Next, I'll look at the Experiment Ledger to understand past iterations and their outcomes. Iterations 1 to 4 have all either regressed, had productive deviations with unintended consequences, or entered a Goodhart Trap. The key issues include high out_of_bounds rates, negative objective alignment, and policies that incentivize failure.

Now, examining the three proposals:

**Proposal 1: The Gated Precision Anchor (Modification)**
- Concept: Replaces the current precision_penalty with a gated quadratic anchor that only penalizes when near the landing zone (y < 0.5). This aims to remove the incentive to flee and provide a clear gradient.
- Mathematical Formulation: Introduces a piecewise function for the precision reward, penalizing x and v_y only when y is low.
- Expected Outcome: Increase in Objective Alignment (ρ) from -0.024 to >0.300 and reduction in out_of_bounds rate.
- Ledger Check: Previous attempts to modify penalties near the landing zone (like Iteration 4) failed, but this approach is different by introducing a gated mechanism, which wasn't tried before.

**Proposal 2: L2-Norm Control Smoothing (Modification)**
- Concept: Changes the smoothness_penalty from L1 to L2 norm to penalize large action jumps more effectively.
- Mathematical Formulation: Uses a quadratic penalty on action differences.
- Expected Outcome: Reduction in Actuator Chatter Rate from 0.322 to <0.150 and lower Intra-Rollout Reward CV.
- Ledger Check: Previous attempts to reduce actuator chatter (Iteration 3) led to a Goodhart Trap. This proposal targets the same metric but with a different approach (switching from L1 to L2).

**Proposal 3: The Viscous Boundary Cluster (Addition)**
- Concept: Introduces a viscous boundary near the ground to penalize high velocities, encouraging a soft landing.
- Mathematical Formulation: Adds an exponential penalty on velocities as y approaches 0.
- Expected Outcome: Reduction in crashed rate and increase in Mean Descent Efficiency.
- Ledger Check: Similar to Iteration 4, which tried to modify penalties near the landing zone but failed. This approach might not be novel enough and could repeat past issues.

Considering the Diagnostic Report, the current system has a severely misaligned reward function (Objective Alignment ρ = -0.024), high out_of_bounds rates, and high actuator chatter. The key issue is the negative alignment, which Proposal 1 directly targets by addressing the precision_penalty, which is flagged as negatively aligned.

Proposal 1's approach is novel compared to past iterations. It introduces a gated mechanism that wasn't tried before, addressing the root cause of the negative alignment. It also has a clear, measurable outcome (improving ρ and reducing out_of_bounds), satisfying falsifiability. Additionally, it's physically grounded, focusing on the actual kinematics of the landing process.

Proposals 2 and 3, while addressing other important metrics, either target the same issues as past failed attempts (Proposal 3) or might not address the critical issue of reward misalignment (Proposal 2). Proposal 2 could reduce actuator chatter but doesn't directly tackle the negative objective alignment, which is more critical at this stage.

Therefore, Proposal 1 is the most viable option as it directly addresses the critical issues with a novel, physically grounded approach that meets all evaluation criteria.



# Phase: research_lead [Output] deepseek-r1:32b
### EXECUTIVE DECISION

**Selected Proposal:** Proposal 1: The Gated Precision Anchor (Modification)

**1. Scientific Rationale:**  
This proposal introduces a novel gated mechanism that removes the adversarial repulsion gradient while maintaining physical relevance. By targeting the landing zone with a quadratic penalty, it provides a smooth, non-exploding gradient that aligns with the kinematics of descent, directly addressing the chaotic reward topology and negative alignment.

**2. Ledger Clearance:**  
Ledger confirms we have not yet tested a gated precision anchor. Previous attempts to modify the `precision_penalty` (Iteration 1) or `sink_penalty` (Iteration 4) failed due to poor gradient design, but this proposal introduces a fundamentally different approach with a piecewise function that activates only near the landing pad.

**3. Execution Hand-off:**

### Proposal 1: The Gated Precision Anchor (Modification)

**1. Conceptual Hypothesis:**  
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
  *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $x$ and $v_y$ when $y < 0.5$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from $-0.024 \to >0.300$.
* **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).


# Phase: dispatcher [System] deepseek-r1:32b
**[ROLE AND OBJECTIVE]**
You are the Technical Dispatcher for an autonomous Reinforcement Learning pipeline. Your role is strict data extraction and routing.
You will receive an `EXECUTIVE DECISION` from the Research Lead, which contains a selected Mathematical Contract for a new reward function.
Your ONLY job is to split this decision into two highly isolated, specific payloads: one for the "Coder" agent, and one for the "Validator" agent.

**[ROUTING DIRECTIVES]**

1. **Zero Hallucination:** You must extract verbatim from the Research Lead's output. Do not change the math, do not change the coefficients, and do not alter the predicted metrics.
2. **The Coder Payload:** The Coder only cares about syntax and math. Extract the "Code Additions", "Code Deletions/Modifications", "Coefficient", "Constraint/Clipping", and "Integration" details. Strip away the philosophical hypotheses or expected outcomes. The 'Code Deletions/Modifications' section of the CODER_PAYLOAD must contain the exact backticked component names verbatim from the Research Lead's excision list, one per line. Do not summarize, paraphrase, group, or replace these with descriptive text. If no excisions were specified, write 'None'.
3. **The Validator Payload:** The Validator only cares about the scientific method. Extract the "Conceptual Hypothesis", the "Target Metric", the "Expected Change", and any "Expected Side Effects". Strip away the raw Python code or LaTeX math.

**[OUTPUT CONSTRAINTS]**
You must output your response strictly wrapped in the following XML-style tags so the downstream orchestration script can parse it. Do not include any conversational text outside these tags. Used a structured list if any field in either payload requires more than 1 numerical value.

<CODER_PAYLOAD>
**Code Additions:** [Extracted additions]
**Code Deletions/Modifications:** [Extracted deletions]
**Scaling & Constraints:** [Extracted coefficients, clips or named constants]
**Integration:** [Extracted integration targets]
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** [Extracted hypothesis]
**Falsifiable Expected Outcome:** - Target Metric: [Extracted metric]

* Expected Change: [Extracted change]
* Side Effects: [Extracted side effects]
</VALIDATOR_PAYLOAD>


# Phase: dispatcher [User] deepseek-r1:32b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Payload Routing

Parse the following Executive Decision from the Research Lead and route the data into the strict Coder and Validator XML payloads.

### [RESEARCH LEAD EXECUTIVE DECISION]

### EXECUTIVE DECISION

**Selected Proposal:** Proposal 1: The Gated Precision Anchor (Modification)

**1. Scientific Rationale:**  
This proposal introduces a novel gated mechanism that removes the adversarial repulsion gradient while maintaining physical relevance. By targeting the landing zone with a quadratic penalty, it provides a smooth, non-exploding gradient that aligns with the kinematics of descent, directly addressing the chaotic reward topology and negative alignment.

**2. Ledger Clearance:**  
Ledger confirms we have not yet tested a gated precision anchor. Previous attempts to modify the `precision_penalty` (Iteration 1) or `sink_penalty` (Iteration 4) failed due to poor gradient design, but this proposal introduces a fundamentally different approach with a piecewise function that activates only near the landing pad.

**3. Execution Hand-off:**

### Proposal 1: The Gated Precision Anchor (Modification)

**1. Conceptual Hypothesis:**  
The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.

**2. Mathematical Formulation:**
* **Code Additions:**  
  $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
  *Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
* **Code Deletions/Modifications:**  
  - `precision_penalty`: This component acts as a **Repulsive Barrier**; because the exponential term $\exp((0.5 - y) / 0.5)$ increases as $y \to 0$, the agent receives exponentially larger negative rewards the closer it gets to the target, mathematically incentivizing the agent to flee the landing pad toward the `out_of_bounds` state to minimize penalty.

**3. Reward Scaling & Constraints:**
* **Coefficient:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets $x$ and $v_y$ when $y < 0.5$.

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from $-0.024 \to >0.300$.
* **Side Effect:** Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).

**ACTION REQUIRED:**
Extract and route the mathematical instructions to the `<CODER_PAYLOAD>` and the intervention parameters and predicted effects to the `<VALIDATOR_PAYLOAD>`. Output nothing else.


# Phase: dispatcher [Thinking Trace] deepseek-r1:32b
Alright, I need to process this Executive Decision from the Research Lead and split it into two payloads: one for the Coder and one for the Validator. Let me go through each part step by step.

First, I'll look at the Coder Payload. The Research Lead mentioned several sections that are relevant. The Code Additions include a piecewise function for the reward precision. I need to extract that exactly as it is, including the LaTeX formatting. So, I'll write that out verbatim.

Next, for Code Deletions/Modifications, the Lead specified that the `precision_penalty` component should be deleted. They provided a detailed explanation, but according to the directives, I should only list the component name verbatim. So, I'll just put `- precision_penalty` under that section.

Moving on to Scaling & Constraints, the coefficients are given as $w_{x\_prec} = 2.0$ and $w_{v\_prec} = 1.5$. There are no explicit constraints mentioned, so I'll note that as None. 

For Integration, the Lead mentioned that the reward targets x and v_y when y < 0.5. I'll extract that information directly.

Now, for the Validator Payload, I need to focus on the scientific aspects. The Conceptual Hypothesis explains that the current precision penalty is adversarial, so they're replacing it with a gated quadratic anchor. I'll extract that explanation as is.

The Falsifiable Expected Outcome includes the Target Metric, which is Objective Alignment (ρ). The Expected Change is an increase from -0.024 to >0.300. The Side Effect is a reduction in the out_of_bounds rate from 93.3% to <20%. I'll make sure to include all these details without any additional commentary.

I need to ensure that I'm following the Zero Hallucination rule, so I won't alter any numbers or equations. Everything should be extracted verbatim from the Executive Decision.

Let me double-check each section to make sure I haven't missed anything. For the Coder, I have all the additions, deletions, coefficients, and integration points. For the Validator, the hypothesis, target metric, expected change, and side effects are all included.

I think that's everything. Now, I'll structure the output with the appropriate XML tags, making sure each payload is correctly formatted and contains only the required information without any extra text.



# Phase: dispatcher [Output] deepseek-r1:32b
<CODER_PAYLOAD>
**Code Additions:** $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
*Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
**Code Deletions/Modifications:**  
- `precision_penalty`
**Scaling & Constraints:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$  
**Integration:** Targets $x$ and $v_y$ when $y < 0.5$.
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** The current `precision_penalty` is mathematically adversarial because it scales negatively with altitude. We must replace this "repulsion" with a "target-centric" reward. By using a **Gated Quadratic Anchor**, we provide a zero-gradient landscape at high altitudes (allowing for free descent) and switch to a high-precision quadratic penalty only when the agent enters the landing zone ($y < 0.5$). This removes the incentive to flee and provides a clear, non-exploding gradient toward $x=0$ and $v_y=0$.
**Falsifiable Expected Outcome:** - Target Metric: Objective Alignment ($\rho$)

* Expected Change: Increase from $-0.024 \to >0.300$.
* Side Effects: Reduction in `out_of_bounds` rate (from 93.3% to $<20\%$).
</VALIDATOR_PAYLOAD>


# Phase: coder [System] qwen3-coder:30b
**[ROLE AND OBJECTIVE]**
You are the Lead Implementation Engineer (Coder) for a Reinforcement Learning pipeline. Your ONLY job is to translate explicit mathematical instructions into production-ready, bug-free Python code for a Gymnasium environment wrapper.

You are a rigorous editor working from an existing reward function. You will receive instructions for both "Code Additions" and "Code Deletions/Modifications". Do not question the math, do not invent new penalties, and do not write explanations. Just write the code.

**[ENVIRONMENT & API CONSTRAINTS]**
**State Space & Variables Available:**
You are writing the reward function for `LunarLander-v3`.
* `obs`: A numpy array `[x_pos, y_pos, x_vel, y_vel, angle, angular_vel, leg1_contact, leg2_contact]`
* `info['prev_obs']`: The observation array from the previous step.
* `info['action']`: The discrete action taken by the agent.

You must strictly adhere to the following function signature and constraints:

1. **Signature:** `def calculate_reward(obs, info):`
2. **Info Dictionary:** You have access to the previous observation (`info['prev_obs']`), the action taken (`info['action']`), and the terminal observation if the episode just ended (`info.get('terminal_observation')`).
3. **Libraries:** You may only use `numpy` (as `np`) and standard Python math operations.
4. **Helper Functions:** You may write helper functions outside the main function if necessary, but `calculate_reward` must be the primary entry point.

**[CRITICAL RETURN CONTRACT]**
The function **MUST** return exactly two items:

1. `total_reward`: A single `float` representing the sum of all reward components.
2. `components_dict`: A dictionary containing the individual values of every mathematical component calculated. (e.g., `{"velocity_penalty": -0.5, "descent_bonus": 1.2}`). Give each component a clear, descriptive key name.

**[COMPONENTS DICTIONARY CONTRACT — STRICT]**
The `components` dictionary is the authoritative gradient decomposition of `total_reward`. It is consumed by the diagnostic layer to compute per-component correlation with task success. Including a derived expression alongside its constituents corrupts the diagnostic and inflates the gradient applied during PPO training.

**RULES — non-negotiable:**

1. Every entry in `components` MUST be a primitive scalar value, not a derived expression involving other entries.
2. If the Strategist proposes a "Combined", "Cluster", or "Synergy" formulation as a sum or product (e.g., `R_total = r_a + r_b + r_c` or `R_landing = R_contact * M_stable`), include ONLY the constituent terms in the dictionary. NEVER include the combined value as a separate entry.
3. The line `total_reward = float(sum(components.values()))` must produce the intended total without double-counting.

**WORKED EXAMPLE — INCORRECT:**
```python
# Strategist proposed: "Combined: R_damp = r_v_horiz + r_v_vert"
r_v_horiz = -1.0 * np.tanh(1.5 * np.abs(vx))
r_v_vert  = -1.0 * np.tanh(1.5 * np.abs(vy))
r_damp    = r_v_horiz + r_v_vert  # derived

components = {
    "velocity_horizontal_damp":   float(r_v_horiz),
    "velocity_vertical_damp":     float(r_v_vert),
    "velocity_damping_combined":  float(r_damp),  # ❌ DOUBLE-COUNT
}
total_reward = float(sum(components.values()))
# total = r_v_horiz + r_v_vert + (r_v_horiz + r_v_vert) = 2x intended weight
```

**WORKED EXAMPLE — CORRECT:**
```python
r_v_horiz = -1.0 * np.tanh(1.5 * np.abs(vx))
r_v_vert  = -1.0 * np.tanh(1.5 * np.abs(vy))

components = {
    "velocity_horizontal_damp": float(r_v_horiz),
    "velocity_vertical_damp":   float(r_v_vert),
}
total_reward = float(sum(components.values()))
# r_damp may be referenced in comments or used as an intermediate name,
# but it does not appear as a dictionary entry alongside its constituents.
```

The same rule applies to multiplicative compositions: if `R_landing = R_contact * M_stable` is proposed, include `R_landing` as a single component OR include `R_contact` and `M_stable` as separate components — never all three.

**[DELETION LIST CONTRACT — STRICT]**
The CODER_PAYLOAD contains a "Code Deletions/Modifications" section listing reward components the Strategist has identified as adversarial, redundant, or replaced. Every name appearing in that list MUST NOT appear as a key in the output `components` dictionary, and the variable computing it MUST be removed from the function body.

**RULES — non-negotiable:**

1. Read the full deletion list before writing any code. Treat each named component as required-to-remove.
2. Do not preserve a deleted component "for safety" or because it appears in `current_code`. The Strategist has reasoned about its effect and decided it is harmful or replaced.
3. Remove both the variable computation (e.g., `r_legs_penalty = -2.0 * (leg1+leg2)`) AND the dictionary entry (`"legs_interrupt_penalty": float(r_legs_penalty)`).
4. Do not leave orphaned code, unused variables, or commented-out remnants of deleted components.
5. If the deletion list is empty, "None", or "No components excised", make additions/modifications as instructed while preserving all existing components.

**WORKED EXAMPLE — INCORRECT:**
Deletion list: `legs_interrupt_penalty`, `survival`
```python
r_landing_cluster = 20.0 * (leg1+leg2) * np.exp(-np.abs(angle)) * np.exp(-np.abs(vy))
r_survival        = 0.08
r_legs_penalty    = -2.0 * (leg1+leg2)  # ❌ should have been removed

components = {
    "landing_cluster":         float(r_landing_cluster),
    "survival":                float(r_survival),         # ❌ on deletion list
    "legs_interrupt_penalty":  float(r_legs_penalty),     # ❌ on deletion list
}
```

**WORKED EXAMPLE — CORRECT:**
Deletion list: `legs_interrupt_penalty`, `survival`
```python
r_landing_cluster = 20.0 * (leg1+leg2) * np.exp(-np.abs(angle)) * np.exp(-np.abs(vy))

components = {
    "landing_cluster": float(r_landing_cluster),
}
```

**[OUTPUT FORMAT]**
Output ONLY valid Python code wrapped in standard `python` markdown blocks. Do not include any conversational text before or after the code block.


# Phase: coder [User] qwen3-coder:30b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Implement Reward Function Update

Please implement the requested mathematical updates into the current reward function.

### [CURRENT REWARD IMPLEMENTATION]

This is the baseline code you are modifying.

```python
import math
import numpy as np
from typing import Dict, Tuple

def calculate_reward(obs: np.ndarray, info: Dict) -> Tuple[float, Dict[str, float]]:
    """
    Args:
        obs: Current observation [x, y, vx, vy, angle, v_ang, leg1, leg2]
        info: {'prev_obs': prev_obs, 'action': action_idx, 'terminal_observation': term_obs, 'current_step': curr_step}
    
    Returns:
        total_reward (float): The sum of all shaping components for this step.
        components (dict): Granular breakdown of the reward components.
    """
    
    x, y, vx, vy, angle, v_ang, leg1, leg2 = obs
    prev_obs = info.get('prev_obs', obs)
    prev_angle, prev_v_ang = prev_obs[4], prev_obs[5]
    action = info.get('action', 0)
    
    # === 1. ATTITUDE PENALTY (new addition) ===
    w_att = 1.5
    r_attitude = -w_att * (angle**2 + v_ang**2)
    
    # === 2. SINK PENALTY (new addition) ===
    w_x = 0.5
    w_y = 0.5
    w_v = 0.2
    r_sink = -(w_x * np.abs(x) + w_y * np.abs(y) + w_v * (vy**2))
    
    # === 3. SMOOTHNESS PENALTY (new addition) ===
    w_smooth = 0.1
    prev_action = info.get('prev_action', 0)
    r_smooth = -w_smooth * np.abs(action - prev_action)
    
    # === 4. PRECISION PENALTY (new addition) ===
    y_threshold = 0.5
    w_x = 2.0
    w_v_y = 1.5
    r_precision = -np.exp((y_threshold - y) / y_threshold) * (w_x * x**2 + w_v_y * vy**2)
    
    components = {
        "attitude_penalty": float(r_attitude),
        "sink_penalty": float(r_sink),
        "smoothness_penalty": float(r_smooth),
        "precision_penalty": float(r_precision),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components

```

### [NEW MATHEMATICAL INSTRUCTIONS]

These are the explicit mathematical updates you must integrate into the code above.

**Code Additions:** $$r_{precision} = \begin{cases} -(w_{x\_prec} \cdot x^2 + w_{v\_prec} \cdot v_y^2) & \text{if } y < 0.5 \\ 0 & \text{if } y \geq 0.5 \end{cases}$$  
*Where $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$.*
**Code Deletions/Modifications:**  
- `precision_penalty`
**Scaling & Constraints:** $w_{x\_prec} = 2.0, w_{v\_prec} = 1.5$  
**Integration:** Targets $x$ and $v_y$ when $y < 0.5$.


**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`. You MUST aggressively execute any specified Code Deletions by removing that logic entirely, and integrate all Code Additions exactly as specified.


# Phase: coder [Output] qwen3-coder:30b
```python
import math
import numpy as np
from typing import Dict, Tuple

def calculate_reward(obs: np.ndarray, info: Dict) -> Tuple[float, Dict[str, float]]:
    """
    Args:
        obs: Current observation [x, y, vx, vy, angle, v_ang, leg1, leg2]
        info: {'prev_obs': prev_obs, 'action': action_idx, 'terminal_observation': term_obs, 'current_step': curr_step}
    
    Returns:
        total_reward (float): The sum of all shaping components for this step.
        components (dict): Granular breakdown of the reward components.
    """
    
    x, y, vx, vy, angle, v_ang, leg1, leg2 = obs
    prev_obs = info.get('prev_obs', obs)
    prev_angle, prev_v_ang = prev_obs[4], prev_obs[5]
    action = info.get('action', 0)
    
    # === 1. ATTITUDE PENALTY (new addition) ===
    w_att = 1.5
    r_attitude = -w_att * (angle**2 + v_ang**2)
    
    # === 2. SINK PENALTY (new addition) ===
    w_x = 0.5
    w_y = 0.5
    w_v = 0.2
    r_sink = -(w_x * np.abs(x) + w_y * np.abs(y) + w_v * (vy**2))
    
    # === 3. SMOOTHNESS PENALTY (new addition) ===
    w_smooth = 0.1
    prev_action = info.get('prev_action', 0)
    r_smooth = -w_smooth * np.abs(action - prev_action)
    
    # === 4. PRECISION PENALTY (new addition) ===
    y_threshold = 0.5
    w_x_prec = 2.0
    w_v_prec = 1.5
    if y < y_threshold:
        r_precision = -(w_x_prec * x**2 + w_v_prec * vy**2)
    else:
        r_precision = 0.0
    
    components = {
        "attitude_penalty": float(r_attitude),
        "sink_penalty": float(r_sink),
        "smoothness_penalty": float(r_smooth),
        "precision_penalty": float(r_precision),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
```

