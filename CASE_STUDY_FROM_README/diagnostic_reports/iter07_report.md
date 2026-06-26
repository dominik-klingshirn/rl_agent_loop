### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0620`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0330`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.000`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `87.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.008`
- **Actuator Chatter Rate:** `0.502`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `landed_centered`: 53.0%
- `landed_off_centered`: 17.0%
- `landed_but_slid_into_valley`: 11.0%
- `crashed`: 10.0%
- `landed_off_centered_timeout`: 6.0%
- `hover_timeout`: 3.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-422.575`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.599`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.433 | 0.123 | 36.4% | 🟢 Optimal |
| `vertical_penalty` | 0.384 | 0.091 | 5.4% | 🟢 Optimal |
| `leg_maintenance` | 0.440 | 0.218 | 26.9% | 🟢 Optimal |
| `orientation_penalty` | 0.281 | 0.108 | 7.5% | 🟢 Optimal |
| `velocity_stability` | 0.419 | 0.119 | 16.9% | 🟢 Optimal |
| `action_smoothness` | -0.359 | 0.125 | 5.7% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `lateral_viscosity` | 0.279 | 0.072 | 1.1% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.596` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.645`
  - *Diagnosis:* The policy is highly fragile. Even with fixed network weights, the agent's performance swings wildly depending on environment initialization.