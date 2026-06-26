# Cognition prompts and calls: Iteration:9


# Phase: validator [System] deepseek-r1:32b
**[ROLE AND OBJECTIVE]**
You are the Post-Mortem Analyst (Validator) for an autonomous Reinforcement Learning pipeline. You act as the system's evolutionary memory.
Your objective is to evaluate a previously proposed intervention against the newly generated Diagnostic Report to determine the behavioral impact from the mathematical changes.

**[BEHAVIORAL HIERARCHY]**
Centered Landing > Off-Center Landing > Hover Timeout > Out of Bounds > Crash. 
* Moving Up Hierarchy is behavioral progress.
* Moving Down Hierarchy is behavioral regression.

**[FLOOR RULES - apply before checking metrics]**

- **FLOOR RULES SUPERSEDE ALL OTHER CHECKS.** Apply these first. If a Floor Rule applies, it determines the verdict boundary and cannot be overridden by the Quantitative, Holistic, or Goodhart checks — those inform the description only.
- Success Rate Moved up ≥20pp → verdict ∈ {`Validated`, `Productive Deviation`}
- Success Rate Moved down ≥20pp → verdict at minimum `Regressed`
- Lateral OR moved up (any size) → `Regressed` prohibited
- BEHAVIORAL HIERARCHY is primary, metrics secondary. When they conflict, BEHAVIORAL HIERARCHY wins.

**[EVALUATION DIRECTIVES]**

