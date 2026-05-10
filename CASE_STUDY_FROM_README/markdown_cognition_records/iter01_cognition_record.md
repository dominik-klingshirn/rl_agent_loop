# Cognition prompts and calls: Iteration:1


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
**CURRENT ITERATION:** `1`

Analyze the following execution data and generate your 3 distinct reward design proposals.

### [1. CURRENT REWARD IMPLEMENTATION]

This is the mathematical logic the agent just trained on.

```python
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
First Iteration: No Past Intervention Records Yet

### [3. DIAGNOSTIC REPORT]

This is the deterministic, mathematically extracted performance data from the most recent training runs across multiple random seeds.
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `173.50`
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `45.74`
  - *Diagnosis:* **CRITICAL FAILURE.** The Critic has systemically diverged across all seeds (CSI > 10). The value network is entirely saturated by noise.
  - *Action Required:* You must simplify the dense reward terms. The current shaping is introducing severe non-Markovian variance or contradictory gradients.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.159`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.022`
- **Actuator Chatter Rate:** `0.030`

#### C. Population Terminal Distribution
- `crashed`: 100.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `0.000`
  - *Diagnosis:* Weak alignment. The shaped reward landscape is poorly correlated with the actual goal of landing.
  - *Action Required:* **Survival Hacking Detected.** The agent is farming points by hovering/delaying the episode. Add a temporal penalty or check for positive constant rewards.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (crashed) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `spin_speed` | -0.360 | 34.6% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |
| `spin_angle` | -0.182 | 57.3% | ⚪ Neutral/Noisy |
| `spin_accel` | -0.352 | 0.3% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |
| `spin_direction_flip` | -0.005 | 0.3% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `action_spin_bonus` | -0.157 | 3.7% | ⚪ Neutral/Noisy |
| `legs_interrupt_penalty` | -0.006 | 0.6% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `survival` | -0.103 | 0.8% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `vertical_tolerance` | 0.241 | 2.4% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.585` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.040`
  - *Diagnosis:* The stochastic policy has completely collapsed into a single pathological failure mode. The KL penalty likely prevented escape from a severe local minimum.

**ACTION REQUIRED:**
Generate your 3 distinct proposals (Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome).


# Phase: strategist [Thinking Trace] gemma4:26b
Lead Algorithmic Reward Designer.
LunarLander-v3 (underactuated, continuous/discrete control).
Design dense reward functions for stable, efficient, robust flight.
A reward function that rewards high angular velocity, high angle, and spin direction flips (essentially rewarding "spinning like a top").

        *   `CSI: 45.74` (CRITICAL FAILURE - Critic diverged).
        *   `Population Success Rate: 0.0%` (Agent crashes 100% of the time).
        *   `Objective Alignment (ρ): 0.000` (No correlation with success).
        *   `spin_speed`: $\rho = -0.360$ (Negatively aligned - spinning fast causes crashes).
        *   `spin_accel`: $\rho = -0.352$ (Negatively aligned).
        *   `vertical_tolerance`: $\rho = 0.241$ (The only positive component).
        *   `Actuator Chatter Rate: 0.030` (Low, so no vibration issue yet, but the policy is "stuck").
        *   `Intra-Rollout Reward CV: 0.585` (High variance/fragility).

    *   The current reward function is *explicitly* designed to reward spinning, not landing.
    *   The "Spinning" reward is the primary driver of the agent's behavior, but the diagnostic shows `spin_speed` and `spin_accel` are negatively correlated with success. This means the agent is "farming" spin rewards, which leads to uncontrolled rotation and inevitable crashing.
    *   The Critic is saturated ($CSI \gg 10$), meaning the rewards are so large and chaotic that the Value network cannot estimate the expected return.
    *   The `vertical_tolerance` component is the only one with positive alignment, suggesting that minimizing vertical velocity is the only useful signal present.
    *   The agent is "survival hacking" (though `survival` magnitude is low, the `spin_speed` is high).

    *   The goal of LunarLander is to land at $(0,0)$ with low velocity and upright angle.
    *   The current reward is essentially a "centrifuge" simulator.
    *   I need to pivot from *Rotation* to *Stabilization*.
    *   *Constraints Check:* No time-based penalties allowed. Must use `obs`.

    *   **Proposal 1: The "Stabilization Anchor" (Replacing the Spin with Orientation/Velocity Control).**
        *   *Problem:* `spin_speed` and `spin_angle` are incentivizing chaos.
        *   *Solution:* Replace the spin-centric terms with a quadratic penalty on angular velocity and tilt angle.
        *   *Math:* $-k_1(\text{angle})^2 - k_2(\text{v\_ang})^2$.
        *   *Goal:* Minimize tilt and rotation.

    *   **Proposal 2: The "Descent Control" (Refining the Vertical Signal).**
        *   *Problem:* `vertical_tolerance` is the only good signal, but it's too weak and lacks spatial context.
        *   *Solution:* We need to reward being near the landing pad and having low velocity *specifically* when $y$ is low.
        *   *Math:* A term that penalizes $v_y$ and $x$ error, but is gated by $y$ (height). Or, more simply, a reward for low $v_y$ and low $v_x$ as $y \to 0$.
        *   *Refinement:* Let's use a "Landing Precision" term: $- (v_x^2 + v_y^2 + \text{angle}^2)$.

    *   **Proposal 3: The "Landing Integrity" (The Terminal/Contact logic).**
        *   *Problem:* The agent doesn't care about the legs until they touch, and even then, the penalty is small.
        *   *Solution:* A "Smooth Touchdown" term. We need to reward the state where legs are in contact AND velocity is low.
        *   *Math:* If `leg1_contact` or `leg2_contact`, reward $- (\text{velocity magnitude})$.

    *   *Wait, I need to be surgical.*
    *   *Excision:* I must excise `spin_speed`, `spin_angle`, `spin_accel`, and `spin_direction_flip`. These are fundamentally adversarial to the task. They are not just miscalibrated; their functional form (rewarding high magnitude) is the opposite of the task (minimizing magnitude).

    *   *Proposal 1 (The Core):* Replace the "Spin" cluster with a "Stabilization" cluster.
        *   Old: $10 \cdot \text{spin\_speed} + 4 \cdot \text{angle} + \dots$
        *   New: $-k_1 \cdot \text{angle}^2 - k_2 \cdot \text{v\_ang}^2$.
        *   Hypothesis: The agent is currently incentivized to maximize kinetic energy in rotation. We must invert the gradient to penalize deviations from the upright vertical.

    *   *Proposal 2 (The Descent):* Enhance `vertical_tolerance` into a "Kinematic Precision" term.
        *   Old: $-0.3 \cdot |v_y|$.
        *   New: $- (v_y^2 + v_x^2)$ weighted by a proximity to the ground.
        *   Hypothesis: The agent needs to minimize total kinetic energy relative to the landing site.

    *   *Proposal 3 (The Gating/Landing):* Introduce a "Landing Success" signal using the leg contacts.
        *   New: A bonus/penalty structure that triggers when `leg1_contact` or `leg2_contact` is true, rewarding low velocity.
        *   Hypothesis: The agent currently ignores the landing. We need a high-magnitude signal that fires only upon contact to provide the "terminal reward" signal.

    *   `CSI` is 45.74. This is huge. The new rewards must be small-magnitude and smooth.
    *   `spin_speed` is the biggest contributor (34.6%) and is negative ($\rho = -0.36$).
    *   I will remove all spin-related terms.

    *   *Proposal 1: The "Attitude Stabilization" Cluster.* (Replaces the spin cluster).
        *   Terms: $R_{angle} = -w_1 \cdot \text{angle}^2$, $R_{v\_ang} = -w_2 \cdot \text{v\_ang}^2$.
        *   This addresses the $\rho < -0.2$ for `spin_speed` and `spin_accel`.

    *   *Proposal 2: The "Landing Velocity" Gating.* (Modifies `vertical_tolerance`).
        *   Term: $R_{v\_landing} = -w_3 \cdot \sqrt{v_x^2 + v_y^2}$ if $y < \text{threshold}$.
        *   This addresses the `0.0%` success rate.

    *   *Proposal 3: The "Landing Precision" (The XY target).*
        *   Term: $R_{pos} = -w_4 \cdot (x^2 + y_{target}^2)$. Wait, $y$ is decreasing. Let's use $R_{pos} = -w_4 \cdot x^2$.
        *   Actually, let's do a "Contact Stability" term. If legs are touching, penalize $v_y$ and $v_{ang}$ even more heavily.

    *   *Final Polish of Proposals:*
        1.  **Cluster: Attitude Stabilization (Replaces Spin Cluster).** Targets: $v_{ang}, \text{angle}$.
        2.  **Modification: Kinetic Energy Dissipation (Modifies `vertical_tolerance`).** Targets: $v_x, v_y$.
        3.  **Addition: Landing Contact Precision (New).** Targets: $v_y, \text{angle}$ specifically when `leg_contact == True`.

    *   *Check Constraints:* No time-based penalties. Using `obs`. All good.

    *   *Check Math:*
        *   $R_{att} = -2.0 \cdot (\text{angle}^2 + \text{v\_ang}^2)$
        *   $R_{kin} = -0.5 \cdot (v_x^2 + v_y^2)$
        *   $R_{contact} = \text{if contact: } -5.0 \cdot (|v_y| + |\text{angle}|)$

    *   *Wait, let's refine Proposal 2.* The agent needs to know it's getting closer to the ground. But I can't use time. I can use $y$.
    *   If $y$ is small, the penalty for $v_y$ should increase. This creates the "urgency" without a timer.

    *   *Final Plan:*
        1.  **Excision:** `spin_speed`, `spin_angle`, `spin_accel`, `spin_direction_flip`, `action_spin_bonus`.
        2.  **Proposal 1 (The Stabilizer):** A quadratic penalty on rotation/tilt.
        3.  **Proposal 2 (The Descent Smoother):** A $v_x, v_y$ penalty gated by altitude.
        4.  **Proposal 3 (The Landing Anchor):** A high-magnitude penalty on velocity/angle *specifically* triggered by leg contact.

    *   *Self-Correction on Proposal 2:* The prompt says "Time-based penalties are forbidden." I cannot use `current_step`. I must use `y`.
    *   *Self-Correction on CSI:* I must ensure the coefficients are small to avoid $CSI > 10$.

    *   *Proposal 1:* $\text{Attitude} = -1.0 \cdot (\text{angle}^2 + \text{v\_ang}^2)$.
    *   *Proposal 2:* $\text{Velocity} = -0.5 \cdot (v_x^2 + v_y^2)$.
    *   *Proposal 3:* $\text{Contact} = \text{if contact: } -2.0 \cdot (|v_y| + |\text{angle}|)$.

    *   *Wait, I need to be more "Algorithmic Designer" style.*
    *   Let's make Proposal 2 a "Proximity-Gated Velocity" term.
    *   $R_{v\_proximity} = -0.5 \cdot \exp(-y) \cdot (v_x^2 + v_y^2)$. This scales the importance of velocity as $y \to 0$.

    *   *Let's re-verify the "Excision" logic.*
    *   `spin_speed`, `spin_angle`, `spin_accel`, `spin_direction_flip`, `action_spin_bonus`.
    *   Why? Because their functional form (rewarding magnitude) is mathematically adversarial to the task of landing (which requires minimizing magnitude). No sign inversion can fix the fact that they encourage unbounded energy gain.

    *   *Final structure check:*
        *   Part 1: Surgical Excision.
        *   Part 2: 3 Proposals (Hypothesis, Math, Outcome).

    *   *Final Polish of the "Synergistic Cluster" idea:* I'll combine the "Attitude" and "Velocity" into one "Kinematic Stability" cluster to ensure the Critic doesn't diverge from competing gradients.

    *   *Wait, I'll do:*
        1.  **Excision:** All spin-related terms.
        2.  **Proposal 1 (The Attitude Stabilizer):** Quadratic penalty on $\text{angle}$ and $\text{v\_ang}$.
        3.  **Proposal 2 (The Altitude-Gated Velocity):** $v_x, v_y$ penalty that scales as $y \to 0$.
        4.  **Proposal 3 (The Terminal Integrity Gate):** A massive penalty for high-velocity contact.

    *   *Wait, let's look at the `vertical_tolerance` in the diagnostic:* It is the only positive alignment ($\rho = 0.241$). I should keep its essence but fix the magnitude.

    *   *Let's check the `action_spin_bonus`*: $\rho = -0.157$. It's not heavily negative, but it's useless. I'll excise it.

    *   *Finalizing the mathematical expressions for the proposals.*
        *   Proposal 1: $R_{\text{att}} = -1.5 \cdot (\text{angle}^2 + \text{v\_ang}^2)$
        *   Proposal 2: $R_{\text{descent}} = -0.5 \cdot \frac{1}{1 + y} \cdot (v_x^2 + v_y^2)$ (As $y$ decreases, penalty increases).
        *   Proposal 3: $R_{\text{contact}} = \mathbb{1}_{\text{contact}} \cdot (-5.0 \cdot (|v_y| + |\text{angle}|))$

    *   *Checking the "Excision" justification:* "The functional form (rewarding high magnitude) is fundamentally adversarial to the stabilization required for landing."

    *   *Checking the "Expected Outcome" metrics:*
        *   P1: `Population Success Rate` $\uparrow$, `CSI` $\downarrow$.
        *   P2: `Mean Descent Efficiency` $\uparrow$, `Vertical Tolerance` $\rho$ $\uparrow$.
        *   P3: `Population Success Rate` $\uparrow$, `Crashed` % $\downarrow$.

    *   *Wait, I must not use `current_step`.* I'm using `y`. Good.
    *   *Wait, I must not use `time`.* Good.

    *   *Final check of the "Excision" list:*
        - `spin_speed`
        - `spin_angle`
        - `spin_accel`
        - `spin_direction_flip`
        - `action_spin_bonus`

    *   *Final check of the "Proposals" list:*
        1.  **The Attitudinal Stabilizer (Modification/Replacement)**
        2.  **The Altitude-Gated Kinetic Dissipation (Modification/Gating)**
        3.  **The Landing Integrity Anchor (Addition/Gating)**

    *   *Wait, Proposal 1 should be a "Replacement" of the spin cluster.*
    *   *Proposal 2 should be a "Modification" of vertical_tolerance.*
    *   *Proposal 3 should be an "Addition".*

    *   *Double check the `CSI`.* The current `CSI` is 45.74. My new rewards are much smaller and quadratic (smooth). This should drop the `CSI` significantly.

    *   *Double check the `action_spin_bonus`.* It's 3.7% of the gradient. It's small, but it's part of the "Spin" logic. I'll excise it.

    *   *Final Polish of the math for P2:* $R = -0.5 \cdot (v_x^2 + v_y^2) \cdot (1.0 - \text{clip}(y/10, 0, 1))$. This means as $y$ goes from 10 to 0, the penalty grows from 0 to 100% of the value. This is a great way to encode "urgency" via spatial state.

    *   *Final Polish of the math for P3:* $R = \text{if (leg1 or leg2): } -10.0 \cdot (|v_y| + |\text{angle}|)$. This is a massive signal at the moment of truth.

    *   *Final check on the "Excision" requirement:* "List components you are excising, with one sentence of justification per component stating why no transformation rescues the form."

    *   *Excision List:*
        - `spin_speed`: The reward for high magnitude is fundamentally adversarial to the stability required for landing.
        - `spin_angle`: Rewarding large angular deviations prevents the agent from achieving a vertical orientation.
        - `spin_accel`: Incentivizing angular acceleration promotes uncontrolled kinetic energy gain.
        - `spin_direction_flip`: The discrete reward for sign-flipping creates high-variance, non-Markovian spikes in the gradient.
        - `action_spin_bonus`: This component incentivizes torque-inducing actions that directly contribute to the observed failure mode.

    *   *All looks solid.*


# Phase: strategist [Output] gemma4:26b
**PART 1: SURGICAL EXCISION**

*   **`spin_speed`**: The functional form (rewarding high magnitude) is fundamentally adversarial to the stability required for landing.
*   **`spin_angle`**: Rewarding large angular deviations prevents the agent from achieving the required vertical orientation.
*   **`spin_accel`**: Incentivizing angular acceleration promotes uncontrolled kinetic energy gain and prevents state convergence.
*   **`spin_direction_flip`**: The discrete, high-magnitude reward for sign-flipping introduces severe non-Markovian variance and spikes the Critic's $CSI$.
*   **`action_spin_bonus`**: This component incentivizes torque-inducing actions that directly drive the observed failure mode of uncontrolled rotation.

***

**PART 2: 3 PROPOSALS**

### Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)
**The Conceptual Hypothesis:** 
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. I will replace the entire spin-centric cluster with a quadratic penalty cluster. Quadratic penalties provide a smooth, vanishing gradient near the target (zero angle/zero angular velocity), which is essential to reduce the **Critic Saturation Index (C15)** and prevent the policy from oscillating wildly around the vertical axis.

**The Mathematical Formulation:**
Replace `r_spin_speed`, `r_spin_angle`, `r_spin_accel`, and `r_spin_flip` with:
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$
Where $w_{att} = 1.5$. 
*Note: We use the square of the terms to ensure the gradient $\frac{\partial R}{\partial \theta}$ approaches $0$ as $\theta \to 0$, preventing "chatter" near the upright state.*

**The Falsifiable Expected Outcome:**
A significant reduction in **Critic Saturation Index (CSI)** (from $45.74 \to < 10.0$) and a decrease in **Intra-Rollout Reward CV** (from $0.585 \to < 0.2$).

---

### Proposal 2: Altitude-Gated Kinetic Dissipation (Modification)
**The Conceptual Hypothesis:** 
The current `vertical_tolerance` is too weak to guide the descent. While the agent needs to descend, it must specifically dissipate kinetic energy ($v_x, v_y$) as it approaches the landing site. I will modify this component to be spatially gated by altitude ($y$). By scaling the penalty by a function of $y$, we encode "urgency" through spatial state: the penalty for high velocity is negligible at high altitudes but becomes massive as $y \to 0$, forcing the agent to prioritize braking during the final descent phase.

**The Mathematical Formulation:**
**Old Form:** `r_vertical = -0.3 * abs(vy)`
**New Form:** 
$$R_{kin} = -0.5 \cdot \left(1.0 - \text{clip}\left(\frac{y}{10.0}, 0, 1\right)\right) \cdot (v_x^2 + v_y^2)$$
*This term effectively vanishes at $y=10$ and reaches its maximum penalty at $y=0$, specifically targeting the $v_x, v_y$ error.*

**The Falsifiable Expected Outcome:**
An increase in **Mean Descent Efficiency** (from $0.022 \to > 0.5$) and a shift in **Objective Alignment ($\rho$)** from $0.000$ to a positive value.

---

### Proposal 3: The Landing Integrity Anchor (Addition)
**The Conceptual Hypothesis:** 
The agent currently has no incentive to utilize the landing legs; it only cares about not crashing. We need a high-magnitude "terminal signal" that triggers upon leg contact. This term will act as an anchor, providing a massive penalty if the velocity or angle is non-zero at the moment of contact. This creates a strong gradient towards the "landing" manifold, transforming the task from "avoiding spinning" to "achieving contact stability."

**The Mathematical Formulation:**
**New Term (Gated by leg contact):**
$$R_{contact} = \begin{cases} 
-5.0 \cdot (|v_y| + |\text{angle}|) & \text{if } (\text{leg1\_contact} \lor \text{leg2\_contact}) \\
0 & \text{otherwise}
\end{cases}$$
*This is a sparse, high-magnitude penalty that only activates during the terminal phase of the trajectory.*

**The Falsifiable Expected Outcome:**
A dramatic increase in **Population Success Rate** (from $0.0\% \to > 20.0\%$) and a reduction in the **`crashed`** terminal distribution percentage.


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

*   **`spin_speed`**: The functional form (rewarding high magnitude) is fundamentally adversarial to the stability required for landing.
*   **`spin_angle`**: Rewarding large angular deviations prevents the agent from achieving the required vertical orientation.
*   **`spin_accel`**: Incentivizing angular acceleration promotes uncontrolled kinetic energy gain and prevents state convergence.
*   **`spin_direction_flip`**: The discrete, high-magnitude reward for sign-flipping introduces severe non-Markovian variance and spikes the Critic's $CSI$.
*   **`action_spin_bonus`**: This component incentivizes torque-inducing actions that directly drive the observed failure mode of uncontrolled rotation.

***

**PART 2: 3 PROPOSALS**

### Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)
**The Conceptual Hypothesis:** 
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. I will replace the entire spin-centric cluster with a quadratic penalty cluster. Quadratic penalties provide a smooth, vanishing gradient near the target (zero angle/zero angular velocity), which is essential to reduce the **Critic Saturation Index (C15)** and prevent the policy from oscillating wildly around the vertical axis.

**The Mathematical Formulation:**
Replace `r_spin_speed`, `r_spin_angle`, `r_spin_accel`, and `r_spin_flip` with:
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$
Where $w_{att} = 1.5$. 
*Note: We use the square of the terms to ensure the gradient $\frac{\partial R}{\partial \theta}$ approaches $0$ as $\theta \to 0$, preventing "chatter" near the upright state.*

**The Falsifiable Expected Outcome:**
A significant reduction in **Critic Saturation Index (CSI)** (from $45.74 \to < 10.0$) and a decrease in **Intra-Rollout Reward CV** (from $0.585 \to < 0.2$).

---

### Proposal 2: Altitude-Gated Kinetic Dissipation (Modification)
**The Conceptual Hypothesis:** 
The current `vertical_tolerance` is too weak to guide the descent. While the agent needs to descend, it must specifically dissipate kinetic energy ($v_x, v_y$) as it approaches the landing site. I will modify this component to be spatially gated by altitude ($y$). By scaling the penalty by a function of $y$, we encode "urgency" through spatial state: the penalty for high velocity is negligible at high altitudes but becomes massive as $y \to 0$, forcing the agent to prioritize braking during the final descent phase.

**The Mathematical Formulation:**
**Old Form:** `r_vertical = -0.3 * abs(vy)`
**New Form:** 
$$R_{kin} = -0.5 \cdot \left(1.0 - \text{clip}\left(\frac{y}{10.0}, 0, 1\right)\right) \cdot (v_x^2 + v_y^2)$$
*This term effectively vanishes at $y=10$ and reaches its maximum penalty at $y=0$, specifically targeting the $v_x, v_y$ error.*

**The Falsifiable Expected Outcome:**
An increase in **Mean Descent Efficiency** (from $0.022 \to > 0.5$) and a shift in **Objective Alignment ($\rho$)** from $0.000$ to a positive value.

---

### Proposal 3: The Landing Integrity Anchor (Addition)
**The Conceptual Hypothesis:** 
The agent currently has no incentive to utilize the landing legs; it only cares about not crashing. We need a high-magnitude "terminal signal" that triggers upon leg contact. This term will act as an anchor, providing a massive penalty if the velocity or angle is non-zero at the moment of contact. This creates a strong gradient towards the "landing" manifold, transforming the task from "avoiding spinning" to "achieving contact stability."

**The Mathematical Formulation:**
**New Term (Gated by leg contact):**
$$R_{contact} = \begin{cases} 
-5.0 \cdot (|v_y| + |\text{angle}|) & \text{if } (\text{leg1\_contact} \lor \text{leg2\_contact}) \\
0 & \text{otherwise}
\end{cases}$$
*This is a sparse, high-magnitude penalty that only activates during the terminal phase of the trajectory.*

**The Falsifiable Expected Outcome:**
A dramatic increase in **Population Success Rate** (from $0.0\% \to > 20.0\%$) and a reduction in the **`crashed`** terminal distribution percentage.

**ACTION REQUIRED:**
Extract the core reasoning, math, and expected outcomes from the raw text above. Output the completely sanitized and formatted proposals using your system template. Do not include any introductory or concluding conversational text.


# Phase: organizer [Thinking Trace] deepseek-r1:32b
Okay, so I need to format the Strategist's raw output into a Mathematical Contract. Let me go through the process step by step.

First, I see that the Strategist's output is divided into two parts: Part 1 is the Global Excision Manifesto, which lists variables to be deleted or modified. Part 2 contains three proposals with their own sections.

I remember the directives: I must extract the Global Excision Manifesto and include it verbatim in each proposal's Code Deletions/Modifications section. Also, I need to ensure that each proposal follows the exact structure provided in the template.

Looking at Proposal 1, the title is "The Attitudinal Stabilizer (Replacement Cluster)". The Conceptual Hypothesis talks about replacing the spin cluster with a quadratic penalty. The Mathematical Formulation includes replacing certain reward terms with a new equation. I need to extract the code additions and insert the Global Excision list into the deletions section.

For Proposal 2, titled "Altitude-Gated Kinetic Dissipation (Modification)", the hypothesis is about modifying the vertical tolerance. The math shows an old and new form, so I'll note the old code as a deletion and the new as an addition. Again, include the Global Excision list.

Proposal 3 is "The Landing Integrity Anchor (Addition)". Here, a new term is added when legs contact the ground. The math is a piecewise function, so I'll extract that as a code addition. The deletions section will include the Global Excision list as well.

I also need to handle the scaling and constraints. For each proposal, I extract the coefficient, any constraints, and which variables they target. If there's no constraint, I note that explicitly.

Finally, the expected outcomes are falsifiable metrics. I need to extract the target metric and the expected change for each proposal.

I must ensure that all mathematical formulas and Python snippets are preserved exactly, without any changes. Also, no new proposals should be invented; only the three provided are formatted.

Let me make sure I'm not missing anything. Each proposal has four sections, and each section's content is accurately extracted from the raw output. The Global Excision is included in each proposal's deletions, as per the instructions.

I think I've covered all the points. Now, I'll structure each proposal according to the template, ensuring that all sections are correctly filled with the extracted information.



# Phase: organizer [Output] deepseek-r1:32b
### Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)

**1. Conceptual Hypothesis:**  
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$  
Where $w_{att} = 1.5$.
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 1.5
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets `angle` and `v_ang` variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Critic Saturation Index (CSI)
* **Expected Change:** Reduction from $45.74 \to < 10.0$

---

### Proposal 2: Altitude-Gated Kinetic Dissipation (Modification)

**1. Conceptual Hypothesis:**  
The current `vertical_tolerance` is too weak to guide the descent. Modifying this component to be gated by altitude will encode urgency through spatial state, forcing the agent to dissipate kinetic energy as it approaches the landing site.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{kin} = -0.5 \cdot \left(1.0 - \text{clip}\left(\frac{y}{10.0}, 0, 1\right)\right) \cdot (v_x^2 + v_y^2)$$
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 0.5
* **Constraint/Clipping:** $\text{clip}\left(\frac{y}{10.0}, 0, 1\right)$
* **Integration:** Targets $v_x$ and $v_y$ variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Mean Descent Efficiency
* **Expected Change:** Increase from $0.022 \to > 0.5$

---

### Proposal 3: The Landing Integrity Anchor (Addition)

**1. Conceptual Hypothesis:**  
The agent currently lacks an incentive to utilize landing legs. Introducing a high-magnitude penalty upon contact will create a strong gradient towards achieving contact stability.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{contact} = \begin{cases} 
-5.0 \cdot (|v_y| + |\text{angle}|) & \text{if } (\text{leg1\_contact} \lor \text{leg2\_contact}) \\
0 & \text{otherwise}
\end{cases}$$
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 5.0
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets $v_y$ and `angle` variables upon leg contact

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from $0.0\% \to > 20.0\%$


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
First Iteration: No Past Intervention Records Yet

### [2. STRATEGIST PROPOSALS]

### Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)

**1. Conceptual Hypothesis:**  
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$  
Where $w_{att} = 1.5$.
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 1.5
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets `angle` and `v_ang` variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Critic Saturation Index (CSI)
* **Expected Change:** Reduction from $45.74 \to < 10.0$

---

### Proposal 2: Altitude-Gated Kinetic Dissipation (Modification)

**1. Conceptual Hypothesis:**  
The current `vertical_tolerance` is too weak to guide the descent. Modifying this component to be gated by altitude will encode urgency through spatial state, forcing the agent to dissipate kinetic energy as it approaches the landing site.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{kin} = -0.5 \cdot \left(1.0 - \text{clip}\left(\frac{y}{10.0}, 0, 1\right)\right) \cdot (v_x^2 + v_y^2)$$
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 0.5
* **Constraint/Clipping:** $\text{clip}\left(\frac{y}{10.0}, 0, 1\right)$
* **Integration:** Targets $v_x$ and $v_y$ variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Mean Descent Efficiency
* **Expected Change:** Increase from $0.022 \to > 0.5$

---

### Proposal 3: The Landing Integrity Anchor (Addition)

**1. Conceptual Hypothesis:**  
The agent currently lacks an incentive to utilize landing legs. Introducing a high-magnitude penalty upon contact will create a strong gradient towards achieving contact stability.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{contact} = \begin{cases} 
-5.0 \cdot (|v_y| + |\text{angle}|) & \text{if } (\text{leg1\_contact} \lor \text{leg2\_contact}) \\
0 & \text{otherwise}
\end{cases}$$
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 5.0
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets $v_y$ and `angle` variables upon leg contact

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Population Success Rate
* **Expected Change:** Increase from $0.0\% \to > 20.0\%$

### [3. DIAGNOSTIC REPORT (CURRENT BEHAVIOR)]
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness
- **Signal-to-Noise Ratio (SNR):** `173.50`
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `45.74`
  - *Diagnosis:* **CRITICAL FAILURE.** The Critic has systemically diverged across all seeds (CSI > 10). The value network is entirely saturated by noise.
  - *Action Required:* You must simplify the dense reward terms. The current shaping is introducing severe non-Markovian variance or contradictory gradients.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.159`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.022`
- **Actuator Chatter Rate:** `0.030`

#### C. Population Terminal Distribution
- `crashed`: 100.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Objective Alignment ($\rho$):** `0.000`
  - *Diagnosis:* Weak alignment. The shaped reward landscape is poorly correlated with the actual goal of landing.
  - *Action Required:* **Survival Hacking Detected.** The agent is farming points by hovering/delaying the episode. Add a temporal penalty or check for positive constant rewards.

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (crashed) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `spin_speed` | -0.360 | 34.6% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |
| `spin_angle` | -0.182 | 57.3% | ⚪ Neutral/Noisy |
| `spin_accel` | -0.352 | 0.3% | 🔴 **NEGATIVELY ALIGNED** (ρ < -0.2) |
| `spin_direction_flip` | -0.005 | 0.3% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `action_spin_bonus` | -0.157 | 3.7% | ⚪ Neutral/Noisy |
| `legs_interrupt_penalty` | -0.006 | 0.6% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `survival` | -0.103 | 0.8% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `vertical_tolerance` | 0.241 | 2.4% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.585` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.040`
  - *Diagnosis:* The stochastic policy has completely collapsed into a single pathological failure mode. The KL penalty likely prevented escape from a severe local minimum.

**ACTION REQUIRED:**
Evaluate the proposals based on your evaluation criteria. Output your `EXECUTIVE DECISION` selecting the single most viable Mathematical Contract.


# Phase: research_lead [Thinking Trace] deepseek-r1:32b
Okay, so I'm trying to figure out which proposal to select for the LunarLander-v3 project. The current iteration is 1, and there are three proposals to consider. Let me go through each step carefully.

First, I need to understand the problem. The system is facing critical issues: the critic saturation index is way too high, the population success rate is zero, and the policy is stuck in a failure mode. The reward landscape isn't aligned with the actual goal of landing, and some components are negatively contributing. So, the main goal is to fix these issues.

Looking at the Evaluation Criteria:

1. **Novelty Check**: I need to ensure the proposal doesn't mirror past failed hypotheses. Since this is the first iteration, there's no past data, so this might not be a big issue here, but I should still check if the proposal introduces something new.

2. **Falsifiability**: The chosen proposal must have a clear, measurable outcome that can be validated in the next run. This means the expected outcome should be specific and testable.

3. **Physical Grounding**: The proposal should address the actual physics of the environment, like kinematics or momentum, rather than just numerical scaling.

Now, let's look at each proposal:

**Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)**
- Hypothesis: Replaces the spin cluster with a quadratic penalty to reduce oscillations and critic saturation.
- Formulation: Adds a reward component based on angle and angular velocity squared.
- Expected Outcome: Reduce CSI from 45.74 to <10.0.

This seems to directly address the critic saturation issue by simplifying the reward and providing a smooth gradient. It's physically grounded as it relates to the angle and velocity, which are kinematic variables.

**Proposal 2: Altitude-Gated Kinetic Dissipation (Modification)**
- Hypothesis: Modifies vertical_tolerance to be gated by altitude to increase descent efficiency.
- Formulation: Adds a reward that penalizes kinetic energy as altitude decreases.
- Expected Outcome: Increase Mean Descent Efficiency from 0.022 to >0.5.

This targets the descent efficiency, which is a thermodynamic aspect. It's physically grounded as it relates to velocity components and altitude. However, the current problem is more critical with critic saturation and success rate, which this might not address directly.

**Proposal 3: The Landing Integrity Anchor (Addition)**
- Hypothesis: Adds a penalty upon leg contact to encourage stability.
- Formulation: Introduces a high-magnitude penalty when legs contact the ground.
- Expected Outcome: Increase success rate from 0% to >20%.

This directly targets the success rate by incentivizing contact stability. It's physically grounded as it uses velocity and angle upon contact. However, introducing a high penalty might complicate the reward landscape further, potentially causing issues elsewhere.

Now, considering the current issues:

- **Critic Saturation (CSI 45.74)**: This is a critical issue that needs immediate attention. Proposal 1 aims to reduce this by simplifying the reward and providing a smoother gradient, which could help the critic converge better.

- **Success Rate 0%**: While Proposal 3 targets this, the root cause might be the critic saturation. Without a stable critic, the policy might not learn effectively, regardless of the landing incentives.

- **Reward Alignment**: The current reward components are negatively aligned, especially the spin-related ones. Proposal 1 replaces these with a more aligned component, which could improve overall alignment.

Looking at the Ledger Clearance: Since this is the first iteration, there's no past data to reference, so all proposals are novel.

Falsifiability: Proposal 1 has a clear metric (CSI) that can be measured and validated. Proposal 2 and 3 also have clear metrics, but the priority is on stabilizing the critic first.

Physical Grounding: All proposals are grounded, but Proposal 1 directly addresses the critic health, which is a more foundational issue.

Considering these factors, Proposal 1 seems to be the most critical step. Addressing the critic saturation will likely lead to better policy learning, which can then be followed by other improvements in subsequent iterations.



# Phase: research_lead [Output] deepseek-r1:32b
### EXECUTIVE DECISION

**Selected Proposal:** Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)

**1. Scientific Rationale:**
This proposal directly addresses the critical issue of critic saturation by replacing the problematic spin cluster with a quadratic penalty, providing a smoother gradient that is physically grounded in kinematics.

**2. Ledger Clearance:**
As this is the first iteration, all proposals are novel and do not reference past failures.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$  
Where $w_{att} = 1.5$.
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 1.5
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets `angle` and `v_ang` variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Critic Saturation Index (CSI)
* **Expected Change:** Reduction from $45.74 \to < 10.0$


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

**Selected Proposal:** Proposal 1: The Attitudinal Stabilizer (Replacement Cluster)

**1. Scientific Rationale:**
This proposal directly addresses the critical issue of critic saturation by replacing the problematic spin cluster with a quadratic penalty, providing a smoother gradient that is physically grounded in kinematics.

**2. Ledger Clearance:**
As this is the first iteration, all proposals are novel and do not reference past failures.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.

**2. Mathematical Formulation:**
* **Code Additions:**  
$$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$  
Where $w_{att} = 1.5$.
* **Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`

