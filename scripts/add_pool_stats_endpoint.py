#!/usr/bin/env python3
"""
Add connection pool statistics endpoint to web server
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def add_pool_stats_endpoint():
    """Add /api/pool-stats endpoint to web_server.py"""
    
    web_server_file = Path(__file__).parent.parent / "src" / "web_server.py"
    
    print(f"Adding pool stats endpoint to {web_server_file}")
    
    with open(web_server_file, 'r') as f:
        content = f.read()
    
    # Add import if not present
    if "from src.core.monitoring.connection_pool_monitor import get_monitor" not in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "from src.core" in line and "import" in line:
                lines.insert(i + 1, "from src.core.monitoring.connection_pool_monitor import get_monitor")
                break
        content = '\n'.join(lines)
    
    # Add the endpoint
    endpoint_code = '''
@app.route('/api/pool-stats')
async def pool_stats(request):
    """Get connection pool statistics"""
    try:
        monitor = get_monitor()
        
        # Get duration from query params (default 60 minutes)
        duration = int(request.args.get('duration', 60))
        
        # Get all summaries
        summaries = monitor.get_all_summaries(duration)
        
        # Get current stats for each session
        current_stats = {}
        for name in summaries:
            stats = monitor.get_current_stats(name)
            if stats:
                current_stats[name] = {
                    'active_connections': stats.active_connections,
                    'total_connections': stats.total_connections,
                    'idle_connections': stats.idle_connections,
                    'pending_connections': stats.pending_connections,
                    'pool_utilization': round(stats.pool_utilization * 100, 1),
                    'requests_per_second': round(stats.requests_per_second, 1)
                }
        
        return json({
            'success': True,
            'duration_minutes': duration,
            'current_stats': current_stats,
            'summaries': summaries,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        return json({
            'success': False,
            'error': str(e)
        }, status=500)


@app.route('/api/pool-stats/export')
async def export_pool_stats(request):
    """Export detailed pool statistics"""
    try:
        monitor = get_monitor()
        
        # Create export file
        export_file = f"exports/pool_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("exports").mkdir(exist_ok=True)
        
        monitor.export_stats(export_file)
        
        # Read and return the file
        with open(export_file, 'r') as f:
            data = json_module.load(f)
            
        return json({
            'success': True,
            'export_file': export_file,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error exporting pool stats: {e}")
        return json({
            'success': False,
            'error': str(e)
        }, status=500)'''
    
    # Find where to insert (after /api/health endpoint)
    lines = content.split('\n')
    insert_idx = None
    
    for i, line in enumerate(lines):
        if "@app.route('/api/health')" in line:
            # Find the end of this endpoint
            j = i + 1
            brace_count = 0
            while j < len(lines):
                if '{' in lines[j]:
                    brace_count += lines[j].count('{')
                if '}' in lines[j]:
                    brace_count -= lines[j].count('}')
                if brace_count == 0 and lines[j].strip() == '':
                    insert_idx = j
                    break
                j += 1
            break
    
    if insert_idx:
        # Insert the new endpoint
        for line in endpoint_code.split('\n'):
            lines.insert(insert_idx, line)
            insert_idx += 1
    
    # Write back
    with open(web_server_file, 'w') as f:
        f.write('\n'.join(lines))
        
    print("✓ Added pool stats endpoints to web server")
    print("\nNew endpoints:")
    print("- GET /api/pool-stats?duration=60 - Get pool statistics summary")
    print("- GET /api/pool-stats/export - Export detailed statistics")


def add_dashboard_display():
    """Add connection pool stats to dashboard"""
    
    dashboard_file = Path(__file__).parent.parent / "src" / "dashboard" / "templates" / "dashboard_desktop_v1.html"
    
    if not dashboard_file.exists():
        print(f"Dashboard file not found: {dashboard_file}")
        return
        
    print(f"\nAdding pool stats display to dashboard")
    
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Add pool stats display section
    pool_stats_html = '''
<!-- Connection Pool Stats -->
<div class="col-md-6">
    <div class="card h-100">
        <div class="card-header">
            <h6 class="mb-0">Connection Pool Status</h6>
        </div>
        <div class="card-body">
            <div id="poolStatsContainer">
                <div class="text-center text-muted">
                    <i class="fas fa-spinner fa-spin"></i> Loading pool stats...
                </div>
            </div>
        </div>
    </div>
</div>'''
    
    # Add JavaScript to fetch and display stats
    pool_stats_js = '''
// Fetch and display connection pool stats
async function updatePoolStats() {
    try {
        const response = await fetch('/api/pool-stats?duration=5');
        const data = await response.json();
        
        if (data.success && data.current_stats) {
            let html = '<div class="pool-stats">';
            
            for (const [name, stats] of Object.entries(data.current_stats)) {
                const utilClass = stats.pool_utilization > 80 ? 'danger' : 
                                 stats.pool_utilization > 60 ? 'warning' : 'success';
                
                html += `
                    <div class="mb-3">
                        <h6>${name}</h6>
                        <div class="progress mb-1" style="height: 20px;">
                            <div class="progress-bar bg-${utilClass}" 
                                 style="width: ${stats.pool_utilization}%">
                                ${stats.pool_utilization}% utilized
                            </div>
                        </div>
                        <small class="text-muted">
                            Active: ${stats.active_connections}/${stats.total_connections} | 
                            Idle: ${stats.idle_connections} | 
                            Pending: ${stats.pending_connections} | 
                            RPS: ${stats.requests_per_second}
                        </small>
                    </div>
                `;
            }
            
            html += '</div>';
            document.getElementById('poolStatsContainer').innerHTML = html;
        }
    } catch (error) {
        console.error('Error fetching pool stats:', error);
    }
}

// Update pool stats every 30 seconds
setInterval(updatePoolStats, 30000);
updatePoolStats(); // Initial load'''
    
    # Find where to insert the HTML (in system metrics section)
    if "System Metrics" in content and pool_stats_html not in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "System Metrics" in line and "</div>" in lines[i+10:i+20]:
                # Find the end of the system metrics row
                j = i + 1
                while j < len(lines) and "</div> <!-- row -->" not in lines[j]:
                    j += 1
                if j < len(lines):
                    # Insert before the closing row div
                    lines.insert(j, pool_stats_html)
                    break
        content = '\n'.join(lines)
    
    # Add the JavaScript
    if "updatePoolStats" not in content:
        # Find where to add the script (before closing </script> tag)
        lines = content.split('\n')
        for i in range(len(lines) - 1, 0, -1):
            if "</script>" in lines[i] and "setInterval" in '\n'.join(lines[i-20:i]):
                lines.insert(i, pool_stats_js)
                break
        content = '\n'.join(lines)
    
    with open(dashboard_file, 'w') as f:
        f.write(content)
        
    print("✓ Added pool stats display to dashboard")


if __name__ == "__main__":
    add_pool_stats_endpoint()
    add_dashboard_display()
    print("\nConnection pool monitoring endpoints added successfully!")