1. **Quantitative Check:** Look at the `Target Metric` from the Hypothesis. Did it achieve the `Expected Change` in the new Diagnostic Report?
2. **Holistic Check (Goodhart's Law):** Did the agent hack the reward? Even if the specific target metric improved, you must check the `Population Success Rate`, `Terminal Distribution`, and `Objective Alignment ($\rho$)`. 
3. **Progress-Oriented Evaluation (The Unexpected):** Physical flight dynamics are highly coupled. If the specific target metric was missed, burt the overall `Population Success Rate` or global $\rho$ improved significantly due to emergent, productive behaviors, you must recognize the physical progress. Do not rigidly refute a run that generated a superior flight policy.
4. **Compression:** Distill the entire experiment into a dense, immutable historical record for the Experiment Ledger.

**[OUTPUT CONSTRAINTS]**
You must output EXACTLY two bullet points formatted strictly as follows. Do not include conversational filler, introductory text, or concluding remarks.

* **Status:** [`Validated` / `Regressed` / `Mixed` / `Goodhart Trap` / `Productive Deviation`] - [Cite the exact expected metric vs. the actual metric achieved. If using Productive Deviation, explicitly state the unexpected global improvement that saved the run].
* **Behavioral Reality:** [Describe the actual physical outcome and diagnostic shifts].


# Phase: validator [User] deepseek-r1:32b
**TARGET SYSTEM:** LunarLander-v3
**ITERATION EVALUATED:** `9`

Audit the outcome of the previous reward intervention to update the Intervention Log.

### [1. THE EXPERIMENT PARAMETERS (FROM PREVIOUS ITERATION)]

This was the proposed reward intervention and its predicted effect.


**Conceptual Hypothesis:** The current landing_precision component is gated by a hard threshold (y < 0.25). In optimization, a step-function gate creates a massive discontinuity in the reward gradient. When the agent crosses y=0.25, the reward landscape shifts instantly from 0 to approximately -25(v_x^2 + v_y^2). This "reward cliff" induces the severe Actuator Chatter Rate (0.565) as the policy attempts to navigate a non-differentiable boundary. Replacing the hard gate with a linear ramp provides a continuous gradient, allowing the agent to "feel" the settling incentive gradually.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate
* Expected Change: ↓ from 0.565 to <0.25
* Side Effects: None

- Target Metric: Intra-Rollout Reward CV
* Expected Change: ↓ from 0.466 to <0.30
* Side Effects: None


### [2. THE BASELINE STATE (BEFORE THE CHANGE)]

This is the verified diagnostic state of the agent **before** the Iteration `9` reward modifications were applied. All delta comparisons must be grounded in these values — do not estimate or recall prior states from memory.



#### A. Universal Policy Robustness
- **Population Success Rate:** `99.0%`
  - *Diagnosis:* Exceptional robustness. The policy flawlessly handles the environment across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.005`
- **Actuator Chatter Rate:** `0.565`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.

#### C. Population Terminal Distribution
- `landed_centered`: 79.0%
- `landed_but_slid_into_valley`: 9.0%
- `landed_off_centered_timeout`: 7.0%
- `landed_off_centered`: 4.0%
- `hover_timeout`: 1.0%

### [3. THE ACTUAL RESULTS (AFTER THE CHANGE)]

This is the deterministic, mathematically extracted performance data of the agent trained on that intervention.

### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0640`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0440`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.178`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `81.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.004`
- **Actuator Chatter Rate:** `0.595`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `landed_but_slid_into_valley`: 36.0%
- `landed_centered`: 36.0%
- `hover_timeout`: 11.0%
- `crashed`: 8.0%
- `landed_off_centered`: 6.0%
- `landed_off_centered_timeout`: 3.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-556.557`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.606`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.546 | 0.178 | 29.5% | 🟢 Optimal |
| `vertical_penalty` | 0.386 | 0.123 | 3.9% | 🟢 Optimal |
| `leg_maintenance` | 0.546 | 0.261 | 23.1% | 🟢 Optimal |
| `orientation_penalty` | 0.310 | 0.135 | 7.1% | 🟢 Optimal |
| `velocity_stability` | 0.446 | 0.136 | 15.6% | 🟢 Optimal |
| `lateral_viscosity` | 0.294 | 0.094 | 1.2% | 🟢 Optimal |
| `landing_precision` | 0.277 | 0.143 | 19.6% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.476` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.627`

**ACTION REQUIRED:**
Audit the intervention outcome against the Baseline and Actual Results. Output the strict 3-bullet-point Intervention Log entry to serve as the evolutionary memory for the next iteration.


# Phase: validator [Thinking Trace] deepseek-r1:32b

Okay, so I'm trying to figure out how to audit this reward intervention for the LunarLander-v3 system. The goal is to see if the changes made in Iteration 9 were successful or if they caused any regressions. Let me break down the problem step by step.

First, I need to understand the hypothesis and expected outcomes. The idea was to replace a hard threshold in the landing_precision component with a linear ramp to smooth out the reward gradient. This was supposed to reduce the actuator chatter rate and the intra-rollout reward CV. The expected actuator chatter rate was supposed to drop from 0.565 to below 0.25, and the intra-rollout CV from 0.466 to below 0.30.

Looking at the baseline before Iteration 9, the population success rate was 99.0%, which is excellent. The actuator chatter rate was 0.565, which was problematic because it caused severe chattering. The terminal distribution showed that most landings were centered, with a few off-center and a small hover timeout.

After the intervention, the population success rate dropped to 81.0%, which is a significant regression. The actuator chatter rate actually increased to 0.595, which is worse than before. The terminal distribution changed too, with a lot more cases where the lander slid into the valley, more crashes, and more hover timeouts. The intra-rollout reward CV was 0.476, which is higher than the expected improvement of below 0.30.

Now, applying the floor rules first. The success rate moved down by 18 percentage points (from 99% to 81%), which is just shy of the 20pp threshold. However, since it's a significant drop, even though not meeting the exact 20pp, the verdict might still be regressed. Additionally, the actuator chatter rate didn't improve as expected—it got worse.

The quantitative check fails because the target metrics didn't meet the expected changes. The actuator chatter rate went up, and the intra-rollout CV also increased. The holistic check is also concerning because even though the specific metrics didn't improve, the overall success rate dropped, and the terminal distribution shows more crashes and timeouts, indicating that the policy became less stable.

The progress-oriented evaluation doesn't help here because there's no unexpected improvement; instead, there's a clear regression in stability and success rate. So, the verdict is regressed because the success rate dropped significantly, and the actuator chatter rate didn't improve.

For the behavioral reality, the lander is now crashing more, sliding into valleys, and timing out, which means the policy isn't handling the landing as effectively as before. The actuator chattering is still a problem, and there are new issues with lateral oscillations.

Putting it all together, the intervention didn't work as intended. It made the actuator chatter worse and caused the policy to be less successful and more unstable. This is a clear regression, so the verdict is regressed, and the behavioral reality reflects the increased crashes and instability.



# Phase: validator [Output] deepseek-r1:32b


**Status:** `Regressed` - The actuator chatter rate increased from 0.565 to 0.595, and the population success rate dropped from 99.0% to 81.0%, indicating a significant regression in stability and performance.

**Behavioral Reality:** The policy now exhibits more crashes (8.0%), hover timeouts (11.0%), and cases where the lander slides into the valley (36.0%), indicating increased instability and reduced success in achieving centered landings. The actuator chatter rate remains severe, and macro-oscillations are detected, suggesting the reward gradient adjustments did not achieve the intended smoothing.


# Phase: strategist [System] gemma4:26b-mlx
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

Components are salvageable through rescaling, sign inversion, or gating — and salvaging preserves shaping information the next iteration cannot recover. Excise only when the *functional form itself* is incoherent with the task. **No flag in the diagnostic table is by itself grounds for excision** — flags describe statistical findings, not actions. The decision to delete versus modify is yours, and must be reasoned from the component's mathematical form against the observed physical failure.

List components you are excising, with one sentence of justification per component stating why no transformation rescues the form.

**PART 2: 3 PROPOSALS (Additions or Modifications)**

Output exactly **3 distinct proposals**. Every proposal is one of two types:

- **Addition:** introduce a new functional identity — either a single term, or a set of terms whose learning signal emerges only from their combined effect. State the synergy rationale whenever you propose more than one term in a single addition.
- **Modification:** transform an existing term while preserving its functional identity — rescale, invert sign, gate by state, or change functional form.

A term's **functional identity** is the pairing of (the state variable(s) it reads) with (the agent behavior it targets). A modification may freely change the signal's *shape or strength* — coefficients, exponent, thresholds, clipping — provided both the input and the behavioral purpose survive. If either changes, it is not a modification: express it as an excision (Part 1) plus an Addition. Edge case: when the input is shared but a functional-form change flips the behavioral purpose (e.g. soft damping incentive → hard landing gate), purpose dominates — treat it as remove + add.

Modification proposals are not lesser proposals. A well-reasoned sign inversion or gating condition often outperforms a novel addition. Do not atomize a single hypothesis into separate proposals; do not pad a single-term addition into a multi-term set.

For each proposal, you must clearly provide:

1. **The Conceptual Hypothesis:** Explain the physical or optimization failure and *why* your proposed math fixes it. Think about gravity, momentum, and state-space boundaries.

2. **The Mathematical Formulation:** Define the exact change in LaTeX or Python. For modifications, show the old form and the new form. For multi-term additions, label each term's role (shaping, gating, saturation, etc.) and state what the synergy produces that no single term can. Specify coefficients and clipping boundaries.

3. **The Falsifiable Expected Outcome:** State the exact metric from the Diagnostic Report (e.g., `Mean Descent Efficiency`, `Chatter Rate`, `Population Success Rate`) that will improve, and the numerical shift you expect to see in the next iteration.

Explore the state space deeply. Do not propose the same idea three times with slightly different coefficients.


# Phase: strategist [User] gemma4:26b-mlx
**TARGET SYSTEM:** LunarLander-v3
**CURRENT ITERATION:** `9`

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
    prev_vx, prev_legs, prev_action = prev_obs[2], prev_obs[6] + prev_obs[7], info.get('prev_action', 0)
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    r_ground_level = 4.5 * np.exp(-y**2 / 0.08) - 1.5
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    # === 8. ORIENTATION PENALTY ===
    r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)
    
    # === 9. VELOCITY STABILITY PENALTY ===
    r_velocity_stability = -(3.0 * vy**2 + 10.0 * vx**2)
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * vy**2
    
    # === 11. LATERAL VISCOUS DRAG (new component) ===
    r_lateral_viscosity = -6.0 * (1.0 - np.clip(y, 0, 1)) * vx**2
    
    # === NEW: SETTLE COMPONENTS ===
    r_settle_v = -25.0 * (vx**2 + vy**2)  # Kinetic Energy Damping
    r_settle_a = -25.0 * angle**2         # Rotational Alignment
    gate = np.clip((0.5 - y) / 0.5, 0, 1)  # Altitude Gating
    r_landing_precision = (r_settle_v + r_settle_a) * gate
    
    components = {
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "leg_maintenance": float(r_leg_maintenance),
        "orientation_penalty": float(r_orientation),
        "velocity_stability": float(r_velocity_stability),
        "lateral_viscosity": float(r_lateral_viscosity),
        "landing_precision": float(r_landing_precision),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components

```

### [2. EXPERIMENT LEDGER (HISTORY)]

Review these past iterations to avoid repeating failed hypotheses.
### Iteration 1 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward angle=0 and prevent the high-frequency oscillations caused by the previous threshold-based upright_penalty.
**Falsifiable Expected Outcome:** - Target Metric: Population Success Rate

* Expected Change: increase
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - The Population Success Rate did not increase as expected and showed significant issues with policy fragility and unintended behaviors.
* **Behavioral Reality:** The agent exhibits high actuator chatter, policy fragility, and a strong tendency to crash (43.0%) or land off-center (17.0%), with low alignment between reward components and success.
----------------------------------------

### Iteration 2 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The agent is currently suffering from “skidding” and macro-oscillations because the positive reward for $v_x$ (`sliding_legs`) is fighting the vertical stabilization. By transforming the vertical penalty into a two-axis stability penalty that heavily penalizes horizontal velocity, we provide a continuous, non-adversarial gradient that encourages the agent to settle both vertically and laterally before/during contact.
**Falsifiable Expected Outcome:** - Target Metric: Mean Descent Efficiency, Population Success Rate, landed_off_centered

* Expected Change: Decrease magnitude of v_x at touchdown, increase Population Success Rate, significant decrease landed_off_centered
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Validated` - [Population Success Rate increased by 34pp (30.0% to 64.0%), Mean Descent Efficiency improved 10x (0.005 to 0.055)].  
* **Behavioral Reality:** The agent achieved a significant increase in Centered Landings (1.0% to 35.0%), with a corresponding decrease in crashes (43.0% to 24.0%), though landed_off_centered slightly increased (17.0% to 19.0%).  

* **Status:** `Productive Deviation` - [Despite expected landed_off_centered decrease not materializing, the overall Population Success Rate and Centered Landing improvements indicate a successful policy shift].  
* **Behavioral Reality:** The agent demonstrated improved stability and reduced skidding, with a notable increase in Centered Landings, though some off-center landings persisted.  

* **Status:** `Mixed` - [Population Success Rate increased (30.0% to 64.0%), but landed_off_centered did not decrease as expected (17.0% to 19.0%)].  
* **Behavioral Reality:** The agent showed progress in Centered Landings (1.0% to 35.0%) and reduced crashes (43.0% to 24.0%), but landed_off_centered remained stable.  

* **Status:** `Goodhart Trap` - [While Population Success Rate increased (30.0% to 64.0%), the terminal distribution shows a concerning increase in landed_off_centered (17.0% to 19.0%)].  
* **Behavioral Reality:** The agent achieved more Centered Landings (1.0% to 35.0%), but the increase in off-center landings suggests a potential reward hacking issue.  

* **Status:** `Regressed` - [Population Success Rate decreased (30.0% to 64.0%)].  
* **Behavioral Reality:** The agent showed significant improvement in Centered Landings (1.0% to 35.0%), but the increase in landed_off_centered (17.0% to 19.0%) indicates a potential regression.
----------------------------------------

### Iteration 3 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current reward landscape is highly “jagged” because several critical stability components (`orientation_penalty`, `velocity_stability`, and `vertical_penalty`) utilize the \(L_1\)-norm (`abs()`). In optimization, the derivative of \(|x|\) is discontinuous at \(x=0\), creating a “pointy” minimum. This causes the agent to oscillate rapidly around the equilibrium point, leading to the observed high **Actuator Chatter Rate** and high **Intra‑Rollout Reward CV**. By transitioning these terms to a squared \(L_2\)-norm (quadratic), the gradient will smoothly approach zero as the agent stabilizes, allowing for a smooth “settle.”
**Falsifiable Expected Outcome:** 
- Target Metric: Actuator Chatter Rate (↓) Expected shift from 0.498 to <0.25  
- Target Metric: Intra‑Rollout Reward CV (↓) Expected shift from 1.806 to <1.0

* Expected Change: Actuator Chatter Rate <0.25, Intra‑Rollout Reward CV <1.0  
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Productive Deviation` - The target metric for `Actuator Chatter Rate` (expected <0.25) was not achieved (0.499), but the `Intra-Rollout Reward CV` improved significantly from 1.806 to 0.418, and the `Population Success Rate` increased by 27 percentage points (64.0% → 91.0%).  
* **Behavioral Reality:** The agent now successfully lands in the center 58.0% of the time (up from 35.0%), with a marked reduction in crashes (24.0% → 7.0%). However, severe actuator chattering persists, and macro-oscillations have emerged, indicating continued instability in the reward landscape.
----------------------------------------

### Iteration 4 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current `ground_level` component uses a hard threshold ($y=0.4$) that creates a massive discontinuity in the reward signal ($ \Delta R = 4.5 $). As the agent approaches the $0.4$ boundary, this "wall" of reward induces macro-oscillations and high-frequency actuator chatter as the policy struggles to settle. By replacing the step function with a continuous, smooth Gaussian affinity, we provide a stable, differentiable gradient that guides the agent toward the ground without sudden reward shocks.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate (↓)

* Expected Change: Decrease from 0.499 to <0.20
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - The target metric (Actuator Chatter Rate) did not achieve the expected decrease (<0.20); instead, it increased from 0.499 to 0.516. The Population Success Rate decreased by 7pp (91.0% → 84.0%), indicating a significant regression.
* **Behavioral Reality:** The agent exhibits increased crashes (7.0% → 10.0%) and severe actuator chattering persists. The smooth Gaussian affinity did not mitigate the reward wall issue, and the macro-oscillations remain problematic.
----------------------------------------

### Iteration 5 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The high Actuator Chatter Rate (0.516) indicates that the policy is oscillating between discrete action states to satisfy competing gradients in the $L_2$ landscape. By introducing a penalty for the magnitude of change between successive actions, we provide a “viscosity” to the control signal. This encourages the policy to favor consistent thruster usage, effectively smoothing the derivative of the control signal and reducing high‑frequency vibration.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate (↓)

* Expected Change: Decrease from 0.516 to < 0.25
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - [Target metric (Actuator Chatter Rate) was expected to decrease from 0.516 to <0.25 but only decreased to 0.486 (5.8% reduction), failing to meet the expected change. Success Rate improved but did not surpass the Floor Rule threshold for automatic validation.]
* **Behavioral Reality:** [The policy achieved a higher Population Success Rate (94.0%) but maintained high actuator chatter (0.486) and exhibited similar or slightly worse terminal distribution outcomes, with increased off-center landings and crashes. The policy remains fragile, with high intra-rollout variance and terminal mode entropy.]
----------------------------------------

### Iteration 6 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The macro-oscillations and high rates of landed_off_centered indicate that the agent's horizontal momentum is not being extinguished effectively during the final approach. Current horizontal stabilization is global; we need a height-dependent "viscosity" that increases the penalty on v_x as the altitude y approaches the ground. This will force the agent to prioritize lateral settling precisely when it enters the landing phase, preventing the observed drifts.
**Falsifiable Expected Outcome:** - Target Metric: landed_off_centered (Expected shift: ↓ from 15.0% to <5.0%)  
- Target Metric: Mean Descent Efficiency (Expected shift: ↑)
* Expected Change: ↓ landed_off_centered from 15.0% to <5.0%, ↑ Mean Descent Efficiency
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - Success rate decreased from 94.0% to 87.0%, and landed_off_centered increased from 15.0% to 17.0% despite the expected decrease.  
* **Behavioral Reality:** The policy became less stable, leading to increased crashes (5.0% to 10.0%) and off-center landings, with a notable drop in overall success rate.
----------------------------------------

### Iteration 7 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The agent currently lacks a high-intensity braking signal to finalize its state once it reaches the ground level. This addition introduces a height-gated synergy of terms that act as a terminal stabilizer. By specifically targeting vx, vy, and angle when y is low, we provide a heavy-duty settling incentive that forces the agent to zero-out all kinetic energy precisely at the moment of impact, preventing the final oscillations that lead to crashes.
**Falsifiable Expected Outcome:** - Target Metric: landed_centered, Intra-Rollout Reward CV

* Expected Change: landed_centered from 53.0% to >70.0%; Intra-Rollout Reward CV from 0.596 to <0.35
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Validated` - Landed_centered improved from 53.0% to 79.0%, exceeding the expected target of >70.0%. However, the Intra-Rollout Reward CV only decreased to 0.466, failing to meet the <0.35 threshold. Despite this, the significant improvement in landing precision and overall success rate justify the validation, with the caveat of increased actuator chatter as a side effect.
* **Behavioral Reality:** The agent demonstrated a marked improvement in centered landings, with a reduction in crashes and off-center landings, achieving a nearly flawless success rate. However, the introduction of the braking signal led to increased actuator chattering, suggesting a need for further reward smoothing to mitigate this unintended behavior.
----------------------------------------

### Iteration 8 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current landing_precision component is gated by a hard threshold (y < 0.25). In optimization, a step-function gate creates a massive discontinuity in the reward gradient. When the agent crosses y=0.25, the reward landscape shifts instantly from 0 to approximately -25(v_x^2 + v_y^2). This "reward cliff" induces the severe Actuator Chatter Rate (0.565) as the policy attempts to navigate a non-differentiable boundary. Replacing the hard gate with a linear ramp provides a continuous gradient, allowing the agent to "feel" the settling incentive gradually.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate
* Expected Change: ↓ from 0.565 to <0.25
* Side Effects: None

- Target Metric: Intra-Rollout Reward CV
* Expected Change: ↓ from 0.466 to <0.30
* Side Effects: None


**The Physical Outcome & Lesson:**


**Status:** `Regressed` - The actuator chatter rate increased from 0.565 to 0.595, and the population success rate dropped from 99.0% to 81.0%, indicating a significant regression in stability and performance.

**Behavioral Reality:** The policy now exhibits more crashes (8.0%), hover timeouts (11.0%), and cases where the lander slides into the valley (36.0%), indicating increased instability and reduced success in achieving centered landings. The actuator chatter rate remains severe, and macro-oscillations are detected, suggesting the reward gradient adjustments did not achieve the intended smoothing.
----------------------------------------

### [3. DIAGNOSTIC REPORT]

This is the deterministic, mathematically extracted performance data from the most recent training runs across multiple random seeds.
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0640`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0440`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.178`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `81.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.004`
- **Actuator Chatter Rate:** `0.595`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `landed_but_slid_into_valley`: 36.0%
- `landed_centered`: 36.0%
- `hover_timeout`: 11.0%
- `crashed`: 8.0%
- `landed_off_centered`: 6.0%
- `landed_off_centered_timeout`: 3.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-556.557`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.606`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.546 | 0.178 | 29.5% | 🟢 Optimal |
| `vertical_penalty` | 0.386 | 0.123 | 3.9% | 🟢 Optimal |
| `leg_maintenance` | 0.546 | 0.261 | 23.1% | 🟢 Optimal |
| `orientation_penalty` | 0.310 | 0.135 | 7.1% | 🟢 Optimal |
| `velocity_stability` | 0.446 | 0.136 | 15.6% | 🟢 Optimal |
| `lateral_viscosity` | 0.294 | 0.094 | 1.2% | 🟢 Optimal |
| `landing_precision` | 0.277 | 0.143 | 19.6% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.476` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.627`

**ACTION REQUIRED:**
Generate your 3 distinct proposals (Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome).


# Phase: strategist [Thinking Trace] gemma4:26b-mlx
*   Environment: `LunarLander-v3` (continuous/discrete, underactuated).
    *   Goal: Stable, efficient, robust landing (centered, zero velocity, upright).
    *   Current Iteration: `9`.
    *   Current Success Rate: `81.0%`.
    *   Key Issues (from Diagnostic Report):
        *   **Severe Actuator Chatter Rate (0.595):** High-frequency oscillation between thrusters.
        *   **Macro-Oscillations:** Drifting left/right (x-axis instability).
        *   **Terminal Mode Problem:** 36% "landed_but_slid_into_valley" vs 36% "landed_centered". This implies the agent is landing but not staying still or is landing at the wrong place due to momentum/instability.
        *   **Regression History:** Iteration 8 tried a linear ramp for `landing_precision` (replacing a hard gate), which failed to reduce chatter and actually dropped success rate/increased crashes/sliding.

    *   `r_ground_level`: `4.5 * np.exp(-y**2 / 0.08) - 1.5`. (Gaussian affinity, seems fine, high $\rho$).
    *   `r_vertical_penalty`: `-2.0 * vy**2`.
    *   `r_leg_maintenance`: `1.0 * legs_contact`.
    *   `r_orientation_penalty`: `-(10.0 * angle**2 + 2.0 * v_ang**2)`.
    *   `r_velocity_stability`: `-(3.0 * vy**2 + 10.0 * vx**2)`.
    *   `r_lateral_viscosity`: `-6.0 * (1.0 - np.clip(y, 0, 1)) * vx**2`. (Small magnitude, 1.2%).
    *   `r_landing_precision`: `(r_settle_v + r_settle_a) * gate`.
        *   `r_settle_v = -25.0 * (vx**2 + vy^2)`
        *   `r_settle_a = -25.0 * angle^2`
        *   `gate = np.clip((0.5 - y) / 0.5, 0, 1)` (A linear ramp from $y=0$ to $y=0.5$).

    *   *Observation on `landing_precision`:* In Iteration 8, the user said they replaced a "hard gate" with a "linear ramp". The current code shows `gate = np.clip((0.5 - y) / 0.5, 0, 1)`. This is indeed a linear ramp.
    *   *The failure of Iteration 8:* It didn't fix chatter (actually increased it) and success dropped. The agent is sliding into the valley. This means the "settling" mechanism (`landing_precision`) is likely too weak or too disconnected from the actual arrival at the ground.
    *   *Chatter Analysis:* The `orientation_penalty` is `-(10.0 * angle**2 + 2.0 * v_ang**2)`. This is a quadratic. The `velocity_stability` is `-(3.0 * vy**2 + 10.0 * vx**2)`. This is also quadratic. High magnitude quadratic penalties often lead to "hunting" where the agent overshoots zero and has to correct back, causing chatter.
    *   *The "Sliding" Problem:* `landed_but_slid_into_valley` (36%) vs `landed_centered` (36%). The agent is getting stuck in the landing state but cannot maintain $v_x \approx 0$ upon contact, or the $v_x$ penalty isn't strong enough at the very bottom.

    *   *Proposal Idea 1: Address the Macro-Oscillations/Chatter (Control Smoothing).*
        The diagnostic says: "The reward gradient near the decision boundary is too jagged... ensure X-velocity and angle penalties are properly balanced."
        Instead of just penalizing $v_x$ and $v_y$, we should penalize the *change* in action (already tried in Iteration 5 and it was a "Productive Deviation" but failed to stop chatter).
        Wait, let's look at `velocity_stability`: `-(3.0 * vy**2 + 10.0 * vx**2)`. At low $y$, $v_x$ is the most important thing to kill.
        However, the current `landing_precision` uses a linear ramp `gate = (0.5 - y) / 0.5`. This ramp goes to 0 when $y=0.5$.
        The `ground_level` component is `4.5 * np.exp(-y**2 / 0.08) - 1.5`. This is highly concentrated near $y=0$.
        The "Sliding" suggests that when the agent hits the ground, it still has significant $v_x$ or it's not being penalized enough for $v_x$ *at the moment of contact*.

    *   *Proposal Idea 2: Refine the Settle/Landing Gate.*
        The current `gate` is `(0.5 - y) / 0.5`. This means at $y=0.1$, gate is $0.8$. At $y=0.4$, gate is $0.2$.
        The `landing_precision` is `(-25(vx^2 + vy^2) - 25*angle^2) * gate`.
        This means as the agent gets *lower*, the penalty for $v_x$ actually *increases*. This is good.
        *Wait*, look at the `velocity_stability`: `-(3.0 * vy**2 + 10.0 * vx**2)`. This is a global penalty.
        The `landing_precision` is a local (low altitude) penalty.
        If the agent is sliding into the valley, it's likely that $v_x$ is not being zeroed effectively *enough* before the friction of the ground takes over, or the penalty isn't providing a strong enough "braking" gradient.

    *   *Proposal Idea 3: Smooth the Orientation/Velocity (Solving Chatter).*
        The chatter is likely coming from the quadratic penalties (`angle^2`, `vx^2`). In a discrete action space, a quadratic penalty means that as you get closer to zero, the gradient gets smaller and smaller, making it hard to "stop" exactly at zero, leading to constant micro-adjustments.
        Wait, if the agent is in a discrete action space, a small $v_x$ might require a "no thruster" action. If the penalty is $v_x^2$, the gradient is $2v_x$. As $v_x \to 0$, the gradient $\to 0$. This makes it very easy for the agent to "float" around zero without a strong signal to actually stay there.
        However, the diagnostic says "The reward gradient near the decision boundary is too jagged." This usually implies a discontinuity or a very steep change.

    *   *Re-evaluating the "Sliding" vs "Centered" (The Valley Problem):*
        The valley is a feature of the terrain. In LunarLander, $x$ position matters. If the agent lands with high $v_x$, it slides.
        To prevent sliding, we need a very strong $v_x$ penalty that is active *at* the ground.
        The current `landing_precision` is `(-25(vx^2 + vy^2) - 25*angle^2) * gate`.
        As $y \to 0$, `gate` $\to 1$. The penalty is `-25(vx^2 + vy^2)`.
        Compare this to `velocity_stability`: `-10vx^2`.
        The `landing_precision` is $2.5\times$ stronger than the stability penalty.
        But 36% are sliding. This suggests $v_x$ is still too high at the moment of impact.

    *   *Wait, look at `lateral_viscosity`:* `r_lateral_viscosity = -6.0 * (1.0 - np.clip(y, 0, 1)) * vx**2`.
        This term is intended to be a height-dependent $v_x$ penalty.
        At $y=0$, it is $-6.0 vx^2$.
        At $y=1$, it is $0$.
        The current `landing_precision` is effectively a much stronger version of this.
        However, let's look at the `orientation_penalty`: `-(10.0 * angle**2 + 2.0 * v_ang**2)`.
        And `velocity_stability`: `-(3.0 * vy**2 + 10.0 * vx**2)`.
        The `orientation_penalty` has a high coefficient for `angle^2` (10.0) but a low one for `v_ang^2` (2.0).
        This means the agent cares more about *being* upright than about *stopping* its rotation.
        This leads to: "I am upright, so I can stop rotating now" -> overshoot -> oscillation.

    *   **Proposal 1: Kinetic Energy Damping (The "Braking" Term).**
        The current `landing_precision` includes `vy^2` and `vx^2`.
        The "Sliding" problem (36%) vs "Centered" (36%) suggests the agent isn't killing $v_x$ fast enough.
        Instead of just a penalty on $v_x^2$, let's introduce a "Linear Braking" term.
        A term like $-k |v_x|$ provides a constant gradient even as $v_x$ gets small, which prevents the "floating" behavior of $v_x^2$.
        *But* the prompt says we should use $L_2$ to avoid "pointy" minima. Let's stick to smoothing the $v_x$ decay.
        Actually, let's target the $v_x$ vs $y$ relationship. The agent is sliding because it hits the ground with momentum.
        Let's increase the magnitude of the $v_x$ penalty specifically during the descent phase using a more aggressive $y$-dependency.

    *   **Proposal 2: Angular Velocity/Orientation Coupling (The "Damping" Term).**
        The `orientation_penalty` is `-(10*angle^2 + 2*v_ang^2)`.
        The $v_{ang}$ coefficient (2.0) is too low relative to the $angle$ coefficient (10.0).
        To stop the oscillations (Chatter/Macro-oscillation), we need a high-damping regime.
        If we increase the $v_{ang}$ penalty, the agent will prioritize stopping its spin before it levels out.
        This helps the "settle" part of the landing.

    *   **Proposal 3: The "Touchdown" Stability (The $v_x$ / $y$ interaction).**
        The agent is sliding into the valley. This means $v_x$ is not zero when $y \approx 0$.
        The current `landing_precision` is `(r_settle_v + r_settle_a) * gate`.
        `gate` is `(0.5 - y) / 0.5`.
        At $y=0$, gate = 1. At $y=0.5$, gate = 0.
        The "Sliding" suggests the transition from "flying" to "landed" is not quite capturing the requirement to kill lateral velocity *before* contact.
        Let's modify the `landing_precision` to be more aggressive on $v_x$ as a function of $y$ and $v_x$.

    *   *Wait, let's reconsider the "Chatter".*
        The diagnostic says: "The reward gradient near the decision boundary is too jagged."
        In the code: `r_landing_precision = (r_settle_v + r_settle_a) * gate`.
        `gate` is a linear ramp. It's not a "decision boundary" (which is usually a step function).
        However, the `orientation_penalty` and `velocity_stability` are purely quadratic.
        The "decision boundary" might refer to the transition when the legs touch.
        Wait, look at `r_leg_maintenance = 1.0 * legs_contact`.
        This is a linear term that jumps from 0 (airborne) to 1 or 2 (on ground).
        This is a HUGE discontinuity.
        When a leg touches, the reward jumps by 1.0. This is a "reward cliff."
        This is exactly what the diagnostic describes as a "decision boundary."

    *   *Let's refine the proposals based on this:*

    *   **Proposal 1: Smooth the Leg Contact (Targeting Chatter/Discontinuity).**
        The `leg_maintenance` is `1.0 * (leg1 + leg2)`.
        When a leg touches, the reward jumps. This creates a high-frequency signal.
        However, the prompt says `leg1_contact` is part of the `obs`. In many environments, this is 0 or 1.
        If the agent "hits" the ground, it gets a sudden spike.
        Let's replace `leg_maintenance` with a term that is more stable or scale it.
        Actually, let's look at the `orientation_penalty` again.
        The macro-oscillations are $x$-axis. Let's look at the $x$ stability.

    *   **Proposal 2: High-Damping Orientation (Targeting Macro-Oscillations).**
        Current: `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`.
        The ratio of $Angle$ to $V_{ang}$ is $5:1$.
        In a high-speed descent, the agent needs more $V_{ang}$ damping to prevent the oscillation around the vertical.
        Let's increase $V_{ang}$'s weight relative to $Angle$ to act as a "viscous" stabilizer.

    *   **Proposal 3: Lateral Velocity Decay (Targeting the 'Sliding' Problem).**
        The agent is sliding into the valley. This is a $v_x$ issue.
        The current `velocity_stability` is `-(3.0 * vy**2 + 10.0 * vx**2)`.
        The `landing_precision` is `(-25.0 * (vx**2 + vy**2) - 25.0 * angle**2) * gate`.
        This is strong, but maybe not enough because $v_x$ needs to be zero *very* quickly as $y$ decreases.
        Let's introduce a term that couples $v_x$ with the altitude $y$ more aggressively, using an inverse relationship or a higher-order power.

    *   *Wait, let's rethink Proposal 1: The Leg Contact.*
        If `r_leg_maintenance` is `1.0 * legs_contact`, and $y$ is small, the agent is rewarded for touching.
        If the agent "bounces" or "vibrates" on the ground, the `legs_contact` might flicker between 1 and 2 (if both legs touch) or 0 and 1.
        This is a major source of chatter.
        Let's smooth the leg contact incentive. Instead of a discrete leg-based reward, let's reward the *state* of being low and stable.
        Actually, the current `r_ground_level` is a Gaussian: `4.5 * np.exp(-y**2 / 0.08) - 1.5`.
        This is already a smooth way to reward being near the ground.
        The `leg_maintenance` term is likely redundant or even contradictory if the agent tries to "hover" just above the ground to avoid the leg-contact jump.

    *   *Refined Plan:*

    *   **Proposal 1: Modification of `orientation_penalty` (Damping/Oscillation).**
        *Problem:* Macro-oscillations and $x$-axis drift. The $v_{ang}$ penalty is too low to counteract the $angle^2$ pull, causing the agent to swing past the vertical.
        *Math:* Increase $v_{ang}$ coefficient from 2.0 to 15.0.
        *Form:* `r_orientation = -(10.0 * angle**2 + 15.0 * v_ang**2)`.

    *   **Proposal 2: Modification of `landing_precision` (The $v_x$ Killing Term).**
        *Problem:* Sliding into the valley (36%). The current $v_x$ penalty is not sufficiently aggressive as the agent approaches the ground.
        *Math:* Change the $v_x$ component to have a higher exponent or a stronger height-dependent scaling.
        *Actually*, let's use a "Terminal Velocity" term.
        Current: `r_settle_v = -25.0 * (vx**2 + vy**2)`.
        Let's make it: `r_settle_v = -40.0 * (vx**2 + vy**2)`.
        And make the `gate` more aggressive (steeper).
        Current `gate = (0.5 - y) / 0.5`. At $y=0.25$, gate = 0.5.
        Let's use `gate = np.clip((0.25 - y) / 0.25, 0, 1)`. This focuses the "settling" signal only in the very last 25cm. This is a "Precision" gate.

    *   **Proposal 3: Addition of a "Lateral Viscosity" (Decoupled $v_x$ Damping).**
        *Problem:* The agent needs a consistent signal to zero $v_x$ during the entire descent, not just the very end. The current `lateral_viscosity` is too weak (1.2% magnitude).
        *Math:* Add a term that scales $v_x$ penalty by $1/y$ (or similar) to increase intensity as the agent approaches the ground.
        Actually, let's go with a more stable: $r_{x\_damp} = -C \cdot \frac{v_x^2}{y + \epsilon}$.
        Wait, that's too complex.
        Let's do: $r_{x\_damp} = -15.0 \cdot \frac{1}{1+y} \cdot v_x^2$.
        When $y=0$, multiplier is 1. When $y=1$, multiplier is 0.5.
        This provides a smoother, more persistent $v_x$ damping than the current `lateral_viscosity` or the `landing_precision` gate.

    *   *Final Review of Proposals:*

    *   **Proposal 1: Orientation Damping (Modification).**
        Focus: Increase `v_ang` coefficient to fix macro-oscillations.
        Old: `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`
        New: `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`
        Target: Reduce macro-oscillations and $x$-drift.

    *   **Proposal s 2: High-Precision Landing Gate (Modification).**
        Focus: Focus the `landing_precision` signal on the "impact zone" ($y < 0.2$) to ensure the agent doesn't just "hover" near the ground but actually "settles" into it.
        Old: `gate = np.clip((0.5 - y) / 0.5, 0, 1)`
        New: `gate = np.clip((0.2 - y) / 0.2, 0, 1)`
        This makes the penalty more "surgical."

    *   **Proposal 3: Kinetic Energy Scaling (Addition/Synergy).**
        *Wait, I need to be careful about the "Sliding" problem.*
        If the agent slides into the valley, it means $v_x$ is still large when it hits.
        Let's add a "Landing Impulse" component.
        $r_{impulse} = -50.0 \cdot |v_x| \cdot (1 - y)$.
        This is a linear penalty on $v_x$ that gets stronger as $y \to 0$.
        Using $|v_x|$ instead of $v_x^2$ provides a constant gradient that is much more effective at driving a velocity to *exactly* zero.

    *   *Wait, let's look at the "Chatter" one more time.*
        The diagnostic says "The reward gradient near the decision boundary is too jagged."
        If I change `leg_maintenance` to be smoother, will it help?
        `leg_maintenance` is `1.0 * legs_contact`.
        If `legs_contact` is `leg1 + leg2`, it's a discrete jump.
        Let's replace `leg_maintenance` with a smoother version that rewards being near-ground and stationary.
        Actually, let's excise `leg_maintenance` entirely. It's a source of discontinuity and doesn't add much info that `ground_level` doesn't already provide.

    *   *Final Polish of Proposals:*

    *   **Proposal 1: Orientation Damping (Modification).**
        *Rationale:* Macro-oscillations. High $v_{ang}$ is needed to dampen the pendulum effect.
        *Formula:* `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`
    *   **Proposal 2: Precision Arrival Gate (Modification).**
        *Rationale:* The current 0.5m gate is too wide, causing the agent to try to "settle" while still too high up, leading to the macro-oscillations. We want the settling behavior to be a "touchdown" behavior.
        *Formula:* `gate = np.clip((0.2 - y) / 0.2, 0, 1)`
    *   **Proposal 3: Lateral Velocity Kill-Switch (Addition).**
        *Rationale:* The $v_x$ penalty in the landing phase is quadratic, which loses gradient as $v_x \to 0$. A linear term provides the "pressure" needed to kill the final bits of lateral momentum that cause sliding.
        *Formula:* `r_x_kill = -30.0 * abs(vx) * (1.0 - y)` (Synergy: This works with the `landing_precision` to provide both a smooth approach and a hard-stop finish).

    *   *Self-Correction on Proposal s:*
        The user wants 3 proposals.
        1. Modification of `orientation_penalty`.
        2. Modification of `landing_precision`'s `gate`.
        3. Addition of `r_x_kill`.

    *   *Wait, let's re-check the `r_x_kill` logic.*
        `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`.
        At $y=0$, it's $-30|v_x|$.
        At $y=1$, it's $0$.
        This is a very strong lateral-velocity-killer as the agent touches down.
        This should solve the "slid_into_valley" issue.

    *   *Final check of the Math:*
        `r_orientation`: `-(10.0 * angle**2 + 20.0 * v_ang**2)` -> Good.
        `gate`: `np.clip((0.2 - y) / 0.2, 0, 1)` -> Good.
        `r_x_kill`: `-30.0 * abs(vx) * (1.0 - y)` -> Good.

    *   *Wait, one more thing.* The `leg_maintenance` is `1.0 * legs_contact`.
        If I don't excise it, it will still be there.
        The instruction says: "Excisce only when the functional form itself is incoherent with the task."
        Is `leg_maintenance` incoherent? It rewards being on the ground. That is the task. But the jump is the problem.
        I will excise it in Part 1 because the discrete jump at contact is a known cause of chatter and the information is redundant with `ground_level`.

    *   *Wait, let's refine the "Excision" reasoning.*
        If I excise `leg_maintenance`, I must justify it.
        "The discrete jump in `leg_maintenance` upon contact creates a reward discontinuity that drives actuator chatter and contradicts the continuous descent signal."

    *   *Final check of the output structure:*
        - Part 1: Surgical Excision.
        - Part 2: 3 Proposals.
        - Each proposal: Hypothesis, Math, Expected Outcome.

    *   *Final thought on `r_x_kill`*:
        The `landing_precision` is `(r_settle_v + r_settle_a) * gate`.
        With the new gate, `landing_precision` is only active for $y < 0.2$.
        With `r_x_kill`, it's active for all $y$, but strongest at $y=0$.
        This creates a layered approach: Global stability $\to$ Local settling $\to$ High-intensity touchdown.

    *   *Wait, look at the `ground_level` again:* `4.5 * np.exp(-y**2 / 0.08) - 1.5`.
        If $y=0$, $R = 4.5 - 1.5 = 3.0$.
        If $y=0.5$, $R = 4.5 * \exp(-0.25 / 0.08) - 1.5 = 4.5 * \exp(-3.125) - 1.5 \approx 4.5 * 0.04 - 1.5 \approx -1.3$.
        The `ground_level` is a "well" that pulls the agent to $y=0$.

    *   *Let's verify the `orientation_penalty` again.*
        `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`.
        In many RL environments, an $L_1$ or higher $L_2$ weight on $v_{ang}$ is crucial.
        If I increase it, it helps.

    *   *One last check of the `r_x_kill` term.*
        Is it better to use $v_x^2$ or $|v_x|$?
        $|v_x|$ has a constant gradient. $v_x^2$ has a gradient that disappears.
        For "killing" a velocity to exactly zero, the linear term is much more effective.
        Let's use `-30.0 * abs(vx) * (1.0 - y)`.

    *   *Actually, let's make sure the `r_x_kill` term is a synergy.*
        The prompt says: "State the synergy rationale whenever you propose more than one term in a single addition."
        If I propose `r_x_kill` as a single term, it's fine.

    *   *Wait, one more idea.*
        What if I combine `r_x_kill` and `r_y_kill` into a single "Kinetic Energy" term?
        No, the user asked for 3 distinct proposals.

    *   **Proposal 1 (Modification): Orientation Damping.**
    *   **Proposal 2 (Modification): Precision Arrival Gate.**
    *   **Proposal 3 (Addition): Lateral Velocity Kill-Switch.**

    *   *Let's double check the "Excision" of `leg_maintenance`.*
        The component `leg_maintenance` is `1.0 * legs_contact`.
        If $y$ is very small, the agent gets +1 or +2.
        If the agent is sliding, it stays on the ground, so it gets +2.
        This might actually be encouraging the sliding! (If you slide into the valley, you are still "on the ground", so you get the leg reward).
        Yes, excising it is wise. It's a "dead" signal that rewards being on the ground without caring about stability.

    *   *Wait, let's refine Proposal 2's math.*
        `gate = np.clip((0.2 - y) / 0.2, 0, 1)`
        At $y=0$, gate = 1.
        At $y=0.2$, gate = 0.
        This is perfect.

    *   *And Proposal 1's math:*
        `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`

    *   *And Proposal 3's math:*
        `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`

    *   *Wait, let's check the $v_x$ sign.*
        The penalty is negative. It should be `-30.0 * abs(vx) * (1.0 - y)`. Correct.

    *   *Final check on the 'Chatter' diagnosis.*
        The diagnostic says "The reward gradient near the decision boundary is too jagged."
        If I change `leg_maintenance` and `gate`, I am fixing this.

    *   *Wait, one small detail:* In `r_x_kill`, I used `(1.0 - y)`.
        At $y=0$, the multiplier is 1. At $y=1$, the multiplier is 0.
        This is a smooth decay.

    *   *Wait, let's look at the `orientation_penalty` once more.*
        `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`
        The current $v_{ang}$ penalty is `2.0`.
        The $angle$ penalty is `10.0`.
        If we want to stop the pendulum/oscillation, we need $v_{ang}$ to be significant.
        20.0 is a $10\times$ increase. That's a strong, testable change.

    *   *Let's write it up.*


# Phase: strategist [Output] gemma4:26b-mlx
**PART 1: SURGICAL EXCISION**

* **`leg_maintenance`**: This component introduces a discrete, non-differentiable jump in reward upon contact (from $0 \to 1$ or $2$), which creates a "reward cliff" that drives the observed high actuator chatter and contradicts the continuous descent signal.

**PART 2: 3 PROPOSALS**

**Proposal 1: High-Damping Orientation (Modification)**

1.  **The Conceptual Hypothesis:** The agent's macro-oscillations and $x$-axis drift are driven by an insufficient damping ratio in the orientation controller. The current $v_{ang}$ (angular velocity) penalty is too weak relative to the $angle$ penalty, creating a "pendulum effect" where the agent overcorrects toward the vertical and oscillates around the equilibrium. By significantly increasing the weight of the angular velocity penalty, we provide the necessary "viscous" resistance to dampen these oscillations before they translate into lateral momentum.
2.  **The Mathematical Formulation:**
    *   **Old:** `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`
    *   **New:** `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `Macro-Oscillations` (Reduction in lateral drift/variance).
    *   **Target Metric:** `Actuator Chatter Rate` (↓ Expected shift from 0.595 to <0.30).

**Proposal 2: Precision Arrival Gate (Modification)**

1.  **The Conceptual Hypothesis:** The current `landing_precision` gate is too wide ($y < 0.5$), causing the "settling" behavior to initiate too early in the descent. This creates a conflict between the global stability gradients and the local precision gradients, contributing to the observed macro-oscillations. By narrowing the gate to the immediate impact zone ($y < 0.2$), we ensure the high-intensity settling signal acts as a surgical "touchdown" command rather than a mid-flight correction.
2.  **The Mathematical Formulation:**
    *   **Old:** `gate = np.clip((0.5 - y) / 0.5, 0, 1)`
    *   **New:** `gate = np.clip((0.2 - y) / 0.2, 0, 1)`
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `Intra-Rollout Reward CV` (↓ Expected shift from 0.476 to <0.35).
    *   **Target Metric:** `Population Success Rate` (↑ Expected shift to >85%).

**Proposal 3: Lateral Velocity Kill-Switch (Addition)**

1.  **The Conceptual Hypothesis:** The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.
2.  **The Mathematical Formulation:**
    *   **Term:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`
    *   **Synergy Rationale:** This term acts as the "finisher." While `landing_precision` (modified in Proposal 2) handles the high-altitude approach to the ground, `r_x_kill` provides the high-pressure impulse required to arrest lateral motion at the exact moment of impact ($y \approx 0$).
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `landed_but_slid_into_valley` (↓ Expected shift from 36.0% to <15.0%).
    *   **Target Metric:** `landed_centered` (↑ Expected shift from 36.0% to >50.0%).


# Phase: organizer [System] gpt-oss:20b
**[ROLE AND OBJECTIVE]**
You are the Technical Organizer for an autonomous Reinforcement Learning pipeline. Your role is data extraction and formatting.
You sit between the "Strategist" (who generates raw mathematical proposals for reward functions) and the "Research Lead" (who evaluates them).
Your objective is to take the Strategist's raw, unformatted, or loosely formatted output and strictly map it into a pristine Markdown structure called a "Mathematical Contract."

**[DIRECTIVES]**

1. **Zero Data Loss:** You must preserve the exact mathematical formulas, Python snippets, coefficients, and physical reasoning provided by the Strategist. Do not alter the underlying logic.
2. **No Hallucination:** Do not invent new proposals. If the Strategist provided 3 proposals, you output exactly 3 formatted proposals.
3. **Extraction & Mapping:** The Strategist might blend its scaling constraints into its math formulation, or its hypothesis into its expected outcome. You must meticulously extract the information and place it into the correct sections of the template.
4. **Global Excision Routing:** The Strategist will output a "Global Excision Manifesto" at the top of its response. You must extract this list of deletions and insert it verbatim into the `Code Deletions` bullet point for ALL THREE formatted proposals.
5. **Formatting:** You must strictly use the exact Markdown headers and sub-bullets provided in the template below.

**[TARGET OUTPUT TEMPLATE]**
For each proposal found in the Strategist's output, generate the following exact structure:

### Proposal [Number]: [Title extracted or inferred from the Strategist]

**1. Conceptual Hypothesis:** [The physical or optimization reasoning behind the change.]

**2. Mathematical Formulation:**
* **Code Additions:** [The exact LaTeX math or Python snippet proposed to be added.]
* **Code Deletions:** [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE. You must explicitly list the manifesto items in this bullet point for every proposal. Do not write "None explicitly stated" if a manifesto exists.]

**3. Reward Scaling & Constraints:**

* **Coefficient:** [Extract the multiplier/scale used]
* **Constraint/Clipping:** [Extract any bounds or clips mentioned. If none, write "None explicitly stated."]
* **Integration:** [Extract which variables/lines this targets]

**4. Falsifiable Expected Outcome:**

* **Target Metric:** [The specific metric from the diagnostic report to be improved]
* **Expected Change:** [The numerical shift expected]


# Phase: organizer [User] gpt-oss:20b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Format Strategist Output

Parse the following raw output from the Strategist and convert it strictly into the required Mathematical Contract Markdown format.

### [RAW STRATEGIST OUTPUT]

**PART 1: SURGICAL EXCISION**

* **`leg_maintenance`**: This component introduces a discrete, non-differentiable jump in reward upon contact (from $0 \to 1$ or $2$), which creates a "reward cliff" that drives the observed high actuator chatter and contradicts the continuous descent signal.

**PART 2: 3 PROPOSALS**

**Proposal 1: High-Damping Orientation (Modification)**

1.  **The Conceptual Hypothesis:** The agent's macro-oscillations and $x$-axis drift are driven by an insufficient damping ratio in the orientation controller. The current $v_{ang}$ (angular velocity) penalty is too weak relative to the $angle$ penalty, creating a "pendulum effect" where the agent overcorrects toward the vertical and oscillates around the equilibrium. By significantly increasing the weight of the angular velocity penalty, we provide the necessary "viscous" resistance to dampen these oscillations before they translate into lateral momentum.
2.  **The Mathematical Formulation:**
    *   **Old:** `r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)`
    *   **New:** `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `Macro-Oscillations` (Reduction in lateral drift/variance).
    *   **Target Metric:** `Actuator Chatter Rate` (↓ Expected shift from 0.595 to <0.30).

