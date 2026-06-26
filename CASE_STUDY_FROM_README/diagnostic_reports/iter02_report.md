### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.1870`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.1470`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.032`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `30.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.005`
- **Actuator Chatter Rate:** `0.409`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `crashed`: 43.0%
- `landed_off_centered`: 17.0%
- `out_of_bounds`: 14.0%
- `hover_timeout`: 13.0%
- `landed_but_slid_into_valley`: 11.0%
- `landed_off_centered_timeout`: 1.0%
- `landed_centered`: 1.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-407.788`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.193`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `sliding_legs` | -0.029 | 0.056 | 7.6% | 🔴 **HIDDEN TRAITOR** — Non-linear association with failure, δ=-0.079/step. Examine functional form (threshold/saturation likely). |
| `slalom_bonus` | 0.000 | 0.002 | 0.0% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `ground_level` | 0.055 | 0.053 | 32.3% | 🔵 **NON-LINEAR HELPER** — Non-linear positive contribution, δ=+0.269/step. Preserve this component's structure. |
| `vertical_penalty` | 0.003 | 0.057 | 28.0% | 🔵 **NON-LINEAR HELPER** — Non-linear positive contribution, δ=+0.099/step. Preserve this component's structure. |
| `leg_maintenance` | 0.092 | 0.174 | 20.5% | 🔵 **NON-LINEAR HELPER** — Non-linear positive contribution, δ=+0.438/step. Preserve this component's structure. |
| `orientation_penalty` | 0.179 | 0.100 | 11.7% | ⚪ Neutral/Noisy |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.863` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.851`
  - *Diagnosis:* The policy is highly fragile. Even with fixed network weights, the agent's performance swings wildly depending on environment initialization.