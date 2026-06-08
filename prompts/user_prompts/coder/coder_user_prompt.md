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
1. Read the deletion list. For each named component: mark its variable, its `components` dict entry, and its section comment for removal.
2. Confirm every component not on the deletion list and not redefined in Code Additions is preserved with its exact variable name, dict key, and computation unchanged.
3. Implement the Code Additions using the specified Scaling & Constraints.
4. Check the `components` dict: verify no entry is a derived combination (sum or product) of other entries already in the dict.

**ACTION REQUIRED:**
Write the complete, updated Python script containing `calculate_reward(obs, info)`.
