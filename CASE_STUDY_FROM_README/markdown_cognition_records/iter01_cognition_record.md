# Cognition prompts and calls: Iteration:1


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
    prev_vx, prev_legs = prev_obs[2], prev_obs[6] + prev_obs[7]
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # Massive bonus for legs down AND sliding fast sideways
    sliding_legs = legs_contact * horiz_slide_speed
    r_sliding_legs = 12.0 * np.clip(sliding_legs / 2.0, 0, 1.5)  # up to +18!
    
    # === 2. PREFER TILTED ORIENTATION (discourage upright) ===
    # Reward moderate tilt (easier to slide)
    r_tilt_preference = 3.0 * np.abs(angle) * 0.5  # up to ~4.5 for π/2 tilt
    
    # Penalty for perfectly upright (stable landing pose)
    upright_penalty = -8.0 if abs(angle) < 0.05 else 0.0
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    r_slalom = 6.0 if vx_sign_flip else 0.0
    
    # === 4. SIDE THRUSTER LOVE (lateral control) ===
    if action in (1, 3):  # left/right thrusters
        r_action = 2.0
    elif action == 2:  # main (less useful for sliding)
        r_action = -0.5
    else:
        r_action = -1.0
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    near_ground = abs(y) < 0.4
    r_ground_level = 3.0 if near_ground else -1.5
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * abs(vy)  # Hate up/down
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    components = {
        "sliding_legs": float(r_sliding_legs),
        "tilt_preference": float(r_tilt_preference),
        "upright_penalty": float(upright_penalty),
        "slalom_bonus": float(r_slalom),
        "side_thruster_bonus": float(r_action),
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "survival": float(r_survival),
        "leg_maintenance": float(r_leg_maintenance),
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

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.1640`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.1600`  *(lower = more settled)*
  - *Diagnosis:* The optimization is still churning inside the final training quartile. The converged policy is non-stationary and may not retain.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `12.45`
  - *Diagnosis:* Warning. The Critic is struggling to map the advantage function. Consider reducing the scale of dense penalty components.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.108`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.022`
- **Actuator Chatter Rate:** `0.031`

#### C. Population Terminal Distribution
- `crashed`: 100.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `undefined (single-class population)`  *(ground truth)*
- **Objective Alignment ($\rho$):** `nan`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (crashed) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `sliding_legs` | -0.295 | 1.0% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `tilt_preference` | -0.335 | 31.5% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `upright_penalty` | -0.239 | 9.9% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `slalom_bonus` | -0.019 | 0.0% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `side_thruster_bonus` | -0.269 | 23.3% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `ground_level` | 0.136 | 9.1% | ⚪ Neutral/Noisy |
| `vertical_penalty` | 0.334 | 23.5% | 🟢 Optimal |
| `survival` | -0.246 | 1.3% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `leg_maintenance` | -0.080 | 0.4% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `1.316` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.004`
  - *Diagnosis:* The stochastic policy has completely collapsed into a single pathological failure mode. The KL penalty likely prevented escape from a severe local minimum.

**ACTION REQUIRED:**
Generate your 3 distinct proposals (Hypothesis, Mathematical Formulation, and Falsifiable Expected Outcome).


# Phase: strategist [Thinking Trace] gemma4:26b-mlx
*   Environment: `LunarLander-v3` (underactuated, continuous/discrete control).
    *   Current Goal: The previous agent was trying to "slide" (lateral movement) instead of landing upright and vertically.
    *   Goal of the *User*: I need to design a reward function that achieves stable, efficient, and robust flight dynamics (landing).

    *   `sliding_legs`: `r_sliding_legs = 12.0 * np.clip(legs_contact * abs(vx) / 2.0, 0, 1.5)`.
        *   *Problem:* It rewards high horizontal velocity while legs are touching. This encourages sliding, not landing.
        *   *Diagnostic:* $\rho = -0.295$ (Negatively Aligned). It's actively pushing the agent to slide instead of stabilize.
    *   `tilt_preference`: `r_tilt_preference = 3.0 * np.abs(angle) * 0.5`.
        *   *Problem:* It rewards being tilted. Landing requires being upright (angle $\approx 0$).
        *   *Diagnostic:* $\rho = -0.335$ (Negatively Aligned).
    *   `upright_penalty`: `-8.0` if `abs(angle) < 0.05`.
        *   *Problem:* It penalizes being upright. This is the exact opposite of what is needed.
        *   *Diagnostic:* $\rho = -0.239$ (Negatively Aligned).
    *   `side_thruster_bonus`: `r_action = 2.0` for side thrusters.
        *   *Problem:* It encourages lateral movement rather than vertical control/stability.
        *   *Diagnostic:* $\rho = -0.269$ (Negatively Aligned).
    *   `vertical_penalty`: `-2.0 * abs(vy)`.
        *   *Problem:* Penalizes all vertical motion. While it wants the agent to settle, it might be too aggressive during descent. However, $\rho = 0.334$ (Optimal), meaning it's helping the agent reach the ground, but it's not enough to overcome the "sliding" incentives.
        *   *Diagnosis:* It's the only thing working to keep the agent from flying away.
    *   `survival`: `0.1` (Positive).
        *   *Problem:* Even if it's small, it's being treated as a "survival" reward, but the agent is crashing 100% of the time.

    *   Success Rate: 0%.
    *   The agent is "sliding" because the reward function essentially explicitly asked it to: "Slide fast, tilt a lot, don't be upright, and use side thrusters."
    *   The agent has collapsed into a "Slalom" or "Sliding" mode.
    *   CSI (Critic Saturation Index) is high (12.45), suggesting the reward values are too large or the gradients are erratic due to the contradictory large-scale terms (like `sliding_legs` up to 18.0 and `tilt_preference` up to 4.5).

    *   *Excision candidates:*
        *   `sliding_legs`: The purpose was "lateral movement/sliding," but the goal is landing. Even if we flipped the sign, "sliding" is the wrong behavior.
        *   `tilt_preference`: This is fundamentally the wrong behavior.
        *   `upright_penalty`: This is fundamentally the wrong behavior.
        *   `side_thruster_bonus`: This is inducing chatter and lateral instability.
        *   `survival`: In a landing task, "survival" is usually implicit in staying alive until landing, or explicitly in reaching a state. A flat +0.1 is not useful if the agent crashes.

    *   *Wait, let's look at the instructions for "Surgical Excision":* "Excise only when the *functional form itself* is incoherent with the task."
        *   `sliding_legs`: Incoherent. The goal is to stop movement, not induce it.
        *   `tilt_preference`: Incoherent. The goal is zero angle.
        *   `upright_penalty`: Incoherent. The goal is zero angle.
        *   `side_thruster_bonus`: Incoherent. It rewards lateral thrusting which is needed for correction, not as a primary goal.

    *   *Actually, I should look at what's needed for a proper LunarLander:*
        1.  Minimize angle (be upright).
        2.  Minimize vertical velocity at impact (land softly).
        3.  Minimize horizontal velocity (land still).
        4.  Maximize landing in the center (stay near $x=0$).

    *   **Proposal 1: Orientation & Stability (Addressing `tilt_preference` and `upright_penalty`).**
        Instead of rewarding tilt, we reward being upright. We need a quadratic penalty around $\text{angle} = 0$.
        *   *Form:* $-C \cdot \text{angle}^2$.

    *   **Proposal 2: Landing Softness (Addressing `vertical_penalty` and `sliding_legs`).**
        We need to penalize high $v_y$ *at the moment of contact*, but also provide a shaping term to guide the descent. The current `vertical_penalty` is `-2.0 * abs(vy)`, which is okay but might be too aggressive too early. We want to incentivize low velocity when $y$ is near 0.
        Actually, let's focus on horizontal stability. The agent was sliding. We need to penalize $v_x$ when $y$ is low.

    *   **Proposal 3: Precision Landing (The $x$-coordinate).**
        The agent needs to be at $x \approx 0$.

    *   *Let's refine the Proposals:*

        *   *Target:* `tilt_preference`, `upright_penalty`, `sliding_legs`.
        *   *Goal:* Replace the "sliding" behavior with "vertical/upright" behavior.
        *   *Math:* A quadratic penalty on `angle` and `v_ang`.
        *   $r_{\text{orientation}} = -a \cdot \text{angle}^2 - b \cdot |v_{\text{ang}}|$.

        *   *Target:* `vertical_penalty`, `side_thruster_bonus`.
        *   *Goal:* Instead of just penalizing all vertical motion, we want to ensure that as the agent approaches the ground, the vertical velocity is controlled.
        *   Actually, a better way to handle "landing" is to penalize the velocity at the time of contact. But for dense rewards, we can penalize high vertical velocity scaled by height.
        s
        *Wait, let's look at the current state:* `vertical_penalty` was `-2.0 * abs(vy)`. This is actually helping. The problem is the *other* terms are fighting it.

    *   *Let's try a different angle:*
        *   **Proposal 1: Orientation/Stability (The "Upright" Pillar).** Target `tilt_preference` and `upright_penalty`.
            Goal: Force $\text{angle} \to 0$ and $\text{v\_ang} \to 0$.
            Math: $r_{\text{orient}} = - (10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)$.
        *   **Proposal 2: Horizontal/Vertical Dampening (The "Stillness" Pillar).** Target `sliding_legs` and `side_thruster_bonus`.
            Goal: Instead of "sliding," we want the agent to lose horizontal momentum as it nears the ground.
            Math: $r_{\text{damping}} = - (w_1 \cdot |v_x| \cdot e^{-y} + w_2 \cdot |v_y| \cdot e^{-y})$. No, that's complex.
            Let's go simpler: $r_{\text{velocity}} = - (C_x \cdot |v_x| + C_y \cdot |v_y|)$.
        *   **Proposal 3: Centering (The "Target" Pillar).**
            Goal: Bring $x$ to $0$.
            Math: $r_{\text{center}} = -C \cdot x^2$.

    *   **Refining Proposal 1: Stability (The Orientation Gate).**
        The agent is currently incentivized to tilt and rotate. We need to invert this.
        *Modification:* Transform `tilt_preference` + `upright_penalty` into a single stability term.
        *Current:* `3.0 * abs(angle) * 0.5` + `-8.0 if abs(angle) < 0.05`.
        *New:* $r_{\text{stability}} = - (5.0 \cdot \text{angle}^2 + 2.0 \cdot |v_{\text{ang}}|)$.
        *Rationale:* Quadratic penalties provide a smooth gradient toward zero, avoiding the "jumpy" behavior of the `upright_penalty` threshold.

    *   **Refining Proposal 2: Velocity Damping (The Landing/Deceleration Gate).**
        The agent is incentivized to "slide" (high $v_x$ with legs down). We need to incentivize the *opposite*: high $v_x$ should be penalized, especially as the agent approaches the ground.
        *Modification:* Transform `sliding_legs` into a velocity damping term.
        *Current:* `12.0 * np.clip(legs_contact * abs(vx) / 2.0, 0, 1.5)` (Positive/Additive).
        *New:* $r_{\text{velocity}} = - (2.0 \cdot |v_x| + 5.0 \cdot |v_y|)$.
        *Rationale:* To land, the agent must minimize all kinetic energy. This penalizes horizontal sliding and vertical impact velocity.

    *   **Refining Proposal 3: Centering (The Positional Constraint).**
        The agent currently has no incentive to be at $x=0$, except maybe the `ground_level` term which is $y$-based.
        *Addition:* $r_{\text{pos}} = - (1.0 \cdot x^2)$.
        *Rationale:* Provides a global gradient toward the center of the landing pad.

    *   *Wait, I need to check the "Surgical Excision" logic again.*
        - `sliding_legs`: Form is "Reward-velocity-during-contact". Goal is "Land-still-on-contact". The form's *purpose* (rewarding velocity) is the exact opposite of the goal. Therefore, the functional identity (rewarding velocity) is incoherent. **Excision.**
        - `tilt_preference`: Form is "Reward-angle". Goal is "Minimize-angle". **Ex-cision.**
        - `upright_penalty`: Form is "Penalty-angle-near-zero". Goal is "Minimize-angle". The purpose is actually *half-right* but it's a jumpy threshold. However, the direction is correct (negative). But since it's part of the "tilt-preference" regime, I'll group it.
        - `side_thruster_bonus`: Form is "Reward-lateral-action". Goal is "Stabilize-vertically". **Excision.**

    *   **Finalizing Proposals:**

    *   **Proposal 1 (Modification):** Transform `tilt_preference` and `upright_penalty` into a single **Orientation Stability** term.
        *   *Old:* `3.0 * abs(angle) * 0.5` and `-8.0 if abs(angle) < 0.05`.
        *   *New:* $r_{\text{orientation}} = - (10.0 \cdot \text{angle}^2 + 5.0 \cdot |v_{\text{ang}}|)$.
        *   *Rationale:* A continuous quadratic penalty on angle and angular velocity provides a smoother, more reliable gradient for the critic, preventing the "jumps" that caused the previous instability.

    *   **Proposal 2 (Modification):** Transform `sliding_legs` into a **Kinetic Damping** term.
        *   *Old:* `12.0 * np.clip(legs_contact * abs(vx) / 2.0, 0, 1.5)`.
        *   *New:* $r_{\text{damping}} = - (2.0 \cdot |v_x| + 4.0 \cdot |v_y|)$.
        *   *Rationale:* The agent was incentivized to maximize horizontal velocity during contact. We must invert this to penalize all kinetic energy, forcing the agent to decelerate before and during landing.

    *   **Proposal 3 (Addition):** A **Positional Centering** term.
        *   *Math:* $r_{\text{centering}} = - (1.0 \cdot x^2)$.
        *   *Rationale:* This creates a potential well at $x=0$, guiding the agent towards the center of the landing zone, which is a prerequisite for a successful, stable landing.

    *   *Self-Correction on Proposal s:*
        Wait, if I modify `sliding_legs` to `damping`, is it a modification or excision+addition?
        *Definition:* "A modification may freely change the signal's shape or strength... provided both the input and the behavioral purpose survive. If either changes, it is not a modification: express it as an excision (Part 1) plus an Addition."
        - `sliding_legs` input: `legs_contact` and `vx`.
        - `sliding_legs` purpose: Reward movement.
        - `damping` purpose: Penalize movement.
        The purpose has changed from *Reward-velocity* to *Penalize-velocity*. Therefore, I must treat it as **Excision + Addition**.

        Let's look at the inputs of `sliding_legs`: `legs_contact` and `vx`.
        If I want to keep the input `legs_contact` (the contact state) but change the purpose to "stabilize once landed," I can. But the instruction says "If either [input or purpose] changes, it is not a modification."
        The input is `legs_contact * vx`. The purpose is "reward sliding."
        If I want "reward stability," the purpose has changed.

    *   Let's re-evaluate.
        - **Excision 1:** `sliding_legs` (Purpose: reward movement; Goal: minimize movement).
        - **Excision 2:** `tilt_preference` (Purpose: reward tilt; Goal: minimize tilt).
        - **Excision 3:** `upright_penalty` (Purpose: penalize upright; Goal: minimize tilt).
        - **Excision 4:** `side_thruster_bonus` (Purpose: reward lateral action; Goal: stabilize/control).

    *   *Wait, let's be smarter about the "Modification" definition.*
        If I take `tilt_preference` (which reads `angle`) and change it from `reward-angle` to `penalty-angle`, I have changed the *purpose* (from seeking tilt to seeking zero). That's an excision.
        BUT, if the "functional identity" is "angle-based control," then a sign change is a modification.
        The prompt says: "A modification may freely change the signal's shape or strength... provided both the input and the behavioral purpose survive."
        "Tilt preference"'s purpose is "influence angle." If I change the sign, the purpose is still "influence angle," just in a different direction. This is a bit ambiguous, but usually, in RL, changing the sign of a shaping term is a modification.

    *   Let's stick to the safest interpretation:
        1.  `sliding_legs` $\to$ `horizontal_velocity_penalty` (Excision + Addition).
        2.  `tilt_preference` $\to$ `orientation_stability` (Modification - sign inversion/quadratic).
        3.  `upright_penalty` $\to$ remove (Excision).
        4.  `side_thruster_bonus` $\to$ remove (Excision).

    *   *Let's check the list of components to excise:*
        - `sliding_legs`: Purpose is to reward motion. This is the opposite of the task.
        - `tilt_preference`: Purpose is to reward tilt. This is the opposite of the task.
        - `upright_penalty`: Purpose is to penalize uprightness. This is the opposite of the task.
        - `side_thruster_bonus`: Purpose is to reward lateral thrusters. This is not the landing goal.

    *   *Wait, the "Vertical Penalty" is good.* $\rho = 0.334$. I should keep it or refine it.

    *   *Final Plan:*
        - **Excision:** `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`.
        - **Proposal 1 (Modification):** Transform `tilt_preference` into `orientation_stability` (Penalty-based).
        - **Proposal 2 (Addition):** `velocity_damping` ($v_x, v_y$ penalty).
        - **Proposal 3 (Addition):** `centering_reward` ($x$ penalty).

    *   *Wait, if I modify `tilt_preference`...*
        Current: `r_tilt_preference = 3.0 * np.abs(angle) * 0.5`
        Target: $r_{\text{orient}} = - (5.0 \cdot \text{angle}^2 + 2.0 \cdot |v_{\text{ang}}|)$
        The input is still `angle` and `v_ang` (implicitly). This is a modification of the *control logic* for orientation.

    *   *Let's refine the "Excision" list to be concise:*
        - `sliding_legs`: The goal is to stop, not to slide.
        - `tilt_preference`: The goal is to be upright, not tilted.
        - `upright_penalty`: The goal is to minimize angle, not penalize the zero-state.
        - `side_thruster_bonus`: Side thrusters are for control, not a primary reward objective.

    *   *Refining Proposal 1 (The Orientation Pillar):*
        Modify `tilt_preference`.
        Old: `3.0 * np.abs(angle) * 0.5`
        New: `- (10.0 * angle**2 + 2.0 * abs(v_ang))`
        *Why:* Quadratic orientation penalty + angular velocity damping.

    *   *Refining Proposal 2 (The Kinetic Damping Pillar):*
        Addition.
        Terms: $r_{\text{dx}} = -2.0 \cdot |v_x|$ and $r_{\text{dy}} = -5.0 \cdot |v_y|$.
        Synergy: Together they form a "braking" signal that reduces all kinetic energy as the agent approaches the landing.

    *   *Refining Proposal 3 (The Centering Pillar):*
        Addition.
        Term: $r_{\text{center}} = -1.0 \cdot x^2$.
        *Why:* Ensures $x \approx 0$.

    *   *Double Check:* Does `vertical_penalty` need to be changed? It's `-2.0 * abs(vy)`. It's already doing what my `r_dy` does. To avoid redundancy, I will incorporate the vertical damping *into* a single kinetic energy term or simply improve the existing one.
    *   Actually, let's make Proposal 2 a **Modification** of `vertical_penalty` to include horizontal velocity.
    *   **Proposal 2 (Modification):** Transform `vertical_penalty` into `kinetic_damping`.
        - Old: `-2.0 * abs(vy)`
        - New: `- (2.0 * abs(vx) + 5.0 * abs(vy))`
        - This preserves the input (velocity) and the purpose (damping), but expands the scope to include horizontal stability.

    *   *Let's re-verify Proposal 1:*
        - If I modify `tilt_preference` (which is `abs(angle)`) to `angle^2`, I am changing the shape. This is allowed.

    *   **One last look at the Diagnostic Report.**
        - `vertical_penalty` has $\rho = 0.334$. It's the only positive thing.
        - `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival` all have negative $\rho$.
        - This confirms the "Sliding/Tilting" regime.

    *   *Final Proposal Selection:*
        1.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (quadratic penalty on angle/v_ang).
        2.  **Modification:** `vertical_penalty` $\to$ `kinetic_damping` (penalize $|v_x|$ and $|v_y|$).
        3.  **Addition:** `centering_potential` (penalize $x^2$).

    *   *Final Check of "Surgical Excision" criteria:*
        - `sliding_legs`: Purpose (rewarding movement) is the literal opposite of the task (stopping). **Excision.**
        - `upright_penalty`: Purpose (penalizing the target state) is the literal opposite of the task. **Excision.**
        - `side_thruster_bonus`: Purpose (rewarding action) is not a landing requirement. **Excision.**
        - `survival`: Purpose (flat bonus) is irrelevant to the landing physics. **Excision.**

    *   *Wait, is `tilt_preference` an excision or a modification?*
        Current purpose: "Reward moderate tilt."
        Target purpose: "Penalize orientation error."
        These are different purposes. So it's an **Excision**.
        *However*, if I treat it as "Angle-based shaping," a sign flip is a modification. Let's be safe and treat it as an Excision.

    *   *Wait, let's try to find a more "elegant" set of 3:*
        1.  **Modification** of `tilt_preference` into `orientation_stability` (Invert sign, change to quadratic). *Reasoning: It's the same sensor (angle), just a different direction/shape.*
        2.  **Modification** of `vertical_penalty` into `kinetic_damping` (Add $v_x$ term). *Reasoning: It's the same sensor (velocity), just expanded.*
        3.  **Addition** of `centering_potential` ($x^2$).

    *   *Actually, let's look at the `upright_penalty` again.* It's `-8.0` if `abs(angle) < 0.05`. This is a *hard* penalty for being correct. This is definitely an excision.

    *   **Final Final Plan:**
        - **Excision:** `sliding_legs`, `upright_penalty`, `side_thruster_bonus`, `survival`.
        - **Proposal 1 (Modification):** `tilt_preference` $\to$ `orientation_stability`. (Sign inversion + Quadratic/Angular Velocity).
        - **Proposal 2 (Modification):** `vertical_penalty` $\to$ `kinetic_damping`. (Add $v_x$ component).
        - **Proposal 3 (Addition):** `centering_potential`. (Minimize $x^2$).

    *   *Check Metrics:*
        - `Population Success Rate`: Should go up from 0%.
        - `Mean Descent Efficiency`: Should improve (get closer to 1.0 or higher as it stabilizes).
        - `Chatter Rate`: Should decrease (due to smooth quadratic/damping vs previous hard penalties).

    - `tilt_preference`: $- (10.0 \cdot \text{angle}^2 + 2.0 \cdot |v_{\text{ang}}|)$
    - `vertical_penalty` $\to$ `kinetic_damping`: $- (2.0 \cdot |v_x| + 5.0 \cdot |v_y|)$
    - `centering_potential`: $- (1.0 \cdot x^2)$

    Wait, the `vertical_penalty` was `r_vertical_penalty = -2.0 * abs(vy)`.
    If I change it to `-(2.0 * abs(vx) + 5.0 * abs(vy))`, I am changing the purpose from "Vertical Damping" to "Kinetic Damping".
    If the purpose of `vertical_penalty` is "damping vertical motion," then adding $v_x$ changes the purpose.
    To be strictly compliant with the "Modification" rule:
    "A modification may freely change the signal's shape or strength... provided both the input and the behavioral purpose survive."
    If I change `vertical_penalty` to include $v_x$, I am adding a new input ($v_x$). So it is technically an **Excision + Addition**.

    Let's just do:
    **Part 1: Excision**
    - `sliding_legs` (purpose: reward movement)
    - `tilt_preference` (purpose: reward tilt)
    - `upright_penalty` (purpose: penalize target state)
    - `side_thruster_bonus` (purpose: reward thruster use)
    - `survival` (purpose: flat constant)

    **Part 2: Proposals**
    1.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (Sign inversion + Quadratic/Angular Velocity).
    2.  **Addition:** `kinetic_damping` (Penalize $|v_x|$ and $|v_y|$).
    3.  **Addition:** `centering_potential` (Penalize $x^2$).

    *Wait, the instruction says: "A modification may freely change the signal's shape or strength... provided both the input and the behavioral purpose survive."*
    The input to `tilt_preference` is `angle`. The purpose is "orientation control."
    Changing it from `+angle` to `-angle^2` preserves the input and the purpose.
    The input to `vertical_penalty` is `vy`. The purpose is "vertical damping."
    If I want to include $v_x$, I am adding a new input.
    So I will keep Proposal 2 as an **Addition** of `kinetic_damping` ($v_x, v_y$) to be safe.

    *Actually, a better Proposal 2:*
    **Modification:** `vertical_penalty` $\to$ `vertical_stability` (Increase coefficient and add angular velocity to ensure vertical descent doesn't just stop, but settles). No, that's too complex.

    Let's go with:
    1.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (Target: `angle`, Purpose: `orientation_control`).
    2.  **Addition:** `kinetic_damping` (Target: `vx, vy`, Purpose: `deceleration`).
    3.  **Addition:** `centering_potential` (Target: `x`, Purpose: `position_centering`).

    *Self-Correction:* The `vertical_penalty` is already `r_vertical_penalty = -2.0 * abs(vy)`. It's better to **Modify** it to include $v_x$ than to add a new one that overlaps. If I change the purpose of `vertical_penalty` to include $v_x$, I am breaking the rule. BUT, if I define the purpose of `vertical_penalty` as "velocity-based damping," then adding $v_x$ is just a shape/strength change of the "damping" concept.
    Let's look at the code: `r_vertical_penalty = -2.0 * abs(vy)`. The purpose is "Penalize vertical motion."
    If I change it to `-(2.0*abs(vx) + 5.0*abs(vy))`, I am changing the purpose to "Penalize all motion."
    Let's avoid the ambiguity.

    **Part 1: Excision**
    - `sliding_legs` (Purpose: reward movement)
    - `tilt_preference` (Purpose: reward tilt)
    - `upright_penalty` (Purpose: penalize target state)
    - `side_thruster_bonus` (Purpose: reward action)
    - `survival` (Purpose: constant)

    **Part 2: Proposals**
    1.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (Invert sign, change to quadratic $\text{angle}^2$ + angular velocity $|v_{\text{ang}}|$).
    2.  **Addition:** `kinetic_damping` (A single term penalizing $w_1|v_x| + w_2|v_y|$).
    3.  **Addition:** `centering_potential` (A single term penalizing $x^2$).

    *Actually, let's check `vertical_penalty` one more time.* It's `r_vertical_penalty = -2.0 * abs(vy)`.
    In Proposal 2, I will use a `kinetic_damping` term that replaces the need for `vertical_penalty`.
    Wait, if I don't excise `vertical_penalty`, it will stay there.
    So I must excise `vertical_penalty` too.

    *Wait, if `vertical_penalty` is optimal ($\rho=0.334$), I should keep it!*
    Okay, final, final, final plan:
    1.  **Excision:** `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`.
    2.  **Modification:** `vertical_penalty` $\to$ `kinetic_damping` (Target: `vy` $\to$ `vx, vy`).
        *Actually*, let's just modify it to include `vx`.
        The purpose of `vertical_penalty` is "Vertical motion penalty."
        The purpose of "Kinetic damping" is "Motion penalty."
        That is a change in purpose.
        I will do:
        **Proposal 2: Modification of `vertical_penalty` to `horizontal_and_vertical_damping`.**
        Input: `vy` $\to$ `vx, vy`.
        Purpose: "Damping of vertical motion" $\to$ "Damping of all velocity".
        Wait, that's still an excision.

    Let's try:
    1.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (Target: `angle`, Purpose: `orientation_control`).
    2.  **Addition:** `horizontal_damping` (Target: `vx`, Purpose: `horizontal_stability`).
    3.  **Addition:** `centering_potential` (Target: `x`, Purpose: `position_centering`).

    This is much cleaner and respects all rules.

    - `tilt_preference` (current: `3.0 * abs(angle) * 0.5`, purpose: `reward_tilt`)
    - `new_tilt_stability` (target: `-(10.0 * angle**2 + 2.0 * abs(v_ang))`, purpose: `orientation_stability`)
    - Is it a modification? The input `angle` is preserved. The purpose changes from `reward_tilt` to `minimize_tilt`. The prompt says: "A modification may freely change the signal's shape or strength... provided both the input and the behavioral purpose survive."
    - *Damn.* If the purpose changes, it's an excision.
    - Let's look at `tilt_preference` again. Its purpose is `r_tilt_preference = 3.0 * np.abs(angle) * 0.5`.
    - If I want to "Modify" it, I must keep the purpose: "Reward moderate tilt." But I want to *not* do that.
    - Okay, so `tilt_preference` **must** be an excision.

    **Correct Logic:**
    1.  **Excision:** `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`.
    2.  **Proposal 1 (Modification):** `vertical_penalty` $\to$ `vertical_stability` (Target: `vy` $\to$ `vy, v_ang`. Purpose: `vertical_damping` $\to$ `vertical_stability`). No, that's still a purpose change.

    *Let's simplify everything.*
    - **Excision:** Everything that is currently negative or wrong.
    - **Addition 1:** `orientation_stability` (Target: `angle, v_ang`, Purpose: `orientation_stability`).
    - **Addition s 2:** `kinetic_damping` (Target: `vx, vy`, Purpose: `kinetic_damping`).
    - **Addition 3:** `centering_potential` (Target: `x`, Purpose: `centering`).

    *Wait, if I excise `vertical_penalty`, I'm removing a good component.*
    - `vertical_penalty` (Target: `vy`, Purpose: `vertical_damping`).
    - **Proposal 1 (Modification):** `vertical_penalty` $\to$ `kinetic_damping` (Target: `vy` $\to$ `vx, vy`, Purpose: `vertical_damping` $\to$ `kinetic_damping`). Still a purpose change.
    - **Actually**, `vertical_damping` and `kinetic_damping` are very similar. I will just **Modify** `vertical_penalty` to include `vx`. This is a strength/shape change of the "damping" concept.

    1.  **Excision:** `sliding_legs` (Purpose: reward movement), `tilt_preference` (Purpose: reward tilt), `upright_penalty` (Purpose: penalize upright), `side_thruster_bonus` (Purpose: reward action), `survival` (Purpose: constant).
    2.  **Proposal 1 (Modification):** `tilt_preference` $\to$ `orientation_stability` (Target: `angle`, Purpose: `orientation_control`). *Wait, I'll just call it orientation control.*
    3.  **Proposal 2 (Modification):** `vertical_penalty` $\to$ `kinetic_damping` (Target: `vy` $\to$ `vx, vy`, Purpose: `velocity_damping`).
    4.  **Proposal 3 (Addition):** `centering_potential` (Target: `x`, Purpose: `position_centering`).

    *Final Check:*
    - `tilt_preference` (Input: `angle`, Purpose: `tilt_preference`) $\to$ `orientation_stability` (Input: `angle`, Purpose: `orientation_stability`). This is a change in purpose.
    - *Wait*, what if I don't change the purpose? What if the purpose of `tilt_preference` was "angle-based shaping"? Then a sign change is a modification.
    - Let's assume "orientation-based shaping" is the purpose.

    *Let's go with this:*
    - **Excision:** `sliding_legs`, `upright_penalty`, `side_thruster_bonus`, `survival`.
    - **Modification 1:** `tilt_preference` (Target: `angle`, Purpose: `angle_shaping`) $\to$ `orientation_stability` (Target: `angle`, Purpose: `angle_shaping`). (Sign flip + Quadratic).
    - **Modification 2:** `vertical_penalty` (Target: `vy`, Purpose: `velocity_damping`) $\to$ `kinetic_damping` (Target: `vx, vy`, Purpose: `velocity_damping`).
    - **Addition 3:** `centering_potential` (Target: `x`, Purpose: `position_centering`).

    *This is the most mathematically sound way to follow the rules.*

    - `vertical_penalty`: `-2.0 * abs(vy)`.
    - `kinetic_damping`: `-(2.0 * abs(vx) + 5.0 * abs(vy))`.
    - Input `vy` is preserved. Purpose `velocity_damping` is preserved (just expanded).

    - `tilt_preference`: `3.0 * abs(angle) * 0.5`.
    - `orientation_stability`: `-(10.0 * angle**2 + 2.0 * abs(v_ang))`.
    - Input `angle` is preserved. Purpose `angle_shaping` is preserved.

    *Wait, `upright_penalty` is a penalty on `angle`. I should excise it to avoid conflict.*

    *Final check on `vertical_penalty`:* If I include `vx` in the `vertical_penalty` modification, I am technically adding a new input (`vx`). The rule says: "If either [input or purpose] changes, it is not a modification."
    Okay, so I will NOT modify `vertical_penalty`. I will:
    1.  **Excision:** `sliding_legs`, `tilt_preference`, `up-right_penalty`, `side_thruster_bonus`, `survival`.
    2.  **Modification:** `tilt_preference` $\to$ `orientation_stability` (Target: `angle`, Purpose: `angle_shaping`).
    3.  s **Addition 1:** `kinetic_damping` (Target: `vx, vy`, Purpose: `velocity_damping`).
    4.  **Addition 2:** `centering_potential` (Target: `x`, Purpose: `position_centering`).

    *Wait, I have a `vertical_penalty` left.* I'll just add it to the `kinetic_damping` list? No.
    I will:
    1.  Excision: `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`, `vertical_penalty`.
    2.  Mod 1: `tilt_preference` $\to$ `orientation_stability` (Input: `angle`, Purpose: `angle_shaping`).
    3.  Add 1: `kinetic_damping` (Input: `vx, vy`, Purpose: `velocity_damping`).
    4.  Add 2: `centering_potential` (Input: `x`, Purpose: `position_centering`).

    *Wait, why excise `vertical_penalty`?* Because `kinetic_damping` is a better version of it. This is cleaner.

    *Final Final Final Plan:*
    - **Excision:** `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`, `vertical_penalty`.
    - **Proposal 1 (Modification):** `tilt_preference` $\to$ `orientation_stability` (Input: `angle`, Purpose: `angle_shaping`).
    - **Proposal 2 (Addition):** `kinetic_damping` (Input: `vx, vy`, Purpose: `velocity_damping`).
    - **Proposal 3 (Addition):** `centering_potential` (Input: `x`, Purpose: `position_centering`).

    *Let's check the `vertical_penalty` $\rho$ again.* It's `0.334`. If I excise it, I'm losing a good signal.
    Maybe I should keep it and just add `vx` as a *new* component?
    **Addition 1:** `horizontal_damping` (Target: `vx`, Purpose: `velocity_damping`).
    This is much safer.

    - **Excision:** `sliding_slegs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`.
    - **Modification 1:** `tilt_preference` (Input: `angle`, Purpose: `angle_shaping`) $\to$ `orientation_stability` (Input: `angle`, Purpose: `angle_shaping`).
    - **Addition 1:** `horizontal_damping` (Input: `vx`, Purpose: `velocity_damping`).
    - **Addition 2:** `centering_potential` (Input: `x`, Purpose: `position_centering`).

    *Wait, `vertical_penalty` is already there. So `horizontal_damping` + `vertical_penalty` = `kinetic_damping`.*

    - `sliding_legs`: Reward-velocity (Incoherent).
    - `tilt_preference`: Reward-tilt (Incoherent).
    - `upright_penalty`: Penalty-upright (Incoherent).
    - `side_thruster_bonus`: Reward-action (Incoherent).
    - `survival`: Constant (Incoherent).

    - **Modification 1:** `tilt_preference` $\to$ `orientation_stability`. (Input: `angle`, Purpose: `angle_shaping`).
    - **Addition 1:** `horizontal_damping` (Input: `vx`, Purpose: `velocity_damping`).
    - **Addition 2:** `centering_potential` (Input: `x`, Purpose: `position_centering`).

    *Let's refine the math for `orientation_stability` to include `v_ang`.* It's a common practice for stability.

    *Final Math Check:*
    - `orientation_stability`: `-(10.0 * angle**2 + 2.0 * abs(v_ang))`
    - `horizontal_damping`: `-2.0 * abs(vx)`
    - `centering_potential`: `-1.0 * x**2`

    *Wait, the vertical penalty is still there.*
    - `vertical_penalty`: `-2.0 * abs(vy)`.
    - So the total damping is `-2.0*abs(vx) - 2.0*abs(vy)`.

    - `Population Success Rate`: Increase.
    - `Mean Descent Efficiency`: Increase.
    - `Chatter Rate`: Decrease.

    *This is ready.*


# Phase: strategist [Output] gemma4:26b-mlx
**PART 1: SURGICAL EXCISION**

* `sliding_legs`: The functional identity (rewarding horizontal velocity during contact) is fundamentally adversarial to the goal of a stable, stationary landing.
* `tilt_preference`: The functional identity (rewarding angular deviation) is the direct opposite of the required landing orientation.
* `upright_penalty`: The functional identity (penalizing the target state) creates a discontinuous optimization landscape that discourages the agent from reaching its goal.
* `side_thruster_bonus`: The functional identity (rewarding lateral action) incentivizes high-frequency control oscillations rather than stability.
* `survival`: The functional identity (a flat scalar) provides no gradient for the landing manifold and is irrelevant to the physical constraints.

**PART 2: 3 PROPOSALS**

**Proposal 1: Modification**
1. **The Conceptual Hypothesis:** The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward $\text{angle} = 0$ and prevent the high-frequency oscillations caused by the previous threshold-based `upright_penalty`.
2. **The Mathematical Formulation:**
   Modify `tilt_preference`:
   $\text{Old Form: } 3.0 \cdot |\text{angle}| \cdot 0.5$
   $\text{New Form: } r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)$
3. **The Falsifiable Expected Outcome:** `Actuator Chatter Rate` will decrease (due to smoother gradients) and `Population Success Rate` will increase as the agent stabilizes its attitude.

**Proposal 2: Addition**
1. **The Conceptual Hypothesis:** While the agent has a vertical damping term (`vertical_penalty`), it lacks a mechanism to penalize lateral momentum. To achieve a stationary landing, the agent must minimize all kinetic energy ($v_x$ and $v_y$) as it approaches the ground.
2. **The Mathematical Formulation:**
   $r_{\text{horizontal\_damping}} = -2.5 \cdot |\text{vx}|$
   *Note: This works in synergy with the existing `vertical_penalty` to create a comprehensive kinetic damping effect.*
3. **The Falsifiable Expected Outcome:** `Mean Descent Efficiency` will increase and `Population Success-Rate` will improve as the agent stops "sliding" and starts settling.

**Proposal 3: Addition**
1. **The Conceptual Hypothesis:** The agent currently has no mathematical incentive to center itself on the landing pad ($x=0$). A centering potential well will provide a global gradient that guides the agent from the edges of the state space toward the target landing coordinate.
2. **The Mathematical Formulation:**
   $r_{\text{centering}} = -1.5 \cdot \text{x}^2$
3. **The Falsifiable Expected Outcome:** The terminal $x$-position distribution will tighten around $0$, and `Population Success Rate` will increase as the agent successfully reaches the landing zone.


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

* `sliding_legs`: The functional identity (rewarding horizontal velocity during contact) is fundamentally adversarial to the goal of a stable, stationary landing.
* `tilt_preference`: The functional identity (rewarding angular deviation) is the direct opposite of the required landing orientation.
* `upright_penalty`: The functional identity (penalizing the target state) creates a discontinuous optimization landscape that discourages the agent from reaching its goal.
* `side_thruster_bonus`: The functional identity (rewarding lateral action) incentivizes high-frequency control oscillations rather than stability.
* `survival`: The functional identity (a flat scalar) provides no gradient for the landing manifold and is irrelevant to the physical constraints.

**PART 2: 3 PROPOSALS**

**Proposal 1: Modification**
1. **The Conceptual Hypothesis:** The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward $\text{angle} = 0$ and prevent the high-frequency oscillations caused by the previous threshold-based `upright_penalty`.
2. **The Mathematical Formulation:**
   Modify `tilt_preference`:
   $\text{Old Form: } 3.0 \cdot |\text{angle}| \cdot 0.5$
   $\text{New Form: } r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)$
3. **The Falsifiable Expected Outcome:** `Actuator Chatter Rate` will decrease (due to smoother gradients) and `Population Success Rate` will increase as the agent stabilizes its attitude.

**Proposal 2: Addition**
1. **The Conceptual Hypothesis:** While the agent has a vertical damping term (`vertical_penalty`), it lacks a mechanism to penalize lateral momentum. To achieve a stationary landing, the agent must minimize all kinetic energy ($v_x$ and $v_y$) as it approaches the ground.
2. **The Mathematical Formulation:**
   $r_{\text{horizontal\_damping}} = -2.5 \cdot |\text{vx}|$
   *Note: This works in synergy with the existing `vertical_penalty` to create a comprehensive kinetic damping effect.*
3. **The Falsifiable Expected Outcome:** `Mean Descent Efficiency` will increase and `Population Success-Rate` will improve as the agent stops "sliding" and starts settling.

**Proposal 3: Addition**
1. **The Conceptual Hypothesis:** The agent currently has no mathematical incentive to center itself on the landing pad ($x=0$). A centering potential well will provide a global gradient that guides the agent from the edges of the state space toward the target landing coordinate.
2. **The Mathematical Formulation:**
   $r_{\text{centering}} = -1.5 \cdot \text{x}^2$
3. **The Falsifiable Expected Outcome:** The terminal $x$-position distribution will tighten around $0$, and `Population Success Rate` will increase as the agent successfully reaches the landing zone.

**ACTION REQUIRED:**
Extract the core reasoning, math, and expected outcomes from the raw text above. Output the completely sanitized and formatted proposals using your system template. Do not include any introductory or concluding conversational text.


# Phase: organizer [Thinking Trace] gpt-oss:20b
We need to produce for each proposal the exact template:

### Proposal [Number]: [Title extracted or inferred from the Strategist]

**1. Conceptual Hypothesis:** [The physical or optimization reasoning behind the change.]

**2. Mathematical Formulation:**
* **Code Additions:** [The exact LaTeX math or Python snippet proposed to be added.]
* **Code Deletions:** [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE. Must list items verbatim.]

**3. Reward Scaling & Constraints:**

* **Coefficient:** [Extract the multiplier/scale used]
* **Constraint/Clipping:** [Extract any bounds or clips mentioned. If none, write "None explicitly stated."]
* **Integration:** [Extract which variables/lines this targets]

**4. Falsifiable Expected Outcome:**

* **Target Metric:** [The specific metric from the diagnostic report to be improved]
* **Expected Change:** [The numerical shift expected]

We have 3 proposals. We need to extract title: maybe from "Proposal 1: Modification" => title "Modification". Proposal 2: "Addition". Proposal 3: "Addition". Use that.

We need to extract conceptual hypothesis: from each.

Mathematical Formulation: Code Additions: the new formula. For Proposal 1: r_orientation = -(10.0 * angle^2 + 2.0 * |v_ang|). The old form is not needed. So Code Additions: that formula.

Code Deletions: must insert global excision manifesto list: from PART 1: sliding_legs, tilt_preference, upright_penalty, side_thruster_bonus, survival. Must list them verbatim. The list includes backticks? The raw list shows bullet items with backticks: `sliding_legs`: ... So we should list them as bullet points? The template says Code Deletions: [INSERT THE GLOBAL EXCISION MANIFESTO LIST HERE. You must explicitly list the manifesto items in this bullet point for every proposal. Do not write "None explicitly stated" if a manifesto exists.] So we need to list the items. Probably as a bullet list inside the bullet? But the template only has one bullet point for Code Deletions. We can include them separated by commas or newlines. The instruction: "explicitly list the manifesto items in this bullet point for every proposal." So we can list them as separate lines maybe preceded by dash or just comma separated. I'll do comma separated list.

Now Reward Scaling & Constraints: We need to extract coefficient: For Proposal 1: multiplier 10.0 for angle^2 and 2.0 for |v_ang| but the coefficient maybe 10.0? The formula includes two terms. We can choose coefficient 10.0? Might need to mention both? The template expects a single coefficient. We can state "10.0" as the main coefficient. Or we could note that the reward is scaled by -1 times (10.0*angle^2 + 2.0*|v_ang|). So coefficient -1? But the coefficient likely refers to the multiplier used. We can choose "10.0" as the main coefficient. For the second term coefficient 2.0. Might be ambiguous. But we can put "10.0" as coefficient for angle^2 and "2.0" for angular velocity. But the template expects one coefficient. Maybe we put "10.0" as the coefficient for angle^2 and mention the other as part of the formulation. But to be safe, we can state "10.0" as the coefficient (since it's the main scaling). Or we can say "10.0 and 2.0" but that's two. I'll choose "10.0" and note the second term coefficient as part of formulation.

Constraint/Clipping: None explicitly stated.

Integration: Targets angle and v_ang.

Now Falsifiable Expected Outcome: Target Metric: Actuator Chatter Rate. Expected Change: decrease (but no numeric value). The raw text says "Actuator Chatter Rate will decrease ... and Population Success Rate will increase". No numeric shift. So we can write "decrease" and "increase" respectively. The template expects a numerical shift expected. But we can just write "decrease" or "increase". If numeric shift not provided, maybe leave blank? But we need to provide something. We can write "decrease" as expected change. For Population Success Rate? The template expects one target metric and expected change. We can choose "Actuator Chatter Rate" and "decrease". Alternatively we could mention both metrics. But the template only has one target metric. The raw text mentions two metrics. We need to choose one. We could pick "Actuator Chatter Rate". For expected change: "decrease". That satisfies.

But the raw text also mentions Population Success Rate. But we can only include one metric. We could mention "Population Success Rate" as target metric and "increase". Which one? The template might allow only one. We'll pick "Population Success Rate" and "increase". But the first metric is Actuator Chatter Rate. The wording: "Actuator Chatter Rate will decrease ... and Population Success Rate will increase". We need to choose one. Maybe choose the first metric. But the "Falsifiable Expected Outcome" in the raw includes two metrics. The template seems to allow only one. But we can choose either. I'll choose "Population Success Rate" as the target metric and "increase" as expected change.

But the template expects "Target Metric" and "Expected Change". We'll fill accordingly.

Now Proposal 2: Title "Addition". Conceptual Hypothesis: from text. Code Additions: r_horizontal_damping = -2.5 * |vx|. Code Deletions: same global excision list. Reward Scaling & Constraints: Coefficient: 2.5 (multiplier). Constraint/Clipping: None explicitly stated. Integration: vx. Falsifiable Expected Outcome: Target Metric: Mean Descent Efficiency or Population Success-Rate. We can choose "Mean Descent Efficiency" and "increase". Or "Population Success-Rate" and "improve". The raw says "Mean Descent Efficiency will increase and Population Success-Rate will improve". We'll choose "Mean Descent Efficiency" and "increase".

Proposal 3: Title "Addition". Conceptual Hypothesis: from text. Code Additions: r_centering = -1.5 * x^2. Code Deletions: same list. Reward Scaling & Constraints: Coefficient: 1.5. Constraint/Clipping: None explicitly stated. Integration: x. Falsifiable Expected Outcome: Target Metric: terminal x-position distribution tightness? But the raw says "terminal x-position distribution will tighten around 0". The metric might be "x-position distribution variance" or "Population Success Rate". We'll choose "Population Success Rate" and "increase".

But the metric "terminal x-position distribution will tighten around 0" is more specific. But the template expects a metric name. We can use "Terminal x-position distribution". But not sure. Let's choose "Population Success Rate" for consistency.

Now we need to produce final output with the template.

Also we need to ensure no extra text. Provide only the proposals.

Also we need to maintain the exact formatting: ### Proposal [Number]: [Title]. Then the sections with **1. Conceptual Hypothesis:** etc.

We must also ensure the bullet points under Code Additions and Code Deletions are correctly formatted. The template says * **Code Additions:** [the formula] * **Code Deletions:** [list]. So we need to use asterisks for bullet list. The bullet list for Code Deletions might be a single bullet containing multiple items. But we can list them separated by commas. Eg: `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`. That might be okay.

Alternatively, we could list them as separate lines with dash inside the bullet. But the template might not allow nested bullet. But we can include them as comma separated.

Let's produce.

Also ensure that we preserve LaTeX math exactly. Use dollar signs.

Now produce final output.


# Phase: organizer [Output] gpt-oss:20b
### Proposal 1: Modification

**1. Conceptual Hypothesis:**  
The current orientation signal is both incorrectly signed and non‑smooth. By transforming the angle‑based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward \(\text{angle}=0\) and prevent the high‑frequency oscillations caused by the previous threshold‑based `upright_penalty`.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 10.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{angle}\) and \(\text{v\_ang}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase

---

### Proposal 2: Addition

**1. Conceptual Hypothesis:**  
While the agent has a vertical damping term (`vertical_penalty`), it lacks a mechanism to penalize lateral momentum. To achieve a stationary landing, the agent must minimize all kinetic energy (\(v_x\) and \(v_y\)) as it approaches the ground.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{horizontal\_damping}} = -2.5 \cdot |\text{vx}|
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 2.5  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{vx}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Mean Descent Efficiency  
* **Expected Change:** increase

---

### Proposal 3: Addition

**1. Conceptual Hypothesis:**  
The agent currently has no mathematical incentive to center itself on the landing pad (\(x=0\)). A centering potential well will provide a global gradient that guides the agent from the edges of the state space toward the target landing coordinate.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{centering}} = -1.5 \cdot \text{x}^2
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 1.5  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{x}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase


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

### Proposal 1: Modification

**1. Conceptual Hypothesis:**  
The current orientation signal is both incorrectly signed and non‑smooth. By transforming the angle‑based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward \(\text{angle}=0\) and prevent the high‑frequency oscillations caused by the previous threshold‑based `upright_penalty`.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 10.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{angle}\) and \(\text{v\_ang}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase

---

### Proposal 2: Addition

**1. Conceptual Hypothesis:**  
While the agent has a vertical damping term (`vertical_penalty`), it lacks a mechanism to penalize lateral momentum. To achieve a stationary landing, the agent must minimize all kinetic energy (\(v_x\) and \(v_y\)) as it approaches the ground.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{horizontal\_damping}} = -2.5 \cdot |\text{vx}|
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 2.5  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{vx}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Mean Descent Efficiency  
* **Expected Change:** increase

---

### Proposal 3: Addition

**1. Conceptual Hypothesis:**  
The agent currently has no mathematical incentive to center itself on the landing pad (\(x=0\)). A centering potential well will provide a global gradient that guides the agent from the edges of the state space toward the target landing coordinate.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{centering}} = -1.5 \cdot \text{x}^2
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 1.5  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{x}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase

### [3. DIAGNOSTIC REPORT (CURRENT BEHAVIOR)]
### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.1640`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.1600`  *(lower = more settled)*
  - *Diagnosis:* The optimization is still churning inside the final training quartile. The converged policy is non-stationary and may not retain.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `12.45`
  - *Diagnosis:* Warning. The Critic is struggling to map the advantage function. Consider reducing the scale of dense penalty components.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.108`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.022`
- **Actuator Chatter Rate:** `0.031`

#### C. Population Terminal Distribution
- `crashed`: 100.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `undefined (single-class population)`  *(ground truth)*
- **Objective Alignment ($\rho$):** `nan`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (crashed) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `sliding_legs` | -0.295 | 1.0% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `tilt_preference` | -0.335 | 31.5% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `upright_penalty` | -0.239 | 9.9% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `slalom_bonus` | -0.019 | 0.0% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `side_thruster_bonus` | -0.269 | 23.3% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `ground_level` | 0.136 | 9.1% | ⚪ Neutral/Noisy |
| `vertical_penalty` | 0.334 | 23.5% | 🟢 Optimal |
| `survival` | -0.246 | 1.3% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `leg_maintenance` | -0.080 | 0.4% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `1.316` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.004`
  - *Diagnosis:* The stochastic policy has completely collapsed into a single pathological failure mode. The KL penalty likely prevented escape from a severe local minimum.

**ACTION REQUIRED:**
Evaluate the proposals based on your evaluation criteria. Output your `EXECUTIVE DECISION` selecting the single most viable Mathematical Contract.


# Phase: research_lead [Thinking Trace] deepseek-r1:32b

Okay, so I'm trying to figure out which proposal to choose for the LunarLander-v3 project. Let me go through each proposal and the evaluation criteria step by step.

First, the evaluation criteria are:
1. Novelty Check: Make sure the proposal doesn't repeat a failed hypothesis from the Experiment Ledger.
2. Falsifiability: The proposal must have a clear, measurable outcome.
3. Physical Grounding: It should address actual physics rather than just scaling numbers.

Looking at the Experiment Ledger, since it's the first iteration, there's no past data to reference. So, I don't have to worry about repeating failed hypotheses here.

Now, looking at the proposals:

Proposal 1 suggests modifying the orientation signal by using a quadratic penalty on angle and angular velocity. The hypothesis is that this will smooth out the gradient and reduce oscillations. The outcome expected is an increase in the population success rate. This seems to address the physics by targeting angle and angular velocity, which are kinematic aspects.

Proposal 2 adds a horizontal damping term to penalize lateral momentum. The idea is to help the agent land more accurately by reducing kinetic energy. The expected outcome is an increase in descent efficiency. This also seems physically grounded as it targets velocity components.

Proposal 3 adds a centering potential well to guide the agent towards the landing pad. The outcome expected is an increase in success rate. This targets the position x, which is another physical aspect.

Looking at the diagnostic report, the current policy is highly stable but consistently failing, with a population success rate of 0%. The critic is struggling, and there's high negative alignment in several reward components, suggesting they're opposing success.

Proposal 1's modification targets the orientation penalty, which was negatively aligned. By replacing it with a quadratic penalty, it could provide a smoother gradient, helping the agent learn better. This directly addresses a problematic reward component.

Proposal 2 aims to reduce lateral movement, which could help in achieving a stationary landing, but the current issue is more about orientation and survival, as indicated by the high negative alignment of the upright_penalty.

Proposal 3 focuses on centering the agent, which might help in guiding it to the landing pad, but the immediate issue seems to be orientation and damping rather than positioning.

Considering the critic saturation, reducing the scale of dense penalties is advised. Proposal 1's formulation uses coefficients of 10.0 and 2.0, which might be high. However, it's replacing multiple existing penalties, so the overall impact might be balanced.

In terms of falsifiability, all proposals have clear expected outcomes, but Proposal 1 directly targets a known issue with the upright_penalty, which was negatively aligned. By replacing it, we can test if this improves the success rate.

So, after evaluating, Proposal 1 seems to address the root cause by modifying a negatively aligned reward component with a physically grounded approach, providing a clear way to test its effectiveness.



# Phase: research_lead [Output] deepseek-r1:32b


### EXECUTIVE DECISION

**Selected Proposal:** Proposal 1: Modification

**1. Scientific Rationale:**  
Proposal 1 addresses the problematic upright_penalty by introducing a smooth quadratic penalty on angle and angular velocity, providing a clearer gradient for learning stability. This modification directly targets the physical aspects of orientation and angular momentum, offering a more effective reward structure.

**2. Ledger Clearance:**  
There is no prior history to reference, so this proposal does not violate past lessons.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward \(\text{angle}=0\) and prevent the high-frequency oscillations caused by the previous threshold-based `upright_penalty`.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 10.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{angle}\) and \(\text{v\_ang}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase


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

**Selected Proposal:** Proposal 1: Modification

**1. Scientific Rationale:**  
Proposal 1 addresses the problematic upright_penalty by introducing a smooth quadratic penalty on angle and angular velocity, providing a clearer gradient for learning stability. This modification directly targets the physical aspects of orientation and angular momentum, offering a more effective reward structure.

**2. Ledger Clearance:**  
There is no prior history to reference, so this proposal does not violate past lessons.

**3. Execution Hand-off:**

**1. Conceptual Hypothesis:**  
The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward \(\text{angle}=0\) and prevent the high-frequency oscillations caused by the previous threshold-based `upright_penalty`.

**2. Mathematical Formulation:**  
* **Code Additions:**  
  \[
  r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
  \]
* **Code Deletions:**  
  `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`

**3. Reward Scaling & Constraints:**  

* **Coefficient:** 10.0  
* **Constraint/Clipping:** None explicitly stated.  
* **Integration:** Targets \(\text{angle}\) and \(\text{v\_ang}\).

**4. Falsifiable Expected Outcome:**  

* **Target Metric:** Population Success Rate  
* **Expected Change:** increase

**ACTION REQUIRED:**
Extract and route the mathematical instructions to the `<CODER_PAYLOAD>` and the intervention parameters and predicted effects to the `<VALIDATOR_PAYLOAD>`. Output nothing else.


# Phase: dispatcher [Thinking Trace] gpt-oss:20b
We need to parse the decision. The Coder payload requires:

- Code Deletions: list of component names to delete entirely. They are backticked: `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`. So we list each on its own line, verbatim.

- Code Additions: the reward math. It's given: r_orientation = -(10.0 * angle^2 + 2.0 * |v_ang|). We need to extract math verbatim. So we put that as the math.

- Scaling & Constraints: coefficients and clip bounds for the additions. Coefficient 10.0. Constraint/Clipping: None explicitly stated. So we list coefficient 10.0 and maybe "None" for clipping. The format expects structured list if more than 1 numerical value. We have coefficient 10.0 and maybe 2.0? Actually the formula includes 10.0 and 2.0. But the coefficient refers to 10.0? The scaling & constraints: "Coefficient: 10.0" and "Constraint/Clipping: None explicitly stated." So we list [10.0, None]. Or maybe we need to list coefficient and clipping. The instructions: "Scaling & Constraints: coefficients and clip bounds for the additions." So we can list coefficient 10.0 and clipping None. Could also include 2.0? But that's part of the formula, not scaling. The formula includes 2.0 for angular velocity. That is part of the math. The scaling is 10.0. So we list [10.0, None].

- Integration: obs variables the additions touch: angle and v_ang. So list [angle, v_ang] maybe.

The Validator payload:

- Conceptual Hypothesis: The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward angle=0 and prevent high-frequency oscillations caused by previous threshold-based upright_penalty.

- Falsifiable Expected Outcome: Target Metric: Population Success Rate. Expected Change: increase. Side Effects: none listed. So we can leave Side Effects blank or None.

We need to output XML tags exactly as specified:

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

We need to fill each field. For Code Deletions: we list each component on separate lines: `sliding_legs`, `tilt_preference`, `upright_penalty`, `side_thruster_bonus`, `survival`.

For Code Additions: we put the formula exactly: r_orientation = -(10.0 * angle^2 + 2.0 * |v_ang|). We need to preserve the formatting. Probably we can use the same LaTeX expression: \[
r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
\] But instructions: "Extract the math verbatim." So we can copy the math as shown. We might keep LaTeX. The original uses LaTeX. So we can include that. But the instructions say: "Extract only math and syntax; strip hypotheses and outcomes. Route into four fields." So we should include the math exactly as provided: r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|). We can wrap in \[ ... \] or not. But it's part of the math. Let's include the same LaTeX block.

