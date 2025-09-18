#!/usr/bin/env python3
"""
Fix OHLCV cache connections between components.
This script ensures signal_generator has access to cached OHLCV data.
"""

import os
import sys

def fix_monitor_initialization():
    """Update monitor.py to properly connect market_data_manager to signal_generator"""
    
    monitor_file = "/home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py"
    
    # Read the current monitor.py
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Find the signal_generator initialization section
    fix_needed = False
    
    # Check if we need to add the connection after signal_generator is resolved
    if "self.signal_generator = await self._di_container.get_service(SignalGenerator)" in content:
        if "# Connect market_data_manager to signal_generator for OHLCV cache access" not in content:
            fix_needed = True
            
            # Add the connection code after signal_generator is resolved
            search_str = """                    self.signal_generator = await self._di_container.get_service(SignalGenerator)
                    self.logger.info("✅ SignalGenerator resolved from DI container")"""
            
            replace_str = """                    self.signal_generator = await self._di_container.get_service(SignalGenerator)
                    self.logger.info("✅ SignalGenerator resolved from DI container")
                    
                    # Connect market_data_manager to signal_generator for OHLCV cache access
                    if self.market_data_manager and self.signal_generator:
                        self.signal_generator.market_data_manager = self.market_data_manager
                        self.signal_generator.monitor = self
                        self.logger.info("✅ Connected market_data_manager and monitor to signal_generator for OHLCV cache access")"""
            
            content = content.replace(search_str, replace_str)
            
            print("✅ Added connection code to monitor.py after DI resolution")
    
    # Also update where signal_generator is used from constructor parameter
    if "self.signal_generator = signal_generator" in content:
        # Add connection code after assignment from parameter
        search_str2 = "        self.signal_generator = signal_generator"
        
        if "# Connect market_data_manager if signal_generator provided" not in content:
            fix_needed = True
            replace_str2 = """        self.signal_generator = signal_generator
        
        # Connect market_data_manager if signal_generator provided
        if self.signal_generator and hasattr(self, 'market_data_manager'):
            if self.market_data_manager:
                self.signal_generator.market_data_manager = self.market_data_manager
                self.signal_generator.monitor = self"""
            
            content = content.replace(search_str2, replace_str2)
            print("✅ Added connection code to monitor.__init__ for passed signal_generator")
    
    # Also ensure market_data_manager is connected after it's resolved
    if "self.market_data_manager = await self._di_container.get_service(MarketDataManager)" in content:
        search_str3 = """                    self.market_data_manager = await self._di_container.get_service(MarketDataManager)
                    self.logger.info("✅ MarketDataManager resolved from DI container")"""
        
        if "# Connect to signal_generator if available" not in content:
            fix_needed = True
            replace_str3 = """                    self.market_data_manager = await self._di_container.get_service(MarketDataManager)
                    self.logger.info("✅ MarketDataManager resolved from DI container")
                    
                    # Connect to signal_generator if available
                    if self.signal_generator and self.market_data_manager:
                        self.signal_generator.market_data_manager = self.market_data_manager
                        self.signal_generator.monitor = self
                        self.logger.info("✅ Connected market_data_manager to existing signal_generator")"""
            
            content = content.replace(search_str3, replace_str3)
            print("✅ Added connection code after MarketDataManager resolution")
    
    if fix_needed:
        # Write the updated content
        with open(monitor_file, 'w') as f:
            f.write(content)
        
        print("✅ Successfully updated monitor.py with OHLCV cache connections")
        return True
    else:
        print("ℹ️  Monitor.py already has the necessary connections")
        return False

def main():
    """Main function to fix OHLCV cache connections"""
    
    print("🔧 Fixing OHLCV cache connections on VPS...")
    
    # Check if we're on the VPS
    if not os.path.exists("/home/linuxuser/trading/Virtuoso_ccxt"):
        print("❌ This script must be run on the VPS")
        sys.exit(1)
    
    # Fix the monitor initialization
    if fix_monitor_initialization():
        print("\n✅ All fixes applied successfully!")
        print("\nPlease restart the service:")
        print("  sudo systemctl restart virtuoso-trading.service")
        print("\nThen monitor logs:")
        print("  sudo journalctl -u virtuoso-trading.service -f | grep -E 'Connected.*signal_generator|OHLCV.*cache'")
    else:
        print("\n✅ No changes needed - connections already in place")

if __name__ == "__main__":
    main()