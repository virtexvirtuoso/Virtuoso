#!/usr/bin/env python3
"""
Fix the missing initialize method in BybitExchange class.
"""

import re
from pathlib import Path

def add_initialize_method():
    """Add the missing initialize method to BybitExchange."""
    
    bybit_file = Path("src/core/exchanges/bybit.py")
    
    if not bybit_file.exists():
        print(f"Error: {bybit_file} not found")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Check if initialize method already exists
    if "async def initialize(self)" in content:
        print("Initialize method already exists")
        return True
    
    # Find where to insert the initialize method (after __init__)
    init_pattern = r'(def __init__\(self.*?\n(?:.*?\n)*?)(    def )'
    
    initialize_method = '''
    async def initialize(self) -> bool:
        """Initialize exchange connection and verify API credentials.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing {self.exchange_id} exchange...")
            
            # Initialize session if not already done
            if not hasattr(self, 'session') or self.session is None:
                self.session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(
                        limit=100,
                        ttl_dns_cache=300,
                        ssl=False
                    ),
                    timeout=aiohttp.ClientTimeout(
                        total=30,
                        connect=5,
                        sock_read=25
                    )
                )
            
            # Initialize pybit client for authenticated endpoints
            if self.api_key and self.api_secret:
                try:
                    self.pybit_client = HTTP(
                        testnet=self.testnet,
                        api_key=self.api_key,
                        api_secret=self.api_secret
                    )
                    self.logger.info("Pybit client initialized for authenticated endpoints")
                except Exception as e:
                    self.logger.error(f"Failed to initialize pybit client: {e}")
                    self.pybit_client = None
            
            # Test connection with a simple API call
            test_result = await self.health_check()
            
            if test_result:
                self.logger.info(f"✅ {self.exchange_id} exchange initialized successfully")
                self.initialized = True
                return True
            else:
                self.logger.error(f"❌ {self.exchange_id} exchange health check failed")
                self.initialized = False
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.exchange_id}: {str(e)}")
            self.initialized = False
            return False
    
    '''
    
    # Find the best place to insert (after __init__ method)
    # Look for the end of __init__ method
    init_match = re.search(
        r'(def __init__\(self.*?\n(?:.*?\n)*?)(^\s{0,4}(?:def|async def|class)\s)',
        content,
        re.MULTILINE | re.DOTALL
    )
    
    if init_match:
        # Insert the initialize method before the next method/class
        insert_pos = init_match.end(1)
        content = content[:insert_pos] + initialize_method + content[insert_pos:]
        print("✅ Added initialize method to BybitExchange")
    else:
        print("❌ Could not find appropriate location to insert initialize method")
        # Try alternative: just add it after the last import
        import_section_end = content.rfind('\nclass BybitExchange')
        if import_section_end > 0:
            # Find the end of the __init__ method
            init_start = content.find('def __init__(self', import_section_end)
            if init_start > 0:
                # Find the next method
                next_method = content.find('\n    def ', init_start + 1)
                if next_method > 0:
                    content = content[:next_method] + '\n' + initialize_method + content[next_method:]
                    print("✅ Added initialize method using alternative approach")
    
    # Write the updated content
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    return True


def verify_fix():
    """Verify that all abstract methods are implemented."""
    
    bybit_file = Path("src/core/exchanges/bybit.py")
    
    if not bybit_file.exists():
        print(f"Error: {bybit_file} not found")
        return False
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # List of required methods
    required_methods = [
        "async def initialize",
        "async def health_check",
        "def sign",
        "def parse_trades",
        "def parse_orderbook", 
        "def parse_ticker",
        "def parse_ohlcv",
        "def parse_balance",
        "def parse_order",
        "async def connect_ws",
        "async def subscribe_ws",
        "async def get_markets",
        "async def fetch_market_data"
    ]
    
    missing = []
    for method in required_methods:
        if method not in content:
            # Some methods might be async in the file
            if method.replace("def ", "async def ") not in content and \
               method.replace("async def ", "def ") not in content:
                missing.append(method)
    
    if missing:
        print(f"❌ Still missing methods: {', '.join(missing)}")
        return False
    else:
        print("✅ All required abstract methods are implemented")
        return True


if __name__ == "__main__":
    print("Fixing BybitExchange abstract method issue...")
    
    if add_initialize_method():
        if verify_fix():
            print("\n✅ Successfully fixed BybitExchange!")
        else:
            print("\n⚠️  Initialize method added but some methods may still be missing")
    else:
        print("\n❌ Failed to fix BybitExchange")