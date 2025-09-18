#!/usr/bin/env python3
"""
Quick fix for market_interpretations validation error.
The Pydantic model expects List[str] but we're sending List[Dict].
"""

import re

def fix_signal_generator():
    """Add validation fix to signal_generator.py"""
    
    file_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/signal_generation/signal_generator.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the location after the _standardize_signal_data method
    fix_code = '''
        
        # FIX: Convert market_interpretations from List[Dict] to List[str] for Pydantic validation
        if 'market_interpretations' in standardized:
            interpretations = standardized['market_interpretations']
            if interpretations and isinstance(interpretations, list):
                fixed_interpretations = []
                for item in interpretations:
                    if isinstance(item, dict):
                        # Extract string from dict format: {'component': 'technical', 'interpretation': 'Strong signal'}
                        if 'interpretation' in item:
                            fixed_interpretations.append(item['interpretation'])
                        elif 'text' in item:
                            fixed_interpretations.append(item['text'])
                        else:
                            # Fallback: convert dict to string
                            fixed_interpretations.append(str(item.get('component', 'Unknown')) + ': ' + str(item))
                    elif isinstance(item, str):
                        # Already a string, keep as is
                        fixed_interpretations.append(item)
                    else:
                        # Convert any other type to string
                        fixed_interpretations.append(str(item))
                standardized['market_interpretations'] = fixed_interpretations
        '''
    
    # Insert the fix before the return statement in _standardize_signal_data
    pattern = r'(\s+)(return standardized)'
    replacement = f'{fix_code}\\1\\2'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Added market_interpretations validation fix to signal_generator.py")
        return True
    else:
        print("❌ Could not find insertion point for fix")
        return False

if __name__ == "__main__":
    success = fix_signal_generator()
    if success:
        print("🚀 Fix applied successfully! Deploy to VPS to resolve Discord alert issue.")
    else:
        print("💥 Fix failed. Manual intervention needed.")