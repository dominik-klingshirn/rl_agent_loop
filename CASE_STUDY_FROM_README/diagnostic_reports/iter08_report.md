### 1. Optimization Dynamics & Critic Health
**Status:** 🟢 **CONVERGED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.0440`  *(lower = more reproducible)*
  - *Diagnosis:* Strong cross-seed consistency. The reward landscape is learnable and reproducible.
- **Within-Seed Terminal Stationarity (CV):** `0.0370`  *(lower = more settled)*
  - *Diagnosis:* Policy has settled. Final-quartile reward is stationary within each seed.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.130`
### 2. Kinematic Behavior & Physical Robustness

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
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-1806.863`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.618`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.570 | 0.205 | 29.4% | 🟢 Optimal |
| `vertical_penalty` | 0.368 | 0.135 | 3.9% | 🟢 Optimal |
| `leg_maintenance` | 0.570 | 0.293 | 23.1% | 🟢 Optimal |
| `orientation_penalty` | 0.318 | 0.132 | 7.1% | 🟢 Optimal |
| `velocity_stability` | 0.459 | 0.150 | 16.1% | 🟢 Optimal |
| `lateral_viscosity` | 0.295 | 0.095 | 1.3% | 🟢 Optimal |
| `landing_precision` | 0.264 | 0.147 | 19.2% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.466` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.595`