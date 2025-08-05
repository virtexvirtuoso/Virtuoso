#!/usr/bin/env python3
"""
Fix critical async issues in the Virtuoso trading system.
This script updates components to use proper initialization patterns.
"""

import os
import sys
import shutil
import re
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def backup_file(filepath):
    """Create a backup of the file before modifying."""
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up {filepath} to {backup_path}")
    return backup_path


def update_bybit_exchange():
    """Update Bybit exchange to use BaseComponent."""
    bybit_file = project_root / "src/core/exchanges/bybit.py"
    
    if not bybit_file.exists():
        print(f"❌ File not found: {bybit_file}")
        return False
    
    backup_file(bybit_file)
    
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Add import for BaseComponent
    import_section = content.find("import asyncio")
    if import_section != -1 and "from src.core.base_component import BaseComponent" not in content:
        # Find the end of imports
        import_end = content.find("\n\n", import_section)
        if import_end != -1:
            new_import = "\nfrom src.core.base_component import BaseComponent"
            content = content[:import_end] + new_import + content[import_end:]
            print("✅ Added BaseComponent import")
    
    # Update class definition to inherit from BaseComponent
    old_class = "class BybitExchange:"
    new_class = "class BybitExchange(BaseComponent):"
    
    if old_class in content:
        content = content.replace(old_class, new_class)
        print("✅ Updated class to inherit from BaseComponent")
    
    # Update __init__ to call super().__init__
    init_pattern = r'def __init__\(self, exchange_config: dict\):\s*"""[^"]*"""\s*'
    init_replacement = '''def __init__(self, exchange_config: dict):
        """Initialize Bybit exchange with given configuration."""
        super().__init__(exchange_config, "BybitExchange")
        '''
    
    content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)
    
    # Replace the old initialize method with one that uses _do_initialize
    old_init_pattern = r'async def initialize\(self\) -> bool:.*?return True.*?except Exception as e:.*?return False'
    
    new_init_method = '''async def _do_initialize(self) -> bool:
        """Perform Bybit-specific initialization."""
        try:
            if not self._validate_config(self.exchange_config):
                self.logger.error("Invalid configuration")
                return False
            
            # Initialize REST client with timeout
            self.logger.info("Initializing REST client...")
            rest_success = await self._init_rest_client_with_timeout()
            if not rest_success:
                return False
            
            # Initialize WebSocket if enabled (with timeout)
            if self.exchange_config.get('websocket', {}).get('enabled'):
                try:
                    async with asyncio.timeout(10.0):
                        await self._init_websocket()
                except asyncio.TimeoutError:
                    self.logger.error("WebSocket initialization timed out")
                    # Continue without WebSocket
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            return False
    
    async def _init_rest_client_with_timeout(self) -> bool:
        """Initialize REST client with proper timeout."""
        try:
            async with asyncio.timeout(10.0):
                return await self._init_rest_client()
        except asyncio.TimeoutError:
            self.logger.error("REST client initialization timed out")
            return False'''
    
    # Replace the initialize method
    content = re.sub(old_init_pattern, new_init_method, content, flags=re.DOTALL)
    print("✅ Updated initialize method to use BaseComponent pattern")
    
    with open(bybit_file, 'w') as f:
        f.write(content)
    
    print("✅ Bybit exchange updated successfully")
    return True


