"""
wild_oscillation_reward.py

Reward function designed to produce extreme horizontal oscillation:
- Massive rewards for large |x| deviations AND high |vx|
- Bonus for rapid direction changes (zig-zag pattern)
- Penalties for staying near center or slow horizontal motion
- Mild survival to allow long oscillation episodes

Signature: calculate_reward(obs, info) -> (float, dict)
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
    prev_x, prev_vx = prev_obs[0], prev_obs[2]
    action = info.get('action', 0)
    term_obs = info.get('terminal_observation', obs)

    position_deviation = abs(x)
    r_position = 8.0 * np.clip(position_deviation / 1.0, 0, 1.5)
    
    r_center_penalty = -10.0 if abs(x) < 0.1 else 0.0
    
    horiz_speed = abs(vx)
    r_horiz_speed = 3.0 * np.clip(horiz_speed / 2.0, 0, 1.0)
    
    r_slow_penalty = -2.0 if abs(vx) < 0.3 else 0.0

    vx_sign_change = (np.sign(vx) != np.sign(prev_vx)) and (abs(vx) > 0.5)
    r_zigzag = 5.0 if vx_sign_change else 0.0

    dvx = abs(vx - prev_vx)
    r_accel_change = 1.5 * np.clip(dvx / 1.5, 0, 1.0)
    
    if action == 1 or action == 3:
        r_action_bonus = 1.0
    elif action == 2:
        r_action_bonus = -0.5
    else:
        r_action_bonus = -0.2

    r_survival = 0.05 

    legs_penalty = -3.0 * (leg1 + leg2)

    r_vertical = -0.5 * abs(vy - (-0.2))
    
    components = {
        "position_deviation": float(r_position),
        "center_penalty": float(r_center_penalty),
        "horizontal_speed": float(r_horiz_speed),
        "slow_penalty": float(r_slow_penalty),
        "zigzag_bonus": float(r_zigzag),
        "accel_change": float(r_accel_change),
        "action_bonus": float(r_action_bonus),
        "survival": float(r_survival),
        "legs_penalty": float(legs_penalty),
        "vertical_bias": float(r_vertical),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
