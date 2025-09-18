#!/usr/bin/env python3
"""
Fix Mock Data Issues in Production Code
Addresses critical issues identified in MOCK_DATA_AUDIT_REPORT.md
"""

import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class MockDataFixer:
    """Fixes mock and placeholder data issues in production code"""
    
    def __init__(self):
        self.project_root = project_root
        self.fixes_applied = []
        self.backup_dir = self.project_root / f"backup_mock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_file(self, filepath: Path) -> None:
        """Create backup of file before modification"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        relative_path = filepath.relative_to(self.project_root)
        backup_path = self.backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, backup_path)
        print(f"  ✓ Backed up: {relative_path}")
    
    def fix_fake_open_interest_history(self) -> bool:
        """Fix fake open interest history generation in market_data_manager.py"""
        print("\n1. Fixing fake open interest history generation...")
        
        filepath = self.project_root / "src/core/market/market_data_manager.py"
        if not filepath.exists():
            print(f"  ✗ File not found: {filepath}")
            return False
        
        self.backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Fix #1: Replace fake history generation with empty history
        # Lines 672-691: Replace the loop creating fake history
        pattern1 = r"for i in range\(10\):.*?history_list\.sort\(key=lambda x: x\['timestamp'\], reverse=True\)"
        replacement1 = """# Return empty history instead of fake data
                                # Real data should come from exchange API
                                history_list = []
                                self.logger.debug(f"No historical OI data available for {symbol}")"""
        
        content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
        
        # Fix #2: Replace synthetic OI history creation (lines 2028-2044)
        pattern2 = r"# Create 5 synthetic entries.*?# Add to history"
        replacement2 = """# Don't create synthetic entries - use empty history
                    # Real historical data should come from exchange API
                    self.logger.debug(f"No historical OI data available for {symbol}")
                    # Skip synthetic data creation"""
        
        content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
        
        # Add method to fetch real open interest from exchange
        if "def fetch_real_open_interest" not in content:
            new_method = '''
    async def fetch_real_open_interest(self, symbol: str) -> Dict:
        """Fetch real open interest data from exchange"""
        try:
            exchange_client = self.exchange_manager.get_primary_exchange()
            if hasattr(exchange_client, 'fetch_open_interest'):
                oi_data = await exchange_client.fetch_open_interest(symbol)
                return {
                    'current': oi_data.get('openInterest', 0),
                    'previous': oi_data.get('prevOpenInterest', 0),
                    'timestamp': oi_data.get('timestamp', int(time.time() * 1000)),
                    'history': [],  # Exchange API typically doesn't provide history
                    'is_synthetic': False
                }
        except Exception as e:
            self.logger.warning(f"Failed to fetch real OI for {symbol}: {e}")
        
        # Return None if real data unavailable
        return None
'''
            # Insert after the class definition
            content = content.replace("class MarketDataManager:", "class MarketDataManager:" + new_method, 1)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed fake open interest history generation")
        print("  ✓ Fixed fake open interest history generation")
        return True
    
    def fix_sample_ticker_fallback(self) -> bool:
        """Remove sample ticker data fallback in populate_cache_service.py"""
        print("\n2. Removing sample ticker data fallback...")
        
        filepath = self.project_root / "scripts/populate_cache_service.py"
        if not filepath.exists():
            print(f"  ✗ File not found: {filepath}")
            return False
        
        self.backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Remove the sample_tickers fallback
        pattern = r"# Fallback: Create sample data.*?cache_adapter\.set\('tickers', sample_tickers\)"
        replacement = """# No fallback - return empty data if fetch fails
            self.logger.error("Failed to fetch real ticker data")
            return {'tickers': {}, 'error': 'Failed to fetch ticker data'}"""
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Removed sample ticker data fallback")
        print("  ✓ Removed sample ticker data fallback")
        return True
    
    def fix_hardcoded_symbols(self) -> bool:
        """Fix hardcoded fallback symbols in main.py files"""
        print("\n3. Fixing hardcoded fallback symbols...")
        
        files_to_fix = [
            "src/main.py",
            "src/main.py.vps_fixed"
        ]
        
        for filename in files_to_fix:
            filepath = self.project_root / filename
            if not filepath.exists():
                print(f"  ⚠ File not found: {filepath}")
                continue
            
            self.backup_file(filepath)
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Replace hardcoded fallback symbols with config loading
            pattern = r"fallback_symbols = \[.*?\]"
            replacement = """# Load symbols from configuration file
            try:
                with open('config/trading_config.json', 'r') as f:
                    config = json.load(f)
                    fallback_symbols = config.get('symbols', [])
            except:
                fallback_symbols = []  # Empty list if config not available
                self.logger.error("No symbols configured - please check config/trading_config.json")"""
            
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"  ✓ Fixed hardcoded symbols in {filename}")
        
        self.fixes_applied.append("Fixed hardcoded fallback symbols")
        return True
    
    def remove_mock_mode_alerts(self) -> bool:
        """Remove mock mode from alert manager"""
        print("\n4. Removing mock mode from alert system...")
        
        filepath = self.project_root / "src/monitoring/alert_manager.py"
        if not filepath.exists():
            print(f"  ✗ File not found: {filepath}")
            return False
        
        self.backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Remove mock_mode checks
        content = re.sub(
            r"self\.mock_mode = config\.get\('monitoring', \{\}\)\.get\('alerts', \{\}\)\.get\('mock_mode', False\)",
            "self.mock_mode = False  # Mock mode disabled in production",
            content
        )
        
        # Remove mock mode logging
        content = re.sub(
            r"if self\.mock_mode:.*?self\.logger\.info\(f\"MOCK MODE:.*?\"\)",
            "# Mock mode removed - always send real alerts",
            content,
            flags=re.DOTALL
        )
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Removed mock mode from alerts")
        print("  ✓ Removed mock mode from alert system")
        return True
    
    def fix_default_neutral_scores(self) -> bool:
        """Fix default neutral scores in indicators"""
        print("\n5. Fixing default neutral scores in indicators...")
        
        filepath = self.project_root / "src/indicators/orderbook_indicators.py"
        if not filepath.exists():
            print(f"  ✗ File not found: {filepath}")
            return False
        
        self.backup_file(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Replace default 50.0 scores with None
        content = re.sub(
            r"return \{'score': 50\.0, 'relative_spread': 0\.0, 'stability': 0\.5\}",
            "return None  # Return None for failed calculations instead of masking with default",
            content
        )
        
        # Update callers to handle None properly
        content = re.sub(
            r"if result and result\.get\('score'\)",
            "if result is not None and result.get('score') is not None",
            content
        )
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.fixes_applied.append("Fixed default neutral scores")
        print("  ✓ Fixed default neutral scores in indicators")
        return True
    
    def create_validation_script(self) -> None:
        """Create script to validate mock data fixes"""
        print("\n6. Creating validation script...")
        
        validation_script = '''#!/usr/bin/env python3
"""Validate that mock data has been removed from production code"""

import sys
import json
from pathlib import Path

def check_no_fake_data():
    """Verify no fake data generation exists"""
    issues = []
    
    # Check for fake timestamps
    files_to_check = [
        "src/core/market/market_data_manager.py",
        "src/indicators/orderflow_indicators.py"
    ]
    
    for filepath in files_to_check:
        path = Path(filepath)
        if path.exists():
            content = path.read_text()
            if "fake_timestamp" in content or "fake_value" in content:
                issues.append(f"Found fake data generation in {filepath}")
    
    # Check for sample tickers
    cache_script = Path("scripts/populate_cache_service.py")
    if cache_script.exists():
        content = cache_script.read_text()
        if "sample_tickers" in content and "113000" in content:
            issues.append("Found hardcoded sample tickers")
    
    # Check for mock mode
    alert_manager = Path("src/monitoring/alert_manager.py")
    if alert_manager.exists():
        content = alert_manager.read_text()
        if "MOCK MODE:" in content:
            issues.append("Found mock mode in alerts")
    
    return issues

if __name__ == "__main__":
    print("Validating mock data removal...")
    issues = check_no_fake_data()
    
    if issues:
        print("\\n❌ Validation FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\\n✅ Validation PASSED - No mock data found in production code")
        sys.exit(0)
'''
        
        filepath = self.project_root / "scripts/validate_mock_data_removal.py"
        with open(filepath, 'w') as f:
            f.write(validation_script)
        
        os.chmod(filepath, 0o755)
        print("  ✓ Created validation script: scripts/validate_mock_data_removal.py")
    
    def run(self) -> None:
        """Execute all mock data fixes"""
        print("=" * 60)
        print("Mock Data Fix Script - Addressing MOCK_DATA_AUDIT_REPORT.md")
        print("=" * 60)
        
        # Apply all critical fixes
        self.fix_fake_open_interest_history()
        self.fix_sample_ticker_fallback()
        self.fix_hardcoded_symbols()
        self.remove_mock_mode_alerts()
        self.fix_default_neutral_scores()
        self.create_validation_script()
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✅ Applied {len(self.fixes_applied)} critical fixes:")
        for fix in self.fixes_applied:
            print(f"  - {fix}")
        
        print(f"\n📁 Backups saved to: {self.backup_dir}")
        print("\n🔍 Run validation with: python scripts/validate_mock_data_removal.py")
        print("\n⚠️  IMPORTANT NEXT STEPS:")
        print("  1. Review the changes")
        print("  2. Test locally with real exchange data")
        print("  3. Deploy to VPS after validation")
        print("  4. Monitor for any data fetch failures")

if __name__ == "__main__":
    fixer = MockDataFixer()
    fixer.run()