#!/usr/bin/env python3
"""
Deploy Health Dashboard Updates to VPS
Run this script directly on the VPS to update the health dashboard.
"""

import os
import sys
import shutil
from datetime import datetime

def main():
    """Deploy health dashboard updates."""
    
    print("🚀 Deploying Health Dashboard Updates...")
    
    # VPS paths
    vps_main_py = "/root/virtuoso_trading/src/main.py"
    backup_dir = "/root/virtuoso_trading/backups"
    
    # Create backup directory if not exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup current main.py
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/main_py_backup_{timestamp}.py"
    
    if os.path.exists(vps_main_py):
        print(f"📦 Creating backup: {backup_path}")
        shutil.copy2(vps_main_py, backup_path)
    
    # Health dashboard function code
    health_dashboard_function = '''
def generate_health_dashboard(data: dict, health_status: str) -> str:
    """Generate HTML health dashboard."""
    status_color = {
        "healthy": "#10B981",  # Green
        "degraded": "#F59E0B", # Amber
        "unhealthy": "#EF4444"  # Red
    }.get(health_status, "#6B7280")
    
    status_icon = {
        "healthy": "✅",
        "degraded": "⚠️",
        "unhealthy": "❌"
    }.get(health_status, "❓")
    
    components_html = ""
    for component, status in data.get("components", {}).items():
        icon = "✅" if status else "❌"
        color = "#10B981" if status else "#EF4444"
        components_html += f"""
        <div class="component">
            <span class="component-icon">{icon}</span>
            <span class="component-name">{component.replace('_', ' ').title()}</span>
            <span class="component-status" style="color: {color}">
                {'Healthy' if status else 'Unhealthy'}
            </span>
        </div>
        """
    
    metrics_html = ""
    if data.get("metrics"):
        for metric, value in data["metrics"].items():
            if isinstance(value, (int, float)):
                if "memory" in metric.lower():
                    # Format memory metrics
                    if value > 1024**3:  # GB
                        formatted_value = f"{value / (1024**3):.1f} GB"
                    elif value > 1024**2:  # MB
                        formatted_value = f"{value / (1024**2):.1f} MB"
                    else:
                        formatted_value = f"{value:.1f} bytes"
                elif "cpu" in metric.lower() or "percent" in metric.lower():
                    formatted_value = f"{value:.1f}%"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
                
            metrics_html += f"""
            <div class="metric">
                <span class="metric-name">{metric.replace('_', ' ').title()}</span>
                <span class="metric-value">{formatted_value}</span>
            </div>
            """
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>System Health Dashboard</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .dashboard {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
                max-width: 800px;
                width: 100%;
            }}
            .header {{
                background: {status_color};
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .status-icon {{
                font-size: 48px;
                margin-bottom: 10px;
            }}
            .status-text {{
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 5px;
            }}
            .timestamp {{
                opacity: 0.9;
                font-size: 14px;
            }}
            .content {{
                padding: 30px;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .section h3 {{
                color: #374151;
                font-size: 18px;
                margin-bottom: 15px;
                font-weight: 600;
            }}
            .component {{
                display: flex;
                align-items: center;
                padding: 12px 16px;
                background: #F8FAFC;
                border-radius: 8px;
                margin-bottom: 8px;
            }}
            .component-icon {{
                font-size: 20px;
                margin-right: 12px;
            }}
            .component-name {{
                flex: 1;
                font-weight: 500;
                color: #374151;
            }}
            .component-status {{
                font-weight: 600;
                font-size: 14px;
            }}
            .metric {{
                display: flex;
                justify-content: space-between;
                padding: 12px 16px;
                background: #F8FAFC;
                border-radius: 8px;
                margin-bottom: 8px;
            }}
            .metric-name {{
                color: #6B7280;
                font-weight: 500;
            }}
            .metric-value {{
                color: #374151;
                font-weight: 600;
            }}
            .run-info {{
                background: #F3F4F6;
                padding: 16px;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 12px;
                color: #6B7280;
                text-align: center;
            }}
            .refresh-button {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: {status_color};
                color: white;
                border: none;
                border-radius: 50px;
                padding: 12px 20px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: transform 0.2s;
            }}
            .refresh-button:hover {{
                transform: translateY(-2px);
            }}
            @media (max-width: 600px) {{
                .dashboard {{
                    margin: 10px;
                }}
                .header {{
                    padding: 20px;
                }}
                .content {{
                    padding: 20px;
                }}
            }}
        </style>
        <script>
            function refreshPage() {{
                window.location.reload();
            }}
            // Auto-refresh every 30 seconds
            setTimeout(refreshPage, 30000);
        </script>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <div class="status-icon">{status_icon}</div>
                <div class="status-text">System {health_status.title()}</div>
                <div class="timestamp">{data.get('timestamp', 'Unknown')}</div>
            </div>
            <div class="content">
                <div class="section">
                    <h3>Components Status</h3>
                    {components_html or '<p style="color: #6B7280; text-align: center; padding: 20px;">No component data available</p>'}
                </div>
                
                {f'''
                <div class="section">
                    <h3>System Metrics</h3>
                    {metrics_html}
                </div>
                ''' if metrics_html else ''}
                
                <div class="section">
                    <h3>System Information</h3>
                    <div class="run-info">
                        Run ID: {data.get('run_id', 'Unknown')}<br>
                        Last Updated: {data.get('timestamp', 'Unknown')}<br>
                        {f"Unhealthy Components: {', '.join(data.get('unhealthy_components', []))}" if data.get('unhealthy_components') else "All components operational"}
                    </div>
                </div>
            </div>
        </div>
        <button class="refresh-button" onclick="refreshPage()">🔄 Refresh</button>
    </body>
    </html>
    """
'''
    
    # Read current main.py
    print("📖 Reading current main.py...")
    with open(vps_main_py, 'r') as f:
        content = f.read()
    
    # Check if HTMLResponse is already imported
    if 'HTMLResponse' not in content:
        print("📝 Adding HTMLResponse import...")
        content = content.replace(
            'from fastapi.responses import FileResponse',
            'from fastapi.responses import FileResponse, HTMLResponse'
        )
    
    # Check if health dashboard function already exists
    if 'def generate_health_dashboard(' not in content:
        print("📝 Adding health dashboard function...")
        # Find the health check function and add the dashboard function before it
        health_check_pos = content.find('@app.get("/health")')
        if health_check_pos != -1:
            content = content[:health_check_pos] + health_dashboard_function + '\n\n' + content[health_check_pos:]
    
    # Update health check function signature to support format parameter
    if 'format: str = Query("json"' not in content:
        print("📝 Updating health check function signature...")
        content = content.replace(
            'async def health_check():',
            'async def health_check(format: str = Query("json", description="Response format: json or html")):'
        )
    
    # Add HTML response in health check
    if 'if format.lower() == "html":' not in content:
        print("📝 Adding HTML response support...")
        # Find the response_data assignment and add HTML support
        response_data_pos = content.find('# Return HTML dashboard if requested')
        if response_data_pos == -1:
            # Add HTML support after response_data definition
            insert_pos = content.find('# Log health check result')
            if insert_pos != -1:
                html_code = '''        
        # Return HTML dashboard if requested
        if format.lower() == "html":
            return HTMLResponse(content=generate_health_dashboard(response_data, health_status), status_code=status_code)
            '''
                content = content[:insert_pos] + html_code + '\n        ' + content[insert_pos:]
    
    # Update exception handling for HTML
    if 'if format.lower() == "html":' not in content[content.find('except Exception as e:'):]:
        print("📝 Updating exception handling for HTML support...")
        exception_pos = content.find('return {')
        if exception_pos != -1:
            # Find the end of the return dict
            dict_end = content.find('}', exception_pos)
            if dict_end != -1:
                html_exception_code = '''
        
        if format.lower() == "html":
            return HTMLResponse(content=generate_health_dashboard(error_data, "degraded"), status_code=200)
        '''
                content = content[:dict_end+1] + html_exception_code + '\n        return error_data' + content[dict_end+1:]
                # Remove the old return statement
                content = content.replace('\n        return {\n            "status": "degraded",\n            "run_id": RUN_DESCRIPTOR,\n            "components": {},\n            "error": str(e),\n            "timestamp": datetime.utcnow().isoformat()\n        }', '\n        error_data = {\n            "status": "degraded",\n            "run_id": RUN_DESCRIPTOR,\n            "components": {},\n            "error": str(e),\n            "timestamp": datetime.utcnow().isoformat()\n        }')
    
    # Write updated main.py
    print("💾 Writing updated main.py...")
    with open(vps_main_py, 'w') as f:
        f.write(content)
    
    print("🔄 Restarting virtuoso service...")
    os.system("sudo systemctl restart virtuoso")
    
    print("✅ Health Dashboard deployment complete!")
    print(f"📊 Access dashboard at: http://45.77.40.77:8003/health?format=html")
    print(f"📋 JSON API at: http://45.77.40.77:8003/health")
    
    # Check service status
    print("\n🔍 Service Status:")
    os.system("sudo systemctl status virtuoso --no-pager -l")

if __name__ == "__main__":
    main()