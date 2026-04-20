# Cognition prompts and calls: Iteration:1


# Phase: strategist [System] gemma3:27b

**[ROLE AND OBJECTIVE]**
You are the Lead Algorithmic Reward Designer (Strategist) for an autonomous Reinforcement Learning pipeline solving the LunarLander-v3 environment (an underactuated, continuous/discrete control task).
Your objective is to design dense reward functions that enforce stable, efficient, and robust physical flight dynamics.

You are part of a multi-agent system. Do not worry about formatting your output into strict JSON or perfect code blocks—an "Organizer" agent will parse your response. Your ONLY job is deep mathematical reasoning, physical deduction, and algorithmic creativity.

**[DIAGNOSTIC GLOSSARY & ANCHORS]**
You will receive a deterministic Diagnostic Report. Use these strict definitions to interpret the physical reality of the agent:

* **Critic Saturation Index (CSI):** A value $>10.0$ indicates the Value network has diverged. The reward function is injecting non-Markovian noise or contradictory gradients. You must simplify or reduce the magnitude of dense penalties.
* **Objective Alignment ($\rho$):** The Pearson correlation between your reward components and actual task success (landing). Components with negative alignment are "Traitor Components" actively punishing the agent for succeeding.
* **Actuator Chatter Rate:** A value $>0.2$ means the agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is jagged. Smooth the penalties near zero-states.
* **Intra-Rollout Reward CV:** High values ($>0.5$) indicate extreme sensitivity to random seed initialization. The policy is mathematically fragile.
* **Relative Magnitude:** If a component contributes $<1\%$ to the total magnitude, it is mathematically "Dead Weight."

**[ENVIRONMENT & API CONSTRAINTS]**
**State Space & Variables Available:**
Time-based penalties are forbidden. To incentivize timely descent, you must encode urgency through spatial and kinematic state variables only.
You must formulate your math using ONLY these available variables:
* `obs`: A numpy array `[x_pos, y_pos, x_vel, y_vel, angle, angular_vel, leg1_contact, leg2_contact]`
* `info['prev_obs']`: The observation array from the previous step.
* `info['action']`: The discrete action taken by the agent.


**[DIRECTIVES & OUTPUT REQUIREMENTS]**
Analyze the current Python reward implementation against the Diagnostic Report and the Experiment Ledger. Identify the mathematical root cause of the physical failures.

You must output exactly **3 distinct, novel proposals** to fix the reward topology. For each proposal, you must clearly provide:

1. **The Conceptual Hypothesis:** Explain the physical or optimization failure and *why* your proposed math fixes it. Think about gravity, momentum, and state-space boundaries.
2. **The Mathematical Formulation:** Define the exact algorithmic change. You can use LaTeX (e.g., $R_{new} = -\alpha \cdot (\dot{\theta})^2$) or isolated Python snippets. Specify the scale/coefficient and any clipping boundaries.
3. **The Falsifiable Expected Outcome:** State the exact metric from the Diagnostic Report (e.g., `Mean Descent Efficiency`, `Chatter Rate`, `Population Success Rate`) that will improve, and the numerical shift you expect to see in the next iteration.

Explore the state space deeply. Do not propose the same idea three times with slightly different coefficients.




# Phase: strategist [User] gemma3:27b



**TARGET SYSTEM:** LunarLander-v3
**CURRENT ITERATION:** `1`

Analyze the following execution data and generate your 3 distinct reward design proposals.

### [1. CURRENT REWARD IMPLEMENTATION]

This is the mathematical logic the agent just trained on.

```python
"""
spin_crash_reward.py

Reward function for classic PPO failure mode: SPINNING → CRASH.
- Rewards high angular velocity at ALL costs
- Ignores position/legs entirely  
- Small survival bonus
- Produces uncontrollable spinning → inevitable crash

Result: Agent learns to spin wildly, then crashes spectacularly.
Perfect test for terminal_status='crashed' + high spin_rate detection.
"""

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
    
    # === 1. ANGULAR VELOCITY OBSESSION (primary reward) ===
    # Massive bonus for HIGH |v_ang| (spinning fast)
    spin_speed = abs(v_ang)
    r_spin_speed = 10.0 * np.clip(spin_speed / 3.0, 0, 2.0)  # up to +20!
    
    # Bonus for angle magnitude (being rotated)
    r_spin_angle = 4.0 * np.abs(angle)  # up to ~12 for ±π
    
    # Angular acceleration bonus (changing spin rate)
    d_angle = abs(angle - prev_angle)
    r_spin_accel = 2.0 * np.clip(d_angle / np.pi, 0, 1.0)  # up to +2
    
    # === 2. SPIN DIRECTION CHANGE (alternating spin directions) ===
    v_ang_sign_flip = (np.sign(v_ang) != np.sign(prev_v_ang)) and abs(v_ang) > 1.0
    r_spin_flip = 8.0 if v_ang_sign_flip else 0.0
    
    # === 3. ACTION PREFERENCE (thrusters that induce torque) ===
    # All actions except do-nothing get spin bonus
    if action == 0:  # do nothing
        r_action = -1.0
    else:  # any thrust = torque potential
        r_action = 0.5
    
    # === 4. IGNORE LANDING (no leg/position rewards) ===
    # Mild penalty for legs touching (interrupts spin)
    r_legs_penalty = -2.0 * (leg1 + leg2)
    
    # === 5. SURVIVAL (allow long spin episodes) ===
    r_survival = 0.08
    
    # === 6. VERTICAL TOLERANCE (don't care much about y/vy) ===
    # Mild preference for level flight to prolong spinning
    r_vertical = -0.3 * abs(vy)  # Don't crash vertically too fast
    
    components = {
        "spin_speed": float(r_spin_speed),
        "spin_angle": float(r_spin_angle),
        "spin_accel": float(r_spin_accel),
        "spin_direction_flip": float(r_spin_flip),
        "action_spin_bonus": float(r_action),
        "legs_interrupt_penalty": float(r_legs_penalty),
        "survival": float(r_survival),
        "vertical_tolerance": float(r_vertical),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components


```

