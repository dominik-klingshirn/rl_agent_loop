### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0200`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0470`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `-0.155`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `91.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.006`
- **Actuator Chatter Rate:** `0.499`
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.
  - *Action Required:* **Macro-Oscillations detected.** The agent is overcorrecting laterally (drifting left/right). Ensure X-velocity and angle penalties are properly balanced.

#### C. Population Terminal Distribution
- `landed_centered`: 58.0%
- `landed_off_centered`: 25.0%
- `crashed`: 7.0%
- `landed_off_centered_timeout`: 6.0%
- `hover_timeout`: 2.0%
- `landed_but_slid_into_valley`: 2.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-192.639`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.647`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.480 | 0.137 | 44.2% | 🟢 Optimal |
| `vertical_penalty` | 0.399 | 0.099 | 4.9% | 🟢 Optimal |
| `leg_maintenance` | 0.485 | 0.226 | 28.6% | 🟢 Optimal |
| `orientation_penalty` | 0.273 | 0.109 | 7.1% | 🟢 Optimal |
| `velocity_stability` | 0.405 | 0.115 | 15.3% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.418` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.657`