#!/usr/bin/env python3
"""
Fix for asyncio shutdown issues in main.py
This script patches the uvicorn server startup to handle shutdown signals properly
"""

import sys
import os

def create_fixed_start_web_server():
    """Create a fixed version of start_web_server with proper shutdown handling"""
    return '''async def start_web_server():
    """Start the FastAPI web server with proper shutdown handling"""
    import uvicorn
    import signal
    import asyncio
    
    # Ensure config_manager is available
    if config_manager is None:
        logger.error("Config manager not initialized. Cannot start web server.")
        raise RuntimeError("Config manager not initialized")
    
    # Get API configuration from config manager (use 'api' section for main FastAPI server)
    api_config = config_manager.config.get('api', {})
    web_config = config_manager.config.get('web_server', {})
    
    # Get host and port from API config with fallbacks to web_server config
    host = api_config.get('host', web_config.get('host', '0.0.0.0'))
    port = api_config.get('port', web_config.get('port', 8003))
    log_level = web_config.get('log_level', 'info')
    access_log = web_config.get('access_log', True)
    reload = web_config.get('reload', False)
    auto_fallback = web_config.get('auto_fallback', True)
    fallback_ports = web_config.get('fallback_ports', [8001, 8002, 8080, 3000, 5000])
    
    logger.info(f"Starting web server on {host}:{port}")
    
    # Try primary port first, then fallback ports if enabled
    ports_to_try = [port] + (fallback_ports if auto_fallback else [])
    
    for attempt_port in ports_to_try:
        try:
            config = uvicorn.Config(
                app=app,
                host=host,
                port=attempt_port,
                log_level=log_level,
                access_log=access_log,
                reload=reload,
                loop="asyncio"  # Explicitly use asyncio loop
            )
            server = uvicorn.Server(config)
            
            if attempt_port != port:
                logger.info(f"Primary port {port} unavailable, trying fallback port {attempt_port}")
            
            # Create a shutdown event
            shutdown_event = asyncio.Event()
            
            # Setup signal handlers for graceful shutdown
            def signal_handler(sig, frame):
                logger.info(f"Received signal {sig}, initiating graceful shutdown...")
                shutdown_event.set()
                # Cancel the server task
                if hasattr(server, 'should_exit'):
                    server.should_exit = True
                if hasattr(server, 'force_exit'):
                    server.force_exit = True
            
            # Register signal handlers (only in main thread)
            try:
                signal.signal(signal.SIGTERM, signal_handler)
                signal.signal(signal.SIGINT, signal_handler)
            except ValueError:
                # Not in main thread, skip signal registration
                pass
            
            # Run server with proper cancellation handling
            try:
                await server.serve()
            except asyncio.CancelledError:
                logger.info("Web server task cancelled, shutting down gracefully...")
                # Ensure server cleanup
                if hasattr(server, 'shutdown'):
                    await server.shutdown()
                raise  # Re-raise to properly propagate cancellation
            except Exception as e:
                logger.error(f"Web server error: {e}")
                if hasattr(server, 'shutdown'):
                    await server.shutdown()
                raise
            
            return  # Success, exit function
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                if attempt_port == ports_to_try[-1]:  # Last port to try
                    logger.error(f"All ports exhausted. Tried: {ports_to_try}")
                    logger.error("Solutions:")'''