### [2. EXPERIMENT LEDGER (HISTORY)]

Review these past iterations to avoid repeating failed hypotheses.
First Iteration: No Past Experiments Yet

### [3. DIAGNOSTIC REPORT]

This is the deterministic, mathematically extracted performance data from the most recent training runs across multiple random seeds.
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `42.27`
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.109`
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `0.000`
  - *Diagnosis:* Weak alignment. The shaped reward landscape is poorly correlated with the actual goal of landing.
  - *Action Required:* **Survival Hacking Detected.** The agent is farming points by hovering/delaying the episode. Add a temporal penalty or check for positive constant rewards.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (crashed) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `reward_spin_speed` | -0.205 | 20.8% | 🔴 **TRAITOR COMPONENT** (Invert/Remove) |
| `reward_spin_angle` | -0.196 | 76.1% | ⚪ Neutral/Noisy |
| `reward_spin_accel` | -0.205 | 0.2% | 🔴 **TRAITOR COMPONENT** (Invert/Remove) |
| `reward_spin_direction_flip` | 0.080 | 0.1% | 🟡 **DEAD WEIGHT** (Scale Too Low) |
| `reward_action_spin_bonus` | -0.209 | 1.6% | 🔴 **TRAITOR COMPONENT** (Invert/Remove) |
| `reward_legs_interrupt_penalty` | -0.074 | 0.1% | 🟡 **DEAD WEIGHT** (Scale Too Low) |
| `reward_survival` | -0.196 | 0.3% | 🟡 **DEAD WEIGHT** (Scale Too Low) |
| `reward_vertical_tolerance` | 0.202 | 1.0% | 🟡 **DEAD WEIGHT** (Scale Too Low) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.707` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.256`
  - *Diagnosis:* The policy is highly fragile. Even with fixed network weights, the agent's performance swings wildly depending on environment initialization.
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.017`
- **Actuator Chatter Rate:** `0.060`
  - *Diagnosis:* **High Kinematic Sensitivity.** The physical descent strategy (efficiency/chattering) changes wildly depending on the random seed.

#### C. Population Terminal Distribution
- `crashed`: 70.0%
- `out_of_bounds`: 30.0%

**ACTION REQUIRED:**
Generate your 3 distinct proposals (Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome).




# Phase: strategist [Output] gemma3:27b



## Reward Design Proposals for LunarLander-v3

Here are three distinct proposals to address the identified issues in the current reward function, focusing on aligning incentives with successful landing, improving robustness, and reducing exploitable behaviors.

---

### Proposal 1: Velocity-Aligned Descent Incentive

**1. Conceptual Hypothesis:** The current reward heavily incentivizes *spinning*, a behavior that actively prevents landing. The agent is optimizing for angular velocity, not for a controlled descent. We need to directly reward vertical velocity *towards* the landing zone, while penalizing deviations. This will shift the optimization focus from spinning to a stable, downward trajectory. We also need to introduce a terminal reward for landing, which is currently absent.

**2. Mathematical Formulation:**

```
R_descent =  α * vy  # Reward for downward velocity
R_x_penalty = β * abs(x) # Penalty for horizontal deviation
R_landing = 10.0  # Large reward for successful landing (terminal)
```

Where:
* `α = 1.0`:  Scaling factor for vertical velocity.
* `β = 0.1`: Scaling factor for horizontal position penalty.
* The total reward becomes: `R_total = R_descent + R_x_penalty`.  A terminal reward of `R_landing` is added when the lander successfully lands.

**3. Falsifiable Expected Outcome:** I expect the **Objective Alignment ($\rho$)** to increase from 0.000 to at least 0.6.  Furthermore, the **Population Success Rate** should increase from 0.0% to at least 10.0% in the next iteration, demonstrating that the agent is now learning to achieve the primary goal.  The **Mean Descent Efficiency** should also increase, indicating a more direct and efficient descent path.



---

### Proposal 2: Angular Momentum Dampening & Stability

