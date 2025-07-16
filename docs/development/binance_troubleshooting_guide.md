# Binance Integration Troubleshooting Guide for Junior Developers

This guide helps you solve common issues when implementing Binance integration in the Virtuoso trading system.

## Quick Diagnostic Checklist

Before diving into specific issues, run this quick diagnostic:

```python
# diagnostic_check.py - Run this to check your setup
import sys
import os
import yaml
from pathlib import Path

def run_diagnostics():
    """Run basic diagnostic checks."""
    print("🔍 Running Binance Integration Diagnostics...")
    print("=" * 50)
    
    issues = []
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 11):
        issues.append(f"❌ Python version {python_version.major}.{python_version.minor} is too old (need 3.11+)")
    else:
        print(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check required packages
    required_packages = ['ccxt', 'aiohttp', 'pandas', 'numpy', 'yaml']
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            issues.append(f"❌ Missing package: {package}")
    
    # Check file structure
    required_files = [
        'config/config.yaml',
        'src/core/exchanges/base.py',
        'src/core/exchanges/ccxt_exchange.py',
        'src/core/exchanges/factory.py'
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            issues.append(f"❌ Missing file: {file_path}")
    
    # Check config.yaml structure
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        if 'exchanges' in config:
            print("✅ exchanges section found in config.yaml")
            if 'binance' in config['exchanges']:
                print("✅ binance section found in config.yaml")
            else:
                issues.append("❌ binance section not found in exchanges config")
        else:
            issues.append("❌ exchanges section not found in config.yaml")
    except Exception as e:
        issues.append(f"❌ Error reading config.yaml: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n📋 See troubleshooting guide below for solutions.")
        return False
    else:
        print("✅ All diagnostic checks passed!")
        print("🚀 Your environment is ready for Binance integration.")
        return True

if __name__ == "__main__":
    run_diagnostics()
```

Run this first:
```bash
python diagnostic_check.py
```

---

## Common Issues and Solutions

### 1. Import and Module Issues

#### Issue: `ImportError: No module named 'ccxt'`
```python
# Error you might see:
ModuleNotFoundError: No module named 'ccxt'
```

**Solutions:**
```bash
# Solution 1: Install ccxt
pip install ccxt

# Solution 2: If using virtual environment
pip install --upgrade pip
pip install ccxt

# Solution 3: If pip doesn't work
python -m pip install ccxt

# Solution 4: Install specific version
pip install 'ccxt>=4.0.0'
```

**Verify installation:**
```python
import ccxt
print(f"CCXT version: {ccxt.__version__}")
print(f"Supported exchanges: {len(ccxt.exchanges)}")
print(f"Binance supported: {'binance' in ccxt.exchanges}")
```

#### Issue: `ImportError: No module named 'src.core.exchanges.binance'`
```python
# Error you might see:
ModuleNotFoundError: No module named 'src.core.exchanges.binance'
```

**Root Cause**: Python can't find your module

**Solutions:**
```bash
# Solution 1: Make sure you're in the right directory
pwd  # Should show path ending in /Virtuoso_ccxt

# Solution 2: Add to Python path temporarily
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Solution 3: Install in development mode
pip install -e .

# Solution 4: Use absolute imports in tests
# Change: from src.core.exchanges.binance import BinanceExchange
# To: from Virtuoso_ccxt.src.core.exchanges.binance import BinanceExchange
```

#### Issue: `ImportError: Cannot import name 'BinanceExchange'`
```python
# Error you might see:
ImportError: cannot import name 'BinanceExchange' from 'src.core.exchanges.binance'
```

**Root Cause**: File exists but class isn't defined correctly

**Solutions:**
1. Check that your `binance.py` file has the class:
   ```python
   # In src/core/exchanges/binance.py
   class BinanceExchange(CCXTExchange):  # Make sure this line exists
       pass
   ```

2. Check for syntax errors:
   ```bash
   python -m py_compile src/core/exchanges/binance.py
   ```

3. Check imports in the file:
   ```python
   # Make sure these imports are at the top of binance.py
   from .ccxt_exchange import CCXTExchange
   from .base import BaseExchange
   ```

### 2. Configuration Issues

#### Issue: `KeyError: 'exchanges'` or `KeyError: 'binance'`
```python
# Error you might see:
KeyError: 'exchanges'
# or
KeyError: 'binance'
```

**Root Cause**: Configuration file is missing sections

**Solutions:**
1. **Check config.yaml structure:**
   ```bash
   # View your config file
   head -50 config/config.yaml | grep -A 20 "exchanges:"
   ```

2. **Verify YAML syntax:**
   ```python
   # test_yaml.py
   import yaml
   
   try:
       with open('config/config.yaml', 'r') as f:
           config = yaml.safe_load(f)
       print("✅ YAML syntax is valid")
       print(f"Top-level keys: {list(config.keys())}")
   except yaml.YAMLError as e:
       print(f"❌ YAML syntax error: {e}")
   ```

