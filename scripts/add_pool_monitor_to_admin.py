#!/usr/bin/env python3
"""
Add connection pool monitoring to admin dashboard
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def add_pool_monitor_to_admin():
    """Add connection pool monitoring section to admin dashboard"""
    
    admin_file = Path(__file__).parent.parent / "src" / "dashboard" / "templates" / "admin_dashboard.html"
    
    if not admin_file.exists():
        print(f"Admin dashboard not found: {admin_file}")
        return False
        
    print(f"Adding connection pool monitor to {admin_file}")
    
    with open(admin_file, 'r') as f:
        content = f.read()
    
    # Add CSS for pool monitor
    pool_monitor_css = '''
        /* Connection Pool Monitor Styles */
        .pool-monitor {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 165, 0, 0.3);
        }
        
        .pool-monitor h3 {
            color: #ffa500;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .pool-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .pool-stat-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .pool-stat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .pool-name {
            font-weight: bold;
            color: #4CAF50;
        }
        
        .pool-utilization {
            font-size: 1.2rem;
            font-weight: bold;
        }
        
        .pool-utilization.high {
            color: #ff4444;
        }
        
        .pool-utilization.medium {
            color: #ffa500;
        }
        
        .pool-utilization.low {
            color: #4CAF50;
        }
        
        .pool-progress {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            height: 10px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        
        .pool-progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
            transition: width 0.3s ease;
        }
        
        .pool-progress-bar.high {
            background: linear-gradient(90deg, #ff4444 0%, #ff6666 100%);
        }
        
        .pool-progress-bar.medium {
            background: linear-gradient(90deg, #ffa500 0%, #ffcc00 100%);
        }
        
        .pool-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            margin-top: 0.5rem;
            font-size: 0.85rem;
            color: #aaa;
        }
        
        .pool-detail-item {
            display: flex;
            justify-content: space-between;
        }
        
        .pool-monitor-controls {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .pool-monitor-btn {
            background: rgba(255, 165, 0, 0.2);
            border: 1px solid #ffa500;
            color: #ffa500;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .pool-monitor-btn:hover {
            background: rgba(255, 165, 0, 0.3);
            transform: translateY(-2px);
        }'''
    
    # Add HTML for pool monitor section
    pool_monitor_html = '''
    <!-- Connection Pool Monitor -->
    <div class="pool-monitor">
        <h3>
            <i class="icon">🔌</i>
            Connection Pool Monitor
            <span id="poolUpdateTime" style="font-size: 0.8rem; color: #aaa; margin-left: auto;"></span>
        </h3>
        
        <div id="poolStatsContainer">
            <div style="text-align: center; padding: 2rem;">
                <div class="spinner"></div>
                <p style="margin-top: 1rem; color: #aaa;">Loading connection pool statistics...</p>
            </div>
        </div>
        
        <div class="pool-monitor-controls">
            <button class="pool-monitor-btn" onclick="refreshPoolStats()">
                <i class="icon">🔄</i> Refresh
            </button>
            <button class="pool-monitor-btn" onclick="exportPoolStats()">
                <i class="icon">💾</i> Export Stats
            </button>
            <select id="poolStatsDuration" class="pool-monitor-btn" onchange="refreshPoolStats()" style="background: transparent;">
                <option value="5">Last 5 minutes</option>
                <option value="15">Last 15 minutes</option>
                <option value="60" selected>Last 1 hour</option>
                <option value="1440">Last 24 hours</option>
            </select>
        </div>
    </div>'''
    
    # Add JavaScript for pool monitor
    pool_monitor_js = '''
    // Connection Pool Monitor Functions
    let poolStatsInterval = null;
    
    async function loadPoolStats() {
        try {
            const duration = document.getElementById('poolStatsDuration').value;
            const response = await fetch(`/api/pool-stats?duration=${duration}`);
            const data = await response.json();
            
            if (data.success) {
                displayPoolStats(data);
                document.getElementById('poolUpdateTime').textContent = 
                    `Last updated: ${new Date().toLocaleTimeString()}`;
            } else {
                console.error('Failed to load pool stats:', data.error);
            }
        } catch (error) {
            console.error('Error loading pool stats:', error);
            document.getElementById('poolStatsContainer').innerHTML = 
                '<div style="text-align: center; color: #ff4444;">Failed to load pool statistics</div>';
        }
    }
    
    function displayPoolStats(data) {
        const container = document.getElementById('poolStatsContainer');
        
        if (!data.current_stats || Object.keys(data.current_stats).length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #aaa;">No active connections</div>';
            return;
        }
        
        let html = '<div class="pool-stats-grid">';
        
        for (const [name, stats] of Object.entries(data.current_stats)) {
            const utilization = stats.pool_utilization || 0;
            const utilClass = utilization > 80 ? 'high' : utilization > 60 ? 'medium' : 'low';
            
            // Get summary data if available
            const summary = data.summaries[name] || {};
            
            html += `
                <div class="pool-stat-card">
                    <div class="pool-stat-header">
                        <span class="pool-name">${name}</span>
                        <span class="pool-utilization ${utilClass}">${utilization}%</span>
                    </div>
                    
                    <div class="pool-progress">
                        <div class="pool-progress-bar ${utilClass}" style="width: ${utilization}%"></div>
                    </div>
                    
                    <div class="pool-details">
                        <div class="pool-detail-item">
                            <span>Active:</span>
                            <span>${stats.active_connections}/${stats.total_connections}</span>
                        </div>
                        <div class="pool-detail-item">
                            <span>Idle:</span>
                            <span>${stats.idle_connections}</span>
                        </div>
                        <div class="pool-detail-item">
                            <span>Pending:</span>
                            <span>${stats.pending_connections}</span>
                        </div>
                        <div class="pool-detail-item">
                            <span>Req/sec:</span>
                            <span>${stats.requests_per_second}</span>
                        </div>
                    </div>
                    
                    ${summary.average_utilization ? `
                        <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.1);">
                            <div style="font-size: 0.8rem; color: #888;">
                                Avg: ${summary.average_utilization.toFixed(1)}% | 
                                Max: ${summary.max_utilization.toFixed(1)}% | 
                                Samples: ${summary.samples}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
    
    function refreshPoolStats() {
        loadPoolStats();
    }
    
    async function exportPoolStats() {
        try {
            const response = await fetch('/api/pool-stats/export');
            const data = await response.json();
            
            if (data.success) {
                // Create download link
                const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `pool_stats_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                alert('Pool statistics exported successfully!');
            }
        } catch (error) {
            console.error('Error exporting pool stats:', error);
            alert('Failed to export pool statistics');
        }
    }
    
    // Auto-refresh pool stats every 30 seconds
    function startPoolStatsMonitoring() {
        loadPoolStats();
        if (poolStatsInterval) {
            clearInterval(poolStatsInterval);
        }
        poolStatsInterval = setInterval(loadPoolStats, 30000);
    }
    
    // Add to page initialization
    document.addEventListener('DOMContentLoaded', function() {
        startPoolStatsMonitoring();
    });'''
    
    # Insert CSS into style section
    if pool_monitor_css not in content:
        style_end = content.find('</style>')
        if style_end > 0:
            content = content[:style_end] + pool_monitor_css + '\n    ' + content[style_end:]
    
    # Insert HTML after system metrics section
    if pool_monitor_html not in content:
        # Find a good place to insert (after system resources or before logs)
        insert_marker = "<!-- System Resources -->"
        if insert_marker in content:
            # Find the end of the system resources section
            marker_pos = content.find(insert_marker)
            # Find the next section
            next_section = content.find("<!--", marker_pos + len(insert_marker))
            if next_section > 0:
                content = content[:next_section] + pool_monitor_html + '\n\n    ' + content[next_section:]
        else:
            # Insert before closing main container
            main_close = content.find('</div> <!-- main-container -->')
            if main_close > 0:
                content = content[:main_close] + pool_monitor_html + '\n    ' + content[main_close:]
    
    # Insert JavaScript before closing script tag
    if "loadPoolStats" not in content:
        script_close = content.rfind('</script>')
        if script_close > 0:
            content = content[:script_close] + '\n' + pool_monitor_js + '\n    ' + content[script_close:]
    
    # Write back
    with open(admin_file, 'w') as f:
        f.write(content)
        
    print("✓ Added connection pool monitor to admin dashboard")
    return True


def main():
    """Main function"""
    success = add_pool_monitor_to_admin()
    
    if success:
        print("\nConnection pool monitoring has been added to the admin dashboard!")
        print("\nFeatures added:")
        print("- Real-time connection pool statistics")
        print("- Visual utilization indicators")
        print("- Auto-refresh every 30 seconds")
        print("- Export functionality")
        print("- Historical statistics (5min, 15min, 1h, 24h)")
        print("\nThe monitor will show:")
        print("- Active/Total connections")
        print("- Idle and pending connections")
        print("- Requests per second")
        print("- Average and max utilization")
    else:
        print("\nFailed to add connection pool monitoring to admin dashboard")


if __name__ == "__main__":
    main()