**3. Reward Scaling & Constraints:**
* **Coefficient:** 1.5
* **Constraint/Clipping:** None explicitly stated
* **Integration:** Targets `angle` and `v_ang` variables

**4. Falsifiable Expected Outcome:**
* **Target Metric:** Critic Saturation Index (CSI)
* **Expected Change:** Reduction from $45.74 \to < 10.0$

**ACTION REQUIRED:**
Extract and route the mathematical instructions to the `<CODER_PAYLOAD>` and the intervention parameters and predicted effects to the `<VALIDATOR_PAYLOAD>`. Output nothing else.


# Phase: dispatcher [Thinking Trace] deepseek-r1:32b
Okay, so I need to help route the Executive Decision from the Research Lead into the Coder and Validator payloads. Let me start by understanding the structure and requirements.

First, the Coder Payload requires specific sections: Code Additions, Code Deletions/Modifications, Scaling & Constraints, and Integration. I need to extract these verbatim from the Research Lead's decision without any changes.

Looking at the Code Additions, the Research Lead provided a LaTeX formula: R_att equals negative w_att times (angle squared plus v_ang squared), with w_att being 1.5. I should include this exactly as is.

For Code Deletions/Modifications, the list includes several components like spin_speed, spin_angle, etc. Each should be on a separate line, and I must ensure they are backticked as per the instructions. If there were none, I'd write 'None', but here there are five items.