def create_improved_cleanup():
    """Create improved cleanup function with better asyncio handling"""
    return '''async def cleanup_all_components():
    """Centralized cleanup of all system components with improved asyncio handling."""
    logger.info("Starting comprehensive application cleanup...")
    
    # Check if we have a running event loop
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning("Event loop is closed, performing synchronous cleanup only")
            await _sync_cleanup()
            return
    except RuntimeError:
        logger.warning("No running event loop, performing synchronous cleanup only")
        await _sync_cleanup()
        return
    
    # Track cleanup tasks
    cleanup_tasks = []
    
    # Create a list of components to clean up
    components = []
    
    # 1. Cancel background tasks first
    if 'monitoring_task' in globals() and monitoring_task and not monitoring_task.done():
        logger.info("Cancelling monitoring task...")
        monitoring_task.cancel()
        cleanup_tasks.append(monitoring_task)
    
    if 'web_server_task' in globals() and web_server_task and not web_server_task.done():
        logger.info("Cancelling web server task...")
        web_server_task.cancel()
        cleanup_tasks.append(web_server_task)
    
    # Wait for task cancellation with timeout
    if cleanup_tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*cleanup_tasks, return_exceptions=True),
                timeout=5.0
            )
            logger.info("Background tasks cancelled")
        except asyncio.TimeoutError:
            logger.warning("Some tasks did not cancel within timeout")
    
    # 2. Stop exchange manager (handles WebSocket connections)
    if exchange_manager:
        logger.info("Cleaning up exchange manager...")
        try:
            await asyncio.wait_for(exchange_manager.cleanup(), timeout=10.0)
            logger.info("Exchange manager cleanup completed")
        except asyncio.TimeoutError:
            logger.warning("Exchange manager cleanup timed out")
        except Exception as e:
            logger.error(f"Error during exchange manager cleanup: {e}")
    
    # 3. Close database connections
    if database_client:
        logger.info("Closing database client...")
        try:
            if hasattr(database_client, 'close'):
                if asyncio.iscoroutinefunction(database_client.close):
                    await asyncio.wait_for(database_client.close(), timeout=5.0)
                else:
                    database_client.close()
            logger.info("Database client closed successfully")
        except asyncio.TimeoutError:
            logger.warning("Database close timed out")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    # 4. Clean up alert manager
    if alert_manager:
        logger.info("Cleaning up alert manager...")
        try:
            if hasattr(alert_manager, 'cleanup'):
                if asyncio.iscoroutinefunction(alert_manager.cleanup):
                    await asyncio.wait_for(alert_manager.cleanup(), timeout=5.0)
                else:
                    alert_manager.cleanup()
            logger.info("Alert manager cleanup completed")
        except asyncio.TimeoutError:
            logger.warning("Alert manager cleanup timed out")
        except Exception as e:
            logger.error(f"Error during alert manager cleanup: {e}")
    
    # 5. Close any remaining aiohttp sessions
    logger.info("Closing aiohttp sessions...")
    closed_sessions = 0
    closed_connectors = 0
    
    # Get all aiohttp ClientSession objects
    for obj in gc.get_objects():
        if isinstance(obj, aiohttp.ClientSession):
            if not obj.closed:
                await obj.close()
                closed_sessions += 1
        elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'TCPConnector':
            if not obj.closed:
                await obj.close()
                closed_connectors += 1
    
    logger.info(f"Closed {closed_sessions} aiohttp sessions and {closed_connectors} connectors")
    
    # 6. Cancel any remaining tasks
    tasks = [t for t in asyncio.all_tasks() if t != asyncio.current_task()]
    if tasks:
        logger.info(f"Cancelling {len(tasks)} remaining tasks...")
        for task in tasks:
            task.cancel()
        
        # Wait for task cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Small delay to ensure all resources are released
    await asyncio.sleep(0.1)
    
    logger.info("Application cleanup completed successfully")'''

def main():
    """Main function to apply the fixes"""
    print("Fixing asyncio shutdown issues...")
    
    # Read the current main.py
    main_file = "src/main.py"
    if not os.path.exists(main_file):
        print(f"Error: {main_file} not found")
        return 1
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = main_file + ".backup_asyncio"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Apply fixes
    fixes_applied = []
    
    # Fix 1: Replace start_web_server function
    if "async def start_web_server():" in content:
        # Find and replace the function
        import re
        pattern = r'async def start_web_server\(\):.*?(?=\nasync def|\nif __name__|$)'
        new_function = create_fixed_start_web_server()
        content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        fixes_applied.append("Fixed start_web_server with proper shutdown handling")
    
    # Fix 2: Replace cleanup_all_components function
    if "async def cleanup_all_components():" in content:
        import re
        pattern = r'async def cleanup_all_components\(\):.*?(?=\nasync def|\nif __name__|$)'
        new_function = create_improved_cleanup()
        content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        fixes_applied.append("Improved cleanup_all_components with better asyncio handling")
    
    # Write the fixed content
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("\nFixes applied:")
    for fix in fixes_applied:
        print(f"  ✓ {fix}")
    
    print("\nDone! The asyncio shutdown issues should be resolved.")
    print("Deploy to VPS with: rsync -avz src/ linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())