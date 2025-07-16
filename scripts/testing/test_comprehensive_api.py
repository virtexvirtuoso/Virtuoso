#!/usr/bin/env python3
"""
Test script for the new comprehensive symbol analysis endpoint.

Tests the all-in-one endpoint: GET /api/market/analysis/{symbol}
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any

class ComprehensiveAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def test_comprehensive_endpoint(self, symbol: str) -> Dict[str, Any]:
        """Test the comprehensive analysis endpoint for a single symbol."""
        
        url = f"{self.base_url}/api/market/analysis/{symbol}"
        params = {"exchange_id": "bybit"}
        
        print(f"\n🚀 Testing COMPREHENSIVE Analysis Endpoint for {symbol}")
        print("=" * 60)
        print(f"📍 URL: {url}")
        print(f"🔧 Params: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._display_comprehensive_results(data)
                        return data
                    else:
                        error_text = await response.text()
                        print(f"❌ Error {response.status}: {error_text}")
                        return {"error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            print(f"💥 Exception: {e}")
            return {"error": str(e)}
    
    def _display_comprehensive_results(self, data: Dict[str, Any]):
        """Display comprehensive analysis results in a readable format."""
        
        # Basic info
        print(f"✅ Status: {data.get('status', 'unknown')}")
        print(f"🎯 Symbol: {data.get('symbol', 'N/A')}")
        print(f"🏢 Exchange: {data.get('exchange', 'N/A')}")
        print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
        
        # Summary section
        if 'summary' in data:
            summary = data['summary']
            print(f"\n📊 SUMMARY")
            print(f"   💰 Price: {summary.get('price', 'N/A')}")
            print(f"   📈 24h Change: {summary.get('price_change', 'N/A')}")
            print(f"   🎭 Contango Status: {summary.get('contango_status', 'N/A')}")
            print(f"   ⚠️  Risk Level: {summary.get('risk_level', 'N/A')}")
            print(f"   📊 Data Quality: {summary.get('data_quality', 0)}/5 sources")
            
            if 'display' in summary:
                display = summary['display']
                print(f"   🎨 Badge: {display.get('primary_badge', 'N/A')}")
        
        # Detailed analysis sections
        if 'analysis' in data:
            analysis = data['analysis']
            
            # Market Data
            if 'market_data' in analysis:
                market = analysis['market_data']
                if 'error' not in market:
                    print(f"\n💹 MARKET DATA")
                    print(f"   Current Price: ${market.get('price', 0):,.2f}")
                    print(f"   24h High/Low: ${market.get('high_24h', 0):,.2f} / ${market.get('low_24h', 0):,.2f}")
                    print(f"   Volume 24h: {market.get('volume_24h', 0):,.0f}")
                    print(f"   Spread: {market.get('spread_percent', 0):.4f}%")
            
            # Contango Analysis
            if 'contango' in analysis:
                contango = analysis['contango']
                if contango.get('is_futures', False) and 'error' not in contango:
                    print(f"\n🔄 CONTANGO ANALYSIS")
                    print(f"   Status: {contango.get('contango_status', 'N/A')}")
                    print(f"   Spot Premium: {contango.get('spot_premium_formatted', 'N/A')}")
                    print(f"   Funding Rate: {contango.get('funding_rate_formatted', 'N/A')}")
                    print(f"   Market Sentiment: {contango.get('market_sentiment', 'N/A')}")
                    if contango.get('has_alerts', False):
                        print(f"   🚨 Alert Conditions: {contango.get('alert_conditions', [])}")
            
            # Orderbook Analysis
            if 'orderbook' in analysis:
                orderbook = analysis['orderbook']
                if 'error' not in orderbook:
                    print(f"\n📚 ORDERBOOK ANALYSIS")
                    print(f"   Best Bid/Ask: ${orderbook.get('best_bid', 0):.2f} / ${orderbook.get('best_ask', 0):.2f}")
                    print(f"   Volume Imbalance: {orderbook.get('volume_imbalance', 0):.2f}%")
                    
                    depth = orderbook.get('depth_analysis', {})
                    if depth.get('strong_support'):
                        print(f"   💪 Strong Support Detected")
                    elif depth.get('strong_resistance'):
                        print(f"   🧱 Strong Resistance Detected")
                    elif depth.get('balanced'):
                        print(f"   ⚖️  Balanced Order Book")
            
            # Confluence Analysis
            if 'confluence' in analysis:
                confluence = analysis['confluence']
                if 'error' not in confluence:
                    print(f"\n🔄 CONFLUENCE ANALYSIS")
                    print(f"   Overall Signal: {confluence.get('overall_signal', 'N/A')}")
                    print(f"   Confluence Score: {confluence.get('confluence_score_formatted', 'N/A')}")
                    print(f"   Reliability: {confluence.get('reliability_formatted', 'N/A')}")
                    print(f"   Signal Strength: {confluence.get('signal_strength', 'N/A')}")
                    
                    components = confluence.get('components', {})
                    if components:
                        print(f"   Component Scores:")
                        for comp_name, score in components.items():
                            print(f"     {comp_name.title()}: {score:.1f}/100")
                    
                    signals = confluence.get('signals', {})
                    if signals:
                        print(f"   Signal Distribution: {signals.get('buy_signals', 0)} Buy, {signals.get('sell_signals', 0)} Sell, {signals.get('neutral_signals', 0)} Neutral")
            
            # Risk Assessment
            if 'risk_assessment' in analysis:
                risk = analysis['risk_assessment']
                if 'error' not in risk:
                    print(f"\n⚠️  RISK ASSESSMENT")
                    print(f"   Risk Level: {risk.get('risk_level', 'N/A')} (Score: {risk.get('risk_score', 0)})")
                    print(f"   Liquidity: {risk.get('liquidity', 'N/A')}")
                    print(f"   Spread Quality: {risk.get('spread_quality', 'N/A')}")
                    if risk.get('risk_factors'):
                        print(f"   Risk Factors: {', '.join(risk.get('risk_factors', []))}")
        
        # Metadata
        if 'metadata' in data:
            metadata = data['metadata']
            print(f"\n📈 METADATA")
            print(f"   Data Sources: {metadata.get('data_sources', [])}")
            print(f"   Completeness: {metadata.get('analysis_completeness', 0):.1f}%")
            print(f"   Cache Duration: {metadata.get('cache_duration', 0)}ms")

async def main():
    """Main test function."""
    
    print("🌟 COMPREHENSIVE SYMBOL ANALYSIS API TEST")
    print("=" * 60)
    print("Testing the new all-in-one endpoint: GET /api/market/analysis/{symbol}")
    print("This endpoint provides COMPLETE analysis for any symbol including:")
    print("  📊 Real-time market data")
    print("  🔄 Contango/backwardation status")
    print("  📚 Orderbook analysis")
    print("  🎯 CONFLUENCE ANALYSIS (6 components: technical, volume, orderflow, sentiment, orderbook, price structure)")
    print("  ⚠️  Risk assessment")
    print("  🎨 Display-ready formatting")
    
    tester = ComprehensiveAPITester()
    
    # Test different symbols
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in test_symbols:
        result = await tester.test_comprehensive_endpoint(symbol)
        if 'error' not in result:
            print(f"\n✅ {symbol} analysis completed successfully!")
        else:
            print(f"\n❌ {symbol} analysis failed: {result['error']}")
    
    print(f"\n🎯 ENDPOINT USAGE:")
    print(f"   curl 'http://localhost:8000/api/market/analysis/BTCUSDT?exchange_id=bybit'")
    
    print(f"\n📋 API ROUTE SUMMARY:")
    print(f"   🌟 NEW: /api/market/analysis/{{symbol}} - Comprehensive all-in-one analysis")
    print(f"   📊 Multi: /api/market/futures-premium - Multiple symbols contango")
    print(f"   🎯 Single: /api/market/futures-premium/{{symbol}} - Single symbol contango")
    print(f"   🚀 Status: /api/market/contango-status - Dashboard status")
    print(f"   📈 Advanced: /api/market/term-structure - Term structure analysis")

if __name__ == "__main__":
    asyncio.run(main()) 