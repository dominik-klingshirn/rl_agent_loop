### 1. Optimization Dynamics & Critic Health
**Status:** 🟡 **HIGHLY SENSITIVE TO INITIALIZATION**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `4.8840`  *(lower = more reproducible)*
  - *Diagnosis:* Pre-convergence regime — reproducibility undefined.
- **Within-Seed Terminal Stationarity (CV):** `0.9500`  *(lower = more settled)*
  - *Diagnosis:* The optimization is still churning inside the final training quartile. The converged policy is non-stationary and may not retain.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.068`
  - *Diagnosis:* The learning curves are completely uncorrelated across seeds. The reward function has created a jagged landscape with multiple competing local minima.
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `64.0%`

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.055`
- **Actuator Chatter Rate:** `0.498`
  - *Diagnosis:* **High Kinematic Sensitivity.** The physical descent strategy (efficiency/chattering) changes wildly depending on the random seed.
  - *Action Required:* **Severe Actuator Chattering detected.** The agent is rapidly vibrating opposing thrusters. The reward gradient near the decision boundary is too jagged. Consider smoothing penalties or adding a minor action-continuity reward.

#### C. Population Terminal Distribution
- `landed_centered`: 35.0%
- `crashed`: 24.0%
- `landed_off_centered`: 19.0%
- `out_of_bounds`: 11.0%
- `landed_but_slid_into_valley`: 8.0%
- `landed_off_centered_timeout`: 2.0%
- `hover_timeout`: 1.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `-80.991`  *(ground truth)*
- **Objective Alignment ($\rho$):** `0.357`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
This table includes Mutual Information (MI) alongside ρ to surface non-linear dependencies that linear correlation misses.
| Reward Component | ρ w/ Success | MI w/ Success | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---:|:---|
| `ground_level` | 0.102 | 0.020 | 6.2% | ⚪ Neutral/Noisy |
| `vertical_penalty` | 0.034 | 0.032 | 17.5% | ⚪ Neutral/Noisy |
| `leg_maintenance` | 0.185 | 0.176 | 7.8% | ⚪ Neutral/Noisy |
| `orientation_penalty` | 0.224 | 0.121 | 6.2% | 🟢 Optimal |
| `velocity_stability` | 0.336 | 0.086 | 62.4% | 🟢 Optimal |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `1.806` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.741`
  - *Diagnosis:* The policy is highly fragile. Even with fixed network weights, the agent's performance swings wildly depending on environment initialization.