#!/usr/bin/env python3
"""
Critical Function Validator
Ensures that essential function calls exist in the codebase to prevent accidental deletion.
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple


class CriticalFunctionValidator(ast.NodeVisitor):
    """AST visitor to validate presence of critical function calls."""

    def __init__(self):
        self.function_calls = []
        self.async_function_calls = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        # Track regular calls
        if isinstance(node.func, ast.Attribute):
            call_name = f"{self._get_name(node.func.value)}.{node.func.attr}"
            self.function_calls.append({
                'call': call_name,
                'in_function': self.current_function,
                'line': node.lineno
            })
        elif isinstance(node.func, ast.Name):
            self.function_calls.append({
                'call': node.func.id,
                'in_function': self.current_function,
                'line': node.lineno
            })
        self.generic_visit(node)

    def visit_Await(self, node):
        # Track await calls
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Attribute):
                call_name = f"{self._get_name(node.value.func.value)}.{node.value.func.attr}"
                self.async_function_calls.append({
                    'call': call_name,
                    'in_function': self.current_function,
                    'line': node.value.lineno
                })
        self.generic_visit(node)

    def _get_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "unknown"


def validate_file(file_path: Path, critical_calls: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate that critical function calls exist in the file.

    Args:
        file_path: Path to Python file
        critical_calls: List of critical call specifications

    Returns:
        Tuple of (success, list of missing calls)
    """
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError as e:
        return False, [f"Syntax error in {file_path}: {e}"]

    validator = CriticalFunctionValidator()
    validator.visit(tree)

    all_calls = validator.function_calls + validator.async_function_calls

    missing = []
    for critical in critical_calls:
        call_pattern = critical['call']
        context = critical.get('context')
        found = False

        for call in all_calls:
            # Check if the call matches the pattern
            if call_pattern in call['call']:
                # If context specified, verify it matches
                if context is None or context in (call['in_function'] or ''):
                    found = True
                    break

        if not found:
            context_msg = f" in context '{context}'" if context else ""
            missing.append(f"Missing critical call: {call_pattern}{context_msg}")

    return len(missing) == 0, missing


def main():
    """Main validation routine."""

    # Define critical function calls that MUST exist
    CRITICAL_CALLS = [
        {
            'file': 'src/main.py',
            'call': 'market_monitor.start',
            'context': 'run_application',  # Must be called within run_application
            'description': 'Monitoring loop startup - CRITICAL for system operation'
        },
        {
            'file': 'src/main.py',
            'call': 'initialize_components',
            'context': 'run_application',
            'description': 'Component initialization in main application'
        },
        {
            'file': 'src/main.py',
            'call': 'create_tracked_task',
            'context': 'run_application',
            'description': 'Task tracking for monitoring loop'
        },
        {
            'file': 'src/main.py',
            'call': 'cache_warmer.start_warming_loop',
            'context': 'start_cache_warming',
            'description': 'Cache warming continuous background loop - prevents stale cache data'
        },
        {
            'file': 'src/main.py',
            'call': 'cache_warmer.warm_all_caches',
            'context': 'start_cache_warming',
            'description': 'Initial cache warming on startup'
        }
    ]

    project_root = Path(__file__).parent.parent
    print("🔍 Validating Critical Function Calls...")
    print(f"📁 Project root: {project_root}\n")

    all_passed = True

    for critical_spec in CRITICAL_CALLS:
        file_path = project_root / critical_spec['file']

        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            all_passed = False
            continue

        print(f"Checking {critical_spec['file']}:")
        print(f"  Looking for: {critical_spec['call']}")
        if critical_spec.get('context'):
            print(f"  Context: {critical_spec['context']}")
        print(f"  Purpose: {critical_spec['description']}")

        success, missing = validate_file(file_path, [critical_spec])

        if success:
            print("  ✅ FOUND\n")
        else:
            print("  ❌ MISSING!")
            for msg in missing:
                print(f"     {msg}")
            print()
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All critical function calls are present")
        print("=" * 70)
        return 0
    else:
        print("❌ VALIDATION FAILED - Missing critical function calls!")
        print("=" * 70)
        print("\n⚠️  WARNING: Deploying this code may break the system!")
        print("Please restore missing function calls before deployment.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
