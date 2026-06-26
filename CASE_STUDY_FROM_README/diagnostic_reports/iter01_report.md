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