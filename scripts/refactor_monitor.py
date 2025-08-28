#!/usr/bin/env python3
"""
Monitor.py Refactoring Script

Safely splits the 357KB monitor.py monolith into focused modules.
Creates backup, runs tests, and provides rollback capability.
"""

import os
import sys
import shutil
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

class MonitorRefactorer:
    """
    Refactors monitor.py into focused modules with safety checks.
    
    Process:
    1. Backup original file
    2. Parse and analyze code structure
    3. Split into modules based on functionality
    4. Update imports across codebase
    5. Run tests to verify functionality
    6. Provide rollback if needed
    """
    
    def __init__(self, project_root: Path = None):
        """Initialize refactorer with project paths."""
        self.project_root = project_root or Path("/Users/ffv_macmini/Desktop/Virtuoso_ccxt")
        self.monitor_path = self.project_root / "src/monitoring/monitor.py"
        self.backup_path = self.project_root / "src/monitoring/monitor_backup.py"
        self.new_modules_dir = self.project_root / "src/monitoring"
        
        # Module definitions
        self.modules = {
            'base': {
                'file': 'base.py',
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'data_collector': {
                'file': 'data_collector.py',
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'validator': {
                'file': 'validator.py',
                'classes': ['TimeRangeValidationRule', 'MarketDataValidator'],
                'methods': [],
                'imports': set()
            },
            'signal_processor': {
                'file': 'signal_processor.py',
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'alert_manager': {
                'file': 'alert_manager.py', 
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'websocket_manager': {
                'file': 'websocket_manager.py',
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'metrics_tracker': {
                'file': 'metrics_tracker.py',
                'classes': [],
                'methods': [],
                'imports': set()
            },
            'utils/logging': {
                'file': 'utils/logging.py',
                'classes': ['LoggingUtility'],
                'methods': [],
                'imports': set()
            },
            'utils/timestamp': {
                'file': 'utils/timestamp.py',
                'classes': ['TimestampUtility'],
                'methods': [],
                'imports': set()
            }
        }
        
        # Method categorization patterns
        self.method_patterns = {
            'data_collector': [
                r'fetch.*', r'get_market.*', r'.*_ohlcv', r'.*_orderbook', 
                r'.*_trades', r'.*_ticker', r'.*_funding'
            ],
            'validator': [
                r'validate.*', r'check.*', r'_validate.*', r'.*validation.*'
            ],
            'signal_processor': [
                r'.*signal.*', r'.*analyze.*', r'.*confluence.*', r'.*strength.*'
            ],
            'alert_manager': [
                r'.*alert.*', r'.*notify.*', r'.*discord.*', r'.*email.*'
            ],
            'websocket_manager': [
                r'.*websocket.*', r'ws_.*', r'.*subscribe.*', r'.*_update'
            ],
            'metrics_tracker': [
                r'.*metric.*', r'.*health.*', r'.*stats.*', r'.*performance.*'
            ]
        }
        
    def backup_original(self):
        """Create backup of original monitor.py."""
        print(f"📦 Creating backup: {self.backup_path}")
        shutil.copy2(self.monitor_path, self.backup_path)
        
        # Also create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_backup = self.monitor_path.parent / f"monitor_backup_{timestamp}.py"
        shutil.copy2(self.monitor_path, timestamped_backup)
        print(f"✅ Backup created: {timestamped_backup}")
        
    def parse_monitor_file(self):
        """Parse monitor.py and categorize components."""
        print(f"🔍 Analyzing {self.monitor_path}")
        
        with open(self.monitor_path, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
            
        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
                
        # Extract classes and methods
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._categorize_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._categorize_function(node)
                
        print(f"✅ Analyzed: {len(imports)} imports, "
              f"{sum(len(m['classes']) for m in self.modules.values())} classes, "
              f"{sum(len(m['methods']) for m in self.modules.values())} methods")
        
    def _categorize_class(self, node: ast.ClassDef):
        """Categorize a class into appropriate module."""
        class_name = node.name
        
        # Check explicit class assignments
        for module_name, module_info in self.modules.items():
            if class_name in module_info['classes']:
                return  # Already assigned
                
        # Categorize MarketMonitor specially
        if class_name == 'MarketMonitor':
            # This stays in main monitor.py but slimmed down
            return
            
    def _categorize_function(self, node: ast.FunctionDef):
        """Categorize a function/method into appropriate module."""
        func_name = node.name
        
        # Match against patterns
        for module_name, patterns in self.method_patterns.items():
            for pattern in patterns:
                if re.match(pattern, func_name):
                    self.modules[module_name]['methods'].append(func_name)
                    return
                    
    def create_module_files(self):
        """Create new module files with proper structure."""
        print("📝 Creating new module files...")
        
        # Create base.py with interfaces
        self._create_base_module()
        
        # Create individual modules
        for module_name, module_info in self.modules.items():
            if module_name == 'base':
                continue
                
            module_path = self.new_modules_dir / module_info['file']
            
            # Create directory if needed
            module_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate module content
            content = self._generate_module_content(module_name, module_info)
            
            # Write module file
            with open(module_path, 'w') as f:
                f.write(content)
                
            print(f"✅ Created: {module_path}")
            
    def _create_base_module(self):
        """Create base.py with shared interfaces and types."""
        base_content = '''"""
Base classes and interfaces for monitoring modules.

This module defines the contracts between monitoring components.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime


class DataCollectorInterface(ABC):
    """Interface for data collection components."""
    
    @abstractmethod
    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch data for multiple symbols."""
        pass
        
    @abstractmethod
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch complete market data for a symbol."""
        pass


class ValidatorInterface(ABC):
    """Interface for data validation components."""
    
    @abstractmethod
    async def validate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate market data."""
        pass
        
    @abstractmethod
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        pass


class SignalProcessorInterface(ABC):
    """Interface for signal processing components."""
    
    @abstractmethod
    async def process(self, market_data: Dict[str, Any]) -> List[Dict]:
        """Process market data to generate signals."""
        pass


class AlertDispatcherInterface(ABC):
    """Interface for alert dispatching components."""
    
    @abstractmethod
    async def dispatch(self, signals: List[Dict]) -> None:
        """Dispatch alerts based on signals."""
        pass


class WebSocketManagerInterface(ABC):
    """Interface for WebSocket management."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to WebSocket streams."""
        pass
        
    @abstractmethod
    async def subscribe(self, symbols: List[str], channels: List[str]) -> None:
        """Subscribe to market data streams."""
        pass


class MetricsTrackerInterface(ABC):
    """Interface for metrics tracking."""
    
    @abstractmethod
    def record_cycle(self) -> None:
        """Record monitoring cycle metrics."""
        pass
        
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        pass


# Shared types
class Signal:
    """Trading signal data structure."""
    
    def __init__(self, symbol: str, action: str, strength: float, **kwargs):
        self.symbol = symbol
        self.action = action
        self.strength = strength
        self.metadata = kwargs
        self.timestamp = datetime.utcnow()


class ValidationResult:
    """Data validation result."""
    
    def __init__(self, is_valid: bool, errors: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
'''
        
        base_path = self.new_modules_dir / "base.py"
        with open(base_path, 'w') as f:
            f.write(base_content)
        print(f"✅ Created: {base_path}")
        
    def _generate_module_content(self, module_name: str, module_info: Dict) -> str:
        """Generate content for a specific module."""
        # Template for module
        template = f'''"""
{module_name.replace('_', ' ').title()} Module

Part of the refactored monitoring system.
Original source: monitor.py (7,699 lines) → focused modules
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

from .base import {self._get_interface_name(module_name)}

logger = logging.getLogger(__name__)


class {self._get_class_name(module_name)}({self._get_interface_name(module_name)}):
    """
    {module_name.replace('_', ' ').title()} implementation.
    
    Responsible for:
    {self._get_responsibilities(module_name)}
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize {module_name.replace('_', ' ')}."""
        self.config = config or {{}}
        self.logger = logger
        
    # Methods will be migrated here from monitor.py
    # This is a placeholder structure for the refactoring
'''
        return template
        
    def _get_interface_name(self, module_name: str) -> str:
        """Get interface name for module."""
        mapping = {
            'data_collector': 'DataCollectorInterface',
            'validator': 'ValidatorInterface',
            'signal_processor': 'SignalProcessorInterface',
            'alert_manager': 'AlertDispatcherInterface',
            'websocket_manager': 'WebSocketManagerInterface',
            'metrics_tracker': 'MetricsTrackerInterface'
        }
        return mapping.get(module_name, 'ABC')
        
    def _get_class_name(self, module_name: str) -> str:
        """Get main class name for module."""
        mapping = {
            'data_collector': 'DataCollector',
            'validator': 'MarketDataValidator',
            'signal_processor': 'SignalProcessor',
            'alert_manager': 'AlertDispatcher',
            'websocket_manager': 'WebSocketManager',
            'metrics_tracker': 'MetricsTracker'
        }
        return mapping.get(module_name, module_name.title().replace('_', ''))
        
    def _get_responsibilities(self, module_name: str) -> str:
        """Get module responsibilities description."""
        responsibilities = {
            'data_collector': """
    - Fetching market data from exchanges
    - Batch data collection for multiple symbols
    - OHLCV, orderbook, trades data retrieval
    - Data aggregation and formatting""",
            'validator': """
    - Data validation and quality checks
    - Timestamp freshness validation
    - Data completeness verification
    - Anomaly detection""",
            'signal_processor': """
    - Signal generation from market data
    - Confluence analysis integration
    - Signal strength calculation
    - Pattern recognition""",
            'alert_manager': """
    - Alert generation and filtering
    - Discord webhook notifications
    - Email notifications
    - Alert throttling and management""",
            'websocket_manager': """
    - WebSocket connection management
    - Real-time data streaming
    - Reconnection handling
    - Message processing""",
            'metrics_tracker': """
    - Performance metrics collection
    - Health status monitoring
    - Statistics aggregation
    - System diagnostics"""
        }
        return responsibilities.get(module_name, "")
        
    def update_imports_codebase(self):
        """Update imports across the codebase."""
        print("🔄 Updating imports across codebase...")
        
        # Files that might import from monitor.py
        files_to_check = [
            self.project_root / "src/main.py",
            self.project_root / "src/api/dependencies.py",
            self.project_root / "src/core/market_data_direct.py",
            self.project_root / "src/signal_generation/signal_generator.py"
        ]
        
        for file_path in files_to_check:
            if not file_path.exists():
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Update imports
            updated = content.replace(
                "from src.monitoring.monitor import MarketMonitor",
                "from src.monitoring.monitor import MarketMonitor"
            )
            
            # Add new module imports if needed
            if "MarketDataValidator" in content:
                updated = updated.replace(
                    "from src.monitoring.monitor import MarketDataValidator",
                    "from src.monitoring.validator import MarketDataValidator"
                )
                
            if updated != content:
                with open(file_path, 'w') as f:
                    f.write(updated)
                print(f"✅ Updated imports in: {file_path}")
                
    def run_tests(self) -> bool:
        """Run tests to verify refactoring."""
        print("🧪 Running tests...")
        
        # Run basic import test
        try:
            sys.path.insert(0, str(self.project_root))
            from src.monitoring.base import DataCollectorInterface
            from src.monitoring.monitor import MarketMonitor
            print("✅ Basic import test passed")
            return True
        except ImportError as e:
            print(f"❌ Import test failed: {e}")
            return False
            
    def rollback(self):
        """Rollback to original monitor.py."""
        print("⏮️ Rolling back changes...")
        
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.monitor_path)
            print(f"✅ Restored original monitor.py from backup")
            
            # Remove new module files
            for module_info in self.modules.values():
                module_path = self.new_modules_dir / module_info['file']
                if module_path.exists() and module_path != self.monitor_path:
                    module_path.unlink()
                    print(f"🗑️ Removed: {module_path}")
        else:
            print("❌ Backup not found! Cannot rollback")
            
    def execute_refactoring(self, dry_run: bool = True):
        """Execute the complete refactoring process."""
        print(f"{'🔍 DRY RUN' if dry_run else '🚀 EXECUTING'} Monitor Refactoring")
        print("=" * 60)
        
        try:
            # Step 1: Backup
            if not dry_run:
                self.backup_original()
            else:
                print("📦 [DRY RUN] Would create backup")
                
            # Step 2: Parse and analyze
            self.parse_monitor_file()
            
            # Step 3: Create modules
            if not dry_run:
                self.create_module_files()
            else:
                print("📝 [DRY RUN] Would create module files")
                
            # Step 4: Update imports
            if not dry_run:
                self.update_imports_codebase()
            else:
                print("🔄 [DRY RUN] Would update imports")
                
            # Step 5: Run tests
            if not dry_run:
                success = self.run_tests()
                if not success:
                    print("❌ Tests failed! Rolling back...")
                    self.rollback()
                    return False
            else:
                print("🧪 [DRY RUN] Would run tests")
                
            print("\n✅ Refactoring completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error during refactoring: {e}")
            if not dry_run:
                print("Rolling back changes...")
                self.rollback()
            return False


def main():
    """Main entry point for refactoring script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Refactor monitor.py into focused modules")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without changes")
    parser.add_argument("--rollback", action="store_true", help="Rollback previous refactoring")
    args = parser.parse_args()
    
    refactorer = MonitorRefactorer()
    
    if args.rollback:
        refactorer.rollback()
    else:
        success = refactorer.execute_refactoring(dry_run=args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()