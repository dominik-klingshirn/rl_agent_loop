import ast
import numpy as np
from typing import Tuple, Optional, Dict, Any

class CodeValidator:
    def __init__(self, code: str):
        self.code = code
        self.tree: Optional[ast.AST] = None
        self.error_message: Optional[str] = None
        
        # Security: Whitelist allowed libraries
        self.ALLOWED_IMPORTS = {'math', 'numpy', 'np', 'gym', 'gymnasium', 'typing'}
        self.FORBIDDEN_FUNCS = {'eval', 'exec', 'open', 'input', 'system', 'subprocess'}
        self.FORBIDDEN_MODULES = {'os', 'sys', 'shutil', 'requests', 'socket'}

        # Build Safe Builtins for AST Scope Checking
        self.safe_builtins = {k for k in __builtins__.keys() if k not in self.FORBIDDEN_FUNCS}

        try:
            self.tree = ast.parse(code)
        except SyntaxError as e:
            self.error_message = f"Syntax Error: {e.msg} at line {e.lineno}, column {e.offset}"

    def validate(self) -> Tuple[bool, str]:
        """
        Main validation entry point. 
        Returns (is_valid: bool, feedback_or_code: str)
        """
        # 1. Syntax Check
        if self.tree is None:
            return False, self.error_message
        
        # 2. Static Security Check
        security_checker = BlacklistChecker(self.FORBIDDEN_FUNCS, self.FORBIDDEN_MODULES, self.ALLOWED_IMPORTS)
        security_checker.visit(self.tree)
        if security_checker.violations:
            return False, "Security Violation: " + ", ".join(security_checker.violations)

        # 3. Static Scope Check (Helper Function Forward Reference Catch)
        scope_checker = ScopeChecker(self.safe_builtins)
        scope_checker.visit(self.tree)
        if scope_checker.violations:
            missing = ", ".join(scope_checker.violations)
            return False, f"Scope Error: The following helper functions are called but never defined in the module: {missing}"
        
        # 4. Execution, Signature, & Boundary Stress Testing
        try:
            # Create a restricted execution environment
            safe_globals = {
                'np': np,
                'numpy': np,
                'math': __import__('math'),
                '__builtins__': {k: v for k, v in __builtins__.items() if k in self.safe_builtins}
            }
            local_namespace = {}
            
            # Execute the code to define the function in memory
            exec(self.code, safe_globals, local_namespace)
            
            if 'calculate_reward' not in local_namespace:
                return False, "Function 'calculate_reward' not found. You must name the function exactly 'calculate_reward'."
            
            calc_func = local_namespace['calculate_reward']
            
            # --- STRESS TEST SUITE ---
            # LunarLander obs array structure: [x, y, vx, vy, angle, v_ang, leg1, leg2]
            test_states = {
                "Zero State": np.zeros(8, dtype=np.float32),
                "Freefall": np.array([0.0, 1.0, 0.0, -5.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32),
                "Max Spin": np.array([0.0, 0.5, 0.0, -1.0, np.pi, 5.0, 0.0, 0.0], dtype=np.float32),
                "Hard Impact": np.array([0.0, 0.0, 2.0, -4.0, 0.5, 1.0, 1.0, 0.0], dtype=np.float32),
                "Perfect Landed": np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0], dtype=np.float32),
                "Out of Bounds": np.array([1.5, 1.5, 0.0, 0.0, -np.pi, -5.0, 0.0, 0.0], dtype=np.float32)
            }

            for action in range(4):
                for state_name, obs in test_states.items():
                    dummy_info = {
                        'prev_obs': obs, # Using current obs as prev_obs for structural testing
                        'action': action,
                        'current_step': 10
                    }
                    
                    # Test Execution for this boundary
                    result = calc_func(obs, dummy_info)
                    
                    # Strict Signature Validation (Checked on every pass to ensure conditional logic doesn't break signature)
                    if not isinstance(result, tuple) or len(result) != 2:
                        return False, f"Function must return a Tuple of length 2. Failed on boundary state: {state_name}."
                    
                    total_reward, components = result
                    
                    if not isinstance(total_reward, (float, int, np.floating, np.integer)):
                        return False, f"First return value must be numeric. Failed on boundary state: {state_name}."
                    
                    if not isinstance(components, dict) or len(components) == 0:
                        return False, f"Second return value must be a populated dictionary. Failed on boundary state: {state_name}."
                    
                    for k, v in components.items():
                        if not isinstance(k, str):
                            return False, f"Component dict keys must be strings. Failed on boundary state: {state_name} for key {k}."
                        if not isinstance(v, (float, int, np.floating, np.integer)):
                            return False, f"Component dict values must be numeric. Failed on boundary state: {state_name} for key '{k}'."

        except ZeroDivisionError:
             return False, f"Mathematical Error: Division by zero detected during '{state_name}' boundary test. Ensure all denominators are guarded (e.g., + 1e-8)."
        except Exception as e:
            return False, f"Runtime Execution Error during '{state_name}' boundary test: {type(e).__name__}: {str(e)}"
            
        # If it passes syntax, security, scope, and all boundary tests, it is safe to write to disk.
        return True, self.code

# =========================================================================
# AST UTILITIES
# =========================================================================
class BlacklistChecker(ast.NodeVisitor):
    def __init__(self, forbidden_funcs, forbidden_modules, allowed_imports):
        self.forbidden_funcs = forbidden_funcs
        self.forbidden_modules = forbidden_modules
        self.allowed_imports = allowed_imports
        self.violations = []
    
    def visit_Import(self, node):
        for alias in node.names:
            base = alias.name.split('.')[0]
            if base in self.forbidden_modules or base not in self.allowed_imports:
                self.violations.append(f"import '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base = node.module.split('.')[0]
            if base in self.forbidden_modules or base not in self.allowed_imports:
                self.violations.append(f"from '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.forbidden_funcs:
            self.violations.append(f"function '{node.func.id}()'")
        self.generic_visit(node)


class ScopeChecker(ast.NodeVisitor):
    """
    A two-pass AST visitor to ensure any standalone function called 
    (e.g., `helper_func()`) is actually defined in the module or is a safe built-in.
    """
    def __init__(self, safe_builtins):
        self.defined_functions = set()
        self.safe_builtins = safe_builtins
        self.violations = set()

    def visit_Module(self, node):
        # Pass 1: Collect all defined functions in the file
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.defined_functions.add(child.name)
        # Pass 2: Visit all nodes to check function calls
        self.generic_visit(node)

    def visit_Call(self, node):
        # We only check bare function calls (like `abs()` or `helper()`). 
        # Method calls like `np.sum()` are Attribute nodes, handled safely by execution limits.
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name not in self.safe_builtins and func_name not in self.defined_functions:
                self.violations.add(func_name)
        self.generic_visit(node)