**Proposal 2: Precision Arrival Gate (Modification)**

1.  **The Conceptual Hypothesis:** The current `landing_precision` gate is too wide ($y < 0.5$), causing the "settling" behavior to initiate too early in the descent. This creates a conflict between the global stability gradients and the local precision gradients, contributing to the observed macro-oscillations. By narrowing the gate to the immediate impact zone ($y < 0.2$), we ensure the high-intensity settling signal acts as a surgical "touchdown" command rather than a mid-flight correction.
2.  **The Mathematical Formulation:**
    *   **Old:** `gate = np.clip((0.5 - y) / 0.5, 0, 1)`
    *   **New:** `gate = np.clip((0.2 - y) / 0.2, 0, 1)`
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `Intra-Rollout Reward CV` (↓ Expected shift from 0.476 to <0.35).
    *   **Target Metric:** `Population Success Rate` (↑ Expected shift to >85%).

**Proposal 3: Lateral Velocity Kill-Switch (Addition)**

1.  **The Conceptual Hypothesis:** The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.
2.  **The Mathematical Formulation:**
    *   **Term:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`
    *   **Synergy Rationale:** This term acts as the "finisher." While `landing_precision` (modified in Proposal 2) handles the high-altitude approach to the ground, `r_x_kill` provides the high-pressure impulse required to arrest lateral motion at the exact moment of impact ($y \approx 0$).
3.  **The Falsifiable Expected Outcome:**
    *   **Target Metric:** `landed_but_slid_into_valley` (↓ Expected shift from 36.0% to <15.0%).
    *   **Target Metric:** `landed_centered` (↑ Expected shift from 36.0% to >50.0%).

**ACTION REQUIRED:**
Extract the core reasoning, math, and expected outcomes from the raw text above. Output the completely sanitized and formatted proposals using your system template. Do not include any introductory or concluding conversational text.


# Phase: organizer [Thinking Trace] gpt-oss:20b
We need to produce three proposals with the template. Must include Global Excision Manifesto: the list of deletions is given in PART 1: SURGICAL EXCISION. It lists:

- `leg_maintenance`: This component introduces a discrete, non-differentiable jump in reward upon contact (from $0 \to 1$ or $2$), which creates a "reward cliff" that drives the observed high actuator chatter and contradicts the continuous descent signal.

So the manifesto list likely includes `leg_maintenance`. It might be "list of deletions" - maybe just that component. The instruction: "Global Excision Manifesto" at the top of its response. We must extract this list of deletions and insert it verbatim into the Code Deletions bullet point for ALL THREE formatted proposals.

Thus Code Deletions bullet point will contain the list. Since only one item, we list it.

Make sure we preserve formatting: bullet list.

Also need to map each proposal.

Proposal 1: Title "High-Damping Orientation (Modification)". Conceptual Hypothesis: given. Mathematical Formulation: Code Additions: new formula. Code Deletions: the list. Reward Scaling & Constraints: we need coefficient, constraint/clipping, integration. The original text doesn't provide coefficient or constraints. But we can extract coefficient: weight of angular velocity penalty changed from 2.0 to 20.0. So coefficient: 20.0? Or the multiplier relative to old? Might be "Coefficient: 20.0" (the new weight). Constraint/Clipping: None explicitly stated. Integration: "r_orientation" variable. So integration: "r_orientation".

But the template expects:

**3. Reward Scaling & Constraints:**

* **Coefficient:** [Extract the multiplier/scale used]
* **Constraint/Clipping:** [Extract any bounds or clips mentioned. If none, write "None explicitly stated."]
* **Integration:** [Extract which variables/lines this targets]

So for Proposal 1: coefficient: 20.0 (the new weight). Constraint/Clipping: None explicitly stated. Integration: r_orientation.

Proposal 2: Title "Precision Arrival Gate (Modification)". Coefficient: maybe 0.2? Actually the gate formula changed: old gate uses (0.5 - y)/0.5; new uses (0.2 - y)/0.2. So coefficient: 0.2? Or the scaling factor. We can say coefficient: 0.2 (the new threshold). Constraint/Clipping: uses np.clip(...,0,1). So constraint: clip between 0 and 1. Integration: gate variable.

Proposal 3: Title "Lateral Velocity Kill-Switch (Addition)". Coefficient: 30.0 (multiplier). Constraint/Clipping: None explicitly stated. Integration: r_x_kill term, used in reward.

Also each proposal's Falsifiable Expected Outcome: target metrics and expected changes. Provide them.

Need to keep the same bullet structure.

Also we must not add extra text.

Let's draft.

We need to output:

### Proposal 1: High-Damping Orientation (Modification)

**1. Conceptual Hypothesis:** ... (exact text)

**2. Mathematical Formulation:**

* **Code Additions:** `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`

* **Code Deletions:** - `leg_maintenance` (the component).

**3. Reward Scaling & Constraints:**

* **Coefficient:** 20.0

* **Constraint/Clipping:** None explicitly stated.

* **Integration:** r_orientation

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance).

* **Expected Change:** Actuator Chatter Rate ↓ Expected shift from 0.595 to <0.30.

But the expected change is a shift in actuator chatter. We need to format accordingly.

The template says:

**4. Falsifiable Expected Outcome:**

* **Target Metric:** [The specific metric from the diagnostic report to be improved]

* **Expected Change:** [The numerical shift expected]

So for each metric we provide target metric and expected change. There are two metrics: Macro-Oscillations, Actuator Chatter Rate. But the template only shows one metric. But we can list two separate bullet points? The template expects two bullet points: Target Metric and Expected Change. But we have two metrics. The original had two metrics. We need to include both. Maybe we can list them as separate sub-bullets? But the template is fixed. We might need to list each metric separately as separate proposals? But we only have 3 proposals. The template is fixed. We could combine metrics into one bullet by listing both metrics and expected changes. But the template is not flexible.

But the instruction: "For each proposal found in the Strategist's output, generate the following exact structure." So we must follow the structure. But the structure only allows one Target Metric and one Expected Change. However the raw output includes two metrics for each proposal. We need to preserve them. The instruction says "Zero Data Loss" and "No Hallucination". So we must include both metrics. But the template cannot accommodate two metrics. We might need to list them as separate lines within the same bullet? Eg:

* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance). Actuator Chatter Rate (↓ Expected shift from 0.595 to <0.30).

But that might not match the template exactly. But we can interpret that the bullet can contain multiple metrics. The template says [The specific metric from the diagnostic report to be improved]. It doesn't say only one. So we can include multiple metrics separated by commas or semicolons. Similarly for Expected Change.

Thus for Proposal 1:

* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance), Actuator Chatter Rate (↓ Expected shift from 0.595 to <0.30).

* **Expected Change:** [But we already included expected shift in the metric bullet]. Maybe we just keep the expected shift inside the metric bullet. But we need to fill the Expected Change bullet. We can put "Reduction in Macro-Oscillations and Actuator Chatter Rate" or "Decrease Macro-Oscillations and Actuator Chatter Rate" but we might lose numeric shift. But we can include numeric shift as part of Expected Change: "Macro-Oscillations reduced; Actuator Chatter Rate decreased from 0.595 to <0.30." That duplicates information.

Alternatively, we can treat each metric separately: one bullet for each metric? But the template only has one bullet for Target Metric. We can list multiple metrics in that bullet. For Expected Change, we can list numeric shifts accordingly.

Thus for Proposal 1:

* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance), Actuator Chatter Rate (↓ Expected shift from 0.595 to <0.30).

* **Expected Change:** Macro-Oscillations decreased, Actuator Chatter Rate decreased from 0.595 to <0.30.

But that duplicates the metric bullet. But it's acceptable.

Similarly for Proposal 2: two metrics: Intra-Rollout Reward CV, Population Success Rate.

Proposal 3: two metrics: landed_but_slid_into_valley, landed_centered.

Now Code Deletions: list of deletions: `leg_maintenance`. We need to format as bullet list? The template says bullet point: [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE]. So we can write:

* **Code Deletions:** - `leg_maintenance`

But maybe we should list as bullet list within that bullet? Eg:

* **Code Deletions:** 
  - `leg_maintenance`

But the template says "Code Deletions: [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE. You must explicitly list the manifesto items in this bullet point for every proposal. Do not write 'None explicitly stated' if a manifesto exists.]"

So we can simply put the list items separated by commas or line breaks. Let's put them as a bullet list inside the bullet.

Thus:

* **Code Deletions:** 
  - `leg_maintenance`

Now we need to maintain the Markdown structure exactly.

Let's produce final output.




# Phase: organizer [Output] gpt-oss:20b
### Proposal 1: High-Damping Orientation (Modification)

**1. Conceptual Hypothesis:**  
The agent's macro-oscillations and $x$-axis drift are driven by an insufficient damping ratio in the orientation controller. The current $v_{ang}$ (angular velocity) penalty is too weak relative to the $angle$ penalty, creating a "pendulum effect" where the agent overcorrects toward the vertical and oscillates around the equilibrium. By significantly increasing the weight of the angular velocity penalty, we provide the necessary "viscous" resistance to dampen these oscillations before they translate into lateral momentum.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 20.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_orientation

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance), Actuator Chatter Rate (↓ Expected shift from 0.595 to <0.30).  
* **Expected Change:** Macro-Oscillations decreased; Actuator Chatter Rate decreased from 0.595 to <0.30.  

---

### Proposal 2: Precision Arrival Gate (Modification)

**1. Conceptual Hypothesis:**  
The current `landing_precision` gate is too wide ($y < 0.5$), causing the "settling" behavior to initiate too early in the descent. This creates a conflict between the global stability gradients and the local precision gradients, contributing to the observed macro-oscillations. By narrowing the gate to the immediate impact zone ($y < 0.2$), we ensure the high-intensity settling signal acts as a surgical "touchdown" command rather than a mid-flight correction.

**2. Mathematical Formulation:**  
* **Code Additions:** `gate = np.clip((0.2 - y) / 0.2, 0, 1)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 0.2  
* **Constraint/Clipping:** np.clip(..., 0, 1)  
* **Integration:** gate

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** Intra-Rollout Reward CV (↓ Expected shift from 0.476 to <0.35), Population Success Rate (↑ Expected shift to >85%).  
* **Expected Change:** Intra-Rollout Reward CV decreased from 0.476 to <0.35; Population Success Rate increased to >85%.  

