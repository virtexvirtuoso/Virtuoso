#!/usr/bin/env python3
"""
Comprehensive fix for dashboard display issues
Ensures market sentiment data is properly displayed
"""

import os
import re

def fix_dashboard_frontend():
    """Fix the frontend JavaScript to properly display market data"""
    
    # Create updated dashboard JavaScript
    js_content = '''// Dashboard Enhanced - Fixed for Market Sentiment Display
(function() {
    'use strict';
    
    let updateInterval = null;
    let lastUpdate = null;
    
    // Main dashboard update function
    async function updateDashboard() {
        try {
            const response = await fetch('/api/dashboard/data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Dashboard data received:', data);
            
            // Update all dashboard sections
            updateMarketOverview(data.market_overview || {});
            updateMarketSentiment(data.market_overview || {});
            updateSignals(data.signals || []);
            updateTopMovers(data.top_movers || {});
            updateConfluenceScores(data.confluence_scores || []);
            
            // Update timestamp
            lastUpdate = new Date();
            updateTimestamp();
            
        } catch (error) {
            console.error('Error updating dashboard:', error);
            showError('Failed to fetch dashboard data');
        }
    }
    
    // Update market overview section
    function updateMarketOverview(overview) {
        // Market Regime
        const regimeElem = document.querySelector('.market-regime');
        if (regimeElem) {
            regimeElem.textContent = overview.market_regime || 'NEUTRAL';
            regimeElem.className = 'market-regime ' + (overview.market_regime || 'neutral').toLowerCase();
        }
        
        // Trend Strength
        const trendBar = document.querySelector('.trend-strength-bar');
        if (trendBar) {
            const strength = overview.trend_strength || 50;
            trendBar.style.width = strength + '%';
            const trendValue = document.querySelector('.trend-strength-value');
            if (trendValue) {
                trendValue.textContent = strength.toFixed(0);
            }
        }
        
        // Volatility
        const volatilityElem = document.querySelector('.volatility-value');
        if (volatilityElem) {
            const vol = overview.volatility || 0;
            volatilityElem.textContent = vol.toFixed(1) + '% vs ' + vol.toFixed(1) + '%';
            const volLabel = document.querySelector('.volatility-label');
            if (volLabel) {
                volLabel.textContent = vol < 10 ? 'VERY LOW' : vol < 20 ? 'LOW' : vol < 30 ? 'MEDIUM' : 'HIGH';
            }
        }
        
        // BTC Dominance
        const btcDomElem = document.querySelector('.btc-dominance-value');
        if (btcDomElem) {
            btcDomElem.textContent = (overview.btc_dominance || 0).toFixed(1) + '%';
        }
        
        // 24H Volume
        const volumeElem = document.querySelector('.volume-24h-value');
        if (volumeElem) {
            const volume = overview.total_volume_24h || 0;
            volumeElem.textContent = '$' + formatNumber(volume);
        }
    }
    
    // Update market sentiment section - CRITICAL FIX
    function updateMarketSentiment(overview) {
        const gainers = overview.gainers || 0;
        const losers = overview.losers || 0;
        const total = gainers + losers;
        
        // Update sentiment label
        const sentimentLabel = document.querySelector('.sentiment-label, .market-sentiment-label');
        if (sentimentLabel) {
            if (total === 0) {
                sentimentLabel.textContent = 'No Data';
                sentimentLabel.className = 'sentiment-label neutral';
            } else {
                const label = gainers > losers ? 'Bulls Leading' : losers > gainers ? 'Bears Leading' : 'Neutral';
                sentimentLabel.textContent = label;
                sentimentLabel.className = 'sentiment-label ' + (gainers > losers ? 'bullish' : losers > gainers ? 'bearish' : 'neutral');
            }
        }
        
        // Update progress bar
        const progressBar = document.querySelector('.sentiment-progress, .market-breadth-bar');
        if (progressBar) {
            const greenBar = progressBar.querySelector('.green-bar, .gainers-bar');
            const redBar = progressBar.querySelector('.red-bar, .losers-bar');
            
            if (greenBar && redBar) {
                if (total > 0) {
                    const gainersPercent = (gainers / total) * 100;
                    const losersPercent = (losers / total) * 100;
                    
                    greenBar.style.width = gainersPercent + '%';
                    redBar.style.width = losersPercent + '%';
                    
                    // Update percentages
                    const greenText = greenBar.querySelector('.percent-text, span');
                    const redText = redBar.querySelector('.percent-text, span');
                    
                    if (greenText) greenText.textContent = gainersPercent.toFixed(0) + '%';
                    if (redText) redText.textContent = losersPercent.toFixed(0) + '%';
                } else {
                    greenBar.style.width = '50%';
                    redBar.style.width = '50%';
                }
            }
        }
        
        // Update counts
        const gainersCount = document.querySelector('.gainers-count, .rising-count');
        const losersCount = document.querySelector('.losers-count, .falling-count');
        
        if (gainersCount) {
            gainersCount.textContent = gainers + ' rising';
            gainersCount.style.color = '#4CAF50';
        }
        
        if (losersCount) {
            losersCount.textContent = losers + ' falling';
            losersCount.style.color = '#f44336';
        }
        
        // Alternative selectors for different dashboard versions
        const marketSentimentValue = document.querySelector('.sentiment-value');
        if (marketSentimentValue) {
            if (total === 0) {
                marketSentimentValue.textContent = 'No Data';
            } else {
                marketSentimentValue.textContent = gainers > losers ? 'Bullish' : losers > gainers ? 'Bearish' : 'Neutral';
            }
        }
    }
    
    // Update signals section
    function updateSignals(signals) {
        const signalsContainer = document.querySelector('.signals-list, .active-signals');
        if (!signalsContainer) return;
        
        signalsContainer.innerHTML = '';
        
        if (signals.length === 0) {
            signalsContainer.innerHTML = '<div class="no-data">No active signals</div>';
            return;
        }
        
        signals.slice(0, 5).forEach(signal => {
            const signalElem = document.createElement('div');
            signalElem.className = 'signal-item ' + (signal.type || 'neutral').toLowerCase();
            signalElem.innerHTML = `
                <span class="signal-symbol">${signal.symbol || 'N/A'}</span>
                <span class="signal-type">${signal.type || 'N/A'}</span>
                <span class="signal-score">${(signal.score || 0).toFixed(1)}</span>
            `;
            signalsContainer.appendChild(signalElem);
        });
    }
    
    // Update top movers section
    function updateTopMovers(movers) {
        const gainersContainer = document.querySelector('.top-gainers, .gainers-list');
        const losersContainer = document.querySelector('.top-losers, .losers-list');
        
        if (gainersContainer) {
            gainersContainer.innerHTML = '';
            const gainers = movers.gainers || [];
            
            if (gainers.length === 0) {
                gainersContainer.innerHTML = '<div class="no-data">No gainers</div>';
            } else {
                gainers.slice(0, 5).forEach(item => {
                    const elem = document.createElement('div');
                    elem.className = 'mover-item gainer';
                    elem.innerHTML = `
                        <span class="symbol">${item.symbol || 'N/A'}</span>
                        <span class="change">+${(item.change_24h || 0).toFixed(2)}%</span>
                    `;
                    gainersContainer.appendChild(elem);
                });
            }
        }
        
        if (losersContainer) {
            losersContainer.innerHTML = '';
            const losers = movers.losers || [];
            
            if (losers.length === 0) {
                losersContainer.innerHTML = '<div class="no-data">No losers</div>';
            } else {
                losers.slice(0, 5).forEach(item => {
                    const elem = document.createElement('div');
                    elem.className = 'mover-item loser';
                    elem.innerHTML = `
                        <span class="symbol">${item.symbol || 'N/A'}</span>
                        <span class="change">${(item.change_24h || 0).toFixed(2)}%</span>
                    `;
                    losersContainer.appendChild(elem);
                });
            }
        }
    }
    
    // Update confluence scores
    function updateConfluenceScores(scores) {
        const scoresContainer = document.querySelector('.confluence-scores, .scores-list');
        if (!scoresContainer) return;
        
        scoresContainer.innerHTML = '';
        
        if (scores.length === 0) {
            scoresContainer.innerHTML = '<div class="no-data">No symbols data available</div>';
            return;
        }
        
        scores.slice(0, 10).forEach(item => {
            const scoreElem = document.createElement('div');
            scoreElem.className = 'score-item';
            scoreElem.innerHTML = `
                <span class="symbol">${item.symbol || 'N/A'}</span>
                <span class="score">${(item.confluence_score || 0).toFixed(1)}</span>
                <span class="signal ${(item.signal || 'neutral').toLowerCase()}">${item.signal || 'NEUTRAL'}</span>
            `;
            scoresContainer.appendChild(scoreElem);
        });
    }
    
    // Update timestamp
    function updateTimestamp() {
        const timestampElems = document.querySelectorAll('.updated-time, .last-update');
        timestampElems.forEach(elem => {
            if (lastUpdate) {
                elem.textContent = 'Updated: ' + lastUpdate.toLocaleTimeString();
            }
        });
    }
    
    // Format large numbers
    function formatNumber(num) {
        if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
        return num.toFixed(2);
    }
    
    // Show error message
    function showError(message) {
        console.error('Dashboard Error:', message);
        // You can add visual error notification here
    }
    
    // Initialize dashboard
    function init() {
        console.log('Initializing dashboard...');
        
        // Initial update
        updateDashboard();
        
        // Set up auto-refresh every 15 seconds
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        updateInterval = setInterval(updateDashboard, 15000);
        
        // Set up manual refresh button if exists
        const refreshBtn = document.querySelector('.refresh-btn, .reload-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', updateDashboard);
        }
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Export for debugging
    window.dashboardDebug = {
        updateDashboard,
        updateMarketSentiment,
        lastUpdate: () => lastUpdate
    };
})();
'''
    
    # Save the fixed JavaScript
    with open('src/static/js/dashboard-enhanced-fixed.js', 'w') as f:
        f.write(js_content)
    
    print("Created fixed dashboard JavaScript")
    
    # Create deployment script
    deploy_script = '''#!/bin/bash
set -e

echo "Deploying dashboard display fixes..."

# Backup current file
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && cp src/static/js/dashboard-enhanced.js src/static/js/dashboard-enhanced.js.backup.$(date +%s)"

# Copy fixed JavaScript
scp src/static/js/dashboard-enhanced-fixed.js vps:/home/linuxuser/trading/Virtuoso_ccxt/src/static/js/dashboard-enhanced.js

# Clear browser cache by adding version parameter
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i 's/dashboard-enhanced\\.js/dashboard-enhanced.js?v='$(date +%s)'/g' src/static/index.html 2>/dev/null || true"

# Restart web service to ensure changes take effect
ssh vps "sudo systemctl restart virtuoso-web.service"

echo "Dashboard display fixes deployed!"
echo ""
echo "Testing dashboard data..."
curl -s http://5.223.63.4:8002/api/dashboard/data | python3 -c "
import json, sys
data = json.load(sys.stdin)
mo = data.get('market_overview', {})
print(f'API Response: Gainers={mo.get(\"gainers\", 0)}, Losers={mo.get(\"losers\", 0)}')
"

echo ""
echo "✅ Dashboard should now display market sentiment correctly!"
echo "🌐 View at: http://5.223.63.4:8002/"
'''
    
    with open('scripts/deploy_dashboard_fix.sh', 'w') as f:
        f.write(deploy_script)
    
    os.chmod('scripts/deploy_dashboard_fix.sh', 0o755)
    print("Created deployment script: scripts/deploy_dashboard_fix.sh")
    
    return True

if __name__ == "__main__":
    print("Creating comprehensive dashboard fix...")
    
    if fix_dashboard_frontend():
        print("\n✅ Dashboard fixes created successfully!")
        print("\nTo deploy, run:")
        print("  ./scripts/deploy_dashboard_fix.sh")
    else:
        print("\n❌ Failed to create dashboard fixes")