#!/usr/bin/env python3
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
        print("\nNext steps:")
        print("1. Deploy to VPS")
        print("2. Restart service")
        print("3. Monitor logs for 'Stored sentiment OI' messages")