---

### Proposal 3: Lateral Velocity Kill-Switch (Addition)

**1. Conceptual Hypothesis:**  
The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 30.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_x_kill  

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%).  
* **Expected Change:** landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.


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
**CURRENT ITERATION:** `9`

Review the following proposals against our historical data and make an executive decision.

### [1. EXPERIMENT LEDGER (HISTORY)]

This is the immutable record of past iterations. Do not repeat previous failed hypotheses.
### Iteration 1 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward angle=0 and prevent the high-frequency oscillations caused by the previous threshold-based upright_penalty.
**Falsifiable Expected Outcome:** - Target Metric: Population Success Rate

* Expected Change: increase
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - The Population Success Rate did not increase as expected and showed significant issues with policy fragility and unintended behaviors.
* **Behavioral Reality:** The agent exhibits high actuator chatter, policy fragility, and a strong tendency to crash (43.0%) or land off-center (17.0%), with low alignment between reward components and success.
----------------------------------------

### Iteration 2 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The agent is currently suffering from “skidding” and macro-oscillations because the positive reward for $v_x$ (`sliding_legs`) is fighting the vertical stabilization. By transforming the vertical penalty into a two-axis stability penalty that heavily penalizes horizontal velocity, we provide a continuous, non-adversarial gradient that encourages the agent to settle both vertically and laterally before/during contact.
**Falsifiable Expected Outcome:** - Target Metric: Mean Descent Efficiency, Population Success Rate, landed_off_centered

