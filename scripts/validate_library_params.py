#!/usr/bin/env python3
"""
Validate library parameters before using them.
Prevents using non-existent parameters that might work in some versions but fail in others.
"""

import inspect
import aiohttp
import importlib
from typing import Dict, List, Set


def get_valid_parameters(class_obj) -> Set[str]:
    """Extract valid parameters for a class constructor."""
    try:
        sig = inspect.signature(class_obj.__init__)
        params = set()
        for param_name, param in sig.parameters.items():
            if param_name not in ('self', 'args', 'kwargs'):
                params.add(param_name)
        return params
    except Exception as e:
        print(f"Error inspecting {class_obj}: {e}")
        return set()


def validate_parameters(class_name: str, used_params: Dict[str, any]) -> List[str]:
    """Validate that all parameters exist in the class."""
    errors = []
    
    # Map class names to actual classes
    class_map = {
        'TCPConnector': aiohttp.TCPConnector,
        'ClientTimeout': aiohttp.ClientTimeout,
        'ClientSession': aiohttp.ClientSession,
    }
    
    if class_name not in class_map:
        errors.append(f"Unknown class: {class_name}")
        return errors
    
    valid_params = get_valid_parameters(class_map[class_name])
    
    for param in used_params:
        if param not in valid_params and param not in ('args', 'kwargs'):
            errors.append(f"Parameter '{param}' does not exist in {class_name}")
    
    return errors


def check_code_file(filepath: str):
    """Check a Python file for invalid parameters."""
    print(f"\nChecking {filepath}...")
    
    # Example checks for common aiohttp patterns
    checks = [
        {
            'pattern': 'aiohttp.TCPConnector(',
            'class': 'TCPConnector',
            'common_params': {
                'limit', 'limit_per_host', 'ttl_dns_cache', 
                'enable_cleanup_closed', 'force_close', 'keepalive_timeout',
                'ssl', 'fingerprint', 'resolver', 'family',
                'ssl_context', 'local_addr', 'happy_eyeballs_delay'
            }
        },
        {
            'pattern': 'aiohttp.ClientTimeout(',
            'class': 'ClientTimeout',
            'common_params': {
                'total', 'connect', 'sock_connect', 'sock_read'
            }
        }
    ]
    
    # This is a simplified check - in production you'd parse the AST
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        for check in checks:
            if check['pattern'] in content:
                print(f"Found {check['class']} usage")
                # In real implementation, parse actual parameters used
                
    except Exception as e:
        print(f"Error reading file: {e}")


def main():
    """Run validation checks."""
    print("=== Library Parameter Validator ===")
    print(f"aiohttp version: {aiohttp.__version__}")
    
    # Example: Validate TCPConnector parameters
    print("\n--- Valid TCPConnector Parameters ---")
    valid_params = get_valid_parameters(aiohttp.TCPConnector)
    for param in sorted(valid_params):
        print(f"  - {param}")
    
    # Example: Check invalid parameters
    print("\n--- Testing Parameter Validation ---")
    
    # This would fail:
    invalid_params = {
        'limit': 150,
        'limit_per_host': 40,
        'limit_per_host_queue': 10,  # Invalid!
        'magic_parameter': True      # Invalid!
    }
    
    errors = validate_parameters('TCPConnector', invalid_params)
    if errors:
        print("❌ Validation errors found:")
        for error in errors:
            print(f"   {error}")
    else:
        print("✅ All parameters valid")
    
    # Check actual files
    print("\n--- Checking Project Files ---")
    files_to_check = [
        'src/core/exchanges/bybit.py',
        'src/core/exchanges/binance.py',
    ]
    
    for filepath in files_to_check:
        check_code_file(filepath)


if __name__ == "__main__":
    main()