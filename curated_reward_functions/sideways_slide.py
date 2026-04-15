"""
sideways_slide_reward.py

Failure mode: SIDEWAYS SLIDING (horizontal ground sliding, never upright landing).
- Rewards legs down WHILE moving fast horizontally (vx high)
- Penalizes upright orientation (prefers tilted/sliding)
- Bonus for maintaining leg contact + lateral velocity
- Ignores vertical control (drifts into walls/crashes)

Produces lander that slides sideways on one leg like a skateboard,
never achieving stable upright landing.
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
    prev_vx, prev_legs = prev_obs[2], prev_obs[6] + prev_obs[7]
    action = info.get('action', 0)
    
    # === 1. LEG CONTACT + HORIZONTAL SLIDE (core reward) ===
    legs_contact = leg1 + leg2
    horiz_slide_speed = abs(vx)
    
    # Massive bonus for legs down AND sliding fast sideways
    sliding_legs = legs_contact * horiz_slide_speed
    r_sliding_legs = 12.0 * np.clip(sliding_legs / 2.0, 0, 1.5)  # up to +18!
    
    # === 2. PREFER TILTED ORIENTATION (discourage upright) ===
    # Reward moderate tilt (easier to slide)
    r_tilt_preference = 3.0 * np.abs(angle) * 0.5  # up to ~4.5 for π/2 tilt
    
    # Penalty for perfectly upright (stable landing pose)
    upright_penalty = -8.0 if abs(angle) < 0.05 else 0.0
    
    # === 3. HORIZONTAL DIRECTION CHANGES (slalom sliding) ===
    vx_sign_flip = (np.sign(vx) != np.sign(prev_vx)) and abs(vx) > 0.8
    r_slalom = 6.0 if vx_sign_flip else 0.0
    
    # === 4. SIDE THRUSTER LOVE (lateral control) ===
    if action in (1, 3):  # left/right thrusters
        r_action = 2.0
    elif action == 2:  # main (less useful for sliding)
        r_action = -0.5
    else:
        r_action = -1.0
    
    # === 5. GROUND LEVEL PREFERENCE (slide near y=0) ===
    near_ground = abs(y) < 0.4
    r_ground_level = 3.0 if near_ground else -1.5
    
    # === 6. PENALIZE VERTICAL MOTION (stay low) ===
    r_vertical_penalty = -2.0 * abs(vy)  # Hate up/down
    
    # === 7. SURVIVAL + LEG MAINTENANCE ===
    r_survival = 0.1
    r_leg_maintenance = 1.0 * legs_contact  # Keep at least one leg down
    
    components = {
        "sliding_legs": float(r_sliding_legs),
        "tilt_preference": float(r_tilt_preference),
        "upright_penalty": float(upright_penalty),
        "slalom_bonus": float(r_slalom),
        "side_thruster_bonus": float(r_action),
        "ground_level": float(r_ground_level),
        "vertical_penalty": float(r_vertical_penalty),
        "survival": float(r_survival),
        "leg_maintenance": float(r_leg_maintenance),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