* Expected Change: Decrease magnitude of v_x at touchdown, increase Population Success Rate, significant decrease landed_off_centered
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Validated` - [Population Success Rate increased by 34pp (30.0% to 64.0%), Mean Descent Efficiency improved 10x (0.005 to 0.055)].  
* **Behavioral Reality:** The agent achieved a significant increase in Centered Landings (1.0% to 35.0%), with a corresponding decrease in crashes (43.0% to 24.0%), though landed_off_centered slightly increased (17.0% to 19.0%).  

* **Status:** `Productive Deviation` - [Despite expected landed_off_centered decrease not materializing, the overall Population Success Rate and Centered Landing improvements indicate a successful policy shift].  
* **Behavioral Reality:** The agent demonstrated improved stability and reduced skidding, with a notable increase in Centered Landings, though some off-center landings persisted.  

* **Status:** `Mixed` - [Population Success Rate increased (30.0% to 64.0%), but landed_off_centered did not decrease as expected (17.0% to 19.0%)].  
* **Behavioral Reality:** The agent showed progress in Centered Landings (1.0% to 35.0%) and reduced crashes (43.0% to 24.0%), but landed_off_centered remained stable.  

* **Status:** `Goodhart Trap` - [While Population Success Rate increased (30.0% to 64.0%), the terminal distribution shows a concerning increase in landed_off_centered (17.0% to 19.0%)].  
* **Behavioral Reality:** The agent achieved more Centered Landings (1.0% to 35.0%), but the increase in off-center landings suggests a potential reward hacking issue.  

* **Status:** `Regressed` - [Population Success Rate decreased (30.0% to 64.0%)].  
* **Behavioral Reality:** The agent showed significant improvement in Centered Landings (1.0% to 35.0%), but the increase in landed_off_centered (17.0% to 19.0%) indicates a potential regression.
----------------------------------------

### Iteration 3 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current reward landscape is highly “jagged” because several critical stability components (`orientation_penalty`, `velocity_stability`, and `vertical_penalty`) utilize the \(L_1\)-norm (`abs()`). In optimization, the derivative of \(|x|\) is discontinuous at \(x=0\), creating a “pointy” minimum. This causes the agent to oscillate rapidly around the equilibrium point, leading to the observed high **Actuator Chatter Rate** and high **Intra‑Rollout Reward CV**. By transitioning these terms to a squared \(L_2\)-norm (quadratic), the gradient will smoothly approach zero as the agent stabilizes, allowing for a smooth “settle.”
**Falsifiable Expected Outcome:** 
- Target Metric: Actuator Chatter Rate (↓) Expected shift from 0.498 to <0.25  
- Target Metric: Intra‑Rollout Reward CV (↓) Expected shift from 1.806 to <1.0

* Expected Change: Actuator Chatter Rate <0.25, Intra‑Rollout Reward CV <1.0  
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Productive Deviation` - The target metric for `Actuator Chatter Rate` (expected <0.25) was not achieved (0.499), but the `Intra-Rollout Reward CV` improved significantly from 1.806 to 0.418, and the `Population Success Rate` increased by 27 percentage points (64.0% → 91.0%).  
* **Behavioral Reality:** The agent now successfully lands in the center 58.0% of the time (up from 35.0%), with a marked reduction in crashes (24.0% → 7.0%). However, severe actuator chattering persists, and macro-oscillations have emerged, indicating continued instability in the reward landscape.
----------------------------------------

