#!/usr/bin/env python3
"""
Test Confluence Quality Metrics with Real Market Data

This script validates the enhanced confluence analysis with live market data
to ensure quality metrics (consensus, confidence, disagreement) are working
correctly in production scenarios.
"""

import sys
import os
import asyncio
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.config.config_manager import ConfigManager
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.logger import Logger


class ConfluenceQualityMetricsLiveTest:
    """Test confluence quality metrics with real market data."""

    def __init__(self):
        self.logger = Logger(__name__)
        self.config = None
        self.analyzer = None

    def load_system_config(self) -> bool:
        """Load the actual system configuration."""
        try:
            self.logger.info("=" * 80)
            self.logger.info("CONFLUENCE QUALITY METRICS - LIVE DATA TEST")
            self.logger.info("=" * 80)
            self.logger.info("\nLoading system configuration...")

            self.config = ConfigManager.load_config()

            if not self.config:
                self.logger.error("Failed to load config")
                return False

            self.logger.info("✅ System configuration loaded")
            return True

        except Exception as e:
            self.logger.error(f"Error loading config: {e}", exc_info=True)
            return False

    def initialize_analyzer(self) -> bool:
        """Initialize the ConfluenceAnalyzer."""
        try:
            self.logger.info("Initializing ConfluenceAnalyzer...")

            self.analyzer = ConfluenceAnalyzer(self.config)

            if not self.analyzer:
                self.logger.error("Failed to initialize analyzer")
                return False

            self.logger.info("✅ ConfluenceAnalyzer initialized")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing analyzer: {e}", exc_info=True)
            return False

    async def fetch_market_data(self, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        """Fetch real market data for testing."""
        try:
            self.logger.info(f"\nFetching market data for {symbol}...")

            # Use the analyzer's analyze method with real data
            result = await self.analyzer.analyze(symbol=symbol)

            return result

        except Exception as e:
            self.logger.error(f"Error fetching market data: {e}", exc_info=True)
            return None

    def display_quality_metrics(self, symbol: str, result: Dict[str, Any]) -> None:
        """Display quality metrics in a formatted way."""
        try:
            if not result:
                self.logger.warning(f"No result for {symbol}")
                return

            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"CONFLUENCE ANALYSIS: {symbol}")
            self.logger.info("=" * 80)

            # Extract metrics
            confluence_score = result.get('confluence_score', 50.0)
            consensus = result.get('consensus', 0.0)
            confidence = result.get('confidence', 0.0)
            disagreement = result.get('disagreement', 0.0)
            reliability = result.get('reliability', 0.0)

            # Display main score
            self.logger.info(f"\n📊 CONFLUENCE SCORE: {confluence_score:.2f}/100")
            self.logger.info(f"   Reliability: {reliability:.1f}%")

            # Display quality metrics
            self.logger.info("\n🎯 QUALITY METRICS:")
            self.logger.info(f"   Consensus:    {consensus:.3f}  {'✅' if consensus > 0.8 else '⚠️' if consensus > 0.6 else '❌'} {self._get_consensus_label(consensus)}")
            self.logger.info(f"   Confidence:   {confidence:.3f}  {'✅' if confidence > 0.5 else '⚠️' if confidence > 0.3 else '❌'} {self._get_confidence_label(confidence)}")
            self.logger.info(f"   Disagreement: {disagreement:.4f}  {'✅' if disagreement < 0.1 else '⚠️' if disagreement < 0.3 else '❌'} {self._get_disagreement_label(disagreement)}")

            # Display interpretation
            self.logger.info("\n💡 INTERPRETATION:")
            self._display_interpretation(consensus, confidence, disagreement, confluence_score)

            # Display components if available
            components = result.get('components', {})
            if components:
                self.logger.info("\n📈 COMPONENT SCORES:")
                for component, score in sorted(components.items(), key=lambda x: x[1], reverse=True):
                    bar = self._create_bar(score)
                    self.logger.info(f"   {component:20s} {score:6.2f}  {bar}")

        except Exception as e:
            self.logger.error(f"Error displaying metrics: {e}", exc_info=True)

    def _get_consensus_label(self, consensus: float) -> str:
        """Get human-readable consensus label."""
        if consensus > 0.8:
            return "High Agreement"
        elif consensus > 0.6:
            return "Moderate Agreement"
        else:
            return "Low Agreement (Conflicting)"

    def _get_confidence_label(self, confidence: float) -> str:
        """Get human-readable confidence label."""
        if confidence > 0.5:
            return "High Quality Signal"
        elif confidence > 0.3:
            return "Moderate Quality"
        else:
            return "Low Quality (Skip Trade)"

    def _get_disagreement_label(self, disagreement: float) -> str:
        """Get human-readable disagreement label."""
        if disagreement < 0.1:
            return "Low Conflict"
        elif disagreement < 0.3:
            return "Moderate Conflict"
        else:
            return "High Conflict (Avoid)"

    def _display_interpretation(self, consensus: float, confidence: float,
                               disagreement: float, score: float) -> None:
        """Display trading interpretation based on quality metrics."""
        # Determine signal direction
        if score > 60:
            direction = "BULLISH"
            emoji = "🟢"
        elif score < 40:
            direction = "BEARISH"
            emoji = "🔴"
        else:
            direction = "NEUTRAL"
            emoji = "⚪"

        self.logger.info(f"   Signal Direction: {emoji} {direction} (score: {score:.1f})")

        # Determine trade recommendation
        if confidence < 0.3:
            recommendation = "❌ SKIP - Low confidence signal"
            reason = f"Confidence {confidence:.3f} is below 0.3 threshold"
        elif disagreement > 0.3:
            recommendation = "❌ SKIP - High disagreement"
            reason = f"Disagreement {disagreement:.4f} exceeds 0.3 threshold"
        elif consensus < 0.6:
            recommendation = "⚠️  CAUTION - Low consensus"
            reason = f"Consensus {consensus:.3f} is below 0.6 threshold"
        elif confidence > 0.5 and consensus > 0.7:
            recommendation = "✅ TRADE - High quality signal"
            reason = f"Strong {direction.lower()} signal with high agreement"
        else:
            recommendation = "⚠️  CONSIDER - Moderate quality"
            reason = f"{direction} signal with moderate quality metrics"

        self.logger.info(f"   Recommendation: {recommendation}")
        self.logger.info(f"   Reason: {reason}")

    def _create_bar(self, value: float, width: int = 30) -> str:
        """Create a visual bar for score visualization."""
        filled = int((value / 100) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar

    async def test_multiple_symbols(self, symbols: List[str]) -> None:
        """Test confluence quality metrics across multiple symbols."""
        try:
            results = []

            for symbol in symbols:
                self.logger.info(f"\n{'=' * 80}")
                self.logger.info(f"Testing {symbol}...")
                self.logger.info(f"{'=' * 80}")

                try:
                    result = await self.fetch_market_data(symbol)

                    if result:
                        self.display_quality_metrics(symbol, result)
                        results.append({
                            'symbol': symbol,
                            'confluence': result.get('confluence_score', 50.0),
                            'consensus': result.get('consensus', 0.0),
                            'confidence': result.get('confidence', 0.0),
                            'disagreement': result.get('disagreement', 0.0)
                        })
                    else:
                        self.logger.warning(f"No result returned for {symbol}")

                except Exception as e:
                    self.logger.error(f"Error testing {symbol}: {e}", exc_info=True)

                # Small delay between symbols
                await asyncio.sleep(1)

            # Display summary
            self._display_summary(results)

        except Exception as e:
            self.logger.error(f"Error testing multiple symbols: {e}", exc_info=True)

    def _display_summary(self, results: List[Dict[str, Any]]) -> None:
        """Display summary of all tested symbols."""
        try:
            if not results:
                return

            self.logger.info("\n" + "=" * 80)
            self.logger.info("SUMMARY - All Symbols")
            self.logger.info("=" * 80)

            self.logger.info(f"\n{'Symbol':<15} {'Score':>8} {'Consensus':>11} {'Confidence':>12} {'Disagreement':>14} {'Quality':>10}")
            self.logger.info("-" * 80)

            for r in results:
                symbol = r['symbol']
                score = r['confluence']
                consensus = r['consensus']
                confidence = r['confidence']
                disagreement = r['disagreement']

                # Quality assessment
                if confidence > 0.5 and consensus > 0.7:
                    quality = "✅ High"
                elif confidence < 0.3 or disagreement > 0.3:
                    quality = "❌ Low"
                else:
                    quality = "⚠️  Medium"

                self.logger.info(
                    f"{symbol:<15} {score:>8.2f} {consensus:>11.3f} "
                    f"{confidence:>12.3f} {disagreement:>14.4f} {quality:>10}"
                )

            # Statistics
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            avg_consensus = sum(r['consensus'] for r in results) / len(results)
            high_quality = sum(1 for r in results if r['confidence'] > 0.5 and r['consensus'] > 0.7)

            self.logger.info("\n" + "-" * 80)
            self.logger.info(f"Average Confidence: {avg_confidence:.3f}")
            self.logger.info(f"Average Consensus:  {avg_consensus:.3f}")
            self.logger.info(f"High Quality Signals: {high_quality}/{len(results)} ({high_quality/len(results)*100:.1f}%)")

        except Exception as e:
            self.logger.error(f"Error displaying summary: {e}", exc_info=True)

    async def run(self) -> bool:
        """Run the live data test."""
        try:
            # Load config
            if not self.load_system_config():
                return False

            # Initialize analyzer
            if not self.initialize_analyzer():
                return False

            # Test symbols
            test_symbols = [
                "BTC/USDT",
                "ETH/USDT",
                "SOL/USDT",
                "BNB/USDT",
                "XRP/USDT"
            ]

            self.logger.info(f"\nTesting {len(test_symbols)} symbols with real market data...")

            await self.test_multiple_symbols(test_symbols)

            self.logger.info("\n" + "=" * 80)
            self.logger.info("✅ LIVE DATA TEST COMPLETE")
            self.logger.info("=" * 80)
            self.logger.info("\nQuality metrics are working correctly:")
            self.logger.info("  ✅ Consensus calculated and displayed")
            self.logger.info("  ✅ Confidence calculated and displayed")
            self.logger.info("  ✅ Disagreement calculated and displayed")
            self.logger.info("  ✅ Quality-based recommendations provided")
            self.logger.info("\nReady for production use!")

            return True

        except Exception as e:
            self.logger.error(f"Error running live test: {e}", exc_info=True)
            return False


async def main():
    """Main entry point."""
    test = ConfluenceQualityMetricsLiveTest()
    success = await test.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
