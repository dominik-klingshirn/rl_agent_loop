"""
spin_crash_reward.py

Reward function for classic PPO failure mode: SPINNING → CRASH.
- Rewards high angular velocity at ALL costs
- Ignores position/legs entirely  
- Small survival bonus
- Produces uncontrollable spinning → inevitable crash

Result: Agent learns to spin wildly, then crashes spectacularly.
Perfect test for terminal_status='crashed' + high spin_rate detection.
"""

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
    
    spin_speed = abs(v_ang)
    r_spin_speed = 10.0 * np.clip(spin_speed / 3.0, 0, 2.0)
    
    r_spin_angle = 4.0 * np.abs(angle)
    
    d_angle = abs(angle - prev_angle)
    r_spin_accel = 2.0 * np.clip(d_angle / np.pi, 0, 1.0)
    
    v_ang_sign_flip = (np.sign(v_ang) != np.sign(prev_v_ang)) and abs(v_ang) > 1.0
    r_spin_flip = 8.0 if v_ang_sign_flip else 0.0
    
    if action == 0:
        r_action = -1.0
    else:
        r_action = 0.5
    
    r_legs_penalty = -2.0 * (leg1 + leg2)
    
    r_survival = 0.08
    
    r_vertical = -0.3 * abs(vy)
    
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