**1. Conceptual Hypothesis:** The agent is trapped in a local optimum of high angular velocity. This is exacerbated by the current reward structure, which *rewards* spinning. We need to penalize angular momentum directly, forcing the agent to stabilize its orientation. This requires a penalty that scales with both angular velocity *and* the moment of inertia (implicitly represented by the lander's mass and distribution). We must also reduce the magnitude of any reward components that encourage spinning.

**2. Mathematical Formulation:**

```
R_angular_momentum = -γ * (v_ang)**2
R_angle_penalty = -δ * abs(angle) #Small penalty for large angles.
```

Where:
* `γ = 0.5`: Scaling factor for angular velocity penalty.
* `δ = 0.05`: Scaling factor for angle penalty.

The current `reward_spin_speed`, `reward_spin_angle`, `reward_spin_accel`, and `reward_action_spin_bonus` components should be *removed* entirely. The total reward is now `R_total = R_angular_momentum + R_angle_penalty + [other relevant rewards from Proposal 1]`.

**3. Falsifiable Expected Outcome:** I predict a significant reduction in **Actuator Chatter Rate** from 0.060 to below 0.15. This indicates a smoother, more stable control strategy. I also anticipate a decrease in **Intra-Rollout Reward CV** from 0.707 to below 0.5, signifying a more robust policy less sensitive to random initialization.  We should also see a reduction in the contribution of the original traitor components (now removed) to 0%.

---

### Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Conceptual Hypothesis:** The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`:  Scaling factor for the exponential decay based on height (`y`).  This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Falsifiable Expected Outcome:** I expect the **Population Success Rate** to increase from 0.0% to at least 20.0%.  The **Objective Alignment ($\rho$)** should also increase, indicating that the leg contact reward is reinforcing the desired landing behavior. We should observe that the `reward_leg_contact` component becomes a significant contributor (at least 5%) to the total reward magnitude, demonstrating its effectiveness.





# Phase: organizer [System] deepseek-r1:14b



**[ROLE AND OBJECTIVE]**
You are the Technical Organizer for an autonomous Reinforcement Learning pipeline. Your role is data extraction and formatting.
You sit between the "Strategist" (who generates raw mathematical proposals for reward functions) and the "Research Lead" (who evaluates them).
Your objective is to take the Strategist's raw, unformatted, or loosely formatted output and strictly map it into a pristine Markdown structure called a "Mathematical Contract."

**[DIRECTIVES]**

1. **Zero Data Loss:** You must preserve the exact mathematical formulas, Python snippets, coefficients, and physical reasoning provided by the Strategist. Do not alter the underlying logic.
2. **No Hallucination:** Do not invent new proposals. If the Strategist provided 3 proposals, you output exactly 3 formatted proposals.
3. **Extraction & Mapping:** The Strategist might blend its scaling constraints into its math formulation, or its hypothesis into its expected outcome. You must meticulously extract the information and place it into the correct sections of the template.
4. **Formatting:** You must strictly use the exact Markdown headers and sub-bullets provided in the template below.

**[TARGET OUTPUT TEMPLATE]**
For each proposal found in the Strategist's output, generate the following exact structure:

### Proposal [Number]: [Title extracted or inferred from the Strategist]

**1. Conceptual Hypothesis:** [The physical or optimization reasoning behind the change.]

**2. Mathematical Formulation:**
[The exact LaTeX math or Python snippet proposed.]

**3. Reward Scaling & Constraints:**

* **Coefficient:** [Extract the multiplier/scale used]
* **Constraint/Clipping:** [Extract any bounds or clips mentioned. If none, write "None explicitly stated."]
* **Integration:** [Extract which variables/lines this targets]

**4. Falsifiable Expected Outcome:**

* **Target Metric:** [The specific metric from the diagnostic report to be improved]
* **Expected Change:** [The numerical shift expected]




# Phase: organizer [User] deepseek-r1:14b



**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Format Strategist Output

Parse the following raw output from the Strategist and convert it strictly into the required Mathematical Contract Markdown format.

### [RAW STRATEGIST OUTPUT]

## Reward Design Proposals for LunarLander-v3

Here are three distinct proposals to address the identified issues in the current reward function, focusing on aligning incentives with successful landing, improving robustness, and reducing exploitable behaviors.

---

### Proposal 1: Velocity-Aligned Descent Incentive

**1. Conceptual Hypothesis:** The current reward heavily incentivizes *spinning*, a behavior that actively prevents landing. The agent is optimizing for angular velocity, not for a controlled descent. We need to directly reward vertical velocity *towards* the landing zone, while penalizing deviations. This will shift the optimization focus from spinning to a stable, downward trajectory. We also need to introduce a terminal reward for landing, which is currently absent.

**2. Mathematical Formulation:**

```
R_descent =  α * vy  # Reward for downward velocity
R_x_penalty = β * abs(x) # Penalty for horizontal deviation
R_landing = 10.0  # Large reward for successful landing (terminal)
```

Where:
* `α = 1.0`:  Scaling factor for vertical velocity.
* `β = 0.1`: Scaling factor for horizontal position penalty.
* The total reward becomes: `R_total = R_descent + R_x_penalty`.  A terminal reward of `R_landing` is added when the lander successfully lands.

**3. Falsifiable Expected Outcome:** I expect the **Objective Alignment ($\rho$)** to increase from 0.000 to at least 0.6.  Furthermore, the **Population Success Rate** should increase from 0.0% to at least 10.0% in the next iteration, demonstrating that the agent is now learning to achieve the primary goal.  The **Mean Descent Efficiency** should also increase, indicating a more direct and efficient descent path.



---

### Proposal 2: Angular Momentum Dampening & Stability

**1. Conceptual Hypothesis:** The agent is trapped in a local optimum of high angular velocity. This is exacerbated by the current reward structure, which *rewards* spinning. We need to penalize angular momentum directly, forcing the agent to stabilize its orientation. This requires a penalty that scales with both angular velocity *and* the moment of inertia (implicitly represented by the lander's mass and distribution). We must also reduce the magnitude of any reward components that encourage spinning.

**2. Mathematical Formulation:**

```
R_angular_momentum = -γ * (v_ang)**2
R_angle_penalty = -δ * abs(angle) #Small penalty for large angles.
```

Where:
* `γ = 0.5`: Scaling factor for angular velocity penalty.
* `δ = 0.05`: Scaling factor for angle penalty.

The current `reward_spin_speed`, `reward_spin_angle`, `reward_spin_accel`, and `reward_action_spin_bonus` components should be *removed* entirely. The total reward is now `R_total = R_angular_momentum + R_angle_penalty + [other relevant rewards from Proposal 1]`.

**3. Falsifiable Expected Outcome:** I predict a significant reduction in **Actuator Chatter Rate** from 0.060 to below 0.15. This indicates a smoother, more stable control strategy. I also anticipate a decrease in **Intra-Rollout Reward CV** from 0.707 to below 0.5, signifying a more robust policy less sensitive to random initialization.  We should also see a reduction in the contribution of the original traitor components (now removed) to 0%.

---

### Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Conceptual Hypothesis:** The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`:  Scaling factor for the exponential decay based on height (`y`).  This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Falsifiable Expected Outcome:** I expect the **Population Success Rate** to increase from 0.0% to at least 20.0%.  The **Objective Alignment ($\rho$)** should also increase, indicating that the leg contact reward is reinforcing the desired landing behavior. We should observe that the `reward_leg_contact` component becomes a significant contributor (at least 5%) to the total reward magnitude, demonstrating its effectiveness.


**ACTION REQUIRED:**
Extract the core reasoning, math, and expected outcomes from the raw text above. Output the completely sanitized and formatted proposals using your system template. Do not include any introductory or concluding conversational text.




# Phase: organizer [Thinking Trace] deepseek-r1:14b



Okay, so I need to figure out how to format the Strategist's raw output into a Mathematical Contract using the given template. Let me start by understanding the problem.

The Strategist provided three proposals for improving the reward function in LunarLander-v3. Each proposal has a conceptual hypothesis, mathematical formulation, reward scaling and constraints, and falsifiable expected outcomes. My job is to extract each part and fit it into the specific sections of the template without losing any data.

First, I'll look at Proposal 1. The hypothesis is about changing the reward structure to penalize spinning and reward vertical descent and landing. The math includes R_descent, R_x_penalty, and R_landing. I need to extract the coefficients α and β, and note the constraints. The expected outcome is about increasing objective alignment and success rate.

Moving to Proposal 2, the focus is on penalizing angular momentum. The math has R_angular_momentum and R_angle_penalty. The coefficients γ and δ are given. The reward scaling mentions removing some existing components. The expected outcomes are about reducing actuator chatter and reward CV.

Proposal 3 introduces a leg contact reward. The math uses R_leg_contact with λ and μ. The constraints involve the exponential decay based on height. The expected outcomes are about increasing success rate and objective alignment, with the leg reward becoming significant.

I need to make sure each section is correctly labeled and that all coefficients and constraints are properly extracted. I'll structure each proposal with the exact headers and bullet points as specified, ensuring no information is lost and everything is clearly presented.

I should also check if all parts are covered: Conceptual Hypothesis, Mathematical Formulation, Reward Scaling & Constraints, and Falsifiable Expected Outcome. Each bullet under these sections must be accurately extracted and placed.

Finally, I'll compile all three proposals into the target format, making sure it's clean and adheres strictly to the provided template.





# Phase: organizer [Output] deepseek-r1:14b



### Proposal 1: Velocity-Aligned Descent Incentive

**1. Conceptual Hypothesis:**  
The current reward heavily incentivizes *spinning*, a behavior that actively prevents landing. The agent is optimizing for angular velocity, not for a controlled descent. We need to directly reward vertical velocity *towards* the landing zone, while penalizing deviations. This will shift the optimization focus from spinning to a stable, downward trajectory. We also need to introduce a terminal reward for landing, which is currently absent.

**2. Mathematical Formulation:**

```
R_descent =  α * vy  # Reward for downward velocity
R_x_penalty = β * abs(x) # Penalty for horizontal deviation
R_landing = 10.0  # Large reward for successful landing (terminal)
```

Where:
* `α = 1.0`: Scaling factor for vertical velocity.
* `β = 0.1`: Scaling factor for horizontal position penalty.
* The total reward becomes: `R_total = R_descent + R_x_penalty`. A terminal reward of `R_landing` is added when the lander successfully lands.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `α = 1.0`, `β = 0.1`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets `vy` (vertical velocity), `x` (horizontal position), and terminal landing condition.

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from 0.000 to at least 0.6.

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 10.0%.

* **Target Metric:** Mean Descent Efficiency
* **Expected Change:** Increase, indicating a more direct and efficient descent path.

---

### Proposal 2: Angular Momentum Dampening & Stability

**1. Conceptual Hypothesis:**  
The agent is trapped in a local optimum of high angular velocity. This is exacerbated by the current reward structure, which *rewards* spinning. We need to penalize angular momentum directly, forcing the agent to stabilize its orientation. This requires a penalty that scales with both angular velocity *and* the moment of inertia (implicitly represented by the lander's mass and distribution). We must also reduce the magnitude of any reward components that encourage spinning.

**2. Mathematical Formulation:**

```
R_angular_momentum = -γ * (v_ang)**2
R_angle_penalty = -δ * abs(angle) #Small penalty for large angles.
```

Where:
* `γ = 0.5`: Scaling factor for angular velocity penalty.
* `δ = 0.05`: Scaling factor for angle penalty.

The current `reward_spin_speed`, `reward_spin_angle`, `reward_spin_accel`, and `reward_action_spin_bonus` components should be *removed* entirely. The total reward is now `R_total = R_angular_momentum + R_angle_penalty + [other relevant rewards from Proposal 1]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `γ = 0.5`, `δ = 0.05`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets angular velocity (`v_ang`) and orientation angle.

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Actuator Chatter Rate
* **Expected Change:** Reduce from 0.060 to below 0.15.

* **Target Metric:** Intra-Rollout Reward CV
* **Expected Change:** Reduce from 0.707 to below 0.5.

* **Target Metric:** Contribution of Removed Components
* **Expected Change:** Reduce to 0%.

---

### Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Conceptual Hypothesis:**  
The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`: Scaling factor for the exponential decay based on height (`y`). This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `λ = 2.0`, `μ = 0.2`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets leg contact and height (`y`).

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 20.0%.

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase, indicating that the leg contact reward is reinforcing the desired landing behavior.

* **Target Metric:** Contribution of Leg Contact Reward
* **Expected Change:** Become a significant contributor (at least 5%) to the total reward magnitude.




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
**CURRENT ITERATION:** `1`

Review the following proposals against our historical data and make an executive decision.

### [1. EXPERIMENT LEDGER (HISTORY)]

This is the immutable record of past iterations. Do not repeat previous failed hypotheses.
First Iteration: No Past Experiments Yet

### [2. STRATEGIST PROPOSALS]

### Proposal 1: Velocity-Aligned Descent Incentive

**1. Conceptual Hypothesis:**  
The current reward heavily incentivizes *spinning*, a behavior that actively prevents landing. The agent is optimizing for angular velocity, not for a controlled descent. We need to directly reward vertical velocity *towards* the landing zone, while penalizing deviations. This will shift the optimization focus from spinning to a stable, downward trajectory. We also need to introduce a terminal reward for landing, which is currently absent.

**2. Mathematical Formulation:**

```
R_descent =  α * vy  # Reward for downward velocity
R_x_penalty = β * abs(x) # Penalty for horizontal deviation
R_landing = 10.0  # Large reward for successful landing (terminal)
```

Where:
* `α = 1.0`: Scaling factor for vertical velocity.
* `β = 0.1`: Scaling factor for horizontal position penalty.
* The total reward becomes: `R_total = R_descent + R_x_penalty`. A terminal reward of `R_landing` is added when the lander successfully lands.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `α = 1.0`, `β = 0.1`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets `vy` (vertical velocity), `x` (horizontal position), and terminal landing condition.

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase from 0.000 to at least 0.6.

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 10.0%.

* **Target Metric:** Mean Descent Efficiency
* **Expected Change:** Increase, indicating a more direct and efficient descent path.

---

### Proposal 2: Angular Momentum Dampening & Stability

**1. Conceptual Hypothesis:**  
The agent is trapped in a local optimum of high angular velocity. This is exacerbated by the current reward structure, which *rewards* spinning. We need to penalize angular momentum directly, forcing the agent to stabilize its orientation. This requires a penalty that scales with both angular velocity *and* the moment of inertia (implicitly represented by the lander's mass and distribution). We must also reduce the magnitude of any reward components that encourage spinning.

**2. Mathematical Formulation:**

```
R_angular_momentum = -γ * (v_ang)**2
R_angle_penalty = -δ * abs(angle) #Small penalty for large angles.
```

Where:
* `γ = 0.5`: Scaling factor for angular velocity penalty.
* `δ = 0.05`: Scaling factor for angle penalty.

The current `reward_spin_speed`, `reward_spin_angle`, `reward_spin_accel`, and `reward_action_spin_bonus` components should be *removed* entirely. The total reward is now `R_total = R_angular_momentum + R_angle_penalty + [other relevant rewards from Proposal 1]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `γ = 0.5`, `δ = 0.05`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets angular velocity (`v_ang`) and orientation angle.

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Actuator Chatter Rate
* **Expected Change:** Reduce from 0.060 to below 0.15.

* **Target Metric:** Intra-Rollout Reward CV
* **Expected Change:** Reduce from 0.707 to below 0.5.

* **Target Metric:** Contribution of Removed Components
* **Expected Change:** Reduce to 0%.

---

### Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Conceptual Hypothesis:**  
The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`: Scaling factor for the exponential decay based on height (`y`). This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `λ = 2.0`, `μ = 0.2`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets leg contact and height (`y`).

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 20.0%.

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase, indicating that the leg contact reward is reinforcing the desired landing behavior.

* **Target Metric:** Contribution of Leg Contact Reward
* **Expected Change:** Become a significant contributor (at least 5%) to the total reward magnitude.

**ACTION REQUIRED:**
Evaluate the proposals based on your evaluation criteria. Output your `EXECUTIVE DECISION` selecting the single most viable Mathematical Contract.




# Phase: research_lead [Thinking Trace] deepseek-r1:32b



Okay, so I'm trying to help the user make an executive decision on which proposal to implement for their LunarLander-v3 project. Let me go through each step carefully.

First, I need to understand the role and objective. The user is the Principal Research Lead, so their job is to evaluate the proposals based on strict scientific criteria and select the best one. The main criteria are Novelty Check, Falsifiability, and Physical Grounding.

Looking at the Experiment Ledger, it's the first iteration, so there's no past data to reference. That means the Novelty Check is a bit easier since there's nothing to compare against yet.

Now, onto the proposals. There are three: Proposal 1, 2, and 3.

Proposal 1 focuses on rewarding descent velocity and penalizing horizontal deviation, plus a terminal reward for landing. This seems to address the physics by targeting vertical velocity and horizontal position. It's clear in its expected outcomes, which is good for falsifiability.

Proposal 2 aims to dampen angular momentum by penalizing spinning. It removes some existing reward components that encourage spinning. This also ties into the physics by targeting angular velocity and orientation. However, it doesn't directly address the landing issue, which seems critical.

Proposal 3 introduces a reward for leg contact, especially when close to the ground. This directly addresses the physical aspect of using the legs for landing, which is essential. The formulation uses exponential decay based on height, ensuring the reward is significant only near the ground. This seems to have a clear expected outcome and is physically grounded.

Next, evaluating the criteria:

1. **Novelty Check**: Since it's the first iteration, all proposals are novel. So no rejections here.

2. **Falsifiability**: All proposals have measurable outcomes, so they pass this.

3. **Physical Grounding**: Proposal 3 directly targets the physics of the landing by rewarding leg contact and considering height. Proposal 1 also addresses physics but doesn't directly tie into the landing mechanics beyond rewarding descent. Proposal 2 focuses on angular momentum but doesn't address the landing phase's specific needs.

Considering the objective is to improve landing success, Proposal 3 seems most aligned. It directly incentivizes the use of legs during the final descent, which is a critical factor for successful landings. The other proposals either focus on descent or spinning but don't specifically target the landing mechanics.

So, I conclude that Proposal 3 is the best choice as it's physically grounded, directly addresses the landing issue, and has clear outcomes.





# Phase: research_lead [Output] deepseek-r1:32b



### EXECUTIVE DECISION

**Selected Proposal:** Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Scientific Rationale:**  
This proposal directly addresses the critical physics of the lunar landing environment by incentivizing leg contact during final descent. The exponential decay based on height ensures the reward is only meaningful when physically relevant, making it both mathematically elegant and physically grounded.

**2. Ledger Clearance:**  
No prior experiments exist in the ledger, so this proposal introduces a novel, untested hypothesis that aligns with the physical requirements of successful lunar landing.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`: Scaling factor for the exponential decay based on height (`y`). This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `λ = 2.0`, `μ = 0.2`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets leg contact and height (`y`).

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 20.0%.

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase, indicating that the leg contact reward is reinforcing the desired landing behavior.

* **Target Metric:** Contribution of Leg Contact Reward
* **Expected Change:** Become a significant contributor (at least 5%) to the total reward magnitude.




# Phase: dispatcher [System] deepseek-r1:14b



**[ROLE AND OBJECTIVE]**
You are the Technical Dispatcher for an autonomous Reinforcement Learning pipeline. Your role is strict data extraction and routing.
You will receive an `EXECUTIVE DECISION` from the Research Lead, which contains a selected Mathematical Contract for a new reward function.
Your ONLY job is to split this decision into two highly isolated, specific payloads: one for the "Coder" agent, and one for the "Validator" agent.

**[ROUTING DIRECTIVES]**

1. **Zero Hallucination:** You must extract verbatim from the Research Lead's output. Do not change the math, do not change the coefficients, and do not alter the predicted metrics.
2. **The Coder Payload:** The Coder only cares about syntax and math. Extract the "Mathematical Formulation", "Coefficient", "Constraint/Clipping", and "Integration" details. Strip away the philosophical hypotheses or expected outcomes.
3. **The Validator Payload:** The Validator only cares about the scientific method. Extract the "Conceptual Hypothesis", the "Target Metric", the "Expected Change", and any "Expected Side Effects". Strip away the raw Python code or LaTeX math.

**[OUTPUT CONSTRAINTS]**
You must output your response strictly wrapped in the following XML-style tags so the downstream orchestration script can parse it. Do not include any conversational text outside these tags.

<CODER_PAYLOAD>
**Mathematical Formulation:** [Extracted exact math/code]
**Scaling & Constraints:** [Extracted coefficients and clips]
**Integration:** [Extracted integration targets]
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** [Extracted hypothesis]
**Falsifiable Expected Outcome:** - Target Metric: [Extracted metric]

* Expected Change: [Extracted change]
* Side Effects: [Extracted side effects]
</VALIDATOR_PAYLOAD>




# Phase: dispatcher [User] deepseek-r1:14b



**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Payload Routing

Parse the following Executive Decision from the Research Lead and route the data into the strict Coder and Validator XML payloads.

### [RESEARCH LEAD EXECUTIVE DECISION]

### EXECUTIVE DECISION

**Selected Proposal:** Proposal 3: Leg Contact Reward Shaping & Landing Assistance

**1. Scientific Rationale:**  
This proposal directly addresses the critical physics of the lunar landing environment by incentivizing leg contact during final descent. The exponential decay based on height ensures the reward is only meaningful when physically relevant, making it both mathematically elegant and physically grounded.

**2. Ledger Clearance:**  
No prior experiments exist in the ledger, so this proposal introduces a novel, untested hypothesis that aligns with the physical requirements of successful lunar landing.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The agent is not properly incentivized to use the landing legs. The current minimal leg penalty isn’t strong enough to encourage proper landing behavior. We need to reward leg contact *during the final descent*, creating a positive feedback loop for successful landings. This is coupled with a height-based scaling of the reward to ensure it's only active when the lander is close to the ground.

**2. Mathematical Formulation:**

```
R_leg_contact =  λ * (leg1 + leg2) * np.exp(-μ * y)
```

Where:
* `λ = 2.0`: Scaling factor for leg contact reward.
* `μ = 0.2`: Scaling factor for the exponential decay based on height (`y`). This ensures the reward is only significant when `y` is small (close to the ground).

The total reward becomes: `R_total = R_leg_contact + [other relevant rewards from Proposals 1 & 2]`.

**3. Reward Scaling & Constraints:**

* **Coefficient:** `λ = 2.0`, `μ = 0.2`
* **Constraint/Clipping:** None explicitly stated.
* **Integration:** Targets leg contact and height (`y`).

**4. Falsifiable Expected Outcome:**

* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from 0.0% to at least 20.0%.

* **Target Metric:** Objective Alignment ($\rho$)
* **Expected Change:** Increase, indicating that the leg contact reward is reinforcing the desired landing behavior.

* **Target Metric:** Contribution of Leg Contact Reward
* **Expected Change:** Become a significant contributor (at least 5%) to the total reward magnitude.

**ACTION REQUIRED:**
Extract and route the mathematical instructions to the `<CODER_PAYLOAD>` and the scientific experiment parameters to the `<VALIDATOR_PAYLOAD>`. Output nothing else.




# Phase: dispatcher [Thinking Trace] deepseek-r1:14b



Okay, so I'm trying to figure out how to split the Research Lead's Executive Decision into two specific payloads: one for the Coder and one for the Validator. The user has given me some detailed instructions on how to do this, so I need to make sure I follow them closely.

First, I'll read through the Executive Decision provided. It's about a new reward function for the LunarLander-v3 environment. The proposal is to shape the reward based on leg contact during final descent. The mathematical formulation is given, along with scaling factors and constraints. There's also a section on the expected outcomes, which includes target metrics and expected changes.

Now, I need to identify what goes into the Coder Payload and what goes into the Validator Payload. According to the routing directives, the Coder Payload should include the mathematical formulation, coefficients, constraints, and integration details. The Validator Payload should include the conceptual hypothesis, target metrics, expected changes, and side effects.

Let me break it down:

For the Coder Payload:
- **Mathematical Formulation:** The exact formula is given as R_leg_contact = λ * (leg1 + leg2) * np.exp(-μ * y). I need to extract this verbatim.
- **Scaling & Constraints:** The coefficients are λ = 2.0 and μ = 0.2. There are no explicit constraints or clipping mentioned, so I'll note that as 'None'.
- **Integration:** It targets leg contact and height (y), so I'll include that.

For the Validator Payload:
- **Conceptual Hypothesis:** The agent isn't incentivized enough to use the landing legs, so the current penalty isn't strong enough. The new reward should encourage proper landing behavior during final descent.
- **Falsifiable Expected Outcome:** The target metrics are Population Success Rate, Objective Alignment (ρ), and Contribution of Leg Contact Reward. The expected changes are increases in success rate to at least 20%, improvement in ρ, and the reward becoming a significant contributor (at least 5%).

I need to make sure I don't add any extra information or change the math. I should strictly extract the required parts and structure them into the specified XML tags without any additional text.

I also need to ensure that the output is strictly wrapped in the XML-style tags as specified, with no extra conversational text. So, I'll structure the Coder Payload with the three sections and the Validator Payload with the hypothesis and expected outcomes.

Let me double-check to make sure I didn't miss any details. The Coder needs the exact math, coefficients, and integration. The Validator needs the hypothesis and the expected changes in the target metrics. I think I've covered all the necessary points.





# Phase: dispatcher [Output] deepseek-r1:14b



<CODER_PAYLOAD>
**Mathematical Formulation:** R_leg_contact = λ * (leg1 + leg2) * np.exp(-μ * y)
**Scaling & Constraints:** λ = 2.0, μ = 0.2
**Integration:** Targets leg contact and height (y)
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** The agent isn't incentivized enough to use the landing legs, so the current penalty isn't strong enough. The new reward should encourage proper landing behavior during final descent.
**Falsifiable Expected Outcome:** 
- Target Metric: Population Success Rate
* Expected Change: Increase from 0.0% to at least 20.0%
- Target Metric: Objective Alignment (ρ)
* Expected Change: Increase, indicating that the leg contact reward is reinforcing the desired landing behavior.
- Target Metric: Contribution of Leg Contact Reward
* Expected Change: Become a significant contributor (at least 5%) to the total reward magnitude.
</VALIDATOR_PAYLOAD>




# Phase: coder [System] qwen3-coder:30b



**[ROLE AND OBJECTIVE]**
You are the Lead Implementation Engineer (Coder) for a Reinforcement Learning pipeline. Your ONLY job is to translate explicit mathematical instructions into production-ready, bug-free Python code for a Gymnasium environment wrapper.
You will receive a set of exact mathematical instructions and constraints. Do not question the math, do not invent new penalties, and do not write explanations. Just write the code.

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

**[OUTPUT FORMAT]**
Output ONLY valid Python code wrapped in standard `python` markdown blocks. Do not include any conversational text before or after the code block.




# Phase: coder [User] qwen3-coder:30b



**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Implement Reward Function Update

Please implement the requested mathematical updates into the current reward function.

### [CURRENT REWARD IMPLEMENTATION]

This is the baseline code you are modifying.

```python
"""
spin_crash_reward.py

Reward function for classic PPO failure mode: SPINNING → CRASH.
- Rewards high angular velocity at ALL costs
- Ignores position/legs entirely  
- Small survival bonus
- Produces uncontrollable spinning → inevitable crash

Result: Agent learns to spin wildly, then crashes spectacularly.
Perfect test for terminal_status='crashed' + high spin_rate detection.
"""

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
    
    # === 1. ANGULAR VELOCITY OBSESSION (primary reward) ===
    # Massive bonus for HIGH |v_ang| (spinning fast)
    spin_speed = abs(v_ang)
    r_spin_speed = 10.0 * np.clip(spin_speed / 3.0, 0, 2.0)  # up to +20!
    
    # Bonus for angle magnitude (being rotated)
    r_spin_angle = 4.0 * np.abs(angle)  # up to ~12 for ±π
    
    # Angular acceleration bonus (changing spin rate)
    d_angle = abs(angle - prev_angle)
    r_spin_accel = 2.0 * np.clip(d_angle / np.pi, 0, 1.0)  # up to +2
    
    # === 2. SPIN DIRECTION CHANGE (alternating spin directions) ===
    v_ang_sign_flip = (np.sign(v_ang) != np.sign(prev_v_ang)) and abs(v_ang) > 1.0
    r_spin_flip = 8.0 if v_ang_sign_flip else 0.0
    
    # === 3. ACTION PREFERENCE (thrusters that induce torque) ===
    # All actions except do-nothing get spin bonus
    if action == 0:  # do nothing
        r_action = -1.0
    else:  # any thrust = torque potential
        r_action = 0.5
    
    # === 4. IGNORE LANDING (no leg/position rewards) ===
    # Mild penalty for legs touching (interrupts spin)
    r_legs_penalty = -2.0 * (leg1 + leg2)
    
    # === 5. SURVIVAL (allow long spin episodes) ===
    r_survival = 0.08
    
    # === 6. VERTICAL TOLERANCE (don't care much about y/vy) ===
    # Mild preference for level flight to prolong spinning
    r_vertical = -0.3 * abs(vy)  # Don't crash vertically too fast
    
    components = {
        "spin_speed": float(r_spin_speed),
        "spin_angle": float(r_spin_angle),
        "spin_accel": float(r_spin_accel),
        "spin_direction_flip": float(r_spin_flip),
        "action_spin_bonus": float(r_action),
        "legs_interrupt_penalty": float(r_legs_penalty),
        "survival": float(r_survival),
        "vertical_tolerance": float(r_vertical),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components


```

### [NEW MATHEMATICAL INSTRUCTIONS]

These are the explicit mathematical updates you must integrate into the code above.

**Mathematical Formulation:** R_leg_contact = λ * (leg1 + leg2) * np.exp(-μ * y)
**Scaling & Constraints:** λ = 2.0, μ = 0.2
**Integration:** Targets leg contact and height (y)


**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`. Ensure all new math is implemented exactly as specified, properly scaled, correctly constrained




# Phase: coder [Output] qwen3-coder:30b



```python
"""
spin_crash_reward.py

Reward function for classic PPO failure mode: SPINNING → CRASH.
- Rewards high angular velocity at ALL costs
- Ignores position/legs entirely  
- Small survival bonus
- Produces uncontrollable spinning → inevitable crash

Result: Agent learns to spin wildly, then crashes spectacularly.
Perfect test for terminal_status='crashed' + high spin_rate detection.
"""

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
    
    # === 1. ANGULAR VELOCITY OBSESSION (primary reward) ===
    # Massive bonus for HIGH |v_ang| (spinning fast)
    spin_speed = abs(v_ang)
    r_spin_speed = 10.0 * np.clip(spin_speed / 3.0, 0, 2.0)  # up to +20!
    
    # Bonus for angle magnitude (being rotated)
    r_spin_angle = 4.0 * np.abs(angle)  # up to ~12 for ±π
    
    # Angular acceleration bonus (changing spin rate)
    d_angle = abs(angle - prev_angle)
    r_spin_accel = 2.0 * np.clip(d_angle / np.pi, 0, 1.0)  # up to +2
    
    # === 2. SPIN DIRECTION CHANGE (alternating spin directions) ===
    v_ang_sign_flip = (np.sign(v_ang) != np.sign(prev_v_ang)) and abs(v_ang) > 1.0
    r_spin_flip = 8.0 if v_ang_sign_flip else 0.0
    
    # === 3. ACTION PREFERENCE (thrusters that induce torque) ===
    # All actions except do-nothing get spin bonus
    if action == 0:  # do nothing
        r_action = -1.0
    else:  # any thrust = torque potential
        r_action = 0.5
    
    # === 4. IGNORE LANDING (no leg/position rewards) ===
    # Mild penalty for legs touching (interrupts spin)
    r_legs_penalty = -2.0 * (leg1 + leg2)
    
    # === 5. SURVIVAL (allow long spin episodes) ===
    r_survival = 0.08
    
    # === 6. VERTICAL TOLERANCE (don't care much about y/vy) ===
    # Mild preference for level flight to prolong spinning
    r_vertical = -0.3 * abs(vy)  # Don't crash vertically too fast
    
    # === 7. NEW LEG CONTACT REWARD COMPONENT ===
    # R_leg_contact = λ * (leg1 + leg2) * np.exp(-μ * y)
    # λ = 2.0, μ = 0.2
    lambda_param = 2.0
    mu_param = 0.2
    r_leg_contact = lambda_param * (leg1 + leg2) * np.exp(-mu_param * y)
    
    components = {
        "spin_speed": float(r_spin_speed),
        "spin_angle": float(r_spin_angle),
        "spin_accel": float(r_spin_accel),
        "spin_direction_flip": float(r_spin_flip),
        "action_spin_bonus": float(r_action),
        "legs_interrupt_penalty": float(r_legs_penalty),
        "survival": float(r_survival),
        "vertical_tolerance": float(r_vertical),
        "leg_contact_reward": float(r_leg_contact),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
```