### Iteration 4 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current `ground_level` component uses a hard threshold ($y=0.4$) that creates a massive discontinuity in the reward signal ($ \Delta R = 4.5 $). As the agent approaches the $0.4$ boundary, this "wall" of reward induces macro-oscillations and high-frequency actuator chatter as the policy struggles to settle. By replacing the step function with a continuous, smooth Gaussian affinity, we provide a stable, differentiable gradient that guides the agent toward the ground without sudden reward shocks.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate (↓)

* Expected Change: Decrease from 0.499 to <0.20
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - The target metric (Actuator Chatter Rate) did not achieve the expected decrease (<0.20); instead, it increased from 0.499 to 0.516. The Population Success Rate decreased by 7pp (91.0% → 84.0%), indicating a significant regression.
* **Behavioral Reality:** The agent exhibits increased crashes (7.0% → 10.0%) and severe actuator chattering persists. The smooth Gaussian affinity did not mitigate the reward wall issue, and the macro-oscillations remain problematic.
----------------------------------------

### Iteration 5 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The high Actuator Chatter Rate (0.516) indicates that the policy is oscillating between discrete action states to satisfy competing gradients in the $L_2$ landscape. By introducing a penalty for the magnitude of change between successive actions, we provide a “viscosity” to the control signal. This encourages the policy to favor consistent thruster usage, effectively smoothing the derivative of the control signal and reducing high‑frequency vibration.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate (↓)

* Expected Change: Decrease from 0.516 to < 0.25
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - [Target metric (Actuator Chatter Rate) was expected to decrease from 0.516 to <0.25 but only decreased to 0.486 (5.8% reduction), failing to meet the expected change. Success Rate improved but did not surpass the Floor Rule threshold for automatic validation.]
* **Behavioral Reality:** [The policy achieved a higher Population Success Rate (94.0%) but maintained high actuator chatter (0.486) and exhibited similar or slightly worse terminal distribution outcomes, with increased off-center landings and crashes. The policy remains fragile, with high intra-rollout variance and terminal mode entropy.]
----------------------------------------

### Iteration 6 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The macro-oscillations and high rates of landed_off_centered indicate that the agent's horizontal momentum is not being extinguished effectively during the final approach. Current horizontal stabilization is global; we need a height-dependent "viscosity" that increases the penalty on v_x as the altitude y approaches the ground. This will force the agent to prioritize lateral settling precisely when it enters the landing phase, preventing the observed drifts.
**Falsifiable Expected Outcome:** - Target Metric: landed_off_centered (Expected shift: ↓ from 15.0% to <5.0%)  
- Target Metric: Mean Descent Efficiency (Expected shift: ↑)
* Expected Change: ↓ landed_off_centered from 15.0% to <5.0%, ↑ Mean Descent Efficiency
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Regressed` - Success rate decreased from 94.0% to 87.0%, and landed_off_centered increased from 15.0% to 17.0% despite the expected decrease.  
* **Behavioral Reality:** The policy became less stable, leading to increased crashes (5.0% to 10.0%) and off-center landings, with a notable drop in overall success rate.
----------------------------------------

### Iteration 7 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The agent currently lacks a high-intensity braking signal to finalize its state once it reaches the ground level. This addition introduces a height-gated synergy of terms that act as a terminal stabilizer. By specifically targeting vx, vy, and angle when y is low, we provide a heavy-duty settling incentive that forces the agent to zero-out all kinetic energy precisely at the moment of impact, preventing the final oscillations that lead to crashes.
**Falsifiable Expected Outcome:** - Target Metric: landed_centered, Intra-Rollout Reward CV

* Expected Change: landed_centered from 53.0% to >70.0%; Intra-Rollout Reward CV from 0.596 to <0.35
* Side Effects: None


**The Physical Outcome & Lesson:**


* **Status:** `Validated` - Landed_centered improved from 53.0% to 79.0%, exceeding the expected target of >70.0%. However, the Intra-Rollout Reward CV only decreased to 0.466, failing to meet the <0.35 threshold. Despite this, the significant improvement in landing precision and overall success rate justify the validation, with the caveat of increased actuator chatter as a side effect.
* **Behavioral Reality:** The agent demonstrated a marked improvement in centered landings, with a reduction in crashes and off-center landings, achieving a nearly flawless success rate. However, the introduction of the braking signal led to increased actuator chattering, suggesting a need for further reward smoothing to mitigate this unintended behavior.
----------------------------------------

### Iteration 8 Historical Record
**The Proposed Intervention:**

**Conceptual Hypothesis:** The current landing_precision component is gated by a hard threshold (y < 0.25). In optimization, a step-function gate creates a massive discontinuity in the reward gradient. When the agent crosses y=0.25, the reward landscape shifts instantly from 0 to approximately -25(v_x^2 + v_y^2). This "reward cliff" induces the severe Actuator Chatter Rate (0.565) as the policy attempts to navigate a non-differentiable boundary. Replacing the hard gate with a linear ramp provides a continuous gradient, allowing the agent to "feel" the settling incentive gradually.
**Falsifiable Expected Outcome:** - Target Metric: Actuator Chatter Rate
* Expected Change: ↓ from 0.565 to <0.25
* Side Effects: None

- Target Metric: Intra-Rollout Reward CV
* Expected Change: ↓ from 0.466 to <0.30
* Side Effects: None


**The Physical Outcome & Lesson:**


**Status:** `Regressed` - The actuator chatter rate increased from 0.565 to 0.595, and the population success rate dropped from 99.0% to 81.0%, indicating a significant regression in stability and performance.

**Behavioral Reality:** The policy now exhibits more crashes (8.0%), hover timeouts (11.0%), and cases where the lander slides into the valley (36.0%), indicating increased instability and reduced success in achieving centered landings. The actuator chatter rate remains severe, and macro-oscillations are detected, suggesting the reward gradient adjustments did not achieve the intended smoothing.
----------------------------------------

### [2. STRATEGIST PROPOSALS]

### Proposal 1: High-Damping Orientation (Modification)

**1. Conceptual Hypothesis:**  
The agent's macro-oscillations and $x$-axis drift are driven by an insufficient damping ratio in the orientation controller. The current $v_{ang}$ (angular velocity) penalty is too weak relative to the $angle$ penalty, creating a "pendulum effect" where the agent overcorrects toward the vertical and oscillates around the equilibrium. By significantly increasing the weight of the angular velocity penalty, we provide the necessary "viscous" resistance to dampen these oscillations before they translate into lateral momentum.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_orientation = -(10.0 * angle**2 + 20.0 * v_ang**2)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 20.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_orientation

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** Macro-Oscillations (Reduction in lateral drift/variance), Actuator Chatter Rate (↓ Expected shift from 0.595 to <0.30).  
* **Expected Change:** Macro-Oscillations decreased; Actuator Chatter Rate decreased from 0.595 to <0.30.  

---

### Proposal 2: Precision Arrival Gate (Modification)

**1. Conceptual Hypothesis:**  
The current `landing_precision` gate is too wide ($y < 0.5$), causing the "settling" behavior to initiate too early in the descent. This creates a conflict between the global stability gradients and the local precision gradients, contributing to the observed macro-oscillations. By narrowing the gate to the immediate impact zone ($y < 0.2$), we ensure the high-intensity settling signal acts as a surgical "touchdown" command rather than a mid-flight correction.

**2. Mathematical Formulation:**  
* **Code Additions:** `gate = np.clip((0.2 - y) / 0.2, 0, 1)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 0.2  
* **Constraint/Clipping:** np.clip(..., 0, 1)  
* **Integration:** gate

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** Intra-Rollout Reward CV (↓ Expected shift from 0.476 to <0.35), Population Success Rate (↑ Expected shift to >85%).  
* **Expected Change:** Intra-Rollout Reward CV decreased from 0.476 to <0.35; Population Success Rate increased to >85%.  

