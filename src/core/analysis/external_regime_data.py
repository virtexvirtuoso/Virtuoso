"""
External Regime Data Provider

Fetches and aggregates external market data to enhance regime detection accuracy.
Integrates data from:
- crypto-perps-tracker (port 8050): Derivatives market sentiment
- CoinGecko: Global market metrics and dominance
- Alternative.me: Fear & Greed Index

These external signals improve regime classification by providing:
1. Derivatives sentiment (funding rate, basis, long/short ratio)
2. Market structure (BTC dominance, market cap trends)
3. Crowd sentiment (Fear & Greed extremes)

Author: Virtuoso Team
Version: 1.0.0
Created: 2025-12-04
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentBias(Enum):
    """Sentiment bias classification from external data."""
    EXTREME_BULLISH = "extreme_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    EXTREME_BEARISH = "extreme_bearish"


@dataclass
class DerivativesData:
    """Derivatives market data from perps-tracker."""
    funding_rate: float = 0.0  # -1 to +1 range (normalized)
    funding_sentiment: str = "NEUTRAL"
    basis_pct: float = 0.0  # Contango (+) / Backwardation (-)
    basis_status: str = "NEUTRAL"
    long_pct: float = 50.0  # Long percentage
    short_pct: float = 50.0  # Short percentage
    total_open_interest: float = 0.0  # Total OI in USD
    total_volume_24h: float = 0.0  # 24h volume in USD
    timestamp: float = 0.0
    is_fresh: bool = False  # Data freshness indicator


@dataclass
class GlobalMarketData:
    """Global market data from CoinGecko."""
    btc_dominance: float = 57.0
    eth_dominance: float = 11.5
    market_cap_change_24h: float = 0.0
    total_market_cap: float = 0.0
    total_volume_24h: float = 0.0
    active_cryptocurrencies: int = 0
    timestamp: float = 0.0
    is_fresh: bool = False


@dataclass
class SentimentData:
    """Sentiment data from Fear & Greed Index."""
    value: int = 50  # 0-100 scale
    classification: str = "Neutral"  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
    timestamp: float = 0.0
    is_fresh: bool = False


@dataclass
class ExternalRegimeSignals:
    """
    Aggregated external signals for regime detection enhancement.

    Provides bias signals and confidence adjustments based on external data.
    """
    derivatives: DerivativesData = field(default_factory=DerivativesData)
    global_market: GlobalMarketData = field(default_factory=GlobalMarketData)
    sentiment: SentimentData = field(default_factory=SentimentData)

    # Aggregated signals
    overall_bias: SentimentBias = SentimentBias.NEUTRAL
    confidence_modifier: float = 1.0  # 0.7 to 1.3 range
    volatility_warning: bool = False
    liquidity_warning: bool = False

    # Metadata
    timestamp: float = 0.0
    data_quality: float = 0.0  # 0-1, how fresh/complete the data is


class ExternalRegimeDataProvider:
    """
    Fetches and processes external market data for regime detection.

    Usage:
        provider = ExternalRegimeDataProvider()
        signals = await provider.get_external_signals()

        # Use in regime detection:
        confidence_adjusted = base_confidence * signals.confidence_modifier
        if signals.volatility_warning:
            # Consider switching to HIGH_VOLATILITY regime
            pass
    """

    # Configuration
    PERPS_TRACKER_URL = "http://localhost:8050/api/perpetuals-pulse"
    COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
    FEAR_GREED_URL = "https://api.alternative.me/fng/"

    # Cache TTLs (seconds)
    PERPS_TTL = 60  # 1 minute (derivatives change fast)
    COINGECKO_TTL = 300  # 5 minutes
    FEAR_GREED_TTL = 3600  # 1 hour (updates daily)

    # Signal thresholds
    FUNDING_EXTREME_THRESHOLD = 0.01  # 1% funding = extreme
    FUNDING_ELEVATED_THRESHOLD = 0.005  # 0.5% funding = elevated
    LONG_SHORT_EXTREME_THRESHOLD = 0.70  # 70% one-sided = extreme
    FEAR_GREED_EXTREME_LOW = 20  # Extreme fear
    FEAR_GREED_EXTREME_HIGH = 80  # Extreme greed
    BTC_DOM_RISING_THRESHOLD = 0.5  # 0.5% daily change = significant

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the external data provider."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Override URLs from config if provided
        if 'perps_tracker_url' in self.config:
            self.PERPS_TRACKER_URL = self.config['perps_tracker_url']

        # Cache storage
        self._derivatives_cache: Optional[DerivativesData] = None
        self._global_cache: Optional[GlobalMarketData] = None
        self._sentiment_cache: Optional[SentimentData] = None

        # Shared HTTP session (lazy initialization)
        self._session: Optional[aiohttp.ClientSession] = None

        # Lock to prevent thundering herd on cache miss
        self._fetch_lock: Optional[asyncio.Lock] = None

        self.logger.info("ExternalRegimeDataProvider initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create shared HTTP session."""
        if self._session is None or self._session.closed:
            # Increased timeout to handle event loop contention during WebSocket activity
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_external_signals(self) -> ExternalRegimeSignals:
        """
        Fetch all external data and compute aggregated signals.

        Returns:
            ExternalRegimeSignals with bias, confidence modifier, and warnings
        """
        try:
            # Fetch all data sources concurrently
            derivatives, global_data, sentiment = await asyncio.gather(
                self._fetch_derivatives_data(),
                self._fetch_global_market_data(),
                self._fetch_fear_greed(),
                return_exceptions=True
            )

            # Handle any fetch errors
            if isinstance(derivatives, Exception):
                self.logger.warning(f"Derivatives fetch failed: {derivatives}")
                derivatives = self._derivatives_cache or DerivativesData()

            if isinstance(global_data, Exception):
                self.logger.warning(f"Global market fetch failed: {global_data}")
                global_data = self._global_cache or GlobalMarketData()

            if isinstance(sentiment, Exception):
                self.logger.warning(f"Fear/Greed fetch failed: {sentiment}")
                sentiment = self._sentiment_cache or SentimentData()

            # Compute aggregated signals
            signals = self._compute_aggregated_signals(derivatives, global_data, sentiment)

            return signals

        except Exception as e:
            self.logger.error(f"Error getting external signals: {e}")
            return ExternalRegimeSignals()

    async def _fetch_derivatives_data(self) -> DerivativesData:
        """Fetch derivatives data from perps-tracker with retry and thundering herd protection."""
        now = time.time()

        # Fast path: check cache without lock
        if self._derivatives_cache and (now - self._derivatives_cache.timestamp) < self.PERPS_TTL:
            return self._derivatives_cache

        # Lazy init lock (must be created in async context)
        if self._fetch_lock is None:
            self._fetch_lock = asyncio.Lock()

        # Acquire lock to prevent thundering herd
        async with self._fetch_lock:
            # Double-check cache after acquiring lock (another coroutine may have populated it)
            now = time.time()
            if self._derivatives_cache and (now - self._derivatives_cache.timestamp) < self.PERPS_TTL:
                return self._derivatives_cache

            # Retry with backoff for local service (handles event loop contention)
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    session = await self._get_session()
                    async with session.get(self.PERPS_TRACKER_URL) as response:
                        if response.status == 200:
                            data = await response.json()

                            if data.get('status') == 'success':
                                result = DerivativesData(
                                    funding_rate=data.get('funding_rate', 0.0),
                                    funding_sentiment=data.get('funding_sentiment', 'NEUTRAL'),
                                    basis_pct=data.get('basis_pct', 0.0),
                                    basis_status=data.get('basis_status', 'NEUTRAL'),
                                    long_pct=data.get('long_pct', 50.0),
                                    short_pct=data.get('short_pct', 50.0),
                                    total_open_interest=data.get('total_open_interest', 0.0),
                                    total_volume_24h=data.get('total_volume_24h', 0.0),
                                    timestamp=time.time(),
                                    is_fresh=True
                                )

                                self._derivatives_cache = result
                                self.logger.debug(
                                    f"Perps data: funding={result.funding_rate:.4f}, "
                                    f"L/S={result.long_pct:.1f}/{result.short_pct:.1f}, "
                                    f"basis={result.basis_pct:.3f}"
                                )
                                return result

                        self.logger.warning("Perps tracker returned non-success status")
                        break  # Don't retry non-success responses

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        self.logger.debug(f"Perps tracker timeout, retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(1)  # Brief pause before retry
                    else:
                        self.logger.warning("Perps tracker request timed out after retries")
                except aiohttp.ClientError as e:
                    self.logger.warning(f"Perps tracker connection error: {e}")
                    break  # Don't retry connection errors
                except Exception as e:
                    self.logger.error(f"Perps tracker error: {e}")
                    break

            return self._derivatives_cache or DerivativesData()

    async def _fetch_global_market_data(self) -> GlobalMarketData:
        """Fetch global market data from CoinGecko."""
        now = time.time()

        # Check cache
        if self._global_cache and (now - self._global_cache.timestamp) < self.COINGECKO_TTL:
            return self._global_cache

        try:
            session = await self._get_session()
            async with session.get(self.COINGECKO_GLOBAL_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    global_data = data.get('data', {})
                    market_cap_pct = global_data.get('market_cap_percentage', {})

                    result = GlobalMarketData(
                        btc_dominance=market_cap_pct.get('btc', 57.0),
                        eth_dominance=market_cap_pct.get('eth', 11.5),
                        market_cap_change_24h=global_data.get('market_cap_change_percentage_24h_usd', 0.0),
                        total_market_cap=global_data.get('total_market_cap', {}).get('usd', 0),
                        total_volume_24h=global_data.get('total_volume', {}).get('usd', 0),
                        active_cryptocurrencies=global_data.get('active_cryptocurrencies', 0),
                        timestamp=now,
                        is_fresh=True
                    )

                    self._global_cache = result
                    self.logger.debug(
                        f"CoinGecko: BTC dom={result.btc_dominance:.1f}%, "
                        f"MCap chg={result.market_cap_change_24h:.2f}%"
                    )
                    return result

        except asyncio.TimeoutError:
            self.logger.warning("CoinGecko request timed out")
        except Exception as e:
            self.logger.warning(f"CoinGecko error: {e}")

        return self._global_cache or GlobalMarketData()

    async def _fetch_fear_greed(self) -> SentimentData:
        """Fetch Fear & Greed Index from Alternative.me."""
        now = time.time()

        # Check cache
        if self._sentiment_cache and (now - self._sentiment_cache.timestamp) < self.FEAR_GREED_TTL:
            return self._sentiment_cache

        try:
            session = await self._get_session()
            async with session.get(self.FEAR_GREED_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    fng_data = data.get('data', [{}])[0]

                    result = SentimentData(
                        value=int(fng_data.get('value', 50)),
                        classification=fng_data.get('value_classification', 'Neutral'),
                        timestamp=now,
                        is_fresh=True
                    )

                    self._sentiment_cache = result
                    self.logger.debug(f"Fear/Greed: {result.value} ({result.classification})")
                    return result

        except asyncio.TimeoutError:
            self.logger.warning("Fear/Greed request timed out")
        except Exception as e:
            self.logger.warning(f"Fear/Greed error: {e}")

        return self._sentiment_cache or SentimentData()

    def _compute_aggregated_signals(
        self,
        derivatives: DerivativesData,
        global_data: GlobalMarketData,
        sentiment: SentimentData
    ) -> ExternalRegimeSignals:
        """
        Compute aggregated signals from all external data sources.

        Signal Logic:
        1. Derivatives signals (funding, basis, L/S ratio) → sentiment bias
        2. Global market signals (dominance, mcap change) → trend confirmation
        3. Fear/Greed → confidence adjustment and warning signals

        Returns:
            ExternalRegimeSignals with computed bias and modifiers
        """
        signals = ExternalRegimeSignals(
            derivatives=derivatives,
            global_market=global_data,
            sentiment=sentiment,
            timestamp=time.time()
        )

        # Calculate data quality (how fresh is the data)
        fresh_count = sum([
            derivatives.is_fresh,
            global_data.is_fresh,
            sentiment.is_fresh
        ])
        signals.data_quality = fresh_count / 3.0

        # === 1. Derivatives Bias Analysis ===
        deriv_bias = self._analyze_derivatives_bias(derivatives)

        # === 2. Market Structure Analysis ===
        market_bias = self._analyze_market_structure(global_data)

        # === 3. Sentiment Analysis ===
        sentiment_bias, sentiment_modifier = self._analyze_sentiment(sentiment)

        # === 4. Combine Signals ===
        # Weight: derivatives (40%), market structure (30%), sentiment (30%)
        bias_scores = {
            SentimentBias.EXTREME_BULLISH: 2.0,
            SentimentBias.BULLISH: 1.0,
            SentimentBias.NEUTRAL: 0.0,
            SentimentBias.BEARISH: -1.0,
            SentimentBias.EXTREME_BEARISH: -2.0
        }

        combined_score = (
            bias_scores[deriv_bias] * 0.4 +
            bias_scores[market_bias] * 0.3 +
            bias_scores[sentiment_bias] * 0.3
        )

        # Map combined score to overall bias
        if combined_score >= 1.5:
            signals.overall_bias = SentimentBias.EXTREME_BULLISH
        elif combined_score >= 0.5:
            signals.overall_bias = SentimentBias.BULLISH
        elif combined_score <= -1.5:
            signals.overall_bias = SentimentBias.EXTREME_BEARISH
        elif combined_score <= -0.5:
            signals.overall_bias = SentimentBias.BEARISH
        else:
            signals.overall_bias = SentimentBias.NEUTRAL

        # === 5. Confidence Modifier ===
        # Start with sentiment modifier (0.8-1.2)
        signals.confidence_modifier = sentiment_modifier

        # Adjust for data quality
        if signals.data_quality < 0.5:
            signals.confidence_modifier *= 0.9  # Reduce confidence if data is stale

        # Alignment bonus: when all signals agree
        if deriv_bias == market_bias == sentiment_bias:
            signals.confidence_modifier *= 1.1  # 10% bonus for alignment

        # Clamp to reasonable range
        signals.confidence_modifier = max(0.7, min(1.3, signals.confidence_modifier))

        # === 6. Warning Signals ===
        # Volatility warning: extreme funding rates or fear/greed
        if (abs(derivatives.funding_rate) > self.FUNDING_EXTREME_THRESHOLD or
            sentiment.value <= self.FEAR_GREED_EXTREME_LOW or
            sentiment.value >= self.FEAR_GREED_EXTREME_HIGH):
            signals.volatility_warning = True

        # Liquidity warning: basis in significant backwardation
        if derivatives.basis_pct < -0.5:  # >0.5% backwardation
            signals.liquidity_warning = True

        self.logger.info(
            f"External signals: bias={signals.overall_bias.value}, "
            f"conf_mod={signals.confidence_modifier:.2f}, "
            f"vol_warn={signals.volatility_warning}, "
            f"quality={signals.data_quality:.1%}"
        )

        return signals

    def _analyze_derivatives_bias(self, data: DerivativesData) -> SentimentBias:
        """Analyze derivatives data for sentiment bias."""
        bias_score = 0.0

        # Funding rate signal
        if data.funding_rate > self.FUNDING_EXTREME_THRESHOLD:
            bias_score += 1.5  # Extreme longs = contrarian bearish signal
        elif data.funding_rate > self.FUNDING_ELEVATED_THRESHOLD:
            bias_score += 0.5
        elif data.funding_rate < -self.FUNDING_EXTREME_THRESHOLD:
            bias_score -= 1.5  # Extreme shorts = contrarian bullish signal
        elif data.funding_rate < -self.FUNDING_ELEVATED_THRESHOLD:
            bias_score -= 0.5

        # Long/Short ratio signal (contrarian)
        # If everyone is long, be cautious; if everyone is short, be optimistic
        ls_ratio = data.long_pct / 100.0
        if ls_ratio > self.LONG_SHORT_EXTREME_THRESHOLD:
            bias_score -= 1.0  # Too many longs = bearish contrarian
        elif ls_ratio < (1 - self.LONG_SHORT_EXTREME_THRESHOLD):
            bias_score += 1.0  # Too many shorts = bullish contrarian

        # Basis signal
        if data.basis_status == "CONTANGO":
            bias_score += 0.5  # Futures premium = bullish
        elif data.basis_status == "BACKWARDATION":
            bias_score -= 0.5  # Futures discount = bearish

        # Map score to bias
        if bias_score >= 1.5:
            return SentimentBias.EXTREME_BULLISH
        elif bias_score >= 0.5:
            return SentimentBias.BULLISH
        elif bias_score <= -1.5:
            return SentimentBias.EXTREME_BEARISH
        elif bias_score <= -0.5:
            return SentimentBias.BEARISH
        return SentimentBias.NEUTRAL

    def _analyze_market_structure(self, data: GlobalMarketData) -> SentimentBias:
        """Analyze global market structure for sentiment bias."""
        bias_score = 0.0

        # Market cap change signal
        if data.market_cap_change_24h > 3.0:
            bias_score += 1.5
        elif data.market_cap_change_24h > 1.0:
            bias_score += 0.5
        elif data.market_cap_change_24h < -3.0:
            bias_score -= 1.5
        elif data.market_cap_change_24h < -1.0:
            bias_score -= 0.5

        # BTC dominance signal (inversely correlated with altcoin season)
        # Rising BTC dominance = risk-off (bearish for alts, neutral/bullish for BTC)
        # Falling BTC dominance = risk-on (bullish for alts)
        # For regime detection, we treat this as a market structure signal
        if data.btc_dominance > 60:
            bias_score -= 0.3  # High BTC dom = cautious
        elif data.btc_dominance < 50:
            bias_score += 0.3  # Low BTC dom = risk-on

        # Map score to bias
        if bias_score >= 1.5:
            return SentimentBias.EXTREME_BULLISH
        elif bias_score >= 0.5:
            return SentimentBias.BULLISH
        elif bias_score <= -1.5:
            return SentimentBias.EXTREME_BEARISH
        elif bias_score <= -0.5:
            return SentimentBias.BEARISH
        return SentimentBias.NEUTRAL

    def _analyze_sentiment(self, data: SentimentData) -> tuple[SentimentBias, float]:
        """
        Analyze Fear & Greed Index for sentiment bias and confidence modifier.

        Returns:
            Tuple of (SentimentBias, confidence_modifier)
        """
        value = data.value

        # Map to bias (note: extreme fear is contrarian bullish)
        if value <= 20:
            bias = SentimentBias.EXTREME_BULLISH  # Extreme fear = buy signal
            modifier = 0.85  # Reduce confidence (high volatility likely)
        elif value <= 35:
            bias = SentimentBias.BULLISH  # Fear = moderate buy
            modifier = 0.95
        elif value >= 80:
            bias = SentimentBias.EXTREME_BEARISH  # Extreme greed = sell signal
            modifier = 0.85  # Reduce confidence (correction likely)
        elif value >= 65:
            bias = SentimentBias.BEARISH  # Greed = moderate caution
            modifier = 0.95
        else:
            bias = SentimentBias.NEUTRAL
            modifier = 1.0

        return bias, modifier

    def get_regime_adjustment(self, signals: ExternalRegimeSignals) -> Dict[str, Any]:
        """
        Get regime adjustment recommendations based on external signals.

        Use this to modify regime detection decisions based on external data.

        Returns:
            Dict with:
            - bias_direction: -1 (bearish) to +1 (bullish)
            - confidence_modifier: multiply base confidence by this
            - regime_overrides: list of regime transitions to consider
        """
        bias_map = {
            SentimentBias.EXTREME_BULLISH: 1.0,
            SentimentBias.BULLISH: 0.5,
            SentimentBias.NEUTRAL: 0.0,
            SentimentBias.BEARISH: -0.5,
            SentimentBias.EXTREME_BEARISH: -1.0
        }

        result = {
            'bias_direction': bias_map[signals.overall_bias],
            'confidence_modifier': signals.confidence_modifier,
            'regime_overrides': [],
            'warnings': []
        }

        # Add override suggestions
        if signals.volatility_warning:
            result['regime_overrides'].append('HIGH_VOLATILITY')
            result['warnings'].append('External data suggests elevated volatility')

        if signals.liquidity_warning:
            result['regime_overrides'].append('LOW_LIQUIDITY')
            result['warnings'].append('Significant backwardation detected')

        # Extreme sentiment suggests reversal potential
        if signals.overall_bias in [SentimentBias.EXTREME_BULLISH, SentimentBias.EXTREME_BEARISH]:
            result['warnings'].append(f'Extreme sentiment: {signals.overall_bias.value}')

        return result
