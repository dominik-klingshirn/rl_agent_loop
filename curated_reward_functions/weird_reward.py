"""
weird_reward.py

Intentionally pathological reward for LunarLander-v3 to produce
odd behaviors (hovering high, spinning, zig-zagging, etc.).

Contract:
    def reward_fn(obs, action, obs, terminated) -> (float, dict)

Compute a deliberately 'weird' LunarLander reward.

Design goals:
- Encourage hovering HIGH above the pad (y large and positive).
- Reward spinning (large |angle| and |angular_velocity|).
- Reward horizontal wandering (being far from center in x AND changing x).
- Mildly penalize actually landing (legs down near center).
- Light reward for taking side actions to induce zig-zag motion.
"""

import numpy as np
from typing import Dict, Tuple


def calculate_reward(obs: np.ndarray, info) -> Tuple[float, Dict[str, float]]:
    """
    Args:
        obs: Current observation [x, y, vx, vy, angle, v_ang, leg1, leg2]
        info: {'prev_obs': prev_obs, 'action': action_idx, 'terminal_observation': term_obs, 'current_step': curr_step}
    
    Returns:
        total_reward (float): The sum of all shaping components for this step.
        components (dict): Granular breakdown of the reward components.
    """
    action = info["action"]
    term_obs = info.get('terminal_observation', False)
    terminated = True if term_obs else False
    x, y, vx, vy, angle, ang_vel, leg1, leg2 = obs

    # 1. Hover HIGH above pad: reward being far above y=0 (but not too high)
    #    y in normalized units; typical landing area is y≈0.
    hover_height = np.clip(y, 0.0, 1.5)
    r_hover_high = 2.0 * hover_height  # up to +3 for staying up high

    # 2. Encourage spinning: large |angle| and |angular_velocity|
    r_spin_angle = 1.0 * np.abs(angle)          # reward tilted body
    r_spin_rate = 0.5 * np.abs(ang_vel)         # reward high angular velocity

    # 3. Encourage horizontal wandering:
    #    - Being far from center in |x|
    #    - Having high |vx|
    r_wander_pos = 1.5 * np.abs(x)              # like exploring left/right
    r_wander_vel = 0.5 * np.abs(vx)             # encourage lateral velocity

    # 4. Reward side thrusters more than main engine:
    #    - main engine: small cost
    #    - side engines: small bonus
    if action == 2:          # main engine
        r_actions = -0.1
    elif action in (1, 3):   # side engines
        r_actions = +0.2
    else:                    # no-op
        r_actions = 0.0

    # 5. Penalize "boring" successful landings a bit:
    legs_down = (leg1 > 0.5) and (leg2 > 0.5)
    near_center = np.abs(x) < 0.2 and np.abs(angle) < 0.2 and y < 0.3
    if terminated and legs_down and near_center:
        r_anti_land = -5.0   # discourage nice centered touchdown
    else:
        r_anti_land = 0.0

    # 6. Very mild survival bonus (so episodes can last long enough):
    r_survival = 0.1 * (0.0 if terminated else 1.0)

    components = {
        "hover_high": float(r_hover_high),
        "spin_angle": float(r_spin_angle),
        "spin_rate": float(r_spin_rate),
        "wander_position": float(r_wander_pos),
        "wander_velocity": float(r_wander_vel),
        "action_preference": float(r_actions),
        "anti_landing": float(r_anti_land),
        "survival": float(r_survival),
    }

    total_reward = float(sum(components.values()))
    return total_reward, components
