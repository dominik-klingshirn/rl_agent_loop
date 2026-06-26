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