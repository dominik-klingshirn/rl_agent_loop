**TARGET SYSTEM:** LunarLander-v3
**CURRENT TASK:** Implement Reward Function Update

Please implement the requested mathematical updates into the current reward function.

### [CURRENT REWARD IMPLEMENTATION]

This is the baseline code you are modifying.

```python
{current_reward_code}

```

### [NEW MATHEMATICAL INSTRUCTIONS]

These are the explicit mathematical updates you must integrate into the code above.
{coder_payload_from_dispatcher}

**EXECUTION CHECKLIST — complete in this order before writing any code:**
1. Apply each DELETE: remove the key and every variable used only by it.
2. Apply each MODIFY: keep the key, replace its computation.
3. Apply each ADD with the exact key, using the specified Scaling & Constraints.
4. Every other key: unchanged.
5. Delete unused variables; never add them to `components`.
6. Check the `components` dict: no entry is a sum of other entries in the dict.

**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`.
