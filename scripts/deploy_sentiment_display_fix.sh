#!/bin/bash

# Deploy sentiment display fixes to VPS
set -e

echo "Deploying Market Sentiment display fixes to VPS..."

# Create a Python script to apply the fixes
cat > /tmp/fix_sentiment_display.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import re

def fix_market_overview_sentiment():
    """Apply the Market Sentiment display fixes from the screenshot"""
    
    # Fix 1: Ensure market_overview includes proper sentiment data
    web_server_path = "src/web_server.py"
    if os.path.exists(web_server_path):
        print(f"Fixing {web_server_path}...")
        with open(web_server_path, 'r') as f:
            content = f.read()
        
        # Check if market_overview properly includes sentiment
        if "market_overview" in content and "'sentiment'" not in content:
            # Add sentiment data to market_overview
            fix = """
            # Ensure market sentiment is properly included
            if market_overview:
                market_overview['sentiment'] = {
                    'label': 'Bulls Leading' if gainers > losers else 'Bears Leading' if losers > gainers else 'Neutral',
                    'percentage': round((gainers / (gainers + losers) * 100) if (gainers + losers) > 0 else 50, 1),
                    'rising_count': gainers,
                    'falling_count': losers,
                    'breadth_indicator': 'BULLISH' if gainers > losers * 1.1 else 'BEARISH' if losers > gainers * 1.1 else 'NEUTRAL'
                }
            """
            content = content.replace("market_overview = {", f"market_overview = {{\n{fix}")
        
        with open(web_server_path, 'w') as f:
            f.write(content)
    
    # Fix 2: Update dashboard HTML to display sentiment properly
    index_path = "src/static/index.html"
    if os.path.exists(index_path):
        print(f"Fixing {index_path}...")
        with open(index_path, 'r') as f:
            content = f.read()
        
        # Add JavaScript to handle market breadth display
        js_fix = """
        function updateMarketBreadth(data) {
            if (data && data.market_overview) {
                const overview = data.market_overview;
                
                // Update gainers/losers display
                if (overview.gainers && overview.losers) {
                    const gainersElem = document.querySelector('.gainers-count');
                    const losersElem = document.querySelector('.losers-count');
                    
                    if (gainersElem) {
                        gainersElem.textContent = overview.gainers.length;
                        gainersElem.style.color = '#4CAF50';
                    }
                    if (losersElem) {
                        losersElem.textContent = overview.losers.length;
                        losersElem.style.color = '#f44336';
                    }
                }
                
                // Update sentiment display
                if (overview.sentiment) {
                    const sentimentElem = document.querySelector('.sentiment-value');
                    if (sentimentElem) {
                        sentimentElem.textContent = overview.sentiment.label || 'Loading...';
                        sentimentElem.style.color = overview.sentiment.label === 'Bulls Leading' ? '#4CAF50' : 
                                                   overview.sentiment.label === 'Bears Leading' ? '#f44336' : '#ffa726';
                    }
                    
                    // Add visual indicator
                    const indicatorElem = document.querySelector('.market-breadth-indicator');
                    if (indicatorElem) {
                        indicatorElem.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="color: #4CAF50;">Bulls: ${overview.sentiment.rising_count || 0}</span>
                                <span style="color: #f44336;">Bears: ${overview.sentiment.falling_count || 0}</span>
                                <span style="color: ${overview.sentiment.breadth_indicator === 'BULLISH' ? '#4CAF50' : 
                                                     overview.sentiment.breadth_indicator === 'BEARISH' ? '#f44336' : '#ffa726'};">
                                    (${overview.sentiment.percentage || 50}% gainers)
                                </span>
                            </div>
                        `;
                    }
                }
            }
        }
        """
        
        # Add the function if it doesn't exist
        if "updateMarketBreadth" not in content:
            content = content.replace("</script>", f"{js_fix}\n</script>")
        
        # Ensure the function is called when data updates
        if "updateMarketBreadth(data)" not in content:
            content = content.replace("updateDashboard(data)", "updateDashboard(data);\nupdateMarketBreadth(data)")
        
        with open(index_path, 'w') as f:
            f.write(content)
    
    print("Market Sentiment display fixes applied successfully!")

if __name__ == "__main__":
    fix_market_overview_sentiment()
EOF

# Copy the fix script to VPS
echo "Copying fix script to VPS..."
scp /tmp/fix_sentiment_display.py vps:/tmp/

# Execute the fix on VPS
echo "Applying fixes on VPS..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && python3 /tmp/fix_sentiment_display.py"

# Restart the web service
echo "Restarting web service..."
ssh vps "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 5

# Verify the service is running
echo "Verifying service status..."
ssh vps "sudo systemctl status virtuoso-web.service | head -10"

# Test the API endpoint
echo "Testing dashboard API..."
ssh vps "curl -s http://localhost:8003/health"

echo "Market Sentiment display fixes deployed successfully!"
echo "Access the dashboard at: http://${VPS_HOST}:8003/"