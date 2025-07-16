#!/usr/bin/env python3
"""
Demo script showing Bitcoin Beta Report with LIVE DATA.

This script demonstrates the Bitcoin Beta Report working with real live market data
from the Virtuoso trading system.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config.config_manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LiveBitcoinBetaDemo:
    """Demo showing live Bitcoin beta analysis."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Simplified timeframes for demo
        self.timeframes = {
            'htf': '4h',   # High timeframe
            'mtf': '30m',  # Medium timeframe  
            'ltf': '5m',   # Low timeframe
            'base': '1m'   # Base timeframe
        }
        
        # Periods to fetch
        self.periods = {
            'htf': 100,   # ~16 days of 4h candles
            'mtf': 200,   # ~4 days of 30m candles  
            'ltf': 300,   # ~1 day of 5m candles
            'base': 200   # ~3 hours of 1m candles
        }
        
    async def run_demo(self):
        """Run the live Bitcoin beta demo."""
        try:
            logger.info("🚀 Starting Live Bitcoin Beta Analysis Demo")
            logger.info("=" * 60)
            
            # Initialize exchange manager
            exchange_manager = ExchangeManager(self.config)
            await exchange_manager.initialize()
            
            # Get primary exchange
            exchange = await exchange_manager.get_primary_exchange()
            if not exchange:
                logger.error("❌ No primary exchange available")
                return False
                
            logger.info(f"✅ Connected to {exchange.__class__.__name__}")
            
            # Test symbols (small set for demo)
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
            logger.info(f"📊 Analyzing symbols: {symbols}")
            
            # Fetch live market data
            logger.info("\n📡 Fetching LIVE market data...")
            market_data = await self._fetch_live_data(exchange_manager, symbols)
            
            if not market_data:
                logger.error("❌ Failed to fetch live data")
                return False
                
            # Calculate beta analysis
            logger.info("\n🧮 Calculating beta statistics...")
            beta_analysis = self._calculate_beta_analysis(market_data)
            
            # Display results
            self._display_results(beta_analysis)
            
            # Detect alpha opportunities using live data
            logger.info("\n🎯 Detecting alpha generation opportunities...")
            alpha_detector = BitcoinBetaAlphaDetector(self.config)
            opportunities = alpha_detector.detect_alpha_opportunities(beta_analysis)
            
            self._display_alpha_opportunities(opportunities)
            
            return True
            
        except Exception as e:
            logger.error(f"Demo error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    async def _fetch_live_data(self, exchange_manager, symbols):
        """Fetch live OHLCV data for all symbols and timeframes."""
        market_data = {}
        
        for symbol in symbols:
            logger.info(f"  Fetching {symbol}...")
            market_data[symbol] = {}
            
            for tf_name, tf_interval in self.timeframes.items():
                try:
                    # Fetch live OHLCV data
                    limit = self.periods[tf_name]
                    ohlcv = await exchange_manager.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=tf_interval,
                        limit=limit
                    )
                    
                    if ohlcv and len(ohlcv) > 30:  # Minimum data check
                        # Convert to DataFrame
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                        
                        # Calculate returns
                        df['returns'] = df['close'].pct_change()
                        
                        market_data[symbol][tf_name] = df
                        
                        logger.info(f"    ✅ {tf_name} ({tf_interval}): {len(df)} candles")
                    else:
                        logger.warning(f"    ⚠️  {tf_name} ({tf_interval}): insufficient data")
                        
                except Exception as e:
                    logger.error(f"    ❌ {tf_name} ({tf_interval}): {str(e)}")
                    
                # Rate limiting
                await asyncio.sleep(0.1)
                
        return market_data
        
    def _calculate_beta_analysis(self, market_data):
        """Calculate beta statistics from live data."""
        beta_analysis = {}
        btc_symbol = 'BTCUSDT'
        
        for tf_name in self.timeframes.keys():
            beta_analysis[tf_name] = {}
            
            # Get Bitcoin data
            if btc_symbol not in market_data or tf_name not in market_data[btc_symbol]:
                continue
                
            btc_data = market_data[btc_symbol][tf_name]
            btc_returns = btc_data['returns'].dropna()
            
            if len(btc_returns) < 20:
                continue
                
            for symbol in market_data.keys():
                if symbol == btc_symbol:
                    # Bitcoin vs itself
                    beta_analysis[tf_name][symbol] = {
                        'beta': 1.0,
                        'correlation': 1.0,
                        'alpha': 0.0,
                        'volatility': btc_returns.std() * np.sqrt(252)
                    }
                    continue
                    
                if tf_name not in market_data[symbol]:
                    continue
                    
                asset_data = market_data[symbol][tf_name]
                asset_returns = asset_data['returns'].dropna()
                
                # Align data
                aligned_data = pd.concat([btc_returns, asset_returns], axis=1, join='inner')
                aligned_data.columns = ['btc_returns', 'asset_returns']
                aligned_data = aligned_data.dropna()
                
                if len(aligned_data) < 20:
                    continue
                    
                btc_aligned = aligned_data['btc_returns']
                asset_aligned = aligned_data['asset_returns']
                
                # Calculate statistics
                covariance = np.cov(asset_aligned, btc_aligned)[0, 1]
                btc_variance = np.var(btc_aligned)
                
                beta = covariance / btc_variance if btc_variance > 0 else 0
                correlation = np.corrcoef(asset_aligned, btc_aligned)[0, 1]
                alpha = asset_aligned.mean() - beta * btc_aligned.mean()
                volatility = asset_aligned.std() * np.sqrt(252)
                
                beta_analysis[tf_name][symbol] = {
                    'beta': beta,
                    'correlation': correlation,
                    'alpha': alpha * 252,  # Annualized
                    'volatility': volatility
                }
                
        return beta_analysis
        
    def _display_results(self, beta_analysis):
        """Display beta analysis results."""
        logger.info("\n📈 LIVE BITCOIN BETA ANALYSIS RESULTS")
        logger.info("=" * 60)
        
        # Display 4H timeframe results
        if 'htf' in beta_analysis:
            logger.info("\n🕐 4-Hour Timeframe Analysis:")
            logger.info("-" * 40)
            
            for symbol, stats in beta_analysis['htf'].items():
                if symbol == 'BTCUSDT':
                    continue
                    
                symbol_clean = symbol.replace('USDT', '')
                beta = stats['beta']
                correlation = stats['correlation']
                alpha = stats['alpha']
                volatility = stats['volatility']
                
                logger.info(f"  {symbol_clean:8s} | β: {beta:6.3f} | ρ: {correlation:6.3f} | α: {alpha:7.1%} | σ: {volatility:7.1%}")
                
        # Display cross-timeframe comparison
        logger.info("\n⏱️  Cross-Timeframe Beta Comparison:")
        logger.info("-" * 50)
        
        for symbol in ['ETHUSDT', 'SOLUSDT', 'AVAXUSDT']:
            if any(symbol in tf_data for tf_data in beta_analysis.values()):
                symbol_clean = symbol.replace('USDT', '')
                betas = []
                
                for tf_name in ['base', 'ltf', 'mtf', 'htf']:
                    if tf_name in beta_analysis and symbol in beta_analysis[tf_name]:
                        betas.append(f"{beta_analysis[tf_name][symbol]['beta']:5.2f}")
                    else:
                        betas.append("  N/A")
                        
                logger.info(f"  {symbol_clean:8s} | 1m: {betas[0]} | 5m: {betas[1]} | 30m: {betas[2]} | 4h: {betas[3]}")
                
    def _display_alpha_opportunities(self, opportunities):
        """Display alpha generation opportunities."""
        logger.info("\n🎯 ALPHA GENERATION OPPORTUNITIES (Live Data)")
        logger.info("=" * 60)
        
        if not opportunities:
            logger.info("  No alpha opportunities detected at this time.")
            return
            
        for i, opp in enumerate(opportunities[:3], 1):  # Top 3
            logger.info(f"\n  #{i} {opp.symbol.replace('USDT', '')} - {opp.divergence_type.value.replace('_', ' ').title()}")
            logger.info(f"      Confidence: {opp.confidence:.0%}")
            logger.info(f"      Alpha Potential: {opp.alpha_potential:.1%}")
            logger.info(f"      Insight: {opp.trading_insight}")
            logger.info(f"      Action: {opp.recommended_action}")
            logger.info(f"      Risk: {opp.risk_level} | Duration: {opp.expected_duration}")

async def main():
    """Main demo function."""
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("❌ Failed to load configuration")
            return False
            
        # Run the demo
        demo = LiveBitcoinBetaDemo(config)
        result = await demo.run_demo()
        
        if result:
            logger.info("\n✅ Live Bitcoin Beta Demo completed successfully!")
            logger.info("\n🔍 Key Insights:")
            logger.info("  • This analysis used REAL LIVE data from exchanges")
            logger.info("  • Beta coefficients show how assets move relative to Bitcoin")
            logger.info("  • Alpha opportunities indicate potential independent returns")
            logger.info("  • Cross-timeframe analysis reveals changing correlations")
            logger.info("\n💡 This demonstrates the production-ready alpha generation system!")
        else:
            logger.error("❌ Demo failed. Check configuration and exchange connectivity.")
            
        return result
        
    except Exception as e:
        logger.error(f"Demo error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔴 LIVE DATA Bitcoin Beta Analysis Demo")
    print("=" * 50)
    print("This demo uses REAL LIVE market data from exchanges!")
    print("")
    
    try:
        result = asyncio.run(main())
        if not result:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        sys.exit(1) 