Scaling & Constraints: we list [10.0, None] maybe as a list. The format: "Coefficients and clips for the math above". So we can write [10.0, None]. If we want to be explicit: [10.0, None].

Integration: [angle, v_ang].

Validator:

Conceptual Hypothesis: copy the hypothesis: "The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward angle=0 and prevent the high-frequency oscillations caused by the previous threshold-based upright_penalty."

Target Metric: Population Success Rate

Expected Change: increase

Side Effects: none. The decision does not mention side effects. So we can put None or empty. The template says "* Side Effects: [Extracted side effects]". So we can put None.

We need to ensure no extra conversational text. Just the tags.

Let's craft the output.

Check formatting: Each field inside tags preceded by **Field Name:** then value. The value can be multiline for deletions. For Code Deletions, list each component on its own line. The instructions: "Copy the exact backticked component names from the Research Lead's excision list, one per line, verbatim — do not summarize, paraphrase, group, or rename." So we should list each on a new line. For example:

**Code Deletions:**
`sliding_legs`
`tilt_preference`
`upright_penalty`
`side_thruster_bonus`
`survival`

But the instructions say "one per line, verbatim". So we should include backticks exactly. So we need to output backticks. The example in the instructions uses backticks. So we must include them. So the output should be:

**Code Deletions:**
`sliding_legs`
`tilt_preference`
`upright_penalty`
`side_thruster_bonus`
`survival`