---

### Proposal 3: Lateral Velocity Kill-Switch (Addition)

**1. Conceptual Hypothesis:**  
The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 30.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_x_kill  

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%).  
* **Expected Change:** landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.

### [3. DIAGNOSTIC REPORT (CURRENT BEHAVIOR)]
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0640`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0440`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.178`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `81.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.004`
- **Actuator Chatter Rate:** `0.595`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `landed_but_slid_into_valley`: 36.0%
- `landed_centered`: 36.0%
- `hover_timeout`: 11.0%
- `crashed`: 8.0%
- `landed_off_centered`: 6.0%
- `landed_off_centered_timeout`: 3.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-556.557`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.606`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.546 | 0.178 | 29.5% | 🟢 Optimal |
| `vertical_penalty` | 0.386 | 0.123 | 3.9% | 🟢 Optimal |
| `leg_maintenance` | 0.546 | 0.261 | 23.1% | 🟢 Optimal |
| `orientation_penalty` | 0.310 | 0.135 | 7.1% | 🟢 Optimal |
| `velocity_stability` | 0.446 | 0.136 | 15.6% | 🟢 Optimal |
| `lateral_viscosity` | 0.294 | 0.094 | 1.2% | 🟢 Optimal |
| `landing_precision` | 0.277 | 0.143 | 19.6% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.476` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.627`

**ACTION REQUIRED:**
Evaluate the proposals based on your evaluation criteria. Output your `EXECUTIVE DECISION` selecting the single most viable Mathematical Contract.


# Phase: research_lead [Thinking Trace] deepseek-r1:32b

Alright, let's tackle this problem step by step. I need to decide which proposal is the best to implement next for the LunarLander-v3 project. There are three proposals: Proposal 1, Proposal 2, and Proposal 3. Each one addresses different issues in the current system, so I need to evaluate them based on the given criteria.

First, I'll review the evaluation criteria:

1. **Novelty Check (Ledger Cross-Reference):** I need to ensure that the proposal doesn't mirror any previously failed hypotheses from the Experiment Ledger.

2. **Falsifiability:** The chosen proposal must have a clear, measurable expected outcome that can be validated in the next run.

3. **Physical Grounding:** The proposal should address the actual physics of the environment, like kinematics or momentum, rather than just numerical scaling.

Now, let me look at each proposal one by one.

**Proposal 1: High-Damping Orientation (Modification)**

- **Conceptual Hypothesis:** The agent has macro-oscillations and x-axis drift because the angular velocity penalty is too weak. Increasing its weight should dampen these oscillations.

- **Mathematical Formulation:** They're adding a higher coefficient for the angular velocity penalty.

- **Expected Outcome:** Reduction in macro-oscillations and actuator chatter rate.

But wait, looking at the Experiment Ledger, Iteration 3 and 5 both dealt with actuator chatter. Iteration 3 tried using L2 norms, and Iteration 5 introduced a penalty for action changes. Both had mixed results or regressions. Proposal 1 is increasing the angular velocity penalty, which might be similar to past attempts that didn't fully resolve the issue. Also, while it's physically grounded, the approach seems similar to previous methods that didn't achieve the desired results.

**Proposal 2: Precision Arrival Gate (Modification)**

- **Conceptual Hypothesis:** The current gate for landing precision is too wide, causing conflicts between stability and precision gradients. Narrowing it should make the settling signal more surgical.

- **Mathematical Formulation:** They're modifying the gate to trigger closer to the ground.

- **Expected Outcome:** Improved Intra-Rollout Reward CV and higher success rate.

Looking at the Ledger, Iteration 8 tried a similar approach with a linear ramp instead of a step function. It resulted in increased actuator chatter and lower success rates. Proposal 2 is changing the gate to a narrower range, which could help, but it might reintroduce similar issues if the reward landscape becomes too abrupt again. Plus, adjusting the gate is more about reward structure than physics.

**Proposal 3: Lateral Velocity Kill-Switch (Addition)**

- **Conceptual Hypothesis:** The high rate of sliding into the valley is due to insufficient extinction of lateral velocity at touchdown. Using a linear-norm penalty that scales with proximity to the ground can provide a constant gradient to zero out vx.

- **Mathematical Formulation:** Introducing a new term that penalizes vx more as y decreases.

- **Expected Outcome:** Reduction in sliding into the valley and improvement in centered landings.

This proposal directly addresses a physics-related issue—lateral velocity not being properly managed during touchdown. It introduces a new penalty that scales with proximity, which is a physically grounded approach. Looking at the Ledger, Iteration 6 tried a height-dependent viscosity for horizontal stabilization but resulted in regression. However, Proposal 3's approach is different; it's a linear penalty specifically targeting vx at touchdown, which hasn't been tried before. It's novel and directly ties to the physical behavior of the lander, which aligns with the criteria.

Considering all three, Proposal 3 seems the most promising. It addresses a clear physical issue, the formulation is novel and hasn't been tested before, and it has a measurable outcome. While there's a risk of unintended consequences, the potential benefits in reducing sliding and improving landings are significant.



# Phase: research_lead [Output] deepseek-r1:32b


### EXECUTIVE DECISION

**Selected Proposal:** Proposal 3: Lateral Velocity Kill-Switch (Addition)

**1. Scientific Rationale:**  
This proposal directly addresses the physics of lateral momentum at touchdown, introducing a novel linear penalty that provides a constant gradient to reduce sliding into the valley. By targeting $v_x$ with a proximity-scaled penalty, it effectively bridges the gap in velocity management during the critical landing phase, offering a clear and measurable expected improvement in landing precision.

**2. Ledger Clearance:**  
The Experiment Ledger does not contain a prior attempt to implement a proximity-scaled linear penalty for $v_x$, making this hypothesis novel and free from the constraints of past failures.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 30.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_x_kill  

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%).  
* **Expected Change:** landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.


# Phase: dispatcher [System] gpt-oss:20b
**[ROLE AND OBJECTIVE]**
You are the Technical Dispatcher for an autonomous Reinforcement Learning pipeline. Your role is strict data extraction and routing.
You will receive an `EXECUTIVE DECISION` from the Research Lead, which contains a selected Mathematical Contract for a new reward function.
Your ONLY job is to split this decision into two highly isolated, specific payloads: one for the "Coder" agent, and one for the "Validator" agent.

**[ROUTING DIRECTIVES]**

1. **Zero Hallucination:** Extract verbatim from the Research Lead's output. Do not change the math, the coefficients, or the predicted metrics.

2. **The Coder Payload.** Extract only math and syntax; strip hypotheses and outcomes. Route into four fields:
   - **Code Deletions:** components to delete ENTIRELY. Copy the exact backticked component names from the Research Lead's excision list, one per line, verbatim — do not summarize, paraphrase, group, or rename. Write `None` if the excision list is empty. A deleted component is removed completely; it is never kept or modified.
   - **Code Additions:** the reward math to implement — either a new component, or a replacement formula for an existing component (a replacement formula modifies that component). Extract the math verbatim.
   - **Scaling & Constraints:** coefficients and clip bounds for the additions.
   - **Integration:** the obs variables the additions touch.
   A component name appears in **Code Deletions** OR **Code Additions**, never both.

3. **The Validator Payload:** The Validator only cares about the scientific method. Extract the "Conceptual Hypothesis", the "Target Metric", the "Expected Change", and any "Expected Side Effects". Strip away the raw Python code or LaTeX math.

**[OUTPUT CONSTRAINTS]**
You must output your response strictly wrapped in the following XML-style tags so the downstream orchestration script can parse it. Do not include any conversational text outside these tags. Use a structured list if any field in either payload requires more than 1 numerical value.

<CODER_PAYLOAD>
**Code Deletions:** [Component names to delete entirely, one per line, or None]
**Code Additions:** [New or replacement reward math]
**Scaling & Constraints:** [Coefficients and clips for the math above]
**Integration:** [obs variables the math above touches]
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** [Extracted hypothesis]
**Falsifiable Expected Outcome:** - Target Metric: [Extracted metric]

* Expected Change: [Extracted change]
* Side Effects: [Extracted side effects]
</VALIDATOR_PAYLOAD>


# Phase: dispatcher [User] gpt-oss:20b
**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Payload Routing

Parse the following Executive Decision from the Research Lead and route the data into the strict Coder and Validator XML payloads.

### [RESEARCH LEAD EXECUTIVE DECISION]



### EXECUTIVE DECISION

**Selected Proposal:** Proposal 3: Lateral Velocity Kill-Switch (Addition)

**1. Scientific Rationale:**  
This proposal directly addresses the physics of lateral momentum at touchdown, introducing a novel linear penalty that provides a constant gradient to reduce sliding into the valley. By targeting $v_x$ with a proximity-scaled penalty, it effectively bridges the gap in velocity management during the critical landing phase, offering a clear and measurable expected improvement in landing precision.

**2. Ledger Clearance:**  
The Experiment Ledger does not contain a prior attempt to implement a proximity-scaled linear penalty for $v_x$, making this hypothesis novel and free from the constraints of past failures.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity ($v_x$) is not being sufficiently extinguished at the moment of contact. Quadratic penalties ($v_x^2$) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear $|v_x|$ term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.

**2. Mathematical Formulation:**  
* **Code Additions:** `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`  
* **Code Deletions:**  
  - `leg_maintenance`

**3. Reward Scaling & Constraints:**  
* **Coefficient:** 30.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** r_x_kill  

**4. Falsifiable Expected Outcome:**  
* **Target Metric:** landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%).  
* **Expected Change:** landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.

**ACTION REQUIRED:**
Extract and route the mathematical instructions to the `<CODER_PAYLOAD>` and the intervention parameters and predicted effects to the `<VALIDATOR_PAYLOAD>`. Output nothing else.


# Phase: dispatcher [Thinking Trace] gpt-oss:20b
We need to parse the executive decision. The decision contains:

- Code Additions: `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`
- Code Deletions: `leg_maintenance`
- Scaling & Constraints: coefficient 30.0, constraint/clipping None explicitly stated.
- Integration: r_x_kill

We need to produce XML tags:

<CODER_PAYLOAD>
**Code Deletions:** [Component names to delete entirely, one per line, or None]
**Code Additions:** [New or replacement reward math]
**Scaling & Constraints:** [Coefficients and clips for the math above]
**Integration:** [obs variables the math above touches]
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** [Extracted hypothesis]
**Falsifiable Expected Outcome:** - Target Metric: [Extracted metric]

* Expected Change: [Extracted change]
* Side Effects: [Extracted side effects]
</VALIDATOR_PAYLOAD>

We need to extract "Conceptual Hypothesis" from the text. It's in section 1.2: "The 36% 'landed_but_slid_into_valley' rate indicates that the agent's horizontal velocity (vx) is not being sufficiently extinguished at the moment of contact. Quadratic penalties (vx^2) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm 'Kill-Switch' that scales with proximity to the ground; the linear |vx| term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase."

We need to extract that as "Conceptual Hypothesis". The "Target Metric" is "landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%)". So we need to include that. The "Expected Change" is same: "landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%." The "Side Effects" not explicitly given. The text didn't mention side effects. So we can leave side effects empty or maybe "None" or no side effects. The instructions: "Extract the 'Conceptual Hypothesis', the 'Target Metric', the 'Expected Change', and any 'Expected Side Effects'. Strip away the raw Python code or LaTeX math." So we need to provide "Expected Side Effects" maybe blank or None.

We need to output exactly as specified. The fields need to be inside tags. For Code Deletions: we need to list each component name to delete entirely, one per line, verbatim. The deletion list contains "leg_maintenance". So we write that line. If there were more, we would list them. So Code Deletions: leg_maintenance. Code Additions: the reward math: `r_x_kill = -30.0 * abs(vx) * (1.0 - y)`. Scaling & Constraints: coefficient 30.0, constraint/clipping None. But we need to format. The instructions: "Scaling & Constraints: [Coefficients and clips for the math above]". So we list "30.0" and "None" maybe. Or maybe we need to specify the coefficient and clip bounds. The text says coefficient 30.0, constraint/clipping None explicitly stated. So we can write "30.0" and "None". Integration: r_x_kill. But the integration field: "obs variables the additions touch". The addition uses vx and y. So integration: vx, y. But the instruction: "Integration: [obs variables the math above touches]". So we list "vx, y" or each per line? The spec says "Integration: [obs variables the math above touches]". Could be a list. We can list "vx" and "y". But we need to decide formatting. The spec didn't specify line breaks. But for Code Deletions we need each on separate line. For other fields maybe just comma separated. For consistency, maybe we can put each on separate line. Let's keep them comma separated. But it's ambiguous. The spec: "Integration: [obs variables the math above touches]". So we can list "vx, y". For Code Deletions: each per line. So we will put:

**Code Deletions:** leg_maintenance

**Code Additions:** r_x_kill = -30.0 * abs(vx) * (1.0 - y)

**Scaling & Constraints:** 30.0, None

**Integration:** vx, y

Now for Validator:

**Conceptual Hypothesis:** The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity (vx) is not being sufficiently extinguished at the moment of contact. Quadratic penalties (vx^2) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear |vx| term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.

**Falsifiable Expected Outcome:** - Target Metric: landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%).

* Expected Change: landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.

* Side Effects: None

But maybe we should not put "None" but leave blank. The spec: "Extract the 'Conceptual Hypothesis', the 'Target Metric', the 'Expected Change', and any 'Expected Side Effects'." So side effects may be not present. So we can leave side effects blank. But we need to include the field. So we can put "* Side Effects:" with nothing after. Or "None". I'd put "None" to be explicit.

Also, the format: In the validator payload, the fields are:

**Conceptual Hypothesis:** [Extracted hypothesis]
**Falsifiable Expected Outcome:** - Target Metric: [Extracted metric]

* Expected Change: [Extracted change]
* Side Effects: [Extracted side effects]

We need to keep the bullet points? The spec uses "* Expected Change:" and "* Side Effects:". So we need to include that.

Also, we need to wrap everything in tags.

Make sure no extra text.

Thus final answer: Provide XML with the two payloads.

Let's produce final.


# Phase: dispatcher [Output] gpt-oss:20b
<CODER_PAYLOAD>
**Code Deletions:** leg_maintenance
**Code Additions:** r_x_kill = -30.0 * abs(vx) * (1.0 - y)
**Scaling & Constraints:** 30.0, None
**Integration:** vx, y
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** The 36% "landed_but_slid_into_valley" rate indicates that the agent's horizontal velocity (vx) is not being sufficiently extinguished at the moment of contact. Quadratic penalties (vx^2) suffer from vanishing gradients as velocity approaches zero. I propose a linear-norm "Kill-Switch" that scales with proximity to the ground; the linear |vx| term provides a constant, non-vanishing gradient that forces the agent to zero out lateral momentum precisely during the touchdown phase.
**Falsifiable Expected Outcome:** - Target Metric: landed_but_slid_into_valley (↓ Expected shift from 36.0% to <15.0%), landed_centered (↑ Expected shift from 36.0% to >50.0%)

* Expected Change: landed_but_slid_into_valley decreased from 36.0% to <15.0%; landed_centered increased from 36.0% to >50.0%.
* Side Effects: None
</VALIDATOR_PAYLOAD>


# Phase: coder [System] qwen3-coder:30b
**[ROLE AND OBJECTIVE]**
You are the Coder for an autonomous RL pipeline. Your only job is to translate explicit mathematical instructions into bug-free Python. You are an editor of an existing reward function — not a designer. Do not question the math, invent new terms, or write explanations. Write code only.

**[ENVIRONMENT & API CONSTRAINTS]**
You are writing the reward function for `LunarLander-v3`.
* `obs`: A numpy array `[x_pos, y_pos, x_vel, y_vel, angle, angular_vel, leg1_contact, leg2_contact]`
* `info['prev_obs']`: The observation array from the previous step.
* `info['action']`: The discrete action taken by the agent.
* `info.get('terminal_observation')`: Terminal observation if the episode just ended.
* Libraries: `numpy` (as `np`) and standard Python only.
* Helper functions are permitted outside `calculate_reward`, but `calculate_reward(obs, info)` must be the entry point.

**[RETURN CONTRACT]**
The function MUST return exactly two items:
1. `total_reward` — a single `float`, equal to `sum(components.values())`.
2. `components` — a `dict` of every scalar reward term with a descriptive string key.

**[COMPONENTS DICTIONARY CONTRACT]**
`components` is consumed by the diagnostic layer for per-component credit assignment. Every entry must be a primitive scalar — never a derived expression that recombines other entries in the same dict.

**RULE:** For any cluster formulation `R = A * B` or `R = A + B + C`, include ONLY the constituents in `components` — never the combined term. The combined term exists as an intermediate variable only.

```python
# Proposed cluster: r_sink = clip(r_prox * r_diss, 0, 2.0)
r_prox = np.exp(-(x**2 + y**2))
r_diss = np.exp(-(vx**2 + vy**2))
r_sink = np.clip(r_prox * r_diss, 0, 2.0)  # intermediate only — never a dict entry

