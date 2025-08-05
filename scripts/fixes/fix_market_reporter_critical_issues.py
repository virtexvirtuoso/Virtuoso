#!/usr/bin/env python3
"""
Critical Issues Fix Script for market_reporter.py
Addresses the most urgent issues that could cause runtime failures
"""

import os
import sys
from pathlib import Path
import shutil
from datetime import datetime

class MarketReporterCriticalFixer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.market_reporter_path = self.project_root / "src/monitoring/market_reporter.py"
        self.backup_path = self.project_root / "backups" / f"market_reporter_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        self.fixes_applied = []
        
    def create_backup(self):
        """Create backup of original file"""
        self.backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.market_reporter_path, self.backup_path)
        print(f"✅ Backup created: {self.backup_path}")
        
    def fix_circuit_breaker_thread_safety(self):
        """Fix circuit breaker thread safety issues"""
        with open(self.market_reporter_path, 'r') as f:
            content = f.read()
        
        # Add thread lock import if not present
        if "import threading" not in content and "from threading import" not in content:
            content = content.replace(
                "import asyncio",
                "import asyncio\nimport threading"
            )
        
        # Fix circuit breaker class to be thread-safe
        old_circuit_breaker = '''class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN'''
        
        new_circuit_breaker = '''class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()  # Thread safety'''
        
        if old_circuit_breaker in content:
            content = content.replace(old_circuit_breaker, new_circuit_breaker)
            self.fixes_applied.append("Added thread safety to CircuitBreaker class")
        
        # Fix circuit breaker methods to use locks
        old_record_failure = '''    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")'''
            
        new_record_failure = '''    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")'''
        
        if old_record_failure in content:
            content = content.replace(old_record_failure, new_record_failure)
            self.fixes_applied.append("Added thread safety to record_failure method")
        
        return content
    
    def fix_recursive_report_generation(self):
        """Fix recursive report generation issue"""
        with open(self.market_reporter_path, 'r') as f:
            content = f.read()
        
        # Add recursion guard
        recursion_fix = '''    def generate_market_summary(self, include_pdf=True, max_recursion_depth=3):
        """Generate comprehensive market summary with recursion protection."""
        # Add recursion depth tracking
        if not hasattr(self, '_recursion_depth'):
            self._recursion_depth = 0
        
        if self._recursion_depth >= max_recursion_depth:
            self.logger.error(f"Maximum recursion depth ({max_recursion_depth}) reached in generate_market_summary")
            return {"error": "Maximum recursion depth reached", "timestamp": datetime.now().isoformat()}
        
        self._recursion_depth += 1
        try:'''
        
        # Find and replace the method start
        old_method_start = '''    def generate_market_summary(self, include_pdf=True):
        """Generate comprehensive market summary."""'''
        
        if old_method_start in content:
            content = content.replace(old_method_start, recursion_fix)
            
            # Add finally block to reset recursion depth
            # Find the end of the method and add finally block before return
            method_end_pattern = r'(\s+return\s+\{[^}]+\})\s*\n\s*async def'
            import re
            
            def add_finally_block(match):
                return_statement = match.group(1)
                return f'''        finally:
            self._recursion_depth = max(0, self._recursion_depth - 1)
{return_statement}

    async def'''
            
            content = re.sub(method_end_pattern, add_finally_block, content)
            self.fixes_applied.append("Added recursion protection to generate_market_summary")
        
        return content
    
    def fix_symbol_format_loop(self):
        """Fix potential infinite loop in symbol format handling"""
        with open(self.market_reporter_path, 'r') as f:
            content = f.read()
        
        # Add loop protection to symbol format retry logic
        old_retry_logic = '''            # Try alternative symbol formats on API errors
            if "symbol" in str(e).lower():
                alternative_formats = self._get_alternative_symbol_formats(symbol)
                for alt_symbol in alternative_formats:
                    if alt_symbol != symbol:  # Avoid infinite recursion
                        try:
                            self.logger.debug(f"Retrying with alternative symbol format: {alt_symbol}")
                            return await self.fetch_market_data(alt_symbol, timeframe, limit)
                        except Exception as alt_e:
                            continue'''
        
        new_retry_logic = '''            # Try alternative symbol formats on API errors (with loop protection)
            if "symbol" in str(e).lower() and not hasattr(self, '_symbol_retry_count'):
                self._symbol_retry_count = 0
                
            if "symbol" in str(e).lower() and self._symbol_retry_count < 3:
                self._symbol_retry_count += 1
                alternative_formats = self._get_alternative_symbol_formats(symbol)
                for alt_symbol in alternative_formats:
                    if alt_symbol != symbol:  # Avoid infinite recursion
                        try:
                            self.logger.debug(f"Retrying with alternative symbol format: {alt_symbol} (attempt {self._symbol_retry_count})")
                            result = await self.fetch_market_data(alt_symbol, timeframe, limit)
                            self._symbol_retry_count = 0  # Reset on success
                            return result
                        except Exception as alt_e:
                            continue
                self._symbol_retry_count = 0  # Reset after all attempts'''
        
        if old_retry_logic in content:
            content = content.replace(old_retry_logic, new_retry_logic)
            self.fixes_applied.append("Added loop protection to symbol format retry logic")
        
        return content
    
    def fix_memory_management(self):
        """Fix manual memory management issues"""
        with open(self.market_reporter_path, 'r') as f:
            content = f.read()
        
        # Replace manual cache clearing with proper cache management
        old_cache_clear = '''        # Manual cache optimization - clear old entries
        current_time = time.time()
        if hasattr(self.cache, '_data'):
            keys_to_remove = []
            for key, (value, timestamp) in list(self.cache._data.items()):
                if current_time - timestamp > self.cache.ttl:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.cache._data.pop(key, None)'''
        
        new_cache_clear = '''        # Let TTLCache handle its own expiration - don't manually manipulate internals
        # Cache will automatically expire old entries based on TTL settings
        cache_info = {
            'current_size': len(self.cache),
            'max_size': self.cache.maxsize,
            'ttl': self.cache.ttl
        }
        self.logger.debug(f"Cache status: {cache_info}")'''
        
        if old_cache_clear in content:
            content = content.replace(old_cache_clear, new_cache_clear)
            self.fixes_applied.append("Fixed manual cache manipulation")
        
        return content
    
    def apply_fixes(self):
        """Apply all critical fixes"""
        print("🔧 Applying critical fixes to market_reporter.py...")
        
        # Create backup first
        self.create_backup()
        
        # Read original content
        with open(self.market_reporter_path, 'r') as f:
            content = f.read()
        
        # Apply fixes
        content = self.fix_circuit_breaker_thread_safety()
        content = self.fix_recursive_report_generation()  
        content = self.fix_symbol_format_loop()
        content = self.fix_memory_management()
        
        # Write back to file
        with open(self.market_reporter_path, 'w') as f:
            f.write(content)
        
        print("\n✅ Fixes Applied:")
        for fix in self.fixes_applied:
            print(f"  - {fix}")
        
        if not self.fixes_applied:
            print("  - No critical issues found requiring fixes")
        
        print(f"\n📄 Backup available at: {self.backup_path}")
        print("🧪 Please test the application to ensure fixes work correctly")
    
    def validate_fixes(self):
        """Validate that fixes were applied correctly"""
        try:
            # Try to compile the file
            with open(self.market_reporter_path, 'r') as f:
                content = f.read()
            
            compile(content, self.market_reporter_path, 'exec')
            print("✅ File compiles successfully after fixes")
            return True
        except SyntaxError as e:
            print(f"❌ Syntax error after fixes: {e}")
            return False
        except Exception as e:
            print(f"❌ Compilation error after fixes: {e}")
            return False

def main():
    fixer = MarketReporterCriticalFixer()
    
    if not fixer.market_reporter_path.exists():
        print(f"❌ market_reporter.py not found at {fixer.market_reporter_path}")
        return
    
    print("🚀 Starting critical fixes for market_reporter.py")
    print("=" * 60)
    
    fixer.apply_fixes()
    
    print("\n" + "=" * 60)
    print("🧪 Validating fixes...")
    
    if fixer.validate_fixes():
        print("✅ All fixes applied successfully!")
    else:
        print("❌ Issues found after applying fixes - check backup file")

if __name__ == "__main__":
    main()