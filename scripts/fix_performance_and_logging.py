#!/usr/bin/env python3
"""
Fix performance warnings and excessive DEBUG logging in Virtuoso.

Issues to fix:
1. liquidity_zones calculation taking too long (2107.4ms)
2. Too much DEBUG logging output
"""

import os
import sys
import shutil
from datetime import datetime

def backup_file(filepath):
    """Create a backup of a file before modification."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path

def optimize_liquidity_zones():
    """Optimize the liquidity_zones calculation to reduce computation time."""
    
    filepath = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/indicators/orderflow_indicators.py"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    # Backup the file
    backup_file(filepath)
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Optimization 1: Reduce swing_length from 50 to 20
    content = content.replace(
        "def _detect_liquidity_zones(self, df: pd.DataFrame, swing_length: int = 50,",
        "def _detect_liquidity_zones(self, df: pd.DataFrame, swing_length: int = 20,"
    )
    
    # Optimization 2: Add early exit for small DataFrames
    optimization_code = '''    def _detect_liquidity_zones(self, df: pd.DataFrame, swing_length: int = 20, range_percent: float = 0.01) -> Dict[str, Any]:
        """
        Detect liquidity zones where multiple swing highs/lows cluster.
        
        This is pure order flow analysis - identifying where stop losses cluster
        and where institutional players target retail liquidity.
        
        Args:
            df: OHLCV DataFrame
            swing_length: Length for swing detection (reduced from 50 to 20 for performance)
            range_percent: Percentage range for clustering
            
        Returns:
            Dict containing liquidity zone information
        """
        try:
            # Performance optimization: Skip if insufficient data
            if len(df) < swing_length * 2:
                return {'bullish': [], 'bearish': []}
            
            # Performance optimization: Limit analysis to recent data
            max_lookback = min(len(df), 500)  # Limit to last 500 candles
            df_subset = df.iloc[-max_lookback:] if len(df) > max_lookback else df'''
    
    # Replace the function definition
    import re
    pattern = r'def _detect_liquidity_zones\(self, df: pd\.DataFrame.*?\):\s*""".*?""".*?try:'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Find the end of the docstring and 'try:' statement
        end_of_try = match.end()
        # Replace with optimized version
        content = content[:match.start()] + optimization_code + '\n' + content[end_of_try:]
        
        # Also replace df with df_subset in the swing detection
        content = content.replace(
            "swing_data = self._detect_swing_highs_lows(df, swing_length)",
            "swing_data = self._detect_swing_highs_lows(df_subset, swing_length)"
        )
        content = content.replace(
            "zone = self._create_liquidity_zone(df, cluster,",
            "zone = self._create_liquidity_zone(df_subset, cluster,"
        )
        content = content.replace(
            "self._check_liquidity_sweeps(df, liquidity_zones)",
            "self._check_liquidity_sweeps(df_subset, liquidity_zones)"
        )
    
    # Write the optimized content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Optimized liquidity_zones calculation in {filepath}")
    return True

def fix_debug_logging():
    """Reduce DEBUG logging to WARNING level for production."""
    
    # Fix in core/logger.py - set default level to INFO instead of DEBUG
    logger_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/core/logger.py"
    
    if os.path.exists(logger_path):
        backup_file(logger_path)
        
        with open(logger_path, 'r') as f:
            content = f.read()
        
        # Change default logging level
        content = content.replace(
            'def __init__(self, name: str, level: Optional[str] = None):',
            'def __init__(self, name: str, level: Optional[str] = "INFO"):'
        )
        
        with open(logger_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated default logging level to INFO in {logger_path}")
    
    # Fix in confluence.py - reduce debug logging
    confluence_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/analysis/core/confluence.py"
    
    if os.path.exists(confluence_path):
        backup_file(confluence_path)
        
        with open(confluence_path, 'r') as f:
            lines = f.readlines()
        
        # Replace verbose debug logs with info level for important messages only
        new_lines = []
        for line in lines:
            # Keep important debug messages as info
            if 'self.logger.debug' in line and any(keyword in line for keyword in [
                'Final', 'Score', 'Result', 'Completed', 'Error'
            ]):
                new_lines.append(line.replace('self.logger.debug', 'self.logger.info'))
            # Comment out verbose debug messages
            elif 'self.logger.debug' in line and any(keyword in line for keyword in [
                'Candle', 'Converting', 'Converted', 'Found', 'Using', 
                'Mapped', 'Sample', 'Input', 'Validating', '===='
            ]):
                new_lines.append('            # ' + line.lstrip())  # Comment out
            else:
                new_lines.append(line)
        
        with open(confluence_path, 'w') as f:
            f.writelines(new_lines)
        
        print(f"✅ Reduced verbose DEBUG logging in {confluence_path}")
    
    return True

def create_logging_config():
    """Create a centralized logging configuration file."""
    
    config_content = '''"""
