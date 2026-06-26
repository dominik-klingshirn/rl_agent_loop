### 1. Optimization Dynamics & Critic Health
**Status:** 🔴 **UNSTABLE/FAILED**

#### A. Cross-Seed Robustness & Terminal Stationarity
- **Cross-Seed Reproducibility (CV):** `0.3720`  *(lower = more reproducible)*
  - *Diagnosis:* Pre-convergence regime — reproducibility undefined.
- **Within-Seed Terminal Stationarity (CV):** `0.1700`  *(lower = more settled)*
  - *Diagnosis:* The optimization is still churning inside the final training quartile. The converged policy is non-stationary and may not retain.

#### B. Value Network (Critic) Integrity
- **Critic Saturation Index (CSI):** `0.00`
  - *Diagnosis:* Healthy. The Critic is accurately mapping the advantage landscape.

#### C. Optimization Landscape
- **Trajectory Isomorphism (Pairwise $\rho$):** `0.758`
### 2. Kinematic Behavior & Physical Robustness

#### A. Universal Policy Robustness
- **Population Success Rate:** `0.0%`
  - *Diagnosis:* The policy is highly stable but mathematically wrong. It consistently executes the same failure mode across all seeds.

#### B. Thermodynamic & Actuator Efficiency
- **Mean Descent Efficiency:** `0.040`
- **Actuator Chatter Rate:** `0.119`

#### C. Population Terminal Distribution
- `out_of_bounds`: 100.0%
### 3. Reward Topology & Algorithmic Credit Assignment

#### A. Global Objective Alignment (Oracle Test)
- **Global Conditional Delta** $\Delta = \mathbb{E}[R \mid \text{land}] - \mathbb{E}[R \mid \text{fail}]$: `undefined (single-class population)`  *(ground truth)*
- **Objective Alignment ($\rho$):** `-0.070`  *(narrative descriptor — point-biserial estimator)*

#### B. Component-Level Contribution (Algorithmic Credit Assignment)
This table isolates the exact mathematical impact of each component you generated.
| Reward Component | Correlation w/ Composite Viability (out_of_bounds) ($\rho$) | Relative Magnitude | Diagnostic Flag |
|:---|:---:|:---:|:---|
| `ground_level` | 0.710 | 0.4% | 🟡 **LOW MAGNITUDE** (<1% of gradient) |
| `vertical_penalty` | 0.766 | 1.9% | 🟢 Optimal |
| `orientation_penalty` | 0.529 | 1.4% | 🟢 Optimal |
| `velocity_stability` | 0.795 | 5.9% | 🟢 Optimal |
| `lateral_viscosity` | -0.269 | 0.0% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `landing_precision` | -0.314 | 0.1% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |
| `x_kill` | -0.735 | 90.3% | 🔴 **NEGATIVELY ALIGNED** — Linear gradient opposes success (ρ < -0.2). Remove or negate. |

#### C. Stochastic Policy Fragility
- **Intra-Rollout Reward CV:** `0.473` (Variance across seeds with *frozen* weights)
- **Terminal Mode Entropy:** `0.017`
  - *Diagnosis:* The stochastic policy has completely collapsed into a single pathological failure mode. The KL penalty likely prevented escape from a severe local minimum.