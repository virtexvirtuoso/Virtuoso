"""
Multi-Timeframe Beta-Based Altcoin Ranker

Ranks altcoins by their performance vs Bitcoin across multiple timeframes.
Uses the existing BetaChartService to analyze 3-7 timeframes simultaneously.

Simple approach for Phase 1: Measure cumulative outperformance/underperformance
relative to BTC across timeframes.

Example:
    ranker = MTFBetaRanker(timeframes=[1, 4, 24])  # 1h, 4h, 24h
    results = await ranker.rank_altcoins(top_n=10)

    for coin in results:
        print(f"{coin['symbol']}: {coin['mtf_score']:.1f}/100")
        print(f"  Performance: {coin['total_outperformance']:.2f}%")
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ..chart.beta_chart_service import get_beta_chart_service, TIMEFRAME_CONFIG

logger = logging.getLogger(__name__)


class MTFBetaRanker:
    """
    Multi-Timeframe Beta-Based Altcoin Ranker.

    Analyzes altcoin performance vs Bitcoin across multiple timeframes,
    scoring based on consistency and magnitude of outperformance.
    """

    # Default timeframe clusters for different trading styles
    CLUSTERS = {
        'scalping': [0.25, 0.5, 1],           # 15m, 30m, 1h
        'day_trading': [1, 4, 8],             # 1h, 4h, 8h
        'swing_trading': [8, 12, 24],         # 8h, 12h, 24h
        'comprehensive': [0.25, 0.5, 1, 4, 8, 12, 24],  # ALL 7 timeframes for maximum confluence
    }

    def __init__(
        self,
        timeframes: Optional[List[float]] = None,
        cluster: str = 'day_trading'
    ):
        """
        Initialize MTF Beta Ranker.

        Args:
            timeframes: List of timeframe hours (e.g., [1, 4, 24])
            cluster: Preset cluster name if timeframes not provided
        """
        self.logger = logging.getLogger(f"{__name__}.MTFBetaRanker")
        self.beta_service = get_beta_chart_service()

        # Use provided timeframes or cluster preset
        if timeframes:
            # Validate all timeframes are supported
            valid_tfs = [tf for tf in timeframes if tf in TIMEFRAME_CONFIG]
            if not valid_tfs:
                raise ValueError(f"No valid timeframes provided. Supported: {list(TIMEFRAME_CONFIG.keys())}")
            self.timeframes = valid_tfs
        else:
            self.timeframes = self.CLUSTERS.get(cluster, self.CLUSTERS['day_trading'])

        self.logger.info(f"Initialized MTF Beta Ranker with timeframes: {self.timeframes}")

    async def rank_altcoins(
        self,
        top_n: int = 10,
        min_score: float = 0.0,
        exclude_symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank altcoins by multi-timeframe beta performance.

        Args:
            top_n: Number of top-ranked coins to return
            min_score: Minimum MTF score threshold (0-100)
            exclude_symbols: List of symbols to exclude from ranking

        Returns:
            List of ranked altcoins with scores and metadata
        """
        start_time = asyncio.get_event_loop().time()
        exclude_symbols = set(exclude_symbols or [])

        self.logger.info(f"Ranking altcoins across {len(self.timeframes)} timeframes...")

        try:
            # Fetch beta chart data for all timeframes in parallel
            tasks = [
                self.beta_service.generate_chart_data(timeframe_hours=tf)
                for tf in self.timeframes
            ]

            timeframe_data = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate performance across timeframes
            symbol_performance = {}  # symbol -> {tf: performance, ...}

            for tf, data in zip(self.timeframes, timeframe_data):
                if isinstance(data, Exception):
                    self.logger.error(f"Error fetching {tf}h data: {data}")
                    continue

                # Extract performance summary
                perf_summary = data.get('performance_summary', [])

                for item in perf_summary:
                    symbol = item['symbol']
                    change = item['change']

                    if symbol == 'BTC' or symbol in exclude_symbols:
                        continue

                    if symbol not in symbol_performance:
                        symbol_performance[symbol] = {}

                    symbol_performance[symbol][tf] = change

            # Calculate MTF scores
            ranked_altcoins = []

            for symbol, tf_changes in symbol_performance.items():
                # Skip if not present in all timeframes
                if len(tf_changes) != len(self.timeframes):
                    continue

                # Calculate scoring components
                score_data = self._calculate_mtf_score(symbol, tf_changes)

                # Apply minimum score filter
                if score_data['mtf_score'] < min_score:
                    continue

                ranked_altcoins.append(score_data)

            # Sort by MTF score (descending)
            ranked_altcoins.sort(key=lambda x: x['mtf_score'], reverse=True)

            # Add rank numbers
            for rank, coin in enumerate(ranked_altcoins[:top_n], 1):
                coin['rank'] = rank

            execution_time = asyncio.get_event_loop().time() - start_time

            self.logger.info(
                f"Ranked {len(ranked_altcoins)} altcoins in {execution_time:.2f}s "
                f"(analyzed {len(symbol_performance)} total)"
            )

            return {
                'rankings': ranked_altcoins[:top_n],
                'timeframes_analyzed': self.timeframes,
                'total_symbols': len(symbol_performance),
                'execution_time_seconds': round(execution_time, 3),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error ranking altcoins: {e}", exc_info=True)
            raise

    def _calculate_mtf_score(
        self,
        symbol: str,
        tf_changes: Dict[float, float]
    ) -> Dict[str, Any]:
        """
        Calculate multi-timeframe score for a symbol.

        Scoring logic:
        1. Total outperformance: Sum of % changes across timeframes
        2. Consistency: How many timeframes show positive performance
        3. Magnitude: Average absolute performance
        4. Trend strength: Standard deviation (lower = more consistent)

        Args:
            symbol: Altcoin symbol
            tf_changes: Dict mapping timeframe -> % change

        Returns:
            Dict with MTF score and component metrics
        """
        changes = list(tf_changes.values())

        # Component 1: Total outperformance
        total_outperformance = sum(changes)

        # Component 2: Consistency (% of timeframes with positive performance)
        positive_tfs = sum(1 for c in changes if c > 0)
        consistency_ratio = positive_tfs / len(changes)

        # Component 3: Magnitude (average absolute performance)
        avg_abs_performance = sum(abs(c) for c in changes) / len(changes)

        # Component 4: Trend strength (lower std dev = more consistent)
        mean_change = sum(changes) / len(changes)
        variance = sum((c - mean_change) ** 2 for c in changes) / len(changes)
        std_dev = variance ** 0.5

        # Normalize to 0-100 scale
        # Base score from total outperformance (-50 to +50 maps to 0-100)
        base_score = 50 + min(max(total_outperformance, -50), 50)

        # Boost for consistency (up to +20 points)
        consistency_boost = consistency_ratio * 20

        # Penalty for high volatility (up to -15 points)
        # std_dev > 10 gets full penalty, linear scaling
        volatility_penalty = min(std_dev / 10, 1.0) * 15

        # Final MTF score (0-100)
        mtf_score = max(0, min(100, base_score + consistency_boost - volatility_penalty))

        # Generate signal
        signal = self._generate_signal(mtf_score, consistency_ratio)

        # Determine timeframe alignment
        aligned_timeframes = positive_tfs if total_outperformance > 0 else (len(changes) - positive_tfs)

        return {
            'symbol': symbol,
            'mtf_score': round(mtf_score, 1),
            'signal': signal,
            'total_outperformance': round(total_outperformance, 2),
            'avg_performance': round(mean_change, 2),
            'consistency_ratio': round(consistency_ratio, 2),
            'volatility': round(std_dev, 2),
            'aligned_timeframes': aligned_timeframes,
            'total_timeframes': len(changes),
            'timeframe_details': {
                str(tf): round(change, 2)
                for tf, change in sorted(tf_changes.items())
            }
        }

    def _generate_signal(self, mtf_score: float, consistency_ratio: float) -> str:
        """
        Generate trading signal based on MTF score and consistency.

        Args:
            mtf_score: Overall MTF score (0-100)
            consistency_ratio: % of timeframes aligned (0-1)

        Returns:
            Signal string: STRONG_BUY, BUY, WEAK_BUY, NEUTRAL, etc.
        """
        # Require both high score AND consistency for strong signals
        if mtf_score >= 80 and consistency_ratio >= 0.8:
            return 'STRONG_BUY'
        elif mtf_score >= 70 and consistency_ratio >= 0.6:
            return 'BUY'
        elif mtf_score >= 60:
            return 'WEAK_BUY'
        elif mtf_score >= 40:
            return 'NEUTRAL'
        elif mtf_score >= 30:
            return 'WEAK_SELL'
        elif mtf_score >= 20:
            return 'SELL'
        else:
            return 'STRONG_SELL'

    async def get_top_performers(
        self,
        top_n: int = 5,
        min_consistency: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Get top performing altcoins with high consistency requirement.

        Args:
            top_n: Number of top performers to return
            min_consistency: Minimum consistency ratio (0-1)

        Returns:
            List of top performers meeting consistency threshold
        """
        all_rankings = await self.rank_altcoins(top_n=50)

        # Filter for high consistency
        consistent_performers = [
            coin for coin in all_rankings['rankings']
            if coin['consistency_ratio'] >= min_consistency
        ]

        return consistent_performers[:top_n]

    async def get_divergence_plays(
        self,
        min_divergence: float = 5.0,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find altcoins with strong performance divergence from BTC.

        Useful for identifying relative strength/weakness trades.

        Args:
            min_divergence: Minimum total outperformance threshold (%)
            top_n: Number of top divergence plays to return

        Returns:
            List of altcoins with strongest divergence from BTC
        """
        all_rankings = await self.rank_altcoins(top_n=50)

        # Filter for significant divergence
        divergence_plays = [
            coin for coin in all_rankings['rankings']
            if abs(coin['total_outperformance']) >= min_divergence
        ]

        # Sort by absolute divergence (strongest first)
        divergence_plays.sort(
            key=lambda x: abs(x['total_outperformance']),
            reverse=True
        )

        return divergence_plays[:top_n]


# Singleton instance
_mtf_beta_ranker: Optional[MTFBetaRanker] = None


def get_mtf_beta_ranker(
    timeframes: Optional[List[float]] = None,
    cluster: str = 'day_trading'
) -> MTFBetaRanker:
    """
    Get or create MTF Beta Ranker instance.

    Args:
        timeframes: Custom timeframe list
        cluster: Preset cluster name

    Returns:
        MTFBetaRanker instance
    """
    global _mtf_beta_ranker
    if _mtf_beta_ranker is None:
        _mtf_beta_ranker = MTFBetaRanker(timeframes=timeframes, cluster=cluster)
    return _mtf_beta_ranker