3. **Add missing sections:**
   ```yaml
   # Add this to config/config.yaml if missing
   exchanges:
     bybit:
       # ... existing bybit config ...
     
     binance:  # Add this section
       enabled: false
       primary: false
       use_ccxt: true
   ```

#### Issue: Environment Variables Not Loading
```python
# Error you might see:
# Values like ${BINANCE_API_KEY} appear as literal strings
```

**Root Cause**: Environment variable substitution not working

**Solutions:**
1. **Check .env file exists:**
   ```bash
   ls -la .env
   # Should show .env file
   ```

2. **Verify .env file format:**
   ```bash
   # .env should look like:
   BINANCE_API_KEY=your_key_here
   BINANCE_API_SECRET=your_secret_here
   ENABLE_BINANCE_DATA=true
   ```

3. **Test environment loading:**
   ```python
   import os
   print(f"ENABLE_BINANCE_DATA: {os.getenv('ENABLE_BINANCE_DATA')}")
   print(f"BINANCE_API_KEY: {os.getenv('BINANCE_API_KEY', 'Not set')}")
   ```

4. **Load .env manually if needed:**
   ```python
   # Add to your test scripts
   from dotenv import load_dotenv
   load_dotenv()  # This loads .env file
   ```

### 3. Testing Issues

#### Issue: `pytest: command not found`
```bash
# Error you might see:
bash: pytest: command not found
```

**Solutions:**
```bash
# Solution 1: Install pytest
pip install pytest pytest-asyncio

# Solution 2: Use python -m pytest
python -m pytest tests/

# Solution 3: Check if it's installed
pip list | grep pytest
```

#### Issue: Tests hanging or timing out
```python
# Symptoms: Tests run forever or timeout
```

**Root Cause**: Async issues or infinite loops

**Solutions:**
1. **Add timeout to async tests:**
   ```python
   import pytest
   import asyncio
   
   @pytest.mark.asyncio
   @pytest.mark.timeout(30)  # 30 second timeout
   async def test_something():
       # Your test code
   ```

2. **Check for missing await keywords:**
   ```python
   # Wrong:
   result = some_async_function()
   
   # Correct:
   result = await some_async_function()
   ```

3. **Use mock objects for external calls:**
   ```python
   from unittest.mock import AsyncMock, patch
   
   @patch('src.core.exchanges.binance.BinanceExchange._test_connection')
   async def test_with_mock(mock_connection):
       mock_connection.return_value = AsyncMock()
       # Your test code
   ```

#### Issue: `AttributeError: 'BinanceExchange' object has no attribute 'ccxt'`
```python
# Error you might see:
AttributeError: 'BinanceExchange' object has no attribute 'ccxt'
```

**Root Cause**: Parent class not initialized properly

**Solutions:**
1. **Check super().__init__() call:**
   ```python
   class BinanceExchange(CCXTExchange):
       def __init__(self, config, error_handler=None):
           # Make sure this line exists:
           super().__init__(config, error_handler)
           # Your initialization code...
   ```

2. **Check if CCXTExchange initializes correctly:**
   ```python
   # Test the parent class first
   from src.core.exchanges.ccxt_exchange import CCXTExchange
   
   config = {'exchanges': {'binance': {'exchange_id': 'binance'}}}
   parent = CCXTExchange(config)
   print(f"Parent has ccxt: {hasattr(parent, 'ccxt')}")
   ```

### 4. API and Network Issues

#### Issue: `ConnectionError` or `HTTPError` when testing
```python
# Error you might see:
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='api.binance.com'...
```

**Root Cause**: Network issues or API problems

**Solutions:**
1. **Check internet connection:**
   ```bash
   ping api.binance.com
   curl -I https://api.binance.com/api/v3/ping
   ```

2. **Test with simple CCXT call:**
   ```python
   import ccxt
   
   exchange = ccxt.binance({
       'sandbox': False,  # Use testnet if needed
       'enableRateLimit': True,
   })
   
   try:
       markets = exchange.load_markets()
       print(f"✅ Connected to Binance, {len(markets)} markets available")
   except Exception as e:
       print(f"❌ Connection failed: {e}")
   ```

3. **Use testnet for testing:**
   ```python
   # Use testnet for development
   exchange = ccxt.binance({
       'sandbox': True,  # Enable testnet
       'urls': {
           'api': 'https://testnet.binance.vision',
       },
   })
   ```

#### Issue: Rate Limiting Errors (HTTP 429)
```python
# Error you might see:
ccxt.base.errors.RateLimitExceeded: binance {"code":-1003,"msg":"Way too many requests..."}
```

**Root Cause**: Making requests too quickly

**Solutions:**
1. **Enable rate limiting in CCXT:**
   ```python
   exchange = ccxt.binance({
       'enableRateLimit': True,  # Important!
       'rateLimit': 1000,        # Wait 1 second between requests
   })
   ```

