#!/usr/bin/env python3
"""Add resilience monitor route to web server."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def add_monitor_route():
    """Add resilience monitor route to web_server.py."""
    
    web_server_path = project_root / "src" / "web_server.py"
    
    # Read current content
    with open(web_server_path, 'r') as f:
        content = f.read()
    
    # Check if already has the route
    if "/resilience-monitor" in content:
        print("Route already exists")
        return
    
    # Add route after dashboard route
    monitor_route = '''
@app.get("/resilience-monitor")
async def resilience_monitor():
    """Serve the resilience monitoring dashboard"""
    file_path = TEMPLATE_DIR / "resilience_monitor.html"
    if file_path.exists():
        return FileResponse(file_path)
    else:
        # Try alternative path
        alt_path = TEMPLATE_DIR_ALT / "resilience_monitor.html"
        if alt_path.exists():
            return FileResponse(alt_path)
        else:
            raise HTTPException(status_code=404, detail="Resilience monitor not found")
'''
    
    # Find where to insert (after dashboard route)
    dashboard_pos = content.find('@app.get("/dashboard")')
    if dashboard_pos > 0:
        # Find the end of the dashboard function
        next_decorator = content.find('\n@app.', dashboard_pos + 1)
        if next_decorator > 0:
            # Insert before the next decorator
            content = content[:next_decorator] + monitor_route + content[next_decorator:]
        else:
            # Append at the end
            content = content + monitor_route
    
    # Write back
    with open(web_server_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Added resilience monitor route to web_server.py")
    print("Access at: /resilience-monitor")


def add_to_api_routes():
    """Add resilience endpoints to API routes if not present."""
    
    api_init_path = project_root / "src" / "api" / "__init__.py"
    
    # Read current content
    with open(api_init_path, 'r') as f:
        content = f.read()
    
    # Check if health routes are included
    if "health.router" not in content:
        # Find where routers are included
        if "app.include_router" in content:
            # Add after the last router
            last_router = content.rfind("app.include_router")
            if last_router > 0:
                # Find the end of the line
                line_end = content.find('\n', last_router)
                if line_end > 0:
                    health_include = '''
    # Health and resilience monitoring
    try:
        from .routes import health
        app.include_router(health.router, prefix="/api/health", tags=["health"])
    except ImportError:
        logger.warning("Health routes not available")
'''
                    content = content[:line_end+1] + health_include + content[line_end+1:]
                    
                    # Write back
                    with open(api_init_path, 'w') as f:
                        f.write(content)
                    
                    print("✅ Added health routes to API")
    else:
        print("Health routes already present")


def main():
    """Main execution."""
    print("=" * 60)
    print("🔧 Adding Resilience Monitor Route")
    print("=" * 60)
    
    # Add routes
    add_monitor_route()
    add_to_api_routes()
    
    print("\n✅ Routes added successfully!")
    print("\n📊 Access points:")
    print("  Monitor: http://localhost:8001/resilience-monitor")
    print("  System Health: http://localhost:8001/api/health/system")
    print("  Resilience Status: http://localhost:8001/api/health/resilience")


if __name__ == "__main__":
    main()