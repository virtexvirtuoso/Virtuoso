#!/usr/bin/env python3
"""
Fix the OI data structure issue where it shows as 0.0 in sentiment.

The problem flow:
1. API returns OI data correctly
2. Market data manager stores it correctly 
3. But sentiment gets {'value': 0.0, 'change_24h': 0.0}

The issue is likely in how the OI data is structured when stored in cache.
"""

import os
import re

def create_oi_structure_fix():
    """Create a fix for the OI data structure issue."""
    
    fix_content = '''
# Fix for OI data structure in market_data_manager.py

# Find this section around line 520-540 where OI is processed:
# market_data['open_interest'] = {
#     'current': current_oi,
#     'previous': previous_oi,
#     ...
# }

# And ensure it also creates the structure expected by sentiment:
# After setting market_data['open_interest'], add:

# Create sentiment-compatible structure
sentiment_oi = {
    'value': current_oi,
    'change_24h': current_oi - previous_oi if previous_oi else 0,
    'timestamp': int(time.time() * 1000)
}

# Store both structures
self.data_cache[symbol]['open_interest'] = sentiment_oi
self.data_cache[symbol]['open_interest_full'] = market_data['open_interest']

# This way sentiment gets the structure it expects
'''
    
    print(fix_content)
    
    # Now let's find the exact location to patch
    print("\n" + "="*60)
    print("FINDING EXACT PATCH LOCATION")
    print("="*60)
    
    mdm_path = 'src/core/market/market_data_manager.py'
    if os.path.exists(mdm_path):
        with open(mdm_path, 'r') as f:
            content = f.read()
        
        # Find where OI is stored in cache after processing
        pattern = r"market_data\['open_interest'\]\s*=\s*{[^}]+}"
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        if matches:
            print(f"\nFound {len(matches)} locations where OI is set in market_data")
            for i, match in enumerate(matches):
                line_num = content[:match.start()].count('\n') + 1
                print(f"\nLocation {i+1} at line {line_num}:")
                # Show some context
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(content), match.end() + 200)
                context = content[start_pos:end_pos]
                print("..." + context + "...")


def create_patch_file():
    """Create a patch file that can be applied."""
    
    patch_content = '''#!/usr/bin/env python3
"""
Patch to fix OI data structure for sentiment processing.
"""

import sys
import re

def apply_patch():
    file_path = 'src/core/market/market_data_manager.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the section where OI is stored after processing (around line 516-540)
    # Look for pattern like:
    # market_data['open_interest'] = {
    #     'current': current_oi,
    #     'previous': previous_oi,
    #     'change_24h': current_oi - previous_oi,
    #     'timestamp': timestamp
    # }
    
    # Pattern to find the OI assignment
    pattern = r"(market_data\['open_interest'\]\s*=\s*{[^}]+})"
    
    def replacement(match):
        original = match.group(1)
        # Add code after the original assignment to also store sentiment format
        addition = """
                        
                        # Also store in sentiment-compatible format
                        if symbol in self.data_cache:
                            sentiment_oi = {
                                'value': float(current_oi),
                                'change_24h': float(current_oi - previous_oi) if previous_oi else 0.0,
                                'timestamp': int(market_data['open_interest'].get('timestamp', time.time() * 1000))
                            }
                            self.data_cache[symbol]['open_interest'] = sentiment_oi
                            self.logger.debug(f"Stored sentiment OI for {symbol}: value={sentiment_oi['value']}, change={sentiment_oi['change_24h']}")"""
        
        return original + addition
    
    # Apply the patch
    modified = re.sub(pattern, replacement, content, count=1)
    
    if modified != content:
        # Backup original
        with open(file_path + '.pre_oi_patch', 'w') as f:
            f.write(content)
        
        # Write patched version
        with open(file_path, 'w') as f:
            f.write(modified)
        
        print("Patch applied successfully!")
        print("Backup saved as: " + file_path + '.pre_oi_patch')
        return True
    else:
        print("Could not find pattern to patch")
        return False

if __name__ == "__main__":
    if apply_patch():
        print("\\nNext steps:")
        print("1. Deploy to VPS")
        print("2. Restart service")
        print("3. Monitor logs for 'Stored sentiment OI' messages")
'''
    
    with open('scripts/apply_oi_patch.py', 'w') as f:
        f.write(patch_content)
    
    os.chmod('scripts/apply_oi_patch.py', 0o755)
    print("\nCreated patch file: scripts/apply_oi_patch.py")
    print("Run it to apply the OI structure fix")


if __name__ == "__main__":
    print("OI Structure Fix Analysis")
    print("========================\n")
    
    create_oi_structure_fix()
    create_patch_file()