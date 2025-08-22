#!/usr/bin/env python3
"""
Test the confluence analysis functionality locally
"""

import asyncio
import webbrowser
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

# Serve the dashboard templates
@app.get("/")
async def root():
    """Serve a simple test page with the Analysis button"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Confluence Analysis Test</title>
        <style>
            body {
                background: #1a1a1a;
                color: #ffbf00;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                margin: 0;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                margin-bottom: 30px;
            }
            .symbol-card {
                background: #2a2a2a;
                border: 1px solid #ffbf00;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .symbol-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .symbol-name {
                font-size: 24px;
                font-weight: bold;
            }
            .score {
                font-size: 28px;
                font-weight: bold;
                color: #00ff88;
            }
            .metrics {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 20px;
            }
            .metric {
                background: #1a1a1a;
                padding: 10px;
                border-radius: 8px;
            }
            .metric-label {
                font-size: 12px;
                color: #888;
                margin-bottom: 5px;
            }
            .metric-value {
                font-size: 18px;
                font-weight: bold;
            }
            .buttons {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .btn {
                padding: 12px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-primary {
                background: #ffbf00;
                color: #1a1a1a;
            }
            .btn-primary:hover {
                background: #ffd700;
                transform: scale(1.05);
            }
            .btn-secondary {
                background: transparent;
                color: #ffbf00;
                border: 2px solid #ffbf00;
            }
            .btn-secondary:hover {
                background: #ffbf00;
                color: #1a1a1a;
                transform: scale(1.05);
            }
            .info {
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                background: #2a2a2a;
                border-radius: 12px;
                border: 1px solid #444;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Confluence Analysis Demo</h1>
            
            <div class="symbol-card">
                <div class="symbol-header">
                    <div class="symbol-name">BTCUSDT</div>
                    <div class="score">85</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-label">Price</div>
                        <div class="metric-value">$97,245</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">24h Change</div>
                        <div class="metric-value" style="color: #00ff88;">+2.45%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Volume</div>
                        <div class="metric-value">$2.3B</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Momentum</div>
                        <div class="metric-value">Strong</div>
                    </div>
                </div>
                <div class="buttons">
                    <button class="btn btn-primary" onclick="alert('Trade button - would open exchange')">Trade</button>
                    <button class="btn btn-secondary" onclick="viewConfluenceAnalysis('BTCUSDT')">Analysis</button>
                </div>
            </div>
            
            <div class="symbol-card">
                <div class="symbol-header">
                    <div class="symbol-name">ETHUSDT</div>
                    <div class="score">72</div>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-label">Price</div>
                        <div class="metric-value">$3,420</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">24h Change</div>
                        <div class="metric-value" style="color: #ff4444;">-1.23%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Volume</div>
                        <div class="metric-value">$1.1B</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Momentum</div>
                        <div class="metric-value">Neutral</div>
                    </div>
                </div>
                <div class="buttons">
                    <button class="btn btn-primary" onclick="alert('Trade button - would open exchange')">Trade</button>
                    <button class="btn btn-secondary" onclick="viewConfluenceAnalysis('ETHUSDT')">Analysis</button>
                </div>
            </div>
            
            <div class="info">
                <h3>📌 How it works:</h3>
                <p style="margin-top: 10px;">Click the <strong>"Analysis"</strong> button on any symbol to see the detailed confluence analysis in a terminal-style view.</p>
                <p style="margin-top: 10px; color: #888;">This is the same functionality that's now deployed on your VPS mobile dashboard.</p>
            </div>
        </div>
        
        <script>
            function viewConfluenceAnalysis(symbol) {
                // Navigate to confluence analysis page
                window.location.href = `/api/dashboard/confluence-analysis-page?symbol=${symbol}`;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/dashboard/confluence-analysis-page")
async def confluence_analysis_page():
    """Serve the confluence analysis page"""
    template_path = "src/dashboard/templates/confluence_analysis.html"
    if os.path.exists(template_path):
        return FileResponse(template_path)
    else:
        # Return a simple version if template not found
        return HTMLResponse(content="<h1>Confluence Analysis Page</h1>")

def create_pretty_table(headers, rows, title=None):
    """Create a pretty ASCII table"""
    # Calculate column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    
    # Create table
    result = []
    
    if title:
        title_width = sum(widths) + 3 * (len(headers) - 1) + 4
        result.append("┌" + "─" * (title_width - 2) + "┐")
        result.append("│" + title.center(title_width - 2) + "│")
        result.append("├" + "─" * (title_width - 2) + "┤")
    
    # Header separator
    separator = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    result.append(separator)
    
    # Headers
    header_row = "│" + "│".join(f" {str(h).ljust(w)} " for h, w in zip(headers, widths)) + "│"
    result.append(header_row)
    
    # Header bottom
    separator = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    result.append(separator)
    
    # Rows
    for row in rows:
        row_str = "│" + "│".join(f" {str(cell).ljust(w)} " for cell, w in zip(row, widths)) + "│"
        result.append(row_str)
    
    # Bottom
    separator = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"
    result.append(separator)
    
    return "\n".join(result)

@app.get("/api/dashboard/confluence-analysis/{symbol}")
async def get_confluence_analysis(symbol: str):
    """Return comprehensive confluence analysis with pretty tables and full interpretations"""
    
    # Mock data based on symbol
    is_btc = symbol == 'BTCUSDT'
    
    # Component scores and interpretations
    components_data = {
        'Technical Analysis': {
            'score': 85 if is_btc else 72,
            'weight': '20%',
            'interpretation': 'Technical indicators show strong bullish trend with RSI approaching overbought levels. MACD confirms bullish crossover with strong momentum. Moving averages aligned bullishly (20>50>200 MA).' if is_btc else 'Technical indicators show mixed signals with slight bearish bias. RSI in neutral zone but trending lower. MACD showing bearish divergence with weakening momentum.',
            'components': {
                'RSI(14)': 68.5 if is_btc else 45.2,
                'MACD': 125 if is_btc else -45,
                'ADX': 45.2 if is_btc else 32.1,
                'Moving Averages': 85 if is_btc else 55,
                'Awesome Oscillator': 72 if is_btc else 48
            }
        },
        'Volume Analysis': {
            'score': 82 if is_btc else 68,
            'weight': '10%',
            'interpretation': 'Volume patterns strongly support price action with significant accumulation detected. Buy/sell ratio heavily skewed toward buyers. Volume profile shows strong support at current levels.' if is_btc else 'Volume showing declining momentum with distribution patterns emerging. Sell pressure increasing with weakening buyer interest. Volume profile suggests resistance above current levels.',
            'components': {
                '24h Volume': f"${2.3 if is_btc else 1.1}B",
                'Volume Ratio': 1.35 if is_btc else 0.92,
                'Volume Profile': 'Accumulation' if is_btc else 'Distribution',
                'On-Balance Volume': 78 if is_btc else 52
            }
        },
        'Order Flow': {
            'score': 88 if is_btc else 65,
            'weight': '25%',
            'interpretation': 'Order flow analysis reveals strong institutional buying pressure with aggressive bid stacking. Low toxicity flow indicates genuine demand. Market microstructure extremely bullish.' if is_btc else 'Order flow showing mixed signals with moderate selling pressure. Increased flow toxicity suggests some distribution. Bid-ask dynamics neutral with slight ask-side pressure.',
            'components': {
                'Bid/Ask Spread': '0.01%' if is_btc else '0.03%',
                'Order Imbalance': '+15% Bid Heavy' if is_btc else '-5% Ask Heavy',
                'Flow Toxicity': 0.12 if is_btc else 0.45,
                'Large Order Impact': 'Low' if is_btc else 'Medium'
            }
        },
        'Market Sentiment': {
            'score': 78 if is_btc else 58,
            'weight': '15%',
            'interpretation': 'Market sentiment extremely bullish with fear & greed index in greed territory. Social metrics showing high engagement and positive sentiment. Funding rates indicate strong conviction.' if is_btc else 'Market sentiment neutral to slightly bearish. Fear & greed index balanced but trending negative. Social metrics showing decreased engagement with mixed sentiment.',
            'components': {
                'Fear & Greed': 72 if is_btc else 48,
                'Social Volume': '+120%' if is_btc else '+5%',
                'Funding Rate': '0.012%' if is_btc else '-0.002%',
                'Open Interest': 'Increasing' if is_btc else 'Stable'
            }
        },
        'Order Book': {
            'score': 80 if is_btc else 62,
            'weight': '20%',
            'interpretation': 'Order book depth excellent with strong bid support. Whale activity indicates accumulation phase. Microstructure patterns strongly bullish with tight spreads.' if is_btc else 'Order book showing moderate depth with balanced bid/ask. Limited whale activity observed. Microstructure neutral with normal spreads.',
            'components': {
                'Depth (2%)': f"${45 if is_btc else 18}M",
                'Whale Activity': 'High Accumulation' if is_btc else 'Quiet',
                'Spread Quality': 'Excellent' if is_btc else 'Good',
                'Book Balance': 'Bid Heavy' if is_btc else 'Neutral'
            }
        },
        'Price Structure': {
            'score': 75 if is_btc else 55,
            'weight': '10%',
            'interpretation': 'Price structure showing strong uptrend with higher highs and higher lows. Support levels holding firm with resistance being broken. Trend strength accelerating.' if is_btc else 'Price structure showing consolidation pattern with weakening trend. Support being tested with uncertain resistance levels. Trend strength declining.',
            'components': {
                'Trend Direction': 'Strong Up' if is_btc else 'Sideways',
                'Support Strength': 'Very Strong' if is_btc else 'Moderate',
                'Resistance': 'Breaking' if is_btc else 'Holding',
                'Pattern': 'Bullish Flag' if is_btc else 'Rectangle'
            }
        }
    }
    
    analysis_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CONFLUENCE ANALYSIS - {symbol}                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
OVERALL CONFLUENCE SCORE: {85 if is_btc else 72}/100

{create_pretty_table(
    ["Component", "Score", "Weight", "Contribution"],
    [
        ["Technical Analysis", f"{components_data['Technical Analysis']['score']}/100", "20%", f"{components_data['Technical Analysis']['score'] * 0.20:.1f}"],
        ["Volume Analysis", f"{components_data['Volume Analysis']['score']}/100", "10%", f"{components_data['Volume Analysis']['score'] * 0.10:.1f}"],
        ["Order Flow", f"{components_data['Order Flow']['score']}/100", "25%", f"{components_data['Order Flow']['score'] * 0.25:.1f}"],
        ["Market Sentiment", f"{components_data['Market Sentiment']['score']}/100", "15%", f"{components_data['Market Sentiment']['score'] * 0.15:.1f}"],
        ["Order Book", f"{components_data['Order Book']['score']}/100", "20%", f"{components_data['Order Book']['score'] * 0.20:.1f}"],
        ["Price Structure", f"{components_data['Price Structure']['score']}/100", "10%", f"{components_data['Price Structure']['score'] * 0.10:.1f}"],
    ],
    "COMPONENT BREAKDOWN"
)}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 📊 TECHNICAL ANALYSIS DETAILS                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Indicator", "Value", "Signal", "Strength"],
    [
        ["RSI (14)", f"{components_data['Technical Analysis']['components']['RSI(14)']}", "Bullish" if is_btc else "Neutral", "Strong" if is_btc else "Weak"],
        ["MACD", f"{components_data['Technical Analysis']['components']['MACD']}", "Buy Signal" if is_btc else "Sell Signal", "High" if is_btc else "Medium"],
        ["ADX", f"{components_data['Technical Analysis']['components']['ADX']}", "Trending" if is_btc else "Ranging", "Moderate"],
        ["Moving Averages", f"{components_data['Technical Analysis']['components']['Moving Averages']}", "Bullish Alignment" if is_btc else "Mixed", "Strong" if is_btc else "Weak"],
        ["Awesome Oscillator", f"{components_data['Technical Analysis']['components']['Awesome Oscillator']}", "Green" if is_btc else "Red", "Medium"],
    ]
)}

INTERPRETATION: {components_data['Technical Analysis']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 📈 VOLUME ANALYSIS DETAILS                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Metric", "Current", "Vs Average", "Signal"],
    [
        ["24h Volume", components_data['Volume Analysis']['components']['24h Volume'], "+45%" if is_btc else "-12%", "Bullish" if is_btc else "Bearish"],
        ["Buy/Sell Ratio", f"{components_data['Volume Analysis']['components']['Volume Ratio']}", "Above 1.0" if is_btc else "Below 1.0", "Bullish" if is_btc else "Bearish"],
        ["Volume Profile", components_data['Volume Analysis']['components']['Volume Profile'], "-", "Accumulation" if is_btc else "Distribution"],
        ["OBV", f"{components_data['Volume Analysis']['components']['On-Balance Volume']}", "Rising" if is_btc else "Falling", "Bullish" if is_btc else "Bearish"],
    ]
)}

INTERPRETATION: {components_data['Volume Analysis']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 🌊 ORDER FLOW ANALYSIS                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Metric", "Value", "Status", "Impact"],
    [
        ["Bid/Ask Spread", components_data['Order Flow']['components']['Bid/Ask Spread'], "Very Tight" if is_btc else "Normal", "Low Cost" if is_btc else "Medium Cost"],
        ["Order Imbalance", components_data['Order Flow']['components']['Order Imbalance'], "Bullish" if is_btc else "Bearish", "High" if is_btc else "Low"],
        ["Flow Toxicity", f"{components_data['Order Flow']['components']['Flow Toxicity']}", "Low" if is_btc else "Medium", "Positive" if is_btc else "Negative"],
        ["Large Orders", components_data['Order Flow']['components']['Large Order Impact'], "Supportive" if is_btc else "Neutral", "Bullish" if is_btc else "Neutral"],
    ]
)}

INTERPRETATION: {components_data['Order Flow']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 🎭 MARKET SENTIMENT ANALYSIS                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Metric", "Value", "Category", "Trend"],
    [
        ["Fear & Greed Index", f"{components_data['Market Sentiment']['components']['Fear & Greed']}", "Greed" if is_btc else "Neutral", "Rising" if is_btc else "Stable"],
        ["Social Volume", components_data['Market Sentiment']['components']['Social Volume'], "High" if is_btc else "Normal", "Increasing" if is_btc else "Stable"],
        ["Funding Rate", components_data['Market Sentiment']['components']['Funding Rate'], "Positive" if is_btc else "Negative", "Bullish" if is_btc else "Bearish"],
        ["Open Interest", components_data['Market Sentiment']['components']['Open Interest'], "Growing" if is_btc else "Stable", "Bullish" if is_btc else "Neutral"],
    ]
)}

INTERPRETATION: {components_data['Market Sentiment']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 📋 ORDER BOOK DYNAMICS                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Metric", "Value", "Quality", "Signal"],
    [
        ["Market Depth", components_data['Order Book']['components']['Depth (2%)'], "Excellent" if is_btc else "Good", "Strong Support" if is_btc else "Moderate"],
        ["Whale Activity", components_data['Order Book']['components']['Whale Activity'], "Very High" if is_btc else "Low", "Accumulation" if is_btc else "Neutral"],
        ["Spread Quality", components_data['Order Book']['components']['Spread Quality'], "Premium" if is_btc else "Standard", "Low Slippage" if is_btc else "Normal"],
        ["Book Balance", components_data['Order Book']['components']['Book Balance'], "Skewed Bullish" if is_btc else "Balanced", "Buy Pressure" if is_btc else "Neutral"],
    ]
)}

INTERPRETATION: {components_data['Order Book']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 📊 PRICE STRUCTURE ANALYSIS                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

{create_pretty_table(
    ["Element", "Status", "Strength", "Outlook"],
    [
        ["Trend Direction", components_data['Price Structure']['components']['Trend Direction'], "Very Strong" if is_btc else "Weak", "Bullish" if is_btc else "Neutral"],
        ["Support Level", components_data['Price Structure']['components']['Support Strength'], "Unbroken" if is_btc else "Tested", "Holding" if is_btc else "Uncertain"],
        ["Resistance", components_data['Price Structure']['components']['Resistance'], "Breaking Out" if is_btc else "Strong Wall", "Bullish" if is_btc else "Bearish"],
        ["Pattern", components_data['Price Structure']['components']['Pattern'], "Continuation" if is_btc else "Reversal", "Bullish" if is_btc else "Bearish"],
    ]
)}

INTERPRETATION: {components_data['Price Structure']['interpretation']}

╔══════════════════════════════════════════════════════════════════════════════╗
║ 🎯 TRADING RECOMMENDATION                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

OVERALL SIGNAL: {'🟢 STRONG BUY' if is_btc else '🟡 NEUTRAL - WAIT FOR CONFIRMATION'}

{create_pretty_table(
    ["Parameter", "Value", "Rationale"],
    [
        ["Entry Zone", f"${'96,500 - 97,000' if is_btc else '3,400 - 3,450'}", "Support confluence + momentum"],
        ["Stop Loss", f"${'94,800 (-2.1%)' if is_btc else '3,350 (-2.9%)'}", "Below key support level"],
        ["Target 1", f"${'99,500 (+2.6%)' if is_btc else '3,600 (+4.3%)'}", "First resistance zone"],
        ["Target 2", f"${'102,000 (+5.2%)' if is_btc else '3,750 (+8.7%)'}", "Major resistance level"],
        ["Risk/Reward", "1:2.5" if is_btc else "1:2.1", "Favorable ratio"],
        ["Position Size", "2-3% of portfolio" if is_btc else "1-2% of portfolio", "Risk management"],
    ]
)}

⚠️ KEY RISKS:
{'• Approaching psychological $100k resistance level' if is_btc else '• Strong resistance at $3,500 level'}
{'• RSI showing early overbought conditions' if is_btc else '• Declining volume momentum concerns'}
{'• Weekend volatility potential' if is_btc else '• BTC correlation dependency risk'}
{'• Potential profit-taking pressure' if is_btc else '• Market uncertainty factors'}

✅ BULLISH CATALYSTS:
{'• Strong institutional accumulation detected' if is_btc else '• Oversold bounce potential remains'}
{'• Breaking above all major moving averages' if is_btc else '• Developer activity increasing steadily'}
{'• Positive funding rates show conviction' if is_btc else '• ETF approval news potential catalyst'}
{'• Whale wallets accumulating aggressively' if is_btc else '• Technical oversold conditions'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated by Virtuoso Trading System v2.0 | Advanced Confluence Analysis Engine
Real-time market analysis with 6-component weighted scoring system
"""
    
    return {
        "analysis": analysis_text,
        "symbol": symbol,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 CONFLUENCE ANALYSIS LOCAL DEMO")
    print("="*60)
    print("\n📌 Starting local server...")
    print("📌 Open your browser to: http://localhost:8888")
    print("📌 Click the 'Analysis' button on any symbol to see the detailed view")
    print("\n📌 Press Ctrl+C to stop the server\n")
    
    # Automatically open the browser
    webbrowser.open("http://localhost:8888")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8888)