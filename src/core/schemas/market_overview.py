"""
Market Overview Schema
======================

Unified contract for market:overview cache key.

This schema is the SINGLE SOURCE OF TRUTH for market overview data.
Both monitoring and web services MUST use this schema to ensure
data compatibility and prevent schema mismatches.

Problem Solved:
    Before: Monitoring wrote 'total_symbols_monitored', web expected 'total_symbols'
    After: Both use MarketOverviewSchema.total_symbols
"""

from dataclasses import dataclass
from typing import Optional
import logging
from .base import CacheSchema, SchemaVersion

logger = logging.getLogger(__name__)


@dataclass
class MarketOverviewSchema(CacheSchema):
    """
    Market overview data schema

    This schema defines ALL fields that can appear in market:overview cache key.
    Any service reading or writing market overview data MUST use this schema.

    Core Fields:
        total_symbols: Total number of symbols being monitored
        total_volume_24h: Total 24h trading volume across all symbols (USD)
        trend_strength: Market trend strength indicator (0-100, 50=neutral)
        btc_dominance: Bitcoin dominance percentage (0-100)

    Volatility Fields:
        current_volatility: Current market volatility (0-100)
        avg_volatility: Average volatility measure (0-100)

    Market State:
        market_regime: Current market regime (Bullish, Bearish, Choppy, Neutral, etc.)
        average_change: Average price change across all symbols (%)

    Volume Breakdown:
        total_volume: Alias for total_volume_24h (backward compatibility)
        spot_volume_24h: Spot market volume (USD)
        linear_volume_24h: Linear/perpetual futures volume (USD)

    Symbol Counts:
        spot_symbols: Number of spot trading pairs
        linear_symbols: Number of linear/perpetual pairs

    Market Sentiment (optional):
        gainers: Number of symbols with positive change
        losers: Number of symbols with negative change

    Migration Helper:
        from_monitoring_data(): Converts old monitoring format to unified format
    """

    # Class constants
    CACHE_KEY = "market:overview"
    VERSION = SchemaVersion.V1

    # === Core Required Fields ===
    total_symbols: int = 0
    total_volume_24h: float = 0.0
    trend_strength: float = 50.0  # 0-100, 50=neutral
    btc_dominance: float = 59.3  # Realistic default

    # === Volatility Measures ===
    # TRUE Crypto Volatility (BTC realized volatility)
    btc_volatility: float = 0.0  # Annualized BTC volatility %
    btc_daily_volatility: float = 0.0  # Daily BTC volatility %
    btc_price: float = 0.0  # Current BTC price
    btc_vol_days: int = 0  # Days of data in volatility calculation

    # Market Dispersion (cross-sectional volatility - spread of returns)
    market_dispersion: float = 0.0  # Current market dispersion %
    avg_market_dispersion: float = 8.0  # Average market dispersion %

    # DEPRECATED: Keep for backward compatibility
    current_volatility: float = 0.0  # DEPRECATED: Use market_dispersion
    avg_volatility: float = 8.0  # DEPRECATED: Use avg_market_dispersion

    # === Market State ===
    average_change: float = 0.0  # Average % change
    market_regime: str = "NEUTRAL"

    # === Volume Breakdown ===
    total_volume: float = 0.0  # Alias for backward compatibility
    spot_volume_24h: float = 0.0
    linear_volume_24h: float = 0.0

    # === Symbol Counts ===
    spot_symbols: int = 0
    linear_symbols: int = 0

    # === Market Sentiment (Optional) ===
    gainers: Optional[int] = None
    losers: Optional[int] = None

    # === CoinGecko Global Data - Additional Dominance Metrics ===
    eth_dominance: float = 11.5  # ETH market cap dominance %
    stablecoin_dominance: float = 8.0  # USDT + USDC combined %
    altcoin_dominance: float = 43.0  # 100 - BTC dominance
    altcoin_season: str = "Dormant"  # Active/Emerging/Dormant

    # === CoinGecko Global Data - Market Cap Metrics ===
    total_market_cap: float = 0.0  # Total crypto market cap (USD)
    market_cap_change_24h: float = 0.0  # 24h market cap change %
    coingecko_volume_24h: float = 0.0  # CoinGecko total 24h volume
    volume_mcap_ratio: float = 0.0  # Volume/Market Cap ratio (liquidity indicator)
    active_cryptocurrencies: int = 0  # Number of active cryptos tracked

    # === Fear & Greed Index (Alternative.me) ===
    fear_greed_value: int = 50  # 0-100 scale
    fear_greed_label: str = "Neutral"  # Extreme Fear/Fear/Neutral/Greed/Extreme Greed

    # === DeFi Data (CoinGecko DeFi endpoint) ===
    defi_market_cap: float = 0.0  # DeFi sector market cap
    defi_dominance: float = 0.0  # DeFi % of total market
    defi_volume_24h: float = 0.0  # DeFi 24h trading volume
    top_defi_protocol: str = ""  # Leading DeFi protocol name
    top_defi_dominance: float = 0.0  # Leading protocol's % of DeFi

    def __post_init__(self):
        """Ensure total_volume stays in sync with total_volume_24h"""
        # Keep both fields synchronized for backward compatibility
        if self.total_volume == 0 and self.total_volume_24h > 0:
            self.total_volume = self.total_volume_24h
        elif self.total_volume_24h == 0 and self.total_volume > 0:
            self.total_volume_24h = self.total_volume

    def validate(self) -> bool:
        """
        Validate market overview data integrity

        Checks:
        - Base validation (non-None required fields)
        - Percentage fields in valid range (0-100)
        - Volume fields non-negative
        - Total symbols matches symbol breakdown

        Returns:
            bool: True if all validation passes
        """
        if not super().validate():
            return False

        # Validate percentages are in valid range
        if not 0 <= self.trend_strength <= 100:
            logger.warning(
                f"trend_strength out of range [0-100]: {self.trend_strength}"
            )
            return False

        if not 0 <= self.btc_dominance <= 100:
            logger.warning(
                f"btc_dominance out of range [0-100]: {self.btc_dominance}"
            )
            return False

        if not 0 <= self.current_volatility <= 100:
            logger.warning(
                f"current_volatility out of range [0-100]: {self.current_volatility}"
            )
            return False

        # Validate volumes are non-negative
        if self.total_volume_24h < 0:
            logger.error(f"Negative total_volume_24h: {self.total_volume_24h}")
            return False

        if self.spot_volume_24h < 0:
            logger.error(f"Negative spot_volume_24h: {self.spot_volume_24h}")
            return False

        if self.linear_volume_24h < 0:
            logger.error(f"Negative linear_volume_24h: {self.linear_volume_24h}")
            return False

        # Validate symbol counts make sense
        calculated_total = self.spot_symbols + self.linear_symbols
        if calculated_total > 0 and self.total_symbols != calculated_total:
            logger.debug(
                f"Symbol count mismatch: total={self.total_symbols}, "
                f"spot+linear={calculated_total}"
            )
            # Not a fatal error, just a warning

        return True

    @classmethod
    def from_monitoring_data(cls, monitoring_data: dict) -> 'MarketOverviewSchema':
        """
        Create unified schema from monitoring service data format

        This method handles the migration from the OLD monitoring schema
        (with fields like 'total_symbols_monitored', 'active_signals_1h')
        to the NEW unified schema (with standardized field names).

        Migration Mapping:
            total_symbols_monitored → total_symbols
            total_volume → total_volume_24h
            bullish_signals, bearish_signals → trend_strength (calculated)
            btc_dom → btc_dominance
            volatility → current_volatility
            avg_change_percent → average_change
            market_state → market_regime

        Args:
            monitoring_data: Data in old monitoring service format

        Returns:
            MarketOverviewSchema instance with unified format

        Example:
            old_data = {
                'total_symbols_monitored': 15,
                'bullish_signals': 8,
                'bearish_signals': 2,
                'total_volume': 45000000000
            }
            schema = MarketOverviewSchema.from_monitoring_data(old_data)
            # schema.total_symbols = 15
            # schema.trend_strength = 80 (calculated from 8 vs 2)
        """
        return cls(
            # Core fields with mapping
            total_symbols=monitoring_data.get('total_symbols_monitored', 0),
            # FIXED: Use total_volume_24h first (CoinGecko global volume), fallback to total_volume
            total_volume_24h=monitoring_data.get('total_volume_24h', monitoring_data.get('total_volume', 0.0)),
            total_volume=monitoring_data.get('total_volume_24h', monitoring_data.get('total_volume', 0.0)),

            # Calculated trend strength from signals
            trend_strength=cls._calculate_trend_strength(monitoring_data),

            # BTC dominance with alias support
            btc_dominance=monitoring_data.get('btc_dominance',
                                             monitoring_data.get('btc_dom', 59.3)),

            # BTC Volatility (TRUE crypto volatility)
            btc_volatility=monitoring_data.get('btc_volatility', 0.0),
            btc_daily_volatility=monitoring_data.get('btc_daily_volatility', 0.0),
            btc_price=monitoring_data.get('btc_price', 0.0),
            btc_vol_days=monitoring_data.get('btc_vol_days', 0),

            # Market Dispersion
            market_dispersion=monitoring_data.get('market_dispersion',
                                                 monitoring_data.get('volatility', 0.0)),
            avg_market_dispersion=monitoring_data.get('avg_market_dispersion',
                                                     monitoring_data.get('avg_volatility', 8.0)),

            # DEPRECATED: Keep for backward compatibility
            current_volatility=monitoring_data.get('market_dispersion',
                                                  monitoring_data.get('volatility', 0.0)),
            avg_volatility=monitoring_data.get('avg_market_dispersion',
                                              monitoring_data.get('avg_volatility', 8.0)),

            # Market state
            average_change=monitoring_data.get('avg_change_percent',
                                              monitoring_data.get('average_change', 0.0)),
            market_regime=monitoring_data.get('market_state',
                                             monitoring_data.get('market_regime', 'NEUTRAL')),

            # Volume breakdown
            spot_volume_24h=monitoring_data.get('spot_volume', 0.0),
            linear_volume_24h=monitoring_data.get('linear_volume', 0.0),

            # Symbol counts
            spot_symbols=monitoring_data.get('spot_count',
                                            monitoring_data.get('spot_symbols', 0)),
            linear_symbols=monitoring_data.get('linear_count',
                                              monitoring_data.get('linear_symbols', 0)),

            # Sentiment counts (if available)
            gainers=monitoring_data.get('gainers'),
            losers=monitoring_data.get('losers'),

            # CoinGecko Global Data - Additional Dominance Metrics
            eth_dominance=monitoring_data.get('eth_dominance', 11.5),
            stablecoin_dominance=monitoring_data.get('stablecoin_dominance', 8.0),
            altcoin_dominance=monitoring_data.get('altcoin_dominance', 43.0),
            altcoin_season=monitoring_data.get('altcoin_season', 'Dormant'),

            # CoinGecko Global Data - Market Cap Metrics
            total_market_cap=monitoring_data.get('total_market_cap', 0.0),
            market_cap_change_24h=monitoring_data.get('market_cap_change_24h', 0.0),
            coingecko_volume_24h=monitoring_data.get('coingecko_volume_24h', 0.0),
            volume_mcap_ratio=monitoring_data.get('volume_mcap_ratio', 0.0),
            active_cryptocurrencies=monitoring_data.get('active_cryptocurrencies', 0),

            # Fear & Greed Index (Alternative.me)
            fear_greed_value=monitoring_data.get('fear_greed_value', 50),
            fear_greed_label=monitoring_data.get('fear_greed_label', 'Neutral'),

            # DeFi Data (CoinGecko DeFi endpoint)
            defi_market_cap=monitoring_data.get('defi_market_cap', 0.0),
            defi_dominance=monitoring_data.get('defi_dominance', 0.0),
            defi_volume_24h=monitoring_data.get('defi_volume_24h', 0.0),
            top_defi_protocol=monitoring_data.get('top_defi_protocol', ''),
            top_defi_dominance=monitoring_data.get('top_defi_dominance', 0.0),
        )

    @staticmethod
    def _calculate_trend_strength(data: dict) -> float:
        """
        Calculate trend strength from market data

        Uses the ratio of gainers vs losers (or bullish vs bearish signals) to determine trend strength.

        Scale:
            0-100 where:
            - 0 = Strongly bearish (all losers/bearish)
            - 50 = Neutral (equal gainers/losers)
            - 100 = Strongly bullish (all gainers/bullish)

        Args:
            data: Dictionary containing either:
                - 'gainers' and 'losers' (preferred - reflects actual market movement)
                - 'bullish_signals' and 'bearish_signals' (fallback - trading signals)

        Returns:
            float: Trend strength between 0-100

        Example:
            data = {'gainers': 8, 'losers': 2}
            strength = _calculate_trend_strength(data)
            # Returns ~80 (8 gainers vs 2 losers = bullish trend)
        """
        # CRITICAL FIX: Prefer gainers/losers (actual market movement) over signals
        if 'gainers' in data and 'losers' in data and (data['gainers'] is not None or data['losers'] is not None):
            bullish = data.get('gainers', 0) or 0
            bearish = data.get('losers', 0) or 0
        else:
            # Fallback to trading signals
            bullish = data.get('bullish_signals', 0)
            bearish = data.get('bearish_signals', 0)

        total = bullish + bearish

        if total == 0:
            return 50.0  # Neutral when no data

        # Calculate imbalance (-1 to 1)
        # -1 = all bearish, 0 = equal, 1 = all bullish
        imbalance = (bullish - bearish) / total

        # Map from [-1, 1] to [0, 100]
        trend_strength = 50.0 + (imbalance * 50.0)

        return round(trend_strength, 2)

    def to_dashboard_dict(self) -> dict:
        """
        Convert to dictionary format expected by dashboard

        Includes both standard fields and aliases for backward compatibility.

        Returns:
            dict: Dashboard-compatible data structure
        """
        base_dict = self.to_dict()

        # Add aliases for backward compatibility
        base_dict['volatility'] = self.current_volatility
        base_dict['avg_range_24h'] = 0.0  # TODO: Calculate if needed
        base_dict['reliability'] = 75.0  # TODO: Calculate if needed
        base_dict['active_symbols'] = self.total_symbols

        return base_dict