2. **Add manual delays:**
   ```python
   import asyncio
   
   # Add this between API calls
   await asyncio.sleep(1)  # Wait 1 second
   ```

3. **Use your rate limiter:**
   ```python
   from src.data_acquisition.binance.rate_limiter import BinanceRateLimiter
   
   limiter = BinanceRateLimiter()
   await limiter.wait_if_needed(1)  # Wait if needed
   # Make API call
   await limiter.record_request(1)  # Record the request
   ```

### 5. Data Format Issues

#### Issue: `KeyError: 'symbol'` in market data
```python
# Error you might see:
KeyError: 'symbol'
```

**Root Cause**: Market data doesn't match expected format

**Solutions:**
1. **Add defensive checks:**
   ```python
   def validate_market_data(data):
       required_fields = ['symbol', 'timestamp', 'ticker']
       missing = [field for field in required_fields if field not in data]
       if missing:
           raise ValueError(f"Missing required fields: {missing}")
       return True
   ```

2. **Log raw API responses:**
   ```python
   # Add this to debug data issues
   import json
   
   async def fetch_market_data(self, symbol):
       raw_data = await self.ccxt.fetch_ticker(symbol)
       self.logger.debug(f"Raw ticker data: {json.dumps(raw_data, indent=2)}")
       # Process data...
   ```

3. **Use default values:**
   ```python
   # Safe data extraction
   market_data = {
       'symbol': data.get('symbol', symbol),
       'timestamp': data.get('timestamp', int(time.time() * 1000)),
       'ticker': data.get('ticker', {}),
   }
   ```

---

## Debugging Strategies

### 1. Enable Debug Logging
```python
# Add this to your test scripts
import logging
logging.basicConfig(level=logging.DEBUG)

# Or for specific modules
logging.getLogger('src.core.exchanges.binance').setLevel(logging.DEBUG)
```

### 2. Use Python Debugger
```python
# Add this line where you want to debug
import pdb; pdb.set_trace()

# Then run your code and you'll get an interactive debugger
```

### 3. Print Debugging
```python
# Strategic print statements
print(f"DEBUG: config = {config}")
print(f"DEBUG: exchange_id = {self.exchange_id}")
print(f"DEBUG: ccxt initialized = {hasattr(self, 'ccxt')}")
```

### 4. Test Individual Components
```python
# Test each piece separately
async def test_individual_components():
    # Test 1: Configuration loading
    config = load_config()
    print(f"Config loaded: {bool(config)}")
    
    # Test 2: Exchange creation
    exchange = BinanceExchange(config)
    print(f"Exchange created: {exchange.exchange_id}")
    
    # Test 3: CCXT initialization
    await exchange.initialize()
    print(f"CCXT initialized: {hasattr(exchange, 'ccxt')}")
    
    # Test 4: Simple API call
    markets = await exchange.ccxt.load_markets()
    print(f"Markets loaded: {len(markets)}")
```

---

## Getting Help

### 1. Check Log Files
```bash
# Look for error logs
find . -name "*.log" -type f -exec grep -l "ERROR\|Exception" {} \;

# Check recent logs
tail -f logs/virtuoso.log
```

### 2. Use Verbose Testing
```bash
# Run tests with maximum verbosity
python -m pytest tests/test_binance_basic.py -v -s --tb=long

# Run with coverage to see what code is executed
python -m pytest tests/ --cov=src.core.exchanges.binance --cov-report=html
```

### 3. Create Minimal Reproduction
```python
# Create the smallest possible script that shows the problem
# minimal_repro.py
import asyncio
from src.core.exchanges.binance import BinanceExchange

async def main():
    config = {'exchanges': {'binance': {'enabled': True}}}
    exchange = BinanceExchange(config)
    print(f"Exchange ID: {exchange.exchange_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Check Dependencies
```bash
# Show all installed packages and versions
pip freeze

# Check for conflicts
pip check

# Update everything (use with caution)
pip install --upgrade -r requirements.txt
```

---

## Prevention Tips

### 1. Always Use Version Control
```bash
# Before making changes
git status
git add .
git commit -m "Working state before Binance changes"

# Create a branch for your work
git checkout -b feature/binance-integration
```

### 2. Test Early and Often
```bash
# Run tests after each small change
python -m pytest tests/test_binance_basic.py

# Test configuration changes immediately
python test_config.py
```

### 3. Use Type Hints
```python
# Makes debugging easier
from typing import Dict, Any, Optional

def process_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Implementation
    pass
```

### 4. Document Your Changes
```python
# Add comments explaining non-obvious code
class BinanceExchange(CCXTExchange):
    def __init__(self, config: Dict[str, Any]):
        # Call parent first to set up CCXT infrastructure
        super().__init__(config)
        
        # Binance-specific rate limiting setup
        self.rate_limiter = BinanceRateLimiter(config)
```

Remember: **It's normal to encounter issues!** Programming is problem-solving, and each error teaches you something about the system. Take breaks when frustrated, and don't hesitate to ask for help when you're stuck. 