But we must be careful: the tags require the field value inside the tags. The value can be multiline. So we can include newlines. That should be fine.

Similarly, for Code Additions: we can include the LaTeX block. We need to preserve the backslashes. So we can write:

**Code Additions:**
\[
r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
\]

But the instructions: "Extract the math verbatim." The original math includes \[ ... \] and \cdot. So we should copy exactly. So we can output exactly as above.

Scaling & Constraints: we can write [10.0, None] or something. But maybe we should list coefficient and clip bounds. The coefficient is 10.0. The constraint is None. So we can write: [10.0, None]. That might be okay.

Integration: [angle, v_ang].

Validator: same.

Let's produce final answer.


# Phase: dispatcher [Output] gpt-oss:20b
<CODER_PAYLOAD>
**Code Deletions:**
`sliding_legs`
`tilt_preference`
`upright_penalty`
`side_thruster_bonus`
`survival`
**Code Additions:**
\[
r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
\]
**Scaling & Constraints:**
[10.0, None]
**Integration:**
[angle, v_ang]
</CODER_PAYLOAD>

<VALIDATOR_PAYLOAD>
**Conceptual Hypothesis:** The current orientation signal is both incorrectly signed and non-smooth. By transforming the angle-based term into a continuous quadratic penalty that includes angular velocity, we provide a smooth gradient toward angle=0 and prevent the high-frequency oscillations caused by the previous threshold-based upright_penalty.
**Falsifiable Expected Outcome:** - Target Metric: Population Success Rate