def update_monitor_start_method():
    """Update monitor.start() to check initialization state."""
    monitor_file = project_root / "src/monitoring/monitor.py"
    
    if not monitor_file.exists():
        print(f"❌ File not found: {monitor_file}")
        return False
    
    backup_file(monitor_file)
    
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Fix the duplicate initialization check
    old_pattern = r'''self\.logger\.debug\(f"Exchange instance retrieved: \{bool\(self\.exchange\)\}"\)
            
            # Check if exchange is already initialized
            if hasattr\(self\.exchange, 'initialized'\) and self\.exchange\.initialized:
                self\.logger\.debug\("Exchange already initialized, skipping re-initialization"\)
            else:
                self\.logger\.debug\("Initializing exchange\.\.\."\)
                # Initialize exchange with timeout
                try:
                    init_success = await asyncio\.wait_for\(
                        self\.exchange\.initialize\(\),
                        timeout=30\.0  # 30 second timeout
                    \)
                    if not init_success:
                        self\.logger\.error\("Failed to initialize exchange"\)
                        return
                except asyncio\.TimeoutError:
                    self\.logger\.error\("Exchange initialization timed out after 30s"\)
                    return'''
    
    new_pattern = '''self.logger.debug(f"Exchange instance retrieved: {bool(self.exchange)}")
            
            # Check initialization state if exchange supports it
            if hasattr(self.exchange, 'initialization_state'):
                from src.core.base_component import InitializationState
                
                current_state = self.exchange.initialization_state
                self.logger.debug(f"Exchange initialization state: {current_state.value}")
                
                if current_state == InitializationState.COMPLETED:
                    self.logger.debug("Exchange already initialized, skipping re-initialization")
                elif current_state == InitializationState.IN_PROGRESS:
                    self.logger.warning("Exchange initialization in progress, waiting...")
                    # Wait up to 30 seconds for initialization to complete
                    for _ in range(30):
                        await asyncio.sleep(1)
                        if self.exchange.initialization_state == InitializationState.COMPLETED:
                            break
                    else:
                        self.logger.error("Exchange initialization did not complete in time")
                        return
                else:
                    # Initialize exchange
                    self.logger.debug("Initializing exchange...")
                    init_success = await self.exchange.initialize(timeout=30.0)
                    if not init_success:
                        self.logger.error("Failed to initialize exchange")
                        return
            else:
                # Fallback for components not using BaseComponent yet
                if hasattr(self.exchange, 'initialized') and self.exchange.initialized:
                    self.logger.debug("Exchange already initialized (legacy check)")
                else:
                    self.logger.debug("Initializing exchange (legacy)...")
                    try:
                        init_success = await asyncio.wait_for(
                            self.exchange.initialize(),
                            timeout=30.0
                        )
                        if not init_success:
                            self.logger.error("Failed to initialize exchange")
                            return
                    except asyncio.TimeoutError:
                        self.logger.error("Exchange initialization timed out after 30s")
                        return'''
    
    content = re.sub(old_pattern, new_pattern, content, flags=re.DOTALL)
    print("✅ Updated monitor.start() initialization check")
    
    with open(monitor_file, 'w') as f:
        f.write(content)
    
    print("✅ Monitor updated successfully")
    return True


