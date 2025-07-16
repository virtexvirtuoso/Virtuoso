#!/usr/bin/env python3
"""
Alpha Scanner API Demo - Standalone Implementation
Compatible with Python 3.7+
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json

# Standalone Alpha Models (Python 3.7 compatible)
class AlphaStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate" 
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"

class AlphaOpportunity:
    def __init__(self, symbol: str, exchange: str, score: float, strength: AlphaStrength,
                 timeframe: str, technical_score: float, momentum_score: float,
                 volume_score: float, sentiment_score: float, volatility: float,
                 liquidity_score: float, current_price: float, entry_price: float,
                 stop_loss: float, target_price: float, confidence: float,
                 indicators: Dict = None, insights: List = None):
        self.symbol = symbol
        self.exchange = exchange
        self.score = score
        self.strength = strength
        self.timeframe = timeframe
        self.technical_score = technical_score
        self.momentum_score = momentum_score
        self.volume_score = volume_score
        self.sentiment_score = sentiment_score
        self.volatility = volatility
        self.liquidity_score = liquidity_score
        self.current_price = current_price
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target_price = target_price
        self.confidence = confidence
        self.indicators = indicators or {}
        self.insights = insights or []
        self.discovered_at = datetime.utcnow()

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'score': self.score,
            'strength': self.strength.value,
            'timeframe': self.timeframe,
            'technical_score': self.technical_score,
            'momentum_score': self.momentum_score,
            'volume_score': self.volume_score,
            'sentiment_score': self.sentiment_score,
            'volatility': self.volatility,
            'liquidity_score': self.liquidity_score,
            'current_price': self.current_price,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'target_price': self.target_price,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'insights': self.insights,
            'discovered_at': self.discovered_at.isoformat()
        }

class AlphaScannerDemo:
    """Standalone Alpha Scanner Demo"""
    
    def __init__(self):
        self.alpha_weights = {
            'confluence_score': 0.40,
            'momentum_strength': 0.25,
            'volume_confirmation': 0.20,
            'liquidity_factor': 0.15
        }
        
        # Mock market data for demo
        self.mock_market_data = {
            'BTCUSDT': {
                'price': 47250.0,
                'volume_24h': 2500000000,
                'confluence_score': 78.5,
                'technical_score': 82.0,
                'momentum_score': 75.0,
                'volume_score': 80.0,
                'sentiment_score': 70.0,
                'volatility': 0.28,
                'liquidity_score': 95.0
            },
            'ETHUSDT': {
                'price': 3845.30,
                'volume_24h': 1800000000,
                'confluence_score': 72.3,
                'technical_score': 75.0,
                'momentum_score': 68.0,
                'volume_score': 75.0,
                'sentiment_score': 72.0,
                'volatility': 0.32,
                'liquidity_score': 88.0
            },
            'SOLUSDT': {
                'price': 149.75,
                'volume_24h': 850000000,
                'confluence_score': 85.2,
                'technical_score': 88.0,
                'momentum_score': 82.0,
                'volume_score': 85.0,
                'sentiment_score': 80.0,
                'volatility': 0.45,
                'liquidity_score': 75.0
            },
            'AVAXUSDT': {
                'price': 42.18,
                'volume_24h': 450000000,
                'confluence_score': 65.8,
                'technical_score': 70.0,
                'momentum_score': 60.0,
                'volume_score': 68.0,
                'sentiment_score': 65.0,
                'volatility': 0.38,
                'liquidity_score': 70.0
            }
        }
    
    def calculate_alpha_score(self, market_data: Dict) -> float:
        """Calculate alpha score using weighted components"""
        
        confluence_score = market_data.get('confluence_score', 50.0)
        momentum_strength = market_data.get('momentum_score', 50.0)
        volume_confirmation = market_data.get('volume_score', 50.0)
        liquidity_factor = market_data.get('liquidity_score', 50.0)
        
        alpha_score = (
            self.alpha_weights['confluence_score'] * confluence_score +
            self.alpha_weights['momentum_strength'] * momentum_strength +
            self.alpha_weights['volume_confirmation'] * volume_confirmation +
            self.alpha_weights['liquidity_factor'] * liquidity_factor
        )
        
        return max(0.0, min(100.0, alpha_score))
    
    def categorize_strength(self, alpha_score: float) -> AlphaStrength:
        """Categorize alpha strength based on score"""
        
        if alpha_score >= 85:
            return AlphaStrength.EXCEPTIONAL
        elif alpha_score >= 75:
            return AlphaStrength.STRONG  
        elif alpha_score >= 65:
            return AlphaStrength.MODERATE
        else:
            return AlphaStrength.WEAK
    
    def calculate_price_levels(self, symbol: str, market_data: Dict) -> Dict[str, float]:
        """Calculate entry, stop loss, and target levels"""
        
        current_price = market_data['price']
        volatility = market_data['volatility']
        
        # Simple ATR-based levels
        atr_estimate = current_price * volatility * 0.02  # 2% of price as ATR estimate
        
        # Assume bullish bias for demo
        entry_price = current_price
        stop_loss = current_price - (1.5 * atr_estimate)
        target_price = current_price + (2.0 * atr_estimate)
        
        return {
            'current': current_price,
            'entry': entry_price,
            'stop': max(0.01, stop_loss),
            'target': max(0.01, target_price)
        }
    
    def generate_insights(self, symbol: str, market_data: Dict, alpha_score: float) -> List[str]:
        """Generate actionable insights"""
        
        insights = []
        
        if alpha_score > 80:
            insights.append(f"Strong alpha opportunity detected for {symbol}")
        elif alpha_score > 70:
            insights.append(f"Moderate alpha signal for {symbol}")
        
        if market_data['volume_score'] > 80:
            insights.append("High volume confirmation supports the signal")
        
        if market_data['technical_score'] > 85:
            insights.append("Strong technical indicators alignment")
        
        if market_data['momentum_score'] > 75:
            insights.append("Positive momentum trend detected")
        
        return insights[:3]  # Limit to top 3 insights
    
    def scan_opportunities(self, min_score: float = 60.0, max_results: int = 10) -> List[AlphaOpportunity]:
        """Scan for alpha opportunities"""
        
        opportunities = []
        
        for symbol, market_data in self.mock_market_data.items():
            # Calculate alpha score
            alpha_score = self.calculate_alpha_score(market_data)
            
            if alpha_score < min_score:
                continue
            
            # Calculate price levels
            levels = self.calculate_price_levels(symbol, market_data)
            
            # Generate insights
            insights = self.generate_insights(symbol, market_data, alpha_score)
            
            # Create opportunity
            opportunity = AlphaOpportunity(
                symbol=symbol,
                exchange='binance',
                score=alpha_score,
                strength=self.categorize_strength(alpha_score),
                timeframe='1h',
                technical_score=market_data['technical_score'],
                momentum_score=market_data['momentum_score'],
                volume_score=market_data['volume_score'],
                sentiment_score=market_data['sentiment_score'],
                volatility=market_data['volatility'],
                liquidity_score=market_data['liquidity_score'],
                current_price=levels['current'],
                entry_price=levels['entry'],
                stop_loss=levels['stop'],
                target_price=levels['target'],
                confidence=alpha_score / 100.0,
                indicators={
                    'confluence_score': market_data['confluence_score'],
                    'rsi': 65.0,  # Mock RSI
                    'macd': 1.2   # Mock MACD
                },
                insights=insights
            )
            
            opportunities.append(opportunity)
        
        # Sort by score and limit results
        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities[:max_results]

def demo_alpha_scanner():
    """Run Alpha Scanner Demo"""
    
    print("🚀 Alpha Scanner API Demo")
    print("=" * 50)
    
    # Initialize scanner
    scanner = AlphaScannerDemo()
    print("✅ Alpha Scanner initialized")
    
    # Scan for opportunities
    print("\n📊 Scanning for alpha opportunities...")
    opportunities = scanner.scan_opportunities(min_score=65.0, max_results=5)
    
    print(f"\n🎯 Found {len(opportunities)} opportunities:")
    print("-" * 50)
    
    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp.symbol} ({opp.exchange})")
        print(f"   Score: {opp.score:.1f} | Strength: {opp.strength.value}")
        print(f"   Price: ${opp.current_price:.2f}")
        print(f"   Entry: ${opp.entry_price:.2f} | Target: ${opp.target_price:.2f}")
        print(f"   Stop Loss: ${opp.stop_loss:.2f}")
        print(f"   Confidence: {opp.confidence:.1%}")
        print(f"   Insights: {', '.join(opp.insights[:2])}")
    
    # Demonstrate API response format
    print("\n" + "=" * 50)
    print("📋 API Response Format (JSON):")
    
    if opportunities:
        sample_response = {
            "opportunities": [opp.to_dict() for opp in opportunities[:2]],
            "scan_timestamp": datetime.utcnow().isoformat(),
            "total_symbols_scanned": len(scanner.mock_market_data),
            "scan_duration_ms": 150,
            "metadata": {
                "timeframes_analyzed": ["1h"],
                "min_score_threshold": 65.0,
                "opportunities_found": len(opportunities)
            }
        }
        
        print(json.dumps(sample_response, indent=2))
    
    print("\n🎉 Alpha Scanner Demo Complete!")
    print("\nThis demonstrates the core functionality of the Alpha Scanner API:")
    print("• Multi-factor alpha scoring")
    print("• Risk-adjusted opportunity ranking")
    print("• Price level calculations")
    print("• Actionable insights generation")
    print("• JSON API response format")

if __name__ == "__main__":
    demo_alpha_scanner() 