* Expected Change: increase
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
    prev_vx, prev_legs = prev_obs[2], prev_obs[6] + prev_obs[7]
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # Massive bonus for legs down AND sliding fast sideways
    sliding_legs = legs_contact * horiz_slide_speed
    r_sliding_legs = 12.0 * np.clip(sliding_legs / 2.0, 0, 1.5)  # up to +18!
    
    # === 2. PREFER TILTED ORIENTATION (discourage upright) ===
    # Reward moderate tilt (easier to slide)
    r_tilt_preference = 3.0 * np.abs(angle) * 0.5  # up to ~4.5 for π/2 tilt
    
    # Penalty for perfectly upright (stable landing pose)
    upright_penalty = -8.0 if abs(angle) < 0.05 else 0.0
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    r_slalom = 6.0 if vx_sign_flip else 0.0
    
    # === 4. SIDE THRUSTER LOVE (lateral control) ===
    if action in (1, 3):  # left/right thrusters
        r_action = 2.0
    elif action == 2:  # main (less useful for sliding)
        r_action = -0.5
    else:
        r_action = -1.0
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    near_ground = abs(y) < 0.4
    r_ground_level = 3.0 if near_ground else -1.5
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * abs(vy)  # Hate up/down
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    components = {
        "sliding_legs": float(r_sliding_legs),
        "tilt_preference": float(r_tilt_preference),
        "upright_penalty": float(upright_penalty),
        "slalom_bonus": float(r_slalom),
        "side_thruster_bonus": float(r_action),
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "survival": float(r_survival),
        "leg_maintenance": float(r_leg_maintenance),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components


```

### [NEW MATHEMATICAL INSTRUCTIONS]

These are the explicit mathematical updates you must integrate into the code above.

**Code Deletions:**
`sliding_legs`
`tilt_preference`
`upright_penalty`
`side_thruster_bonus`
`survival`
**Code Additions:**
\[
r_{\text{orientation}} = -(10.0 \cdot \text{angle}^2 + 2.0 \cdot |\text{v\_ang}|)
\]
**Scaling & Constraints:**
[10.0, None]
**Integration:**
[angle, v_ang]


**EXECUTION CHECKLIST — complete in this order before writing any code:**
1. Read the deletion list. For each named component: mark its variable, its `components` dict entry, and its section comment for removal.
2. Confirm every component not on the deletion list and not redefined in Code Additions is preserved with its exact variable name, dict key, and computation unchanged.
3. Implement the Code Additions using the specified Scaling & Constraints.
4. Check the `components` dict: verify no entry is a derived combination (sum or product) of other entries already in the dict.

**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`.


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
    prev_vx, prev_legs = prev_obs[2], prev_obs[6] + prev_obs[7]
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # Massive bonus for legs down AND sliding fast sideways
    sliding_legs = legs_contact * horiz_slide_speed
    r_sliding_legs = 12.0 * np.clip(sliding_legs / 2.0, 0, 1.5)  # up to +18!
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    r_slalom = 6.0 if vx_sign_flip else 0.0
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    near_ground = abs(y) < 0.4
    r_ground_level = 3.0 if near_ground else -1.5
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * abs(vy)  # Hate up/down
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    # === 8. ORIENTATION PENALTY ===
    r_orientation = -(10.0 * angle**2 + 2.0 * abs(v_ang))
    
    components = {
        "sliding_legs": float(r_sliding_legs),
        "slalom_bonus": float(r_slalom),
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "leg_maintenance": float(r_leg_maintenance),
        "orientation_penalty": float(r_orientation),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
```

