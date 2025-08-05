#!/usr/bin/env python3
"""
Comprehensive fix for OI showing as 0.0 in sentiment data.

The issue: Market data manager gets OI from cache, but the cache
has the wrong structure or defaults.
"""

import re

def create_comprehensive_fix():
    """Create a fix that ensures OI data flows correctly."""
    
    # Read the market data manager
    mdm_path = 'src/core/market/market_data_manager.py'
    
    with open(mdm_path, 'r') as f:
        content = f.read()
    
    # Find the sentiment assembly section (around line 1705)
    # We need to fix where it gets OI from the cache
    
    # Pattern to find the sentiment assembly
    pattern = r"(for key in \['funding_rate', 'liquidations', 'market_mood', 'risk', 'open_interest'\]:.*?\n\s+if key in self\.data_cache\[symbol\]:.*?\n\s+sentiment\[key\] = self\.data_cache\[symbol\]\[key\])"
    
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("Could not find the sentiment assembly pattern")
        return False
    
    # Create the replacement that properly handles OI
    replacement = """for key in ['funding_rate', 'liquidations', 'market_mood', 'risk']:
            if key in self.data_cache[symbol]:
                sentiment[key] = self.data_cache[symbol][key]
        
        # Special handling for open_interest to ensure correct structure
        if 'open_interest' in self.data_cache[symbol]:
            oi_data = self.data_cache[symbol]['open_interest']
            
            # Check if we have the full OI structure with history
            if isinstance(oi_data, dict) and 'current' in oi_data:
                # We have the full structure from market data
                sentiment['open_interest'] = {
                    'value': float(oi_data.get('current', 0)),
                    'change_24h': float(oi_data.get('current', 0)) - float(oi_data.get('previous', 0)),
                    'timestamp': int(oi_data.get('timestamp', time.time() * 1000))
                }
            elif isinstance(oi_data, dict) and 'value' in oi_data:
                # Already in sentiment format
                sentiment['open_interest'] = oi_data
            else:
                # Try to get from market_data['open_interest'] if available
                if 'open_interest' in market_data and market_data['open_interest']:
                    md_oi = market_data['open_interest']
                    if isinstance(md_oi, dict) and 'current' in md_oi:
                        sentiment['open_interest'] = {
                            'value': float(md_oi.get('current', 0)),
                            'change_24h': float(md_oi.get('current', 0)) - float(md_oi.get('previous', 0)),
                            'timestamp': int(md_oi.get('timestamp', time.time() * 1000))
                        }
                    else:
                        # Last resort - check if we have OI history
                        oi_history = self.get_open_interest_data(symbol)
                        if oi_history and isinstance(oi_history, dict):
                            if 'current' in oi_history:
                                sentiment['open_interest'] = {
                                    'value': float(oi_history.get('current', 0)),
                                    'change_24h': float(oi_history.get('current', 0)) - float(oi_history.get('previous', 0)),
                                    'timestamp': int(oi_history.get('timestamp', time.time() * 1000))
                                }
                            elif 'history' in oi_history and oi_history['history']:
                                # Extract from history
                                latest = oi_history['history'][0]
                                previous = oi_history['history'][1] if len(oi_history['history']) > 1 else latest
                                sentiment['open_interest'] = {
                                    'value': float(latest.get('value', 0)),
                                    'change_24h': float(latest.get('value', 0)) - float(previous.get('value', 0)),
                                    'timestamp': int(latest.get('timestamp', time.time() * 1000))
                                }
                            else:
                                # No valid OI data found
                                self.logger.warning(f"No valid OI data found for {symbol}")
                                sentiment['open_interest'] = {
                                    'value': 0.0,
                                    'change_24h': 0.0,
                                    'timestamp': int(time.time() * 1000)
                                }
                else:
                    # No OI data available
                    self.logger.debug(f"No open interest data in cache for {symbol}")
                    sentiment['open_interest'] = {
                        'value': 0.0,
                        'change_24h': 0.0,
                        'timestamp': int(time.time() * 1000)
                    }"""
    
    # Replace the old code with the new
    new_content = content.replace(match.group(1), replacement)
    
    # Save backup
    with open(mdm_path + '.pre_oi_comprehensive', 'w') as f:
        f.write(content)
    
    # Write the fixed version
    with open(mdm_path, 'w') as f:
        f.write(new_content)
    
    print("Applied comprehensive OI fix!")
    print("\nThe fix:")
    print("1. Checks multiple sources for OI data")
    print("2. Handles different OI data structures")
    print("3. Falls back to get_open_interest_data() if needed")
    print("4. Extracts from history if available")
    print("5. Only defaults to 0.0 if no data found anywhere")
    
    return True


if __name__ == "__main__":
    print("Applying Comprehensive OI Fix")
    print("============================\n")
    
    if create_comprehensive_fix():
        print("\nNext steps:")
        print("1. Deploy to VPS")
        print("2. Restart service")
        print("3. Monitor logs for OI data")
    else:
        print("\nFix could not be applied - manual intervention needed")