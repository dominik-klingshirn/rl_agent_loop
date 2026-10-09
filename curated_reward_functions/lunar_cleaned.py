import numpy as np

def _compute_shaping(obs: np.ndarray) -> float:
    x, y, vx, vy, angle, _, left_leg, right_leg = obs
    
    return (
        -100.0 * np.sqrt(x**2 + y**2)
        - 100.0 * np.sqrt(vx**2 + vy**2)
        - 100.0 * abs(angle)
        + 10.0 * left_leg
        + 10.0 * right_leg
    )

def calculate_reward(obs: np.ndarray, info: dict) -> tuple[float, dict[str, float]]:
    """
    Args:
        obs: Current observation [x, y, vx, vy, angle, v_ang, leg1, leg2]
        info: {'prev_obs': prev_obs, 'action': action_idx, 'terminal_observation': term_obs, 'current_step': curr_step}
    
    Returns:
        total_reward (float): The sum of all shaping components for this step.
        components (dict): Granular breakdown of the reward components.
    """
    prev_obs = info.get("prev_obs")
    action = info.get("action")
    
    if prev_obs is not None:
        curr_shaping = _compute_shaping(obs)
        prev_shaping = _compute_shaping(prev_obs)
        shaping_delta = curr_shaping - prev_shaping
    else:
        shaping_delta = 0.0
        
    main_engine_penalty = -0.30 if action == 2 else 0.0
    side_engine_penalty = -0.03 if action in [1, 3] else 0.0
    
    total_shaped_reward = shaping_delta + main_engine_penalty + side_engine_penalty
    
    components = {
        "shaping_delta": float(shaping_delta),
        "main_engine_penalty": float(main_engine_penalty),
        "side_engine_penalty": float(side_engine_penalty)
    }
    
    return float(total_shaped_reward), components