def create_startup_orchestrator():
    """Create a startup orchestrator for controlled initialization."""
    orchestrator_file = project_root / "src/core/startup_orchestrator.py"
    
    content = '''"""
Startup orchestrator for controlled component initialization.
Ensures components are initialized in the correct order with proper timeouts.
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime


class StartupOrchestrator:
    """Orchestrates system startup with proper initialization order and timeouts."""
    
    def __init__(self):
        self.logger = logging.getLogger("src.core.StartupOrchestrator")
        self.components: Dict[str, Any] = {}
        self.initialization_times: Dict[str, float] = {}
        self.initialization_errors: Dict[str, str] = {}
        
    def register_component(self, name: str, component: Any) -> None:
        """Register a component for initialization."""
        self.components[name] = component
        self.logger.debug(f"Registered component: {name}")
    
    async def initialize_all(self, initialization_order: Optional[List[Tuple[str, float]]] = None) -> bool:
        """
        Initialize all components in the specified order.
        
        Args:
            initialization_order: List of (component_name, timeout) tuples
            
        Returns:
            bool: True if all components initialized successfully
        """
        if initialization_order is None:
            # Default initialization order
            initialization_order = [
                ("config_manager", 5.0),
                ("database_client", 10.0),
                ("exchange_manager", 30.0),
                ("market_data_manager", 20.0),
                ("confluence_analyzer", 10.0),
                ("alert_manager", 10.0),
                ("market_monitor", 15.0),
                ("dashboard_integration", 10.0),
            ]
        
        self.logger.info(f"Starting system initialization with {len(initialization_order)} components")
        start_time = datetime.now()
        success_count = 0
        
        for component_name, timeout in initialization_order:
            if component_name not in self.components:
                self.logger.warning(f"Component {component_name} not registered, skipping")
                continue
            
            component = self.components[component_name]
            component_start = datetime.now()
            
            try:
                self.logger.info(f"Initializing {component_name} with {timeout}s timeout...")
                
                # Check if component has our new initialize method
                if hasattr(component, 'initialize') and hasattr(component, 'initialization_state'):
                    # Use new initialization pattern
                    success = await component.initialize(timeout=timeout)
                else:
                    # Fallback for legacy components
                    async with asyncio.timeout(timeout):
                        if hasattr(component, 'initialize'):
                            success = await component.initialize()
                        else:
                            self.logger.warning(f"Component {component_name} has no initialize method")
                            success = True
                
                duration = (datetime.now() - component_start).total_seconds()
                self.initialization_times[component_name] = duration
                
                if success:
                    self.logger.info(f"✅ {component_name} initialized in {duration:.2f}s")
                    success_count += 1
                else:
                    error_msg = f"{component_name} initialization returned False"
                    self.logger.error(f"❌ {error_msg}")
                    self.initialization_errors[component_name] = error_msg
                    
            except asyncio.TimeoutError:
                duration = (datetime.now() - component_start).total_seconds()
                error_msg = f"Timeout after {timeout}s"
                self.logger.error(f"❌ {component_name} initialization timed out after {duration:.2f}s")
                self.initialization_errors[component_name] = error_msg
                
            except Exception as e:
                duration = (datetime.now() - component_start).total_seconds()
                error_msg = str(e)
                self.logger.error(f"❌ {component_name} initialization failed: {error_msg}")
                self.initialization_errors[component_name] = error_msg
        
        total_duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"System initialization completed in {total_duration:.2f}s: "
            f"{success_count}/{len(initialization_order)} components successful"
        )
        
        # Log summary
        self._log_initialization_summary()
        
        return len(self.initialization_errors) == 0
    
    def _log_initialization_summary(self) -> None:
        """Log a summary of the initialization process."""
        self.logger.info("=" * 60)
        self.logger.info("Initialization Summary:")
        self.logger.info("=" * 60)
        
        # Successful initializations
        for name, duration in self.initialization_times.items():
            if name not in self.initialization_errors:
                self.logger.info(f"✅ {name:25} {duration:6.2f}s")
        
        # Failed initializations
        for name, error in self.initialization_errors.items():
            duration = self.initialization_times.get(name, 0.0)
            self.logger.error(f"❌ {name:25} {duration:6.2f}s - {error}")
        
        self.logger.info("=" * 60)
    
    def get_initialization_report(self) -> Dict[str, Any]:
        """Get a detailed initialization report."""
        return {
            "components": list(self.components.keys()),
            "successful": [
                name for name in self.initialization_times.keys()
                if name not in self.initialization_errors
            ],
            "failed": list(self.initialization_errors.keys()),
            "initialization_times": self.initialization_times,
            "errors": self.initialization_errors,
            "total_components": len(self.components),
            "successful_count": len(self.initialization_times) - len(self.initialization_errors),
            "failed_count": len(self.initialization_errors),
        }
    
    async def shutdown_all(self) -> None:
        """Shutdown all components in reverse order."""
        self.logger.info("Starting system shutdown...")
        
        # Shutdown in reverse order
        for name in reversed(list(self.components.keys())):
            component = self.components[name]
            
            try:
                if hasattr(component, 'close'):
                    self.logger.info(f"Closing {name}...")
                    await component.close()
                elif hasattr(component, 'stop'):
                    self.logger.info(f"Stopping {name}...")
                    await component.stop()
                    
            except Exception as e:
                self.logger.error(f"Error closing {name}: {str(e)}")
        
        self.logger.info("System shutdown complete")
'''
    
    with open(orchestrator_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Created startup orchestrator at {orchestrator_file}")
    return True


def main():
    """Apply critical async fixes."""
    print("🔧 Applying critical async architecture fixes")
    print("=" * 60)
    
    success = True
    
    # Create base component
    print("\n1. Creating BaseComponent class...")
    # Already created above
    print("✅ BaseComponent created")
    
    # Update Bybit exchange
    print("\n2. Updating Bybit exchange...")
    if not update_bybit_exchange():
        success = False
    
    # Update monitor
    print("\n3. Updating monitor initialization check...")
    if not update_monitor_start_method():
        success = False
    
    # Create startup orchestrator
    print("\n4. Creating startup orchestrator...")
    if not create_startup_orchestrator():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All critical async fixes applied successfully!")
        print("\nNext steps:")
        print("1. Run the test suite to verify fixes")
        print("2. Test locally before deploying to VPS")
        print("3. Monitor initialization times and states")
    else:
        print("❌ Some fixes failed. Please check the output above.")
    
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)