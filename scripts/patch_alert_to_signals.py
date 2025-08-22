#!/usr/bin/env python3
"""
Patch AlertManager to also store signals in cache when Discord alerts are sent
This ensures alerts appear in the dashboard Signals tab
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def patch_alert_manager():
    """Add signal caching to AlertManager"""
    
    # Read the current alert_manager.py
    alert_manager_path = os.path.join(project_root, 'src/monitoring/alert_manager.py')
    
    with open(alert_manager_path, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'self._cache_signal_for_dashboard' in content:
        print("AlertManager already patched for signal caching")
        return False
    
    # Find the send_alert method and add caching after Discord send
    patch_code = '''
    async def _cache_signal_for_dashboard(self, message: str, details: Dict[str, Any]) -> None:
        """Cache signal for dashboard display"""
        try:
            # Only cache trading signals
            if details and details.get('type') in ['confluence', 'signal', 'whale_activity', 'large_aggressive_order']:
                from pymemcache.client.base import Client
                from pymemcache import serde
                import time
                
                cache = Client(('localhost', 11211), serde=serde.pickle_serde)
                
                # Get existing signals
                existing = cache.get('analysis:signals')
                if not existing or not isinstance(existing, dict):
                    existing = {'signals': [], 'count': 0, 'timestamp': int(time.time())}
                
                # Create signal from alert
                symbol = details.get('symbol', 'UNKNOWN')
                score = details.get('confluence_score', details.get('score', 50))
                
                signal = {
                    'symbol': symbol,
                    'type': details.get('type', 'alert'),
                    'direction': 'buy' if score > 60 else 'sell' if score < 40 else 'neutral',
                    'score': score,
                    'timestamp': time.time(),
                    'message': message[:200],  # Truncate message
                    'strength': 'strong' if abs(score - 50) > 20 else 'medium',
                    'components': details.get('components', {})
                }
                
                # Add to signals list (keep last 50)
                existing['signals'].insert(0, signal)
                existing['signals'] = existing['signals'][:50]
                existing['count'] = len(existing['signals'])
                existing['timestamp'] = int(time.time())
                
                # Store in cache
                cache.set('analysis:signals', existing, expire=300)
                cache.close()
                
                self.logger.debug(f"Cached signal for {symbol} in dashboard signals")
                
        except Exception as e:
            self.logger.debug(f"Failed to cache signal for dashboard: {e}")
'''
    
    # Find where to insert the method (after __init__ method)
    import_index = content.find('async def send_alert(')
    if import_index == -1:
        print("Could not find send_alert method")
        return False
    
    # Insert the new method before send_alert
    content = content[:import_index] + patch_code + "\n" + content[import_index:]
    
    # Now add the call to cache signals in send_alert method
    # Find the line after Discord webhook is sent
    discord_send_index = content.find('await self._send_discord_alert(alert)')
    if discord_send_index != -1:
        # Find the end of that line
        line_end = content.find('\n', discord_send_index)
        # Insert our cache call
        cache_call = "\n                # Cache signal for dashboard display\n                await self._cache_signal_for_dashboard(message, details)"
        content = content[:line_end] + cache_call + content[line_end:]
    
    # Write back the patched file
    with open(alert_manager_path, 'w') as f:
        f.write(content)
    
    print("Successfully patched AlertManager to cache signals for dashboard")
    return True

if __name__ == "__main__":
    if patch_alert_manager():
        print("\nPatch applied successfully!")
        print("Signals sent to Discord will now appear in the dashboard Signals tab")
    else:
        print("\nNo changes needed")