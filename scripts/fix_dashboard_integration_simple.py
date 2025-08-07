#!/usr/bin/env python3
"""
Simple fix: Update dashboard routes to fetch from main service API
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def update_mobile_data_endpoint():
    """Update the mobile-data endpoint to fetch from main service first"""
    
    dashboard_file = Path(__file__).parent.parent / "src" / "api" / "routes" / "dashboard.py"
    
    # Read the file
    with open(dashboard_file, 'r') as f:
        lines = f.readlines()
    
    # Find the mobile-data endpoint
    for i, line in enumerate(lines):
        if 'async def get_mobile_dashboard_data()' in line:
            # Find where it checks for integration
            for j in range(i, min(i + 50, len(lines))):
                if 'if not integration:' in lines[j]:
                    # Add code to try fetching from main service first
                    indent = '        '  # 8 spaces
                    new_code = f'''        if not integration:
            response["status"] = "no_integration"
            
            # Try to get data from main service API
            try:
                async with aiohttp.ClientSession() as session:
                    # Get overview data from main service
                    async with session.get("http://localhost:8003/api/dashboard/overview", timeout=2) as resp:
                        if resp.status == 200:
                            overview = await resp.json()
                            if overview.get('signals'):
                                # We have data from main service!
                                response["status"] = "main_service_proxy"
                                
                                # Extract signals data
                                signals = []
                                # Try to get detailed signals
                                try:
                                    async with session.get("http://localhost:8003/api/signals", timeout=2) as sig_resp:
                                        if sig_resp.status == 200:
                                            signals = await sig_resp.json()
                                except:
                                    pass
                                
                                # Process signals for confluence scores
                                if signals:
                                    confluence_scores = []
                                    for signal in signals[:15]:
                                        confluence_scores.append({{
                                            "symbol": signal.get('symbol', ''),
                                            "score": round(signal.get('score', 50), 2),
                                            "price": signal.get('price', 0),
                                            "change_24h": round(signal.get('change_24h', 0), 2),
                                            "volume_24h": signal.get('volume', 0),
                                            "components": signal.get('components', {{}})
                                        }})
                                    response["confluence_scores"] = confluence_scores
                                    
                                    # Extract top movers from signals
                                    sorted_by_change = sorted(signals, key=lambda x: x.get('change_24h', 0))
                                    response["top_movers"]["losers"] = [
                                        {{"symbol": s['symbol'], "change": round(s['change_24h'], 2)}} 
                                        for s in sorted_by_change[:5] if s.get('change_24h', 0) < 0
                                    ]
                                    response["top_movers"]["gainers"] = [
                                        {{"symbol": s['symbol'], "change": round(s['change_24h'], 2)}} 
                                        for s in sorted_by_change[-5:] if s.get('change_24h', 0) > 0
                                    ]
                                    
                                    # If we have some data from main service, return it
                                    if response["confluence_scores"] or response["top_movers"]["gainers"]:
                                        return response
            except Exception as e:
                logger.debug(f"Could not fetch from main service: {{e}}")
            
            # Continue with Bybit fallback
'''
                    
                    # Replace the simple assignment with our enhanced version
                    # Find the end of the if statement and insert our code
                    lines[j] = new_code
                    break
            break
    
    # Write back
    with open(dashboard_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Updated mobile-data endpoint to use main service proxy")

def update_overview_endpoint():
    """Make the overview endpoint try main service first"""
    
    dashboard_file = Path(__file__).parent.parent / "src" / "api" / "routes" / "dashboard.py"
    
    # Read the file
    with open(dashboard_file, 'r') as f:
        content = f.read()
    
    # Find the overview endpoint
    overview_code = '''@router.get("/overview")
async def get_dashboard_overview() -> Dict[str, Any]:
    """Get comprehensive dashboard overview with aggregated data."""
    try:
        # First try to get from main service
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8003/api/dashboard/overview", timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('status') == 'success':
                            return data
        except Exception as e:
            logger.debug(f"Could not fetch overview from main service: {e}")
        
        # Fallback to integration service
        integration = get_dashboard_integration()'''
    
    # Replace the existing overview endpoint
    if '@router.get("/overview")' in content:
        start_idx = content.find('@router.get("/overview")')
        end_idx = content.find('integration = get_dashboard_integration()', start_idx)
        if start_idx != -1 and end_idx != -1:
            # Find the actual end of the line
            end_idx = content.find('\n', end_idx)
            # Replace
            content = content[:start_idx] + overview_code + content[end_idx:]
            
            # Write back
            with open(dashboard_file, 'w') as f:
                f.write(content)
                
            print("✅ Updated overview endpoint to use main service proxy")

if __name__ == "__main__":
    print("Updating dashboard endpoints to use main service data...")
    update_mobile_data_endpoint()
    update_overview_endpoint()
    
    print("\nTo deploy:")
    print("1. scp src/api/routes/dashboard.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/")
    print("2. ssh vps 'sudo systemctl restart virtuoso-web'")
    print("\nThis will make the web server fetch data from the main service API when available.")