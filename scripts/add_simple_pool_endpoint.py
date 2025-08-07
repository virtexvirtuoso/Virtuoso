#!/usr/bin/env python3
"""
Add simple connection stats endpoint to web_server.py
"""

import sys
from pathlib import Path

# Add project root to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

# Read web_server.py
web_server_file = Path(__file__).parent.parent / "src" / "web_server.py"

with open(web_server_file, 'r') as f:
    content = f.read()

# Add the endpoint
endpoint_code = '''
@app.route('/api/connection-stats')
async def connection_stats(request):
    """Get simple connection statistics"""
    try:
        # Read the latest stats from the monitor log
        log_file = '/tmp/virtuoso_connections.log'
        stats = {
            'current': {},
            'history': []
        }
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()[-10:]  # Last 10 entries
                
            for line in lines:
                if '|' in line:
                    parts = line.strip().split('|')
                    if len(parts) >= 6:
                        timestamp = parts[0].strip()
                        connections = parts[2].strip()
                        cpu_mem = parts[5].strip() if len(parts) > 5 else ''
                        
                        entry = {
                            'timestamp': timestamp,
                            'connections': connections,
                            'cpu_mem': cpu_mem
                        }
                        stats['history'].append(entry)
                        
            # Parse the latest entry for current stats
            if stats['history']:
                latest = stats['history'][-1]
                # Extract numbers from connections string
                import re
                conn_match = re.search(r'Connections: (\d+)/(\d+) \(Bybit: (\d+)\)', latest['connections'])
                if conn_match:
                    stats['current'] = {
                        'established': int(conn_match.group(1)),
                        'total': int(conn_match.group(2)),
                        'bybit': int(conn_match.group(3)),
                        'timestamp': latest['timestamp']
                    }
                    
                # Extract CPU and memory
                cpu_match = re.search(r'CPU: ([\d.]+)%', latest['cpu_mem'])
                mem_match = re.search(r'Mem: (\d+)MB', latest['cpu_mem'])
                if cpu_match:
                    stats['current']['cpu_percent'] = float(cpu_match.group(1))
                if mem_match:
                    stats['current']['memory_mb'] = int(mem_match.group(1))
        
        return json({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        return json({
            'success': False,
            'error': str(e)
        }, status=500)'''

# Find where to insert (after /api/health endpoint)
if '/api/connection-stats' not in content:
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
        
        content = '\n'.join(lines)

# Add import for re if not present
if 'import re' not in content:
    # Find where to add the import
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'import os' in line:
            lines.insert(i + 1, 'import re')
            break
    content = '\n'.join(lines)

# Write back
with open(web_server_file, 'w') as f:
    f.write(content)

print("Added connection stats endpoint to web server")