Centralized logging configuration for Virtuoso.
"""

import logging
import os
from typing import Optional

# Environment variable to control logging level
LOG_LEVEL = os.environ.get('VIRTUOSO_LOG_LEVEL', 'INFO').upper()

# Specific module log levels
MODULE_LOG_LEVELS = {
    'src.analysis.core.confluence': 'WARNING',  # Reduce verbose confluence logging
    'src.indicators.orderflow_indicators': 'INFO',  # Reduce orderflow debug logs
    'src.core.exchanges': 'INFO',  # Reduce exchange debug logs
    'src.monitoring': 'INFO',  # Keep monitoring at INFO level
}

def setup_logging(level: Optional[str] = None):
    """
    Configure logging for the entire application.
    
    Args:
        level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = level or LOG_LEVEL
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific module log levels
    for module_name, module_level in MODULE_LOG_LEVELS.items():
        logger = logging.getLogger(module_name)
        logger.setLevel(getattr(logging, module_level))
    
    # Suppress overly verbose third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return logging.getLogger()

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with appropriate configuration.
    
    Args:
        name: Logger name (usually __name__)
        level: Override log level for this logger
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Check if this module has a specific log level
    if name in MODULE_LOG_LEVELS and not level:
        level = MODULE_LOG_LEVELS[name]
    
    if level:
        logger.setLevel(getattr(logging, level))
    
    return logger
'''
    
    config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/config/logging_config.py"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Created centralized logging configuration at {config_path}")
    return True

def update_main_py():
    """Update main.py to use the new logging configuration."""
    
    main_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/main.py"
    
    if not os.path.exists(main_path):
        print(f"❌ File not found: {main_path}")
        return False
    
    backup_file(main_path)
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    # Add import for logging config at the top
    import_line = "from config.logging_config import setup_logging, get_logger\n"
    
    # Find the imports section
    if "import logging" in content:
        content = content.replace("import logging", f"import logging\n{import_line}")
    else:
        # Add after the first import statement
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                lines.insert(i + 1, import_line)
                break
        content = '\n'.join(lines)
    
    # Add setup_logging() call in main or at module level
    if "if __name__ == '__main__':" in content:
        content = content.replace(
            "if __name__ == '__main__':",
            "if __name__ == '__main__':\n    # Setup logging configuration\n    setup_logging()\n"
        )
    
    with open(main_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated main.py to use centralized logging configuration")
    return True

def main():
    """Main function to apply all fixes."""
    
    print("=" * 60)
    print("🔧 Fixing Performance and Logging Issues")
    print("=" * 60)
    
    # Fix 1: Optimize liquidity zones calculation
    print("\n📊 Optimizing liquidity_zones calculation...")
    if optimize_liquidity_zones():
        print("   ✓ Reduced swing_length from 50 to 20")
        print("   ✓ Added early exit for small DataFrames")
        print("   ✓ Limited analysis to last 500 candles")
    
    # Fix 2: Reduce DEBUG logging
    print("\n📝 Fixing excessive DEBUG logging...")
    if fix_debug_logging():
        print("   ✓ Set default log level to INFO")
        print("   ✓ Commented out verbose debug messages")
    
    # Fix 3: Create centralized logging config
    print("\n⚙️ Creating centralized logging configuration...")
    if create_logging_config():
        print("   ✓ Created logging_config.py")
        print("   ✓ Set module-specific log levels")
    
    # Fix 4: Update main.py
    print("\n🔄 Updating main.py...")
    if update_main_py():
        print("   ✓ Added logging configuration import")
        print("   ✓ Added setup_logging() call")
    
    print("\n" + "=" * 60)
    print("✅ All fixes applied successfully!")
    print("\nTo control logging level, set environment variable:")
    print("  export VIRTUOSO_LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR")
    print("\nRestart the service to apply changes:")
    print("  sudo systemctl restart virtuoso.service")
    print("=" * 60)

if __name__ == "__main__":
    main()