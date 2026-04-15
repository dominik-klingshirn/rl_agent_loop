"""
vertical_bounce_reward.py

Failure mode: VERTICAL BOUNCING (up/down oscillation near pad).
- Rewards rapid vy sign changes (bouncing motion)
- Rewards y oscillation around pad level (y≈0)
- Penalizes smooth descent or stable hovering
- Side-effect: ignores horizontal control

Produces lander that bounces up/down like a pogo stick,
never actually landing → perfect hover/crash diagnostic test.
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
    prev_y, prev_vy = prev_obs[1], prev_obs[3]
    action = info.get('action', 0)
    
    # === 1. VERTICAL POSITION OSCILLATION (bounce near pad y≈0) ===
    # Reward crossing y=0 repeatedly (oscillation around pad)
    y_deviation = abs(y)
    near_pad = y_deviation < 0.4  # Near landing zone
    r_y_oscillation = 6.0 if near_pad else -1.0
    
    # Bonus for being exactly at pad level
    r_pad_level = 3.0 * np.exp(-y_deviation**2 / 0.05)  # Gaussian peak at y=0
    
    # === 2. VERTICAL VELOCITY SIGN CHANGES (rapid up/down) ===
    vy_sign_change = (np.sign(vy) != np.sign(prev_vy)) and abs(vy) > 0.5
    r_vy_flip = 8.0 if vy_sign_change else 0.0
    
    # Reward HIGH |vy| near pad (fast bounces)
    bounce_speed = abs(vy)
    r_bounce_speed = 4.0 * np.clip(bounce_speed / 2.0, 0, 1.0) * near_pad
    
    # === 3. MAIN ENGINE PREFERENCE (vertical bouncing needs up-thrust) ===
    if action == 2:  # main engine (vertical thrust)
        r_action = 1.5
    else:
        r_action = -0.8  # Side engines disrupt vertical focus
    
    # === 4. PENALIZE STABLE HOVERING (must bounce!) ===
    stable_hover = abs(vy) < 0.2 and abs(y) < 0.3
    r_anti_hover = -6.0 if stable_hover else 0.0
    
    # === 5. PENALIZE LANDING (legs down = failure) ===
    legs_penalty = -4.0 * (leg1 + leg2)  # Hate touching down
    
    # === 6. IGNORE HORIZONTAL (don't care about x/vx) ===
    r_horizontal_ignore = 0.0  # No x-position or vx rewards
    
    # === 7. MILD SURVIVAL + UPRIGHT ===
    r_survival = 0.1
    r_upright = -0.5 * abs(angle)  # Mild upright preference
    
    components = {
        "y_oscillation": float(r_y_oscillation),
        "pad_level_bonus": float(r_pad_level),
        "vy_sign_flip": float(r_vy_flip),
        "bounce_speed": float(r_bounce_speed),
        "main_engine_bonus": float(r_action),
        "anti_hover_penalty": float(r_anti_hover),
        "legs_penalty": float(legs_penalty),
        "survival": float(r_survival),
        "upright_bonus": float(r_upright),
    }
    
    total_reward = float(sum(components.values()))
    return total_reward, components
