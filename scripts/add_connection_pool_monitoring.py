#!/usr/bin/env python3
"""
Add connection pool monitoring to Bybit exchange
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def add_import_statement(content: str) -> str:
    """Add import for connection pool monitor"""
    import_line = "from src.core.monitoring.connection_pool_monitor import get_monitor"
    
    # Find the last import statement
    lines = content.split('\n')
    last_import_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            last_import_idx = i
            
    # Insert after last import
    lines.insert(last_import_idx + 1, import_line)
    return '\n'.join(lines)


def add_monitor_registration(content: str) -> str:
    """Add monitor registration after session creation"""
    
    # Pattern to add monitoring after session creation
    monitor_code = """
            # Register session with connection pool monitor
            try:
                monitor = get_monitor()
                monitor.register_session(f"bybit_{self.exchange_id}", self.session)
                self.logger.info("Registered session with connection pool monitor")
            except Exception as e:
                self.logger.warning(f"Failed to register with connection pool monitor: {e}")"""
    
    # Find all session creation points
    session_patterns = [
        "self.session = aiohttp.ClientSession(",
        "self.session = session"
    ]
    
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if this is a session creation line
        for pattern in session_patterns:
            if pattern in line:
                # Find the end of the session creation block
                indent = len(line) - len(line.lstrip())
                j = i + 1
                
                # Skip to the end of the ClientSession creation
                while j < len(lines) and (lines[j].strip() == '' or 
                                         lines[j].startswith(' ' * (indent + 4)) or
                                         lines[j].strip() == ')'):
                    new_lines.append(lines[j])
                    j += 1
                
                # Add monitor registration
                for monitor_line in monitor_code.split('\n'):
                    if monitor_line:
                        new_lines.append(' ' * indent + monitor_line)
                    else:
                        new_lines.append('')
                        
                i = j - 1
                break
        
        i += 1
    
    return '\n'.join(new_lines)


def add_request_tracking(content: str) -> str:
    """Add request counting to _make_request method"""
    
    tracking_code = """                # Track request for monitoring
                try:
                    monitor = get_monitor()
                    monitor.increment_request_count(f"bybit_{self.exchange_id}")
                except:
                    pass  # Don't fail requests due to monitoring issues
                    """
    
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Find the _make_request method and add tracking after headers setup
        if "async with self.session.get(url, params=params, headers=headers)" in line:
            indent = len(line) - len(line.lstrip())
            # Add tracking before the request
            for track_line in tracking_code.split('\n'):
                if track_line:
                    new_lines.insert(len(new_lines) - 1, ' ' * (indent - 4) + track_line)
                else:
                    new_lines.insert(len(new_lines) - 1, '')
                    
        i += 1
    
    return '\n'.join(new_lines)


def add_cleanup_monitoring(content: str) -> str:
    """Add monitor cleanup in close method"""
    
    cleanup_code = """
        # Unregister from connection pool monitor
        try:
            monitor = get_monitor()
            monitor.unregister_session(f"bybit_{self.exchange_id}")
        except Exception as e:
            self.logger.debug(f"Error unregistering from monitor: {e}")"""
    
    lines = content.split('\n')
    new_lines = []
    
    in_close_method = False
    close_indent = 0
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Find the close method
        if "async def close(self)" in line:
            in_close_method = True
            close_indent = len(line) - len(line.lstrip())
            
        # Add cleanup before session close
        if in_close_method and "await self.session.close()" in line:
            indent = len(line) - len(line.lstrip())
            # Add cleanup before closing session
            for cleanup_line in cleanup_code.split('\n'):
                if cleanup_line:
                    new_lines.insert(len(new_lines) - 1, ' ' * (indent - 4) + cleanup_line)
                else:
                    new_lines.insert(len(new_lines) - 1, '')
            in_close_method = False
    
    return '\n'.join(new_lines)


def main():
    """Apply connection pool monitoring patches"""
    
    bybit_file = Path(__file__).parent.parent / "src" / "core" / "exchanges" / "bybit.py"
    
    print(f"Adding connection pool monitoring to {bybit_file}")
    
    # Read current content
    with open(bybit_file, 'r') as f:
        content = f.read()
    
    # Apply patches
    content = add_import_statement(content)
    content = add_monitor_registration(content)
    content = add_request_tracking(content)
    content = add_cleanup_monitoring(content)
    
    # Write back
    with open(bybit_file, 'w') as f:
        f.write(content)
        
    print("✓ Added connection pool monitoring to Bybit exchange")
    
    # Also need to start the monitor in main.py
    main_file = Path(__file__).parent.parent / "src" / "main.py"
    
    print(f"\nAdding monitor startup to {main_file}")
    
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    # Add import
    if "from src.core.monitoring.connection_pool_monitor import start_monitoring" not in main_content:
        # Find imports section
        lines = main_content.split('\n')
        for i, line in enumerate(lines):
            if "from src.core" in line:
                lines.insert(i + 1, "from src.core.monitoring.connection_pool_monitor import start_monitoring, stop_monitoring")
                break
        main_content = '\n'.join(lines)
    
    # Add monitor startup in main
    if "start_monitoring()" not in main_content:
        lines = main_content.split('\n')
        for i, line in enumerate(lines):
            if "async def main():" in line:
                # Find where to add startup
                j = i + 1
                while j < len(lines) and "try:" not in lines[j]:
                    j += 1
                if j < len(lines):
                    # Add after try:
                    indent = len(lines[j+1]) - len(lines[j+1].lstrip())
                    lines.insert(j + 2, f"{' ' * indent}# Start connection pool monitoring")
                    lines.insert(j + 3, f"{' ' * indent}asyncio.create_task(start_monitoring())")
                break
        main_content = '\n'.join(lines)
    
    # Add cleanup in shutdown
    if "stop_monitoring()" not in main_content:
        lines = main_content.split('\n')
        for i, line in enumerate(lines):
            if "async def graceful_shutdown" in line:
                # Find where to add cleanup
                j = i + 1
                while j < len(lines) and "logger.info" not in lines[j]:
                    j += 1
                if j < len(lines):
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    lines.insert(j + 1, f"{' ' * indent}# Stop connection pool monitoring")
                    lines.insert(j + 2, f"{' ' * indent}await stop_monitoring()")
                break
        main_content = '\n'.join(lines)
    
    with open(main_file, 'w') as f:
        f.write(main_content)
        
    print("✓ Added monitor startup/shutdown to main.py")
    print("\nConnection pool monitoring integration complete!")
    print("\nThe monitor will:")
    print("- Track active/idle/pending connections")
    print("- Log pool utilization every 60 seconds")
    print("- Alert when utilization exceeds 80%")
    print("- Track requests per second")
    print("- Export statistics on demand")


if __name__ == "__main__":
    main()