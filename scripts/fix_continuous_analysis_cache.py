#!/usr/bin/env python3
"""
Fix Continuous Analysis Manager Cache Population
Ensures the Continuous Analysis Manager properly populates cache with market overview data
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def backup_file(filepath):
    """Create timestamped backup of file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "backups" / f"pre_continuous_analysis_fix_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    rel_path = Path(filepath).relative_to(PROJECT_ROOT)
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {rel_path}")
    return backup_dir

def fix_continuous_analysis_manager():
    """Fix the Continuous Analysis Manager cache population"""
    main_file = PROJECT_ROOT / "src/main.py"
    
    if not main_file.exists():
        print(f"❌ File not found: {main_file}")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Add error handling and logging to cache push
    old_push = '''    async def _push_to_unified_cache(self):
        """Push aggregated analysis data to the unified cache system"""
        try:
            # Initialize memcache client if needed
            if not self._memcache_client:
                import aiomcache
                self._memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)'''
    
    new_push = '''    async def _push_to_unified_cache(self):
        """Push aggregated analysis data to the unified cache system"""
        try:
            # Initialize memcache client if needed
            if not self._memcache_client:
                import aiomcache
                self._memcache_client = aiomcache.Client('localhost', 11211, pool_size=2)
                logger.info("✅ Initialized memcache client for continuous analysis")'''
    
    if old_push in content:
        content = content.replace(old_push, new_push)
        print("  ✅ Added logging for memcache initialization")
    
    # Fix 2: Add logging for successful cache operations
    old_cache_set = '''            # Push to cache
            await self._memcache_client.set(
                b'market:overview',
                json.dumps(overview_data).encode(),
                exptime=10
            )'''
    
    new_cache_set = '''            # Push to cache
            await self._memcache_client.set(
                b'market:overview',
                json.dumps(overview_data).encode(),
                exptime=30  # Increased TTL from 10 to 30 seconds
            )
            logger.info(f"✅ Pushed market overview to cache: {total_symbols} symbols, ${total_volume:,.0f} volume")'''
    
    if old_cache_set in content:
        content = content.replace(old_cache_set, new_cache_set)
        print("  ✅ Added logging for market overview cache push")
    
    # Fix 3: Add confluence scores to cache for dashboard to use
    old_end_push = '''            logger.debug(f"Pushed market analysis to cache: {total_symbols} symbols")
            
        except Exception as e:
            logger.error(f"Failed to push to unified cache: {e}")'''
    
    new_end_push = '''            # Push confluence scores for dashboard
            confluence_scores = []
            for symbol, analysis in analyses.items():
                if analysis and 'score' in analysis:
                    confluence_scores.append({
                        'symbol': symbol,
                        'score': analysis.get('score', 50),
                        'sentiment': analysis.get('sentiment', 'NEUTRAL'),
                        'price': analysis.get('price', 0),
                        'change_24h': analysis.get('change_24h', analysis.get('price_change_24h', 0)),
                        'volume_24h': analysis.get('volume_24h', 0)
                    })
            
            if confluence_scores:
                await self._memcache_client.set(
                    b'confluence:scores',
                    json.dumps(confluence_scores).encode(),
                    exptime=30
                )
                logger.info(f"✅ Pushed {len(confluence_scores)} confluence scores to cache")
            
            logger.info(f"✅ Successfully pushed market analysis to cache: {total_symbols} symbols, market regime: {market_regime}")
            
        except Exception as e:
            logger.error(f"❌ Failed to push to unified cache: {e}", exc_info=True)'''
    
    if old_end_push in content:
        content = content.replace(old_end_push, new_end_push)
        print("  ✅ Added confluence scores cache push")
    
    # Fix 4: Ensure the loop doesn't fail silently
    old_loop_error = '''            except Exception as e:
                logger.error(f"Error in continuous analysis: {e}")
                await asyncio.sleep(5)  # Wait longer on error'''
    
    new_loop_error = '''            except Exception as e:
                logger.error(f"❌ Error in continuous analysis loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait longer on error'''
    
    if old_loop_error in content:
        content = content.replace(old_loop_error, new_loop_error)
        print("  ✅ Improved error logging in analysis loop")
    
    # Fix 5: Add check for top_symbols_manager
    old_symbols_check = '''                # Get symbols to analyze
                if hasattr(app.state, 'top_symbols_manager') and app.state.top_symbols_manager:
                    symbols = await app.state.top_symbols_manager.get_top_symbols(limit=30)'''
    
    new_symbols_check = '''                # Get symbols to analyze
                if hasattr(app.state, 'top_symbols_manager') and app.state.top_symbols_manager:
                    symbols = await app.state.top_symbols_manager.get_top_symbols(limit=30)
                    logger.debug(f"🔄 Analyzing {len(symbols)} symbols")'''
    
    if old_symbols_check in content:
        content = content.replace(old_symbols_check, new_symbols_check)
        print("  ✅ Added symbols count logging")
    
    # Write the fixed content
    with open(main_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated: {main_file.name}")
    return True

def main():
    """Apply continuous analysis cache fixes"""
    print("=" * 60)
    print("🔧 CONTINUOUS ANALYSIS CACHE FIX")
    print("=" * 60)
    
    # Create backup
    print("\n📦 Creating backup...")
    backup_dir = backup_file(PROJECT_ROOT / "src/main.py")
    print(f"\n💾 Backup location: {backup_dir}")
    
    # Apply fixes
    print("\n🔧 Applying fixes...")
    fix_continuous_analysis_manager()
    
    print("\n" + "=" * 60)
    print("✅ CONTINUOUS ANALYSIS CACHE FIXES COMPLETE")
    print("=" * 60)
    
    print("\n📋 Key improvements:")
    print("  • Added logging for memcache initialization")
    print("  • Increased cache TTL from 10 to 30 seconds")
    print("  • Added confluence scores to cache")
    print("  • Improved error logging with stack traces")
    print("  • Added debug logging for symbols count")
    
    print("\n📋 Next steps:")
    print("1. Deploy to VPS: ./scripts/deploy_continuous_analysis_fix.sh")
    print("2. Monitor logs: ssh vps 'sudo journalctl -u virtuoso.service -f | grep -E \"cache|continuous\"'")
    print(f"3. To rollback: cp {backup_dir}/src/main.py {PROJECT_ROOT}/src/")

if __name__ == "__main__":
    main()