Scaling & Constraints mention a coefficient of 1.5 and no explicit clipping. So I'll note the coefficient and state that there's no constraint.

Integration targets the angle and v_ang variables, so I'll list them as specified.

Now, the Validator Payload needs the Conceptual Hypothesis, Target Metric, Expected Change, and Side Effects. The hypothesis is about replacing the spin cluster with a quadratic penalty to reduce oscillations and saturation. The target metric is the Critic Saturation Index (CSI), expected to drop from 45.74 to below 10.0. There are no side effects mentioned, so I'll note that as 'None'.

I need to make sure all the extracted information is wrapped correctly in the XML-style tags without any extra text. Also, I should avoid any markdown formatting and keep the output strictly as per the directives.

Let me double-check each section to ensure nothing is missed or altered. The Coder gets the code parts, and the Validator gets the scientific rationale and expected outcomes. Everything seems to be in order, so I'll proceed to format the response accordingly.



# Phase: dispatcher [Output] deepseek-r1:32b
<CODER_PAYLOAD>
**Code Additions:** $$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$ Where $w_{att} = 1.5$.
**Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`
**Scaling & Constraints:** Coefficient: 1.5; Constraint/Clipping: None
**Integration:** Targets `angle` and `v_ang` variables
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** The current "Spin" cluster is a centrifuge that maximizes kinetic energy. To land, the agent must minimize the potential energy of rotation. Replacing the spin-centric cluster with a quadratic penalty cluster will provide a smooth gradient near the target state, reducing oscillations and critic saturation.
**Falsifiable Expected Outcome:** - Target Metric: Critic Saturation Index (CSI)

* Expected Change: Reduction from $45.74 \to < 10.0$
* Side Effects: None
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

**Code Additions:** $$R_{att} = -w_{att} \cdot (\text{angle}^2 + \text{v\_ang}^2)$$ Where $w_{att} = 1.5$.
**Code Deletions/Modifications:**  
- `spin_speed`  
- `spin_angle`  
- `spin_accel`  
- `spin_direction_flip`  
- `action_spin_bonus`
**Scaling & Constraints:** Coefficient: 1.5; Constraint/Clipping: None
**Integration:** Targets `angle` and `v_ang` variables


**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`. You MUST aggressively execute any specified Code Deletions by removing that logic entirely, and integrate all Code Additions exactly as specified.


# Phase: coder [Output] qwen3-coder:30b
```python
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
    
    # === 2. IGNORE LANDING (no leg/position rewards) ===
    # Mild penalty for legs touching (interrupts spin)
    r_legs_penalty = -2.0 * (leg1 + leg2)
    
    # === 3. SURVIVAL (allow long spin episodes) ===
    r_survival = 0.08
    
    # === 4. VERTICAL TOLERANCE (don't care much about y/vy) ===
    # Mild preference for level flight to prolong spinning
    r_vertical = -0.3 * abs(vy)  # Don't crash vertically too fast
    
    components = {
        "attitude_penalty": float(r_attitude),
        "legs_interrupt_penalty": float(r_legs_penalty),
        "survival": float(r_survival),
        "vertical_tolerance": float(r_vertical),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
```