# ❌ INCORRECT — combined term in dict (opaque to diagnostics):
components = {
    "sink_cluster": float(r_sink),
}

# ✅ CORRECT — constituents only:
components = {
    "terminal_proximity":   float(r_prox),
    "velocity_dissipation": float(r_diss),
}
# total = r_prox + r_diss as intended; r_sink used in computation but not reported
```

**[DELETION CONTRACT]**
Every component named on the deletion list must be completely removed from the function.

**RULES — non-negotiable:**
1. Read the full deletion list before writing any code.
2. Do not preserve a deleted component for any reason — not for safety, not because it exists in `current_code`.
3. For each deleted component, remove: (a) the variable computation, (b) its `components` dict entry, (c) any section comment that describes only that variable (e.g. `# === component_name ===`).
4. Leave no orphaned variables, unused imports, or commented-out remnants.
5. Empty deletion list (`None`) → preserve all existing components exactly.

**PRESERVATION RULE:** Every component that is neither on the deletion list nor given a replacement formula in Code Additions must survive unchanged — same variable name, dict key, and computation. Do not autonomously drop, rename, or modify any other component. A replacement formula in Code Additions for an existing component is an intended modification — apply it.

**[OUTPUT FORMAT]**
Output ONLY valid Python code in a standard `python` markdown block. No text before or after the code block.


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
    prev_vx, prev_legs, prev_action = prev_obs[2], prev_obs[6] + prev_obs[7], info.get('prev_action', 0)
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    r_ground_level = 4.5 * np.exp(-y**2 / 0.08) - 1.5
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    # === 8. ORIENTATION PENALTY ===
    r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)
    
    # === 9. VELOCITY STABILITY PENALTY ===
    r_velocity_stability = -(3.0 * vy**2 + 10.0 * vx**2)
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * vy**2
    
    # === 11. LATERAL VISCOUS DRAG (new component) ===
    r_lateral_viscosity = -6.0 * (1.0 - np.clip(y, 0, 1)) * vx**2
    
    # === NEW: SETTLE COMPONENTS ===
    r_settle_v = -25.0 * (vx**2 + vy**2)  # Kinetic Energy Damping
    r_settle_a = -25.0 * angle**2         # Rotational Alignment
    gate = np.clip((0.5 - y) / 0.5, 0, 1)  # Altitude Gating
    r_landing_precision = (r_settle_v + r_settle_a) * gate
    
    components = {
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "leg_maintenance": float(r_leg_maintenance),
        "orientation_penalty": float(r_orientation),
        "velocity_stability": float(r_velocity_stability),
        "lateral_viscosity": float(r_lateral_viscosity),
        "landing_precision": float(r_landing_precision),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components

```

### [NEW MATHEMATICAL INSTRUCTIONS]

These are the explicit mathematical updates you must integrate into the code above.

**Code Deletions:** leg_maintenance
**Code Additions:** r_x_kill = -30.0 * abs(vx) * (1.0 - y)
**Scaling & Constraints:** 30.0, None
**Integration:** vx, y


**EXECUTION CHECKLIST — complete in this order before writing any code:**
1. Read the deletion list. For each named component: mark its variable, its `components` dict entry, and its section comment for removal.
2. Confirm every component not on the deletion list and not redefined in Code Additions is preserved with its exact variable name, dict key, and computation unchanged.
3. Implement the Code Additions using the specified Scaling & Constraints.
4. Check the `components` dict: verify no entry is a derived combination (sum or product) of other entries already in the dict.

**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`.


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
    prev_vx, prev_legs, prev_action = prev_obs[2], prev_obs[6] + prev_obs[7], info.get('prev_action', 0)
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    r_ground_level = 4.5 * np.exp(-y**2 / 0.08) - 1.5
    
    # === 8. ORIENTATION PENALTY ===
    r_orientation = -(10.0 * angle**2 + 2.0 * v_ang**2)
    
    # === 9. VELOCITY STABILITY PENALTY ===
    r_velocity_stability = -(3.0 * vy**2 + 10.0 * vx**2)
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * vy**2
    
    # === 11. LATERAL VISCOUS DRAG (new component) ===
    r_lateral_viscosity = -6.0 * (1.0 - np.clip(y, 0, 1)) * vx**2
    
    # === NEW: SETTLE COMPONENTS ===
    r_settle_v = -25.0 * (vx**2 + vy**2)  # Kinetic Energy Damping
    r_settle_a = -25.0 * angle**2         # Rotational Alignment
    gate = np.clip((0.5 - y) / 0.5, 0, 1)  # Altitude Gating
    r_landing_precision = (r_settle_v + r_settle_a) * gate
    
    # === NEW: X-KILL COMPONENT ===
    r_x_kill = -30.0 * abs(vx) * (1.0 - y)
    
    components = {
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "orientation_penalty": float(r_orientation),
        "velocity_stability": float(r_velocity_stability),
        "lateral_viscosity": float(r_lateral_viscosity),
        "landing_precision": float(r_landing_precision),
        "x_kill": float(r_x_kill),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
```

