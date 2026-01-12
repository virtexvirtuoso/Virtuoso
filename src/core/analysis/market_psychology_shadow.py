#!/usr/bin/env python3
"""
Market Psychology Shadow Mode
=============================

Runs market psychology indicators in shadow mode - observing and logging
without affecting trading decisions. This allows validation of:
- Open Interest Z-Score
- Order Book Depth Imbalance
- Correlation Rate of Change

These indicators feed into novel trading signals (CAS, CTUS, CREW, FRAPS).

Usage:
    python src/core/analysis/market_psychology_shadow.py
"""

import asyncio
import logging
import os
import sys
import signal
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from src.core.analysis.market_psychology_indicators import (
    OpenInterestZScore,
    OrderBookDepthImbalance,
    CorrelationRateOfChange,
    create_market_psychology_calculators
)
from src.core.analysis.cas_calculator import CASCalculator, create_cas_calculator
from src.core.analysis.liquidation_cluster_service import get_liquidation_service, LiquidationClusterService
from src.database.shadow_storage import (
    init_shadow_tables,
    store_cas_signal,
    get_cas_signals_pending_returns,
    update_cas_forward_returns,
    store_btc_prediction,
    store_crypto_regime_detection,
    get_crypto_regime_pending_returns,
    update_crypto_regime_forward_returns,
    store_dual_regime_adjustment,
    get_dual_regime_pending_returns,
    update_dual_regime_forward_returns,
    store_distribution_signal,
    get_distribution_pending_returns,
    update_distribution_forward_returns
)
from src.core.analysis.bitcoin_altcoin_predictor import BitcoinAltcoinPredictor
from src.core.analysis.crypto_regime_enhancements import CryptoRegimeDetector, CryptoRegimeThresholds

# Configure logging
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Discord webhook for development alerts
DISCORD_WEBHOOK_URL = os.getenv('DEVELOPMENT_WEBHOOK_URL', '')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, 'market_psychology_shadow.log'))
    ]
)
logger = logging.getLogger('MarketPsychologyShadow')


class MarketPsychologyShadowMode:
    """
    Shadow mode runner for market psychology indicators.

    Connects to live market data and calculates indicators without
    affecting trading decisions. Logs results for analysis.
    """

    # Default symbols (used as fallback if config unavailable)
    DEFAULT_SYMBOLS = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT',
        'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'POLUSDT', 'ATOMUSDT'
    ]

    # Update intervals
    OI_UPDATE_INTERVAL = 300      # 5 minutes
    ORDERBOOK_INTERVAL = 60       # 1 minute
    CORRELATION_INTERVAL = 3600   # 1 hour
    CAS_UPDATE_INTERVAL = 300     # 5 minutes (aligned with liquidation data refresh)
    FORWARD_RETURN_INTERVAL = 900 # 15 minutes (check for return calculations)
    LOG_SUMMARY_INTERVAL = 3600   # 1 hour (check for daily report)
    REPORT_HOUR_UTC = 0           # Midnight UTC (aligned with other shadow reports)
    BTC_PREDICTION_INTERVAL = 300 # 5 minutes (aligned with BTC moves)
    CRYPTO_REGIME_INTERVAL = 300  # 5 minutes (regime can shift quickly)
    DUAL_REGIME_INTERVAL = 600    # 10 minutes (less frequent, regime-level)
    DISTRIBUTION_SIGNAL_INTERVAL = 300  # 5 minutes (CVD divergence detection)

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize shadow mode runner.

        Args:
            config: Optional config dict. If not provided, loads from config.yaml
        """
        self.calculators = create_market_psychology_calculators()
        self.cas_calculator = create_cas_calculator()  # CAS v2.0 calculator
        self.btc_predictor = BitcoinAltcoinPredictor()  # BTC lead/lag predictor
        self.crypto_regime_detector = CryptoRegimeDetector()  # Crypto-specific regimes
        self.exchange = None
        self.running = False
        self.tasks: List[asyncio.Task] = []  # Store task references for graceful shutdown
        self._shutdown_event: Optional[asyncio.Event] = None  # Event to signal shutdown

        # Load config and symbols
        self.config = config or self._load_config()
        self.tracked_symbols = self._load_symbols()

        # Initialize shadow storage tables (including CAS)
        init_shadow_tables()

        # Track extreme signals
        self.extreme_signals: List[Dict[str, Any]] = []
        self.last_summary_time = datetime.now(timezone.utc)
        self.last_daily_report_date: Optional[str] = None  # Track daily report to avoid duplicates

        # Cooldown tracking for real-time alerts (1 hour per symbol+type combo)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.ALERT_COOLDOWN_SECONDS = 3600  # 1 hour cooldown per symbol

        # Statistics
        self.stats = {
            'oi_updates': 0,
            'orderbook_updates': 0,
            'correlation_updates': 0,
            'cas_updates': 0,
            'cas_valid_signals': 0,
            'cas_strong_signals': 0,
            'extreme_oi_signals': 0,
            'extreme_depth_signals': 0,
            'regime_changes': 0,
            'forward_returns_calculated': 0,
            'btc_predictions': 0,
            'btc_divergence_signals': 0,
            'crypto_regime_detections': 0,
            'dual_regime_adjustments': 0,
            'distribution_signals': 0,
            'distribution_bearish_signals': 0,
            'distribution_bullish_signals': 0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }

        # Discord webhook
        self.webhook_url = DISCORD_WEBHOOK_URL
        self.alerts_sent = 0

        logger.info("MarketPsychologyShadowMode initialized")
        logger.info(f"Tracking symbols: {self.tracked_symbols}")
        logger.info(f"Discord alerts: {'✅ Enabled' if self.webhook_url else '❌ Disabled'}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml."""
        try:
            import yaml
            config_path = os.path.join(PROJECT_ROOT, 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}, using defaults")
            return {}

    def _load_symbols(self) -> List[str]:
        """Load initial symbols from defaults (will be updated dynamically at startup)."""
        return self.DEFAULT_SYMBOLS.copy()

    async def _fetch_top_symbols_from_bybit(self, limit: int = 10) -> List[str]:
        """Fetch top perpetual symbols by 24h volume from Bybit API.

        Args:
            limit: Number of top symbols to return

        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=linear"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(BYBIT_TICKERS_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Bybit API returned {response.status}, using defaults")
                        return self.DEFAULT_SYMBOLS.copy()

                    data = await response.json()

                    if data.get('retCode') != 0:
                        logger.warning(f"Bybit API error: {data.get('retMsg')}, using defaults")
                        return self.DEFAULT_SYMBOLS.copy()

                    tickers = data.get('result', {}).get('list', [])
                    if not tickers:
                        logger.warning("No tickers from Bybit API, using defaults")
                        return self.DEFAULT_SYMBOLS.copy()

                    # Filter USDT perpetuals and sort by 24h turnover (USD volume)
                    usdt_perps = [
                        t for t in tickers
                        if t.get('symbol', '').endswith('USDT')
                        and not t.get('symbol', '').endswith('1000USDT')  # Skip 1000x contracts
                    ]

                    # Sort by 24h turnover (highest first)
                    usdt_perps.sort(
                        key=lambda x: float(x.get('turnover24h', 0)),
                        reverse=True
                    )

                    # Get top symbols by volume
                    top_symbols = [t['symbol'] for t in usdt_perps[:limit]]

                    # Ensure major coins are always included (essential for market analysis)
                    # These are the most liquid, lowest manipulation risk, best for psychology signals
                    essential_majors = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
                    for sym in essential_majors:
                        if sym not in top_symbols:
                            # Insert at position after existing majors but before others
                            insert_pos = sum(1 for s in top_symbols if s in essential_majors)
                            top_symbols.insert(insert_pos, sym)
                            if len(top_symbols) > limit:
                                top_symbols.pop()  # Remove last to maintain limit

                    logger.info(f"📊 Fetched top {len(top_symbols)} symbols by volume from Bybit:")
                    for i, sym in enumerate(top_symbols, 1):
                        ticker = next((t for t in usdt_perps if t['symbol'] == sym), None)
                        if ticker:
                            vol_usd = float(ticker.get('turnover24h', 0)) / 1e9  # Billions
                            logger.info(f"   {i}. {sym}: ${vol_usd:.2f}B 24h volume")

                    return top_symbols

        except asyncio.TimeoutError:
            logger.warning("Bybit API timeout, using defaults")
            return self.DEFAULT_SYMBOLS.copy()
        except Exception as e:
            logger.error(f"Error fetching symbols from Bybit: {e}, using defaults")
            return self.DEFAULT_SYMBOLS.copy()

    async def _update_tracked_symbols(self):
        """Update tracked symbols from Bybit API."""
        new_symbols = await self._fetch_top_symbols_from_bybit(limit=10)

        if new_symbols != self.tracked_symbols:
            old_symbols = set(self.tracked_symbols)
            new_set = set(new_symbols)

            added = new_set - old_symbols
            removed = old_symbols - new_set

            if added:
                logger.info(f"📈 Added symbols: {', '.join(added)}")
            if removed:
                logger.info(f"📉 Removed symbols: {', '.join(removed)}")

            self.tracked_symbols = new_symbols

    async def send_discord_alert(self, embed: Dict[str, Any]) -> bool:
        """Send alert to Discord development webhook."""
        if not self.webhook_url:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"embeds": [embed]}
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.alerts_sent += 1
                        return True
                    else:
                        logger.warning(f"Discord webhook returned {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    def _build_extreme_signal_embed(self, signal_type: str, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Discord embed for extreme signal."""
        # Color based on signal type
        colors = {
            'OI_ZSCORE': 0x3498db,      # Blue
            'DEPTH_IMBALANCE': 0x9b59b6,  # Purple
            'CORRELATION_ROC': 0xe74c3c,  # Red
            'CAS_SIGNAL': 0xf39c12       # Gold/Orange for CAS
        }

        # Emoji based on signal type
        emojis = {
            'OI_ZSCORE': '📊',
            'DEPTH_IMBALANCE': '📈',
            'CORRELATION_ROC': '🔄',
            'CAS_SIGNAL': '🌊'  # Wave emoji for cascade absorption
        }

        color = colors.get(signal_type, 0x95a5a6)
        emoji = emojis.get(signal_type, '⚠️')

        # Build fields based on signal type
        fields = []

        if signal_type == 'OI_ZSCORE':
            fields = [
                {"name": "Z-Score", "value": f"`{data.get('zscore', 0):.2f}`", "inline": True},
                {"name": "Trend", "value": data.get('trend', 'N/A'), "inline": True},
                {"name": "OI Change", "value": f"{data.get('oi_change_pct', 0):.2f}%", "inline": True},
                {"name": "Current OI", "value": f"${data.get('current_oi', 0):,.0f}", "inline": True},
            ]
        elif signal_type == 'DEPTH_IMBALANCE':
            # Determine trading bias from pressure
            pressure = data.get('pressure', 'NEUTRAL')
            if pressure == 'BULLISH':
                bias = '🟢 LONG'
                color = 0x00d68f  # Green
            elif pressure == 'BEARISH':
                bias = '🔴 SHORT'
                color = 0xff5252  # Red
            else:
                bias = '⚪ NEUTRAL'

            fields = [
                {"name": "Trading Bias", "value": f"**{bias}**", "inline": True},
                {"name": "Pressure", "value": pressure, "inline": True},
                {"name": "Z-Score", "value": f"`{data.get('zscore', 0):.2f}`", "inline": True},
                {"name": "OIR", "value": f"`{data.get('oir', 0):.3f}`", "inline": True},
                {"name": "Bid Depth", "value": f"{data.get('bid_depth', 0):,.0f}", "inline": True},
                {"name": "Ask Depth", "value": f"{data.get('ask_depth', 0):,.0f}", "inline": True},
            ]
        elif signal_type == 'CORRELATION_ROC':
            fields = [
                {"name": "Regime", "value": data.get('regime', 'N/A'), "inline": True},
                {"name": "Correlation", "value": f"`{data.get('current_correlation', 0):.3f}`", "inline": True},
                {"name": "RoC", "value": f"{data.get('roc_pct', 0):.2f}%", "inline": True},
                {"name": "Z-Score", "value": f"`{data.get('zscore', 0):.2f}`", "inline": True},
            ]
        elif signal_type == 'CAS_SIGNAL':
            # Determine color based on signal direction
            direction = data.get('signal_direction', 'NEUTRAL')
            if direction == 'BULLISH':
                color = 0x00d68f  # Green
                dir_emoji = '🟢'
            elif direction == 'BEARISH':
                color = 0xff5252  # Red
                dir_emoji = '🔴'
            else:
                dir_emoji = '⚪'

            components = data.get('components', {})
            fields = [
                {"name": "Signal", "value": f"**{dir_emoji} {direction}**", "inline": True},
                {"name": "CAS Score", "value": f"`{data.get('cas_score', 0):.1f}`", "inline": True},
                {"name": "Strength", "value": data.get('signal_strength', 'NONE'), "inline": True},
                {"name": "Cascade Side", "value": data.get('cascade_side', 'N/A').upper(), "inline": True},
                {"name": "Proximity", "value": f"`{components.get('proximity', 0):.2f}`", "inline": True},
                {"name": "Whale Signal", "value": f"`{components.get('whale_signal', 0):.2f}`", "inline": True},
                {"name": "Retail Extreme", "value": f"`{components.get('retail_extreme', 0):.2f}`", "inline": True},
                {"name": "Trend Damping", "value": f"`{components.get('trend_damping', 0):.2f}`", "inline": True},
                {"name": "Confidence", "value": f"`{data.get('confidence', 0):.0%}`", "inline": True},
            ]

        return {
            "title": f"{emoji} {signal_type.replace('_', ' ')} Alert",
            "description": f"**{symbol}** - Extreme signal detected",
            "color": color,
            "fields": fields,
            "footer": {"text": "Market Psychology Shadow Mode"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _build_summary_embed(self) -> Dict[str, Any]:
        """Build Discord embed for periodic summary."""
        uptime = datetime.now(timezone.utc) - datetime.fromisoformat(self.stats['start_time'].replace('Z', '+00:00'))
        hours = uptime.total_seconds() / 3600

        # Get regime summary
        regime_summary = self.calculators['correlation_roc'].get_regime_summary(
            [s.replace('USDT', '') for s in self.tracked_symbols if s != 'BTCUSDT'],
            base='BTC'
        )

        fields = [
            {"name": "⏱️ Uptime", "value": f"{hours:.1f} hours", "inline": True},
            {"name": "📊 OI Updates", "value": str(self.stats['oi_updates']), "inline": True},
            {"name": "📈 Orderbook Updates", "value": str(self.stats['orderbook_updates']), "inline": True},
            {"name": "🔄 Correlation Updates", "value": str(self.stats['correlation_updates']), "inline": True},
            {"name": "🌊 CAS Valid Signals", "value": str(self.stats['cas_valid_signals']), "inline": True},
            {"name": "💪 CAS Strong Signals", "value": str(self.stats['cas_strong_signals']), "inline": True},
            {"name": "🚨 Extreme OI Signals", "value": str(self.stats['extreme_oi_signals']), "inline": True},
            {"name": "📉 Extreme Depth Signals", "value": str(self.stats['extreme_depth_signals']), "inline": True},
            {"name": "⚡ Regime Changes", "value": str(self.stats['regime_changes']), "inline": True},
            {"name": "📤 Alerts Sent", "value": str(self.alerts_sent), "inline": True},
            {"name": "🎯 Dominant Regime", "value": regime_summary.get('dominant_regime', 'UNKNOWN'), "inline": True},
        ]

        # Add recent extreme signals if any
        if self.extreme_signals:
            recent = self.extreme_signals[-3:]
            recent_text = "\n".join([f"• {s['type']} on {s['symbol']}" for s in recent])
            fields.append({"name": "📋 Recent Signals", "value": recent_text, "inline": False})

        return {
            "title": "📊 Market Psychology Shadow Mode Report",
            "description": f"Tracking {len(self.tracked_symbols)} symbols for CAS/CTUS/CREW/FRAPS signals",
            "color": 0x2ecc71,  # Green
            "fields": fields,
            "footer": {"text": "Shadow Mode - Observe Only"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def initialize_exchange(self):
        """Initialize exchange connection."""
        try:
            from src.core.exchanges.bybit import BybitExchange
            import yaml

            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                'config', 'config.yaml'
            )

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.exchange = await BybitExchange.get_instance(config)
            logger.info("✅ Exchange connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            return False

    async def fetch_and_update_oi(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch OI data and update calculator."""
        try:
            if not self.exchange:
                return None

            # Fetch OI history
            oi_history = await self.exchange.fetch_open_interest_history(symbol, interval='5min', limit=50)

            if oi_history and 'data' in oi_history:
                # Update calculator with history
                self.calculators['oi_zscore'].update_from_history(symbol, oi_history['data'])

                # Get latest result
                if oi_history['data']:
                    latest_oi = float(oi_history['data'][-1].get('value', 0))
                    result = self.calculators['oi_zscore'].calculate(symbol, latest_oi)

                    self.stats['oi_updates'] += 1

                    # Log extreme signals
                    if result.is_extreme:
                        self.stats['extreme_oi_signals'] += 1
                        await self._log_extreme_signal('OI_ZSCORE', symbol, result.to_dict())

                    return result.to_dict()

            return None

        except Exception as e:
            logger.error(f"Error fetching OI for {symbol}: {e}")
            return None

    async def fetch_and_update_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch orderbook and update calculator."""
        try:
            if not self.exchange:
                return None

            # Fetch orderbook
            orderbook = await self.exchange.fetch_order_book(symbol, limit=25)

            if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                bids = orderbook['bids']
                asks = orderbook['asks']

                if bids and asks:
                    result = self.calculators['depth_imbalance'].calculate(symbol, bids, asks)

                    self.stats['orderbook_updates'] += 1

                    # Log extreme signals
                    if result.is_extreme:
                        self.stats['extreme_depth_signals'] += 1
                        await self._log_extreme_signal('DEPTH_IMBALANCE', symbol, result.to_dict())

                    return result.to_dict()

            return None

        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None

    async def update_correlations(self) -> Dict[str, Any]:
        """Update correlation calculations."""
        try:
            if not self.exchange:
                return {}

            results = {}

            # Calculate correlations between BTC and alts
            for symbol in self.tracked_symbols:
                if symbol == 'BTCUSDT':
                    continue

                try:
                    # Fetch price history for correlation calculation
                    btc_ohlcv = await self.exchange.fetch_ohlcv('BTCUSDT', '1h', limit=168)  # 7 days
                    alt_ohlcv = await self.exchange.fetch_ohlcv(symbol, '1h', limit=168)

                    if btc_ohlcv and alt_ohlcv and len(btc_ohlcv) > 20 and len(alt_ohlcv) > 20:
                        # Calculate returns
                        btc_returns = [(btc_ohlcv[i][4] - btc_ohlcv[i-1][4]) / btc_ohlcv[i-1][4]
                                      for i in range(1, len(btc_ohlcv))]
                        alt_returns = [(alt_ohlcv[i][4] - alt_ohlcv[i-1][4]) / alt_ohlcv[i-1][4]
                                      for i in range(1, len(alt_ohlcv))]

                        # Align lengths
                        min_len = min(len(btc_returns), len(alt_returns))
                        btc_returns = btc_returns[-min_len:]
                        alt_returns = alt_returns[-min_len:]

                        # Calculate correlation
                        import numpy as np
                        correlation = np.corrcoef(btc_returns, alt_returns)[0, 1]

                        # Update calculator
                        result = self.calculators['correlation_roc'].calculate(
                            'BTC', symbol.replace('USDT', ''), correlation
                        )

                        self.stats['correlation_updates'] += 1

                        if result.is_regime_change:
                            self.stats['regime_changes'] += 1
                            await self._log_extreme_signal('CORRELATION_ROC', symbol, result.to_dict())

                        results[symbol] = result.to_dict()

                except Exception as e:
                    logger.debug(f"Error calculating correlation for {symbol}: {e}")

            return results

        except Exception as e:
            logger.error(f"Error updating correlations: {e}")
            return {}

    async def _log_extreme_signal(self, signal_type: str, symbol: str, data: Dict[str, Any]):
        """
        Log extreme signal and send Discord alert with cooldown.

        Real-time alerts are sent but rate-limited to max 1 per symbol+type per hour
        to avoid spam while still notifying of genuinely extreme events.
        """
        now = datetime.now(timezone.utc)
        cooldown_key = f"{signal_type}:{symbol}"

        signal = {
            'type': signal_type,
            'symbol': symbol,
            'timestamp': now.isoformat(),
            'data': data
        }

        self.extreme_signals.append(signal)

        # Keep last 100 signals
        if len(self.extreme_signals) > 100:
            self.extreme_signals = self.extreme_signals[-100:]

        logger.warning(f"🚨 EXTREME SIGNAL: {signal_type} on {symbol}")
        logger.warning(f"   Data: {json.dumps(data, indent=2, default=str)}")

        # Check cooldown before sending Discord alert
        last_alert_time = self.alert_cooldowns.get(cooldown_key)
        if last_alert_time:
            seconds_since_last = (now - last_alert_time).total_seconds()
            if seconds_since_last < self.ALERT_COOLDOWN_SECONDS:
                remaining = int(self.ALERT_COOLDOWN_SECONDS - seconds_since_last)
                logger.debug(f"Skipping Discord alert for {cooldown_key} (cooldown: {remaining}s remaining)")
                return

        # Send Discord alert and update cooldown
        embed = self._build_extreme_signal_embed(signal_type, symbol, data)
        await self.send_discord_alert(embed)
        self.alert_cooldowns[cooldown_key] = now
        logger.info(f"📤 Discord alert sent for {cooldown_key} (next allowed in {self.ALERT_COOLDOWN_SECONDS}s)")

    async def _log_summary(self, force_discord: bool = False):
        """
        Log periodic summary and send Discord report once daily at midnight UTC.

        Args:
            force_discord: If True, send Discord report regardless of time (used on shutdown)
        """
        now = datetime.now(timezone.utc)
        today_str = now.strftime('%Y-%m-%d')

        # Always log to file (hourly)
        logger.info("=" * 60)
        logger.info("📊 MARKET PSYCHOLOGY SHADOW MODE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Running since: {self.stats['start_time']}")
        logger.info(f"  OI Updates: {self.stats['oi_updates']}")
        logger.info(f"  Orderbook Updates: {self.stats['orderbook_updates']}")
        logger.info(f"  Correlation Updates: {self.stats['correlation_updates']}")
        logger.info(f"  CAS Updates: {self.stats['cas_updates']}")
        logger.info(f"  CAS Valid Signals: {self.stats['cas_valid_signals']}")
        logger.info(f"  CAS Strong Signals: {self.stats['cas_strong_signals']}")
        logger.info(f"  Forward Returns Calculated: {self.stats['forward_returns_calculated']}")
        logger.info(f"  Extreme OI Signals: {self.stats['extreme_oi_signals']}")
        logger.info(f"  Extreme Depth Signals: {self.stats['extreme_depth_signals']}")
        logger.info(f"  Regime Changes Detected: {self.stats['regime_changes']}")
        logger.info(f"  Discord Alerts Sent: {self.alerts_sent}")

        if self.extreme_signals:
            logger.info(f"\n  Recent Extreme Signals ({len(self.extreme_signals)}):")
            for sig in self.extreme_signals[-5:]:
                logger.info(f"    - {sig['type']} on {sig['symbol']} at {sig['timestamp']}")

        logger.info("=" * 60)

        # Only send Discord summary once daily at midnight UTC (aligned with other shadow reports)
        should_send_discord = force_discord or (
            now.hour == self.REPORT_HOUR_UTC and
            self.last_daily_report_date != today_str
        )

        if should_send_discord:
            logger.info(f"📤 Sending daily Discord summary (hour={now.hour}, date={today_str})")
            embed = self._build_summary_embed()
            await self.send_discord_alert(embed)
            self.last_daily_report_date = today_str

            # Clear daily stats after report
            self.extreme_signals.clear()
        else:
            logger.debug(f"Skipping Discord (hour={now.hour}, report_hour={self.REPORT_HOUR_UTC}, last_report={self.last_daily_report_date})")

        self.last_summary_time = now

    async def run_oi_loop(self):
        """Run OI update loop."""
        logger.info("Starting OI update loop")

        while self.running:
            try:
                for symbol in self.tracked_symbols:
                    if not self.running:
                        break

                    result = await self.fetch_and_update_oi(symbol)
                    if result:
                        logger.debug(f"OI {symbol}: zscore={result['zscore']:.2f}, trend={result['trend']}")

                    await asyncio.sleep(2)  # Small delay between symbols

                await asyncio.sleep(self.OI_UPDATE_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in OI loop: {e}")
                await asyncio.sleep(60)

    async def run_orderbook_loop(self):
        """Run orderbook update loop."""
        logger.info("Starting orderbook update loop")

        while self.running:
            try:
                for symbol in self.tracked_symbols[:5]:  # Top 5 symbols only
                    if not self.running:
                        break

                    result = await self.fetch_and_update_orderbook(symbol)
                    if result:
                        logger.debug(f"Depth {symbol}: oir={result['oir']:.3f}, pressure={result['pressure']}")

                    await asyncio.sleep(1)

                await asyncio.sleep(self.ORDERBOOK_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in orderbook loop: {e}")
                await asyncio.sleep(30)

    async def run_correlation_loop(self):
        """Run correlation update loop."""
        logger.info("Starting correlation update loop")

        while self.running:
            try:
                results = await self.update_correlations()

                if results:
                    logger.info(f"Correlation update: {len(results)} symbols analyzed")

                    # Get regime summary
                    summary = self.calculators['correlation_roc'].get_regime_summary(
                        [s.replace('USDT', '') for s in self.tracked_symbols if s != 'BTCUSDT'],
                        base='BTC'
                    )
                    logger.info(f"Regime Summary: {summary['dominant_regime']}, "
                               f"stress={summary['correlation_stress']:.2f}")

                await asyncio.sleep(self.CORRELATION_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in correlation loop: {e}")
                await asyncio.sleep(300)

    async def run_cas_loop(self):
        """
        Run CAS (Cascade Absorption Signal) calculation loop.

        This loop calculates CAS signals for each tracked symbol using:
        - Orderbook imbalance (whale proxy) from depth_imbalance calculator
        - Long/short ratio from Bybit API
        - Liquidation zones from cache/API
        - OHLCV data for ATR and trend calculation
        """
        logger.info("Starting CAS calculation loop")

        # Wait for initial data collection
        await asyncio.sleep(60)

        while self.running:
            try:
                for symbol in self.tracked_symbols[:5]:  # Top 5 symbols only
                    if not self.running:
                        break

                    result = await self._calculate_cas_signal(symbol)
                    if result and result.get('is_valid'):
                        self.stats['cas_valid_signals'] += 1
                        if result.get('signal_strength') == 'STRONG':
                            self.stats['cas_strong_signals'] += 1
                            await self._log_extreme_signal('CAS_SIGNAL', symbol, result)

                    self.stats['cas_updates'] += 1
                    await asyncio.sleep(2)  # Small delay between symbols

                await asyncio.sleep(self.CAS_UPDATE_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CAS loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_cas_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Calculate CAS signal for a single symbol.

        Gathers all required data and passes to CAS calculator.
        """
        try:
            if not self.exchange:
                return None

            # 1. Get current price and OHLCV for ATR/trend
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '1h', limit=50)
            if not ohlcv or len(ohlcv) < 20:
                logger.debug(f"Insufficient OHLCV data for {symbol}")
                return None

            current_price = ohlcv[-1][4]  # Close price

            # Calculate ATR (14-period)
            highs = [c[2] for c in ohlcv[-14:]]
            lows = [c[3] for c in ohlcv[-14:]]
            closes = [c[4] for c in ohlcv[-14:]]
            tr_values = []
            for i in range(1, len(highs)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                tr_values.append(tr)
            atr = sum(tr_values) / len(tr_values) if tr_values else current_price * 0.02

            # Calculate hourly returns for trend
            hourly_returns = []
            for i in range(1, len(ohlcv)):
                prev_close = ohlcv[i-1][4]
                if prev_close > 0:
                    ret = (ohlcv[i][4] - prev_close) / prev_close
                    hourly_returns.append(ret)

            # 2. Get orderbook imbalance (whale proxy) - always fetch fresh
            orderbook_imbalance = 0.0
            orderbook = await self.exchange.fetch_order_book(symbol, limit=25)
            if orderbook and 'bids' in orderbook and 'asks' in orderbook:
                depth_result = self.calculators['depth_imbalance'].calculate(
                    symbol, orderbook['bids'], orderbook['asks']
                )
                if depth_result:
                    orderbook_imbalance = depth_result.oir

            # 3. Get long/short ratio
            lsr_data = await self.exchange.fetch_long_short_ratio(symbol)
            long_short_ratio = 1.0
            logger.debug(f"[CAS] LSR raw data for {symbol}: {lsr_data}")
            if lsr_data and isinstance(lsr_data, dict):
                # Handle Bybit's direct format: {'long': 52.5, 'short': 47.5}
                if 'long' in lsr_data and 'short' in lsr_data:
                    long_pct = float(lsr_data.get('long', 50.0))
                    short_pct = float(lsr_data.get('short', 50.0))
                    if short_pct > 0:
                        long_short_ratio = long_pct / short_pct  # e.g., 52.5 / 47.5 = 1.105
                    logger.debug(f"[CAS] Parsed LSR for {symbol}: long={long_pct}, short={short_pct}, ratio={long_short_ratio:.3f}")
                # Handle nested 'data' format (Binance-style)
                elif 'data' in lsr_data and lsr_data['data']:
                    latest = lsr_data['data'][-1] if isinstance(lsr_data['data'], list) else lsr_data['data']
                    if isinstance(latest, dict):
                        if 'buyRatio' in latest:
                            long_short_ratio = float(latest['buyRatio']) / max(0.01, float(latest.get('sellRatio', 1)))
                        elif 'longRatio' in latest:
                            long_short_ratio = float(latest['longRatio']) / max(0.01, float(latest.get('shortRatio', 1)))
            else:
                logger.warning(f"[CAS] No LSR data for {symbol}, using default 1.0")

            # 4. Get liquidation zones using REAL liquidation data
            # Uses LiquidationClusterService to analyze actual liquidation events
            try:
                liq_service = get_liquidation_service()
                cascade_zone = liq_service.get_cascade_zone(
                    symbol=symbol,
                    current_price=current_price,
                    atr=atr,
                    lookback_hours=24
                )
                cascade_price = cascade_zone.cascade_price
                cascade_size = cascade_zone.cascade_size
                cascade_side = cascade_zone.cascade_side
                cascade_velocity = cascade_zone.velocity
                cascade_data_source = cascade_zone.data_source

                if cascade_data_source == 'real':
                    logger.debug(f"[CAS] Real liquidation data for {symbol}: "
                                f"price=${cascade_price:,.0f}, size=${cascade_size:,.0f}, "
                                f"side={cascade_side}, velocity={cascade_velocity:.2f}")
            except Exception as e:
                logger.warning(f"[CAS] Liquidation service error for {symbol}, using fallback: {e}")
                # Fallback to ATR-based estimate
                cascade_distance = atr * 2.5
                cascade_side = 'long' if orderbook_imbalance < 0 else 'short'
                cascade_price = current_price - cascade_distance if cascade_side == 'long' else current_price + cascade_distance
                oi_stats = self.calculators['oi_zscore'].get_stats(symbol)
                cascade_size = 5_000_000
                if oi_stats and 'current_oi' in oi_stats:
                    cascade_size = oi_stats['current_oi'] * 0.001
                cascade_velocity = 1.0
                cascade_data_source = 'estimated'

            # 5. Build data dict for CAS calculator
            cas_data = {
                'symbol': symbol,
                'current_price': current_price,
                'cascade_price': cascade_price,
                'cascade_size': cascade_size,
                'cascade_side': cascade_side,
                'cascade_velocity': cascade_velocity,
                'cascade_data_source': cascade_data_source,
                'atr': atr,
                'orderbook_imbalance': orderbook_imbalance,
                'long_short_ratio': long_short_ratio,
                'hourly_returns': hourly_returns
            }
            logger.debug(f"[CAS] Input data for {symbol}: LSR={long_short_ratio:.3f}, OIR={orderbook_imbalance:.3f}, "
                        f"data_source={cascade_data_source}, velocity={cascade_velocity:.2f}")

            # 6. Calculate CAS signal
            result = self.cas_calculator.calculate(cas_data)
            result_dict = result.to_dict()

            # 7. Store to shadow database
            store_cas_signal(result_dict)

            logger.debug(f"CAS {symbol}: score={result.cas_score:.1f}, "
                        f"direction={result.signal_direction}, valid={result.is_valid}")

            return result_dict

        except Exception as e:
            logger.error(f"Error calculating CAS for {symbol}: {e}")
            return None

    async def run_forward_return_loop(self):
        """
        Calculate forward returns for stored CAS signals.

        This loop checks for signals that are old enough to calculate returns:
        - 1h return: signals > 1 hour old
        - 4h return: signals > 4 hours old
        - 24h return: signals > 24 hours old
        """
        logger.info("Starting forward return calculation loop")

        # Wait for some signals to accumulate
        await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

        while self.running:
            try:
                # Get signals pending return calculation
                pending = get_cas_signals_pending_returns()

                if pending:
                    logger.info(f"Processing {len(pending)} signals for forward returns")

                    for signal in pending:
                        if not self.running:
                            break

                        await self._calculate_forward_return(signal)
                        self.stats['forward_returns_calculated'] += 1

                await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in forward return loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_forward_return(self, signal: Dict[str, Any]):
        """Calculate forward returns for a single CAS signal."""
        try:
            signal_id = signal['id']
            symbol = signal['symbol']
            entry_price = float(signal['current_price'])  # FIX: Convert from string to float
            signal_time = signal['timestamp']
            signal_direction = signal['signal_direction']

            now = datetime.now(timezone.utc).timestamp()
            signal_age_hours = (now - signal_time) / 3600

            # Determine which returns to calculate
            returns = {}

            # Fetch current price
            ticker = await self.exchange.fetch_ticker(symbol)
            if not ticker or 'last' not in ticker:
                return

            current_price = ticker['last']

            # Calculate return (positive if correct direction)
            raw_return = (current_price - entry_price) / entry_price * 100

            # Adjust for direction (bullish expects positive, bearish expects negative)
            if signal_direction == 'BEARISH':
                raw_return = -raw_return

            # Assign to appropriate time bucket
            if signal_age_hours >= 1 and signal.get('return_1h') is None:
                returns['return_1h'] = raw_return
            if signal_age_hours >= 4 and signal.get('return_4h') is None:
                returns['return_4h'] = raw_return
            if signal_age_hours >= 24 and signal.get('return_24h') is None:
                returns['return_24h'] = raw_return

            if returns:
                update_cas_forward_returns(signal_id, returns)
                logger.debug(f"Updated forward returns for signal {signal_id}: {returns}")

        except Exception as e:
            logger.error(f"Error calculating forward return for signal {signal.get('id')}: {e}")

    async def run_btc_prediction_loop(self):
        """
        Run BTC Prediction shadow collection loop.

        Analyzes Bitcoin lead/lag relationships with altcoins and stores
        predictions for later validation.
        """
        logger.info("Starting BTC prediction loop")

        # Wait for initial data
        await asyncio.sleep(120)

        while self.running:
            try:
                # Get BTC price history (1h candles, 240 points = 10 days)
                btc_ohlcv = await self.exchange.fetch_ohlcv('BTCUSDT', '1h', limit=240)
                if not btc_ohlcv or len(btc_ohlcv) < 60:
                    logger.warning("Insufficient BTC data for prediction")
                    await asyncio.sleep(self.BTC_PREDICTION_INTERVAL)
                    continue

                btc_closes = pd.Series([c[4] for c in btc_ohlcv])

                # Calculate recent BTC move (last 4 hours)
                if len(btc_closes) >= 4:
                    btc_recent_move = (btc_closes.iloc[-1] - btc_closes.iloc[-4]) / btc_closes.iloc[-4] * 100
                else:
                    btc_recent_move = 0

                # Analyze each altcoin
                for symbol in self.tracked_symbols[1:5]:  # Skip BTCUSDT, top 4 alts
                    if not self.running:
                        break

                    try:
                        alt_ohlcv = await self.exchange.fetch_ohlcv(symbol, '1h', limit=240)
                        if not alt_ohlcv or len(alt_ohlcv) < 60:
                            continue

                        alt_closes = pd.Series([c[4] for c in alt_ohlcv])

                        # Align lengths
                        min_len = min(len(btc_closes), len(alt_closes))
                        btc_aligned = btc_closes.iloc[-min_len:].reset_index(drop=True)
                        alt_aligned = alt_closes.iloc[-min_len:].reset_index(drop=True)

                        # Run analysis
                        analysis = self.btc_predictor.analyze_altcoin(
                            symbol=symbol.replace('USDT', ''),
                            btc_prices=btc_aligned,
                            alt_prices=alt_aligned,
                            btc_recent_move_pct=btc_recent_move
                        )

                        if 'error' not in analysis:
                            # Determine what would boost score based on divergence
                            divergence = analysis.get('divergence', {})
                            stability = analysis.get('stability', {})
                            prediction = analysis.get('prediction', {})

                            would_boost = 0
                            signal_type = 'NEUTRAL'

                            if divergence.get('signal_active'):
                                direction = divergence.get('direction', 'neutral')
                                z_score = abs(divergence.get('z_score', 0))
                                signal_type = 'LONG' if direction == 'long' else 'SHORT'
                                # Boost proportional to z-score and stability
                                would_boost = min(15, z_score * 3) * (stability.get('stability_score', 50) / 100)
                                self.stats['btc_divergence_signals'] += 1

                            # Store prediction
                            store_btc_prediction({
                                'timestamp': int(datetime.now(timezone.utc).timestamp()),
                                'symbol': symbol,
                                'signal_type': signal_type,
                                'original_score': 50,  # Baseline
                                'would_boost': would_boost,
                                'btc_direction': 'UP' if btc_recent_move > 0.5 else ('DOWN' if btc_recent_move < -0.5 else 'FLAT'),
                                'confidence': divergence.get('confidence', 0),
                                'stability_score': stability.get('stability_score', 0),
                                'beta': analysis.get('beta', 1.0)
                            })

                            self.stats['btc_predictions'] += 1
                            logger.debug(f"BTC Prediction {symbol}: beta={analysis.get('beta'):.2f}, "
                                        f"divergence={divergence.get('signal_active')}, "
                                        f"stability={stability.get('stability_score', 0):.0f}")

                    except Exception as e:
                        logger.debug(f"Error analyzing {symbol} for BTC prediction: {e}")

                    await asyncio.sleep(2)  # Rate limit

                await asyncio.sleep(self.BTC_PREDICTION_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in BTC prediction loop: {e}")
                await asyncio.sleep(60)

    async def run_crypto_regime_loop(self):
        """
        Run Crypto Regime shadow collection loop.

        Detects crypto-specific market regimes (volatility breakout/chop,
        funding extremes, squeeze conditions, liquidation cascades).
        """
        logger.info("Starting crypto regime detection loop")

        # Wait for OI and orderbook data to populate
        await asyncio.sleep(180)

        while self.running:
            try:
                for symbol in self.tracked_symbols[:5]:  # Top 5 symbols
                    if not self.running:
                        break

                    try:
                        detection = await self._detect_crypto_regime(symbol)
                        if detection and detection.get('crypto_regime'):
                            store_crypto_regime_detection(detection)
                            self.stats['crypto_regime_detections'] += 1
                            logger.info(f"Crypto regime detected for {symbol}: {detection.get('crypto_regime')}")

                    except Exception as e:
                        logger.debug(f"Error detecting crypto regime for {symbol}: {e}")

                    await asyncio.sleep(2)

                await asyncio.sleep(self.CRYPTO_REGIME_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in crypto regime loop: {e}")
                await asyncio.sleep(60)

    async def _detect_crypto_regime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Detect crypto-specific regime for a single symbol."""
        try:
            # 1. Get volatility percentile from ATR
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '1h', limit=100)
            if not ohlcv or len(ohlcv) < 50:
                return None

            # Calculate ATR and percentile
            highs = np.array([c[2] for c in ohlcv])
            lows = np.array([c[3] for c in ohlcv])
            closes = np.array([c[4] for c in ohlcv])

            tr_values = []
            for i in range(1, len(ohlcv)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                tr_values.append(tr)

            current_atr = np.mean(tr_values[-14:]) if len(tr_values) >= 14 else np.mean(tr_values)
            historical_atrs = [np.mean(tr_values[max(0,i-14):i+1]) for i in range(14, len(tr_values))]

            if historical_atrs:
                volatility_pct = sum(1 for a in historical_atrs if a < current_atr) / len(historical_atrs) * 100
                atr_expansion = current_atr / np.mean(historical_atrs) if np.mean(historical_atrs) > 0 else 1.0
            else:
                volatility_pct = 50.0
                atr_expansion = 1.0

            # 2. Calculate ADX proxy using price momentum
            # ADX measures trend strength (0-100), typically 15-50 range
            # Using signal-to-noise ratio as proxy: |mean(returns)| / std(returns)
            returns = np.diff(closes) / closes[:-1]
            recent_returns = returns[-20:]
            signal_to_noise = abs(np.mean(recent_returns)) / (np.std(recent_returns) + 1e-10)
            # Scale: SNR of 0.5 → ADX ~25, SNR of 1.0 → ADX ~50, SNR of 2.0 → ADX ~75
            adx = min(100, max(0, signal_to_noise * 50))  # More realistic scaling

            # 3. Direction based on recent trend
            if len(closes) >= 20:
                short_ma = np.mean(closes[-5:])
                long_ma = np.mean(closes[-20:])
                direction = (short_ma - long_ma) / long_ma * 10  # Scale to roughly -1 to 1
                direction = max(-1, min(1, direction))
            else:
                direction = 0

            # 4. Get funding rate
            funding_rate = None
            try:
                funding_data = await self.exchange.fetch_funding_rate(symbol)
                if funding_data and isinstance(funding_data, dict):
                    funding_rate = float(funding_data.get('fundingRate', 0))
            except:
                pass

            # 5. Get long/short ratio
            long_ratio = None
            try:
                lsr_data = await self.exchange.fetch_long_short_ratio(symbol)
                if lsr_data and isinstance(lsr_data, dict):
                    if 'long' in lsr_data:
                        long_ratio = float(lsr_data.get('long', 50))
            except:
                pass

            # 6. Get cascade probability from liquidation service
            # Cascade probability should trigger >0.6 only in genuinely dangerous conditions
            # Threshold is 0.6 (60%), so cascade_prob should rarely exceed this
            cascade_prob = None
            try:
                current_price = closes[-1]
                atr = current_atr
                liq_service = get_liquidation_service()
                cascade_zone = liq_service.get_cascade_zone(symbol, current_price, atr, lookback_hours=24)
                # More conservative cascade probability calculation
                # Only trigger high probability when price is within 1-2 ATR of cascade zone
                if cascade_zone and cascade_zone.cascade_price > 0 and atr > 0:
                    distance_pct = abs(current_price - cascade_zone.cascade_price) / current_price
                    # Use ATR-relative distance: cascade_prob > 0.6 only when within ~2% of cascade
                    # - Within 1%: prob = 0.8-1.0
                    # - Within 2%: prob = 0.6-0.8
                    # - Within 5%: prob = 0.3-0.6
                    # - Beyond 5%: prob < 0.3
                    cascade_prob = max(0, min(1.0, 1.0 - distance_pct * 20))
            except:
                pass

            # 7. Detect crypto regime
            regime = self.crypto_regime_detector.detect(
                volatility_pct=volatility_pct,
                adx=adx,
                direction=direction,
                funding_rate=funding_rate,
                long_ratio=long_ratio,
                cascade_prob=cascade_prob,
                atr_expansion=atr_expansion
            )

            if regime:
                return {
                    'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),  # milliseconds
                    'symbol': symbol,
                    'signal_type': 'REGIME',
                    'base_regime': 'STANDARD',
                    'crypto_regime': regime.value,
                    'funding_rate': funding_rate,
                    'oi_change_pct': None,  # Could add OI tracking later
                    'volatility_percentile': volatility_pct,
                    'atr_expansion': atr_expansion,
                    'entry_price': float(closes[-1]),  # For forward return calculation
                    'detection_data': {
                        'adx': adx,
                        'direction': direction,
                        'long_ratio': long_ratio,
                        'cascade_prob': cascade_prob,
                        'is_opportunity': regime.is_opportunity,
                        'is_danger': regime.is_danger,
                        'is_contrarian': regime.is_contrarian,
                        'description': self.crypto_regime_detector.get_regime_description(regime)
                    }
                }

            return None

        except Exception as e:
            logger.debug(f"Error detecting crypto regime for {symbol}: {e}")
            return None

    async def run_dual_regime_loop(self):
        """
        Run Dual Regime shadow collection loop.

        Tracks when market-level regime differs from symbol-level regime,
        which can create opportunities or risks.
        """
        logger.info("Starting dual regime detection loop")

        # Wait for other data to populate
        await asyncio.sleep(240)

        while self.running:
            try:
                # Get overall market regime from BTC
                btc_regime = await self._get_symbol_regime('BTCUSDT')

                for symbol in self.tracked_symbols[1:5]:  # Top 4 alts
                    if not self.running:
                        break

                    try:
                        symbol_regime = await self._get_symbol_regime(symbol)

                        if btc_regime and symbol_regime:
                            # Check for regime divergence
                            adjustment = self._calculate_regime_adjustment(btc_regime, symbol_regime)

                            if abs(adjustment) > 2:  # Only store meaningful adjustments
                                store_dual_regime_adjustment({
                                    'timestamp': int(datetime.now(timezone.utc).timestamp()),
                                    'symbol': symbol,
                                    'signal_type': 'LONG' if adjustment > 0 else 'SHORT',
                                    'score_before': 50,
                                    'score_after': 50 + adjustment,
                                    'adjustment': adjustment,
                                    'market_regime': btc_regime.get('trend', 'UNKNOWN'),
                                    'symbol_regime': symbol_regime.get('trend', 'UNKNOWN'),
                                    'fear_greed': None  # Could integrate Fear & Greed API later
                                })

                                self.stats['dual_regime_adjustments'] += 1
                                logger.debug(f"Dual regime adjustment for {symbol}: {adjustment:.1f} "
                                           f"(market={btc_regime.get('trend')}, symbol={symbol_regime.get('trend')})")

                    except Exception as e:
                        logger.debug(f"Error in dual regime for {symbol}: {e}")

                    await asyncio.sleep(2)

                await asyncio.sleep(self.DUAL_REGIME_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dual regime loop: {e}")
                await asyncio.sleep(60)

    async def run_dual_regime_forward_return_loop(self):
        """
        Calculate forward returns for stored dual-regime adjustments.

        This loop checks for adjustments that are old enough to calculate returns:
        - 15m return: adjustments > 15 minutes old
        - 1h return: adjustments > 1 hour old
        - 4h return: adjustments > 4 hours old
        - 24h return: adjustments > 24 hours old
        """
        logger.info("Starting dual-regime forward return calculation loop")

        # Wait for some adjustments to accumulate
        await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

        while self.running:
            try:
                # Get adjustments pending return calculation (last 48 hours with entry_price)
                pending = get_dual_regime_pending_returns(hours_back=48, return_type='1h')

                if pending:
                    logger.info(f"Processing {len(pending)} dual-regime adjustments for forward returns")

                    for record in pending:
                        if not self.running:
                            break

                        await self._calculate_dual_regime_forward_return(record)
                        self.stats['dual_regime_returns_calculated'] = self.stats.get('dual_regime_returns_calculated', 0) + 1

                await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dual-regime forward return loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_dual_regime_forward_return(self, record: Dict[str, Any]):
        """Calculate forward returns for a single dual-regime adjustment."""
        try:
            record_id = record['id']
            symbol = record['symbol']
            entry_price = record.get('entry_price')
            signal_type = record['signal_type']  # LONG or SHORT
            record_time = record['timestamp'] / 1000  # Convert ms to seconds

            # Skip if no entry price (from older records before this feature)
            if not entry_price or entry_price <= 0:
                return

            now = datetime.now(timezone.utc).timestamp()
            record_age_hours = (now - record_time) / 3600

            # Fetch current price
            ticker = await self.exchange.fetch_ticker(symbol)
            if not ticker or 'last' not in ticker:
                return

            current_price = ticker['last']

            # Calculate return (positive if correct direction)
            raw_return = (current_price - entry_price) / entry_price * 100

            # Adjust for signal direction (LONG expects positive, SHORT expects negative)
            if signal_type == 'SHORT':
                raw_return = -raw_return

            # Determine which returns to calculate
            return_15m = None
            return_1h = None
            return_4h = None
            return_24h = None

            if record_age_hours >= 0.25 and record.get('return_15m') is None:  # 15 minutes = 0.25 hours
                return_15m = raw_return
            if record_age_hours >= 1 and record.get('return_1h') is None:
                return_1h = raw_return
            if record_age_hours >= 4 and record.get('return_4h') is None:
                return_4h = raw_return
            if record_age_hours >= 24 and record.get('return_24h') is None:
                return_24h = raw_return

            if return_15m is not None or return_1h is not None or return_4h is not None or return_24h is not None:
                update_dual_regime_forward_returns(
                    record_id,
                    return_15m=return_15m,
                    return_1h=return_1h,
                    return_4h=return_4h,
                    return_24h=return_24h
                )
                logger.debug(f"Updated dual-regime forward returns for {symbol} (id={record_id}): "
                           f"15m={return_15m}, 1h={return_1h}, 4h={return_4h}, 24h={return_24h}")

        except Exception as e:
            logger.error(f"Error calculating dual-regime forward return for record {record.get('id')}: {e}")

    async def run_crypto_regime_forward_return_loop(self):
        """
        Calculate forward returns for stored crypto regime detections.

        This loop checks for detections that are old enough to calculate returns:
        - 15m return: detections > 15 minutes old
        - 1h return: detections > 1 hour old
        - 4h return: detections > 4 hours old
        - 24h return: detections > 24 hours old
        """
        logger.info("Starting crypto-regime forward return calculation loop")

        # Wait for some detections to accumulate
        await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

        while self.running:
            try:
                # Get detections pending return calculation (last 48 hours with entry_price)
                # Use 'any' to get records missing ANY forward return (15m, 1h, 4h, or 24h)
                pending = get_crypto_regime_pending_returns(hours_back=48, return_type='any')

                if pending:
                    logger.info(f"Processing {len(pending)} crypto-regime detections for forward returns")

                    for record in pending:
                        if not self.running:
                            break

                        await self._calculate_crypto_regime_forward_return(record)
                        self.stats['crypto_regime_returns_calculated'] = self.stats.get('crypto_regime_returns_calculated', 0) + 1

                await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in crypto-regime forward return loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_crypto_regime_forward_return(self, record: Dict[str, Any]):
        """Calculate forward returns for a single crypto regime detection."""
        try:
            record_id = record['id']
            symbol = record['symbol']
            entry_price = record.get('entry_price')
            signal_type = record['signal_type']  # LONG or SHORT
            record_time = record['timestamp'] / 1000  # Convert ms to seconds

            # Skip if no entry price (from older records before this feature)
            if not entry_price or entry_price <= 0:
                return

            now = datetime.now(timezone.utc).timestamp()
            record_age_hours = (now - record_time) / 3600

            # Fetch current price
            ticker = await self.exchange.fetch_ticker(symbol)
            if not ticker or 'last' not in ticker:
                return

            current_price = ticker['last']

            # Calculate return (positive if correct direction)
            raw_return = (current_price - entry_price) / entry_price * 100

            # Adjust for signal direction (LONG expects positive, SHORT expects negative)
            if signal_type == 'SHORT':
                raw_return = -raw_return

            # Determine which returns to calculate
            return_15m = None
            return_1h = None
            return_4h = None
            return_24h = None

            if record_age_hours >= 0.25 and record.get('return_15m') is None:  # 15 minutes = 0.25 hours
                return_15m = raw_return
            if record_age_hours >= 1 and record.get('return_1h') is None:
                return_1h = raw_return
            if record_age_hours >= 4 and record.get('return_4h') is None:
                return_4h = raw_return
            if record_age_hours >= 24 and record.get('return_24h') is None:
                return_24h = raw_return

            if return_15m is not None or return_1h is not None or return_4h is not None or return_24h is not None:
                update_crypto_regime_forward_returns(
                    record_id,
                    return_15m=return_15m,
                    return_1h=return_1h,
                    return_4h=return_4h,
                    return_24h=return_24h
                )
                logger.debug(f"Updated crypto-regime forward returns for {symbol} (id={record_id}): "
                           f"15m={return_15m}, 1h={return_1h}, 4h={return_4h}, 24h={return_24h}")

        except Exception as e:
            logger.error(f"Error calculating crypto-regime forward return for record {record.get('id')}: {e}")

    async def run_distribution_signal_loop(self):
        """
        Run Distribution Signal (CVD Divergence) detection loop.

        Detects whale distribution/accumulation patterns:
        - Bearish divergence: Price↑ + CVD↓ = whales selling into rally
        - Bullish divergence: Price↓ + CVD↑ = whales buying the dip

        This is the BEARISH signal counterpart to CAS (which is inherently bullish).
        """
        logger.info("Starting distribution signal detection loop")

        # Wait for initial data
        await asyncio.sleep(180)

        while self.running:
            try:
                for symbol in self.tracked_symbols[:5]:  # Top 5 symbols
                    if not self.running:
                        break

                    try:
                        signal = await self._detect_distribution_signal(symbol)
                        if signal and signal.get('divergence_strength', 0) >= 30:
                            store_distribution_signal(signal)
                            self.stats['distribution_signals'] += 1

                            if signal.get('divergence_type') == 'bearish':
                                self.stats['distribution_bearish_signals'] += 1
                                logger.info(f"🔴 Bearish divergence {symbol}: "
                                          f"price_trend={signal.get('price_trend', 0):.2f}%, "
                                          f"cvd_trend={signal.get('cvd_trend', 0):.2f}, "
                                          f"strength={signal.get('divergence_strength', 0):.1f}")
                            else:
                                self.stats['distribution_bullish_signals'] += 1
                                logger.info(f"🟢 Bullish divergence {symbol}: "
                                          f"price_trend={signal.get('price_trend', 0):.2f}%, "
                                          f"cvd_trend={signal.get('cvd_trend', 0):.2f}, "
                                          f"strength={signal.get('divergence_strength', 0):.1f}")

                    except Exception as e:
                        logger.debug(f"Error detecting distribution signal for {symbol}: {e}")

                    await asyncio.sleep(2)

                await asyncio.sleep(self.DISTRIBUTION_SIGNAL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in distribution signal loop: {e}")
                await asyncio.sleep(60)

    async def _detect_distribution_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Detect CVD divergence for a single symbol.

        CVD Divergence Detection:
        1. Calculate price trend over lookback period
        2. Calculate CVD trend (cumulative buy/sell delta)
        3. If trends diverge significantly, flag as distribution/accumulation

        Returns:
            Dict with divergence data or None if no significant divergence
        """
        try:
            lookback_bars = 20  # 20 bars for divergence detection

            # 1. Fetch OHLCV for price trend
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '5m', limit=lookback_bars + 5)
            if not ohlcv or len(ohlcv) < lookback_bars:
                return None

            closes = np.array([c[4] for c in ohlcv[-lookback_bars:]])
            volumes = np.array([c[5] for c in ohlcv[-lookback_bars:]])
            highs = np.array([c[2] for c in ohlcv[-lookback_bars:]])
            lows = np.array([c[3] for c in ohlcv[-lookback_bars:]])
            opens = np.array([c[1] for c in ohlcv[-lookback_bars:]])

            current_price = closes[-1]

            # 2. Calculate price trend (percentage change over lookback)
            price_start = closes[0]
            price_end = closes[-1]
            price_trend = (price_end - price_start) / price_start * 100  # % change

            # 3. Calculate CVD (Cumulative Volume Delta)
            # Delta = volume * (close - open) / (high - low) simplified
            # Positive delta = buying pressure, negative = selling pressure
            deltas = []
            for i in range(len(closes)):
                candle_range = highs[i] - lows[i]
                if candle_range > 0:
                    # Where price closed within the candle (0=low, 1=high)
                    close_position = (closes[i] - lows[i]) / candle_range
                    # Delta: volume * position_bias (-0.5 to +0.5)
                    delta = volumes[i] * (close_position - 0.5)
                else:
                    delta = 0
                deltas.append(delta)

            cvd = np.cumsum(deltas)
            cvd_start = cvd[0]
            cvd_end = cvd[-1]
            cvd_trend = cvd_end - cvd_start  # Absolute CVD change

            # Normalize CVD trend relative to total volume
            total_volume = np.sum(volumes)
            if total_volume > 0:
                cvd_normalized = cvd_trend / total_volume  # -0.5 to +0.5 range
            else:
                cvd_normalized = 0

            # 4. Detect divergence
            divergence_type = None
            divergence_strength = 0

            # Bearish divergence: Price up, CVD down (whales distributing)
            if price_trend > 0.5 and cvd_normalized < -0.05:
                divergence_type = 'bearish'
                # Strength = how strong the divergence is
                # Higher price trend + more negative CVD = stronger bearish signal
                divergence_strength = min(100, abs(price_trend) * 10 + abs(cvd_normalized) * 100)

            # Bullish divergence: Price down, CVD up (whales accumulating)
            elif price_trend < -0.5 and cvd_normalized > 0.05:
                divergence_type = 'bullish'
                divergence_strength = min(100, abs(price_trend) * 10 + abs(cvd_normalized) * 100)

            if divergence_type:
                return {
                    'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
                    'symbol': symbol,
                    'divergence_type': divergence_type,
                    'divergence_strength': divergence_strength,
                    'price_trend': price_trend,
                    'cvd_trend': cvd_normalized,
                    'entry_price': current_price,
                    'lookback_bars': lookback_bars,
                    'volume_profile': {
                        'total_volume': total_volume,
                        'cvd_raw': cvd_trend,
                        'avg_delta': np.mean(deltas)
                    }
                }

            return None

        except Exception as e:
            logger.debug(f"Error detecting distribution signal for {symbol}: {e}")
            return None

    async def run_distribution_forward_return_loop(self):
        """
        Calculate forward returns for stored distribution signals.

        This validates whether bearish divergence actually predicts price drops
        and bullish divergence predicts price rises.
        """
        logger.info("Starting distribution forward return calculation loop")

        # Wait for signals to accumulate
        await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

        while self.running:
            try:
                # Get signals pending return calculation
                pending = get_distribution_pending_returns(hours_back=48, return_type='1h')

                if pending:
                    logger.info(f"Processing {len(pending)} distribution signals for forward returns")

                    for record in pending:
                        if not self.running:
                            break

                        await self._calculate_distribution_forward_return(record)

                await asyncio.sleep(self.FORWARD_RETURN_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in distribution forward return loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_distribution_forward_return(self, record: Dict[str, Any]):
        """Calculate forward returns for a single distribution signal."""
        try:
            record_id = record['id']
            symbol = record['symbol']
            entry_price = record.get('entry_price')
            divergence_type = record['divergence_type']
            record_time = record['timestamp'] / 1000  # Convert ms to seconds

            if not entry_price or entry_price <= 0:
                return

            now = datetime.now(timezone.utc).timestamp()
            record_age_hours = (now - record_time) / 3600

            # Fetch current price
            ticker = await self.exchange.fetch_ticker(symbol)
            if not ticker or 'last' not in ticker:
                return

            current_price = ticker['last']

            # Calculate return
            raw_return = (current_price - entry_price) / entry_price * 100

            # For bearish divergence, we expect negative returns (price drop)
            # So a "correct" signal = negative return for bearish
            # Adjust: bearish expects negative, bullish expects positive
            if divergence_type == 'bearish':
                raw_return = -raw_return  # Flip sign so positive = correct

            # Determine which returns to calculate
            return_15m = None
            return_1h = None
            return_4h = None
            return_24h = None

            if record_age_hours >= 0.25 and record.get('return_15m') is None:
                return_15m = raw_return
            if record_age_hours >= 1 and record.get('return_1h') is None:
                return_1h = raw_return
            if record_age_hours >= 4 and record.get('return_4h') is None:
                return_4h = raw_return
            if record_age_hours >= 24 and record.get('return_24h') is None:
                return_24h = raw_return

            if return_15m is not None or return_1h is not None or return_4h is not None or return_24h is not None:
                update_distribution_forward_returns(
                    record_id,
                    return_15m=return_15m,
                    return_1h=return_1h,
                    return_4h=return_4h,
                    return_24h=return_24h
                )
                logger.debug(f"Updated distribution forward returns for {symbol} (id={record_id})")

        except Exception as e:
            logger.error(f"Error calculating distribution forward return for record {record.get('id')}: {e}")

    async def _get_symbol_regime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get simplified regime info for a symbol."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, '4h', limit=50)
            if not ohlcv or len(ohlcv) < 20:
                return None

            closes = np.array([c[4] for c in ohlcv])

            # Simple trend detection
            sma_short = np.mean(closes[-5:])
            sma_long = np.mean(closes[-20:])

            if sma_short > sma_long * 1.02:
                trend = 'UPTREND'
            elif sma_short < sma_long * 0.98:
                trend = 'DOWNTREND'
            else:
                trend = 'RANGING'

            # Volatility (ATR-based)
            highs = np.array([c[2] for c in ohlcv[-20:]])
            lows = np.array([c[3] for c in ohlcv[-20:]])
            atr = np.mean(highs - lows)
            atr_pct = atr / closes[-1] * 100

            return {
                'trend': trend,
                'sma_short': sma_short,
                'sma_long': sma_long,
                'atr_pct': atr_pct,
                'momentum': (closes[-1] - closes[-5]) / closes[-5] * 100
            }

        except Exception as e:
            logger.debug(f"Error getting regime for {symbol}: {e}")
            return None

    def _calculate_regime_adjustment(self, market_regime: Dict, symbol_regime: Dict) -> float:
        """
        Calculate score adjustment based on regime divergence.

        When symbol is outperforming market (diverging up), boost long signals.
        When symbol is underperforming (diverging down), boost short signals.
        """
        try:
            market_trend = market_regime.get('trend', 'RANGING')
            symbol_trend = symbol_regime.get('trend', 'RANGING')
            symbol_momentum = symbol_regime.get('momentum', 0)
            market_momentum = market_regime.get('momentum', 0) if market_regime else 0

            # Divergence = symbol momentum - market momentum
            divergence = symbol_momentum - market_momentum

            adjustment = 0

            # Same trend = confidence boost
            if market_trend == symbol_trend and market_trend != 'RANGING':
                adjustment = 3 if market_trend == 'UPTREND' else -3

            # Opposite trends = opportunity
            elif market_trend == 'DOWNTREND' and symbol_trend == 'UPTREND':
                adjustment = 5  # Symbol showing relative strength
            elif market_trend == 'UPTREND' and symbol_trend == 'DOWNTREND':
                adjustment = -5  # Symbol showing relative weakness

            # Add momentum divergence factor
            adjustment += divergence * 0.5

            return max(-15, min(15, adjustment))  # Clamp

        except Exception as e:
            logger.debug(f"Error calculating regime adjustment: {e}")
            return 0

    async def run_summary_loop(self):
        """Run periodic summary logging and Discord reports."""
        while self.running:
            try:
                await asyncio.sleep(self.LOG_SUMMARY_INTERVAL)
                await self._log_summary()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in summary loop: {e}")

    async def run(self):
        """Main run loop."""
        logger.info("🚀 Starting Market Psychology Shadow Mode")

        # Initialize exchange
        if not await self.initialize_exchange():
            logger.error("Failed to initialize exchange, exiting")
            return

        # Fetch top symbols by volume from Bybit API
        logger.info("📊 Fetching top symbols by 24h volume...")
        await self._update_tracked_symbols()
        logger.info(f"🎯 Tracking {len(self.tracked_symbols)} symbols: {', '.join(self.tracked_symbols)}")

        self.running = True
        self._shutdown_event = asyncio.Event()

        # Create tasks and store references for graceful shutdown
        self.tasks = [
            asyncio.create_task(self.run_oi_loop(), name="oi_loop"),
            asyncio.create_task(self.run_orderbook_loop(), name="orderbook_loop"),
            asyncio.create_task(self.run_correlation_loop(), name="correlation_loop"),
            asyncio.create_task(self.run_cas_loop(), name="cas_loop"),
            asyncio.create_task(self.run_forward_return_loop(), name="forward_return_loop"),
            asyncio.create_task(self.run_btc_prediction_loop(), name="btc_prediction_loop"),
            asyncio.create_task(self.run_crypto_regime_loop(), name="crypto_regime_loop"),
            asyncio.create_task(self.run_crypto_regime_forward_return_loop(), name="crypto_regime_forward_return_loop"),
            asyncio.create_task(self.run_dual_regime_loop(), name="dual_regime_loop"),
            asyncio.create_task(self.run_dual_regime_forward_return_loop(), name="dual_regime_forward_return_loop"),
            asyncio.create_task(self.run_distribution_signal_loop(), name="distribution_signal_loop"),
            asyncio.create_task(self.run_distribution_forward_return_loop(), name="distribution_forward_return_loop"),
            asyncio.create_task(self.run_summary_loop(), name="summary_loop")
        ]

        logger.info("All shadow mode loops started")

        try:
            # Wait for shutdown signal or task completion
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Shadow mode cancelled via CancelledError")
        finally:
            await self._cleanup()

    async def _cleanup(self):
        """Clean up tasks and resources on shutdown."""
        logger.info("🛑 Cleaning up shadow mode...")
        self.running = False

        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled task: {task.get_name()}")

        # Wait for tasks to complete cancellation (with timeout)
        if self.tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.tasks, return_exceptions=True),
                    timeout=5.0
                )
                logger.info("All tasks cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not cancel within timeout")

        # Log final summary
        await self._log_summary()
        logger.info("✅ Market Psychology Shadow Mode stopped gracefully")

    async def stop_async(self):
        """Async stop method - triggers shutdown event."""
        logger.info("Stopping shadow mode (async)...")
        self.running = False
        if self._shutdown_event:
            self._shutdown_event.set()

    def stop(self):
        """Stop shadow mode (sync wrapper for signal handlers)."""
        logger.info("Stopping shadow mode...")
        self.running = False
        if self._shutdown_event:
            self._shutdown_event.set()


async def main():
    """Main entry point."""
    shadow = MarketPsychologyShadowMode()
    loop = asyncio.get_running_loop()

    # Use asyncio-compatible signal handling for graceful shutdown
    def signal_handler(signum):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shadow.stop()

    # Register signal handlers (Unix only)
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler, sig)
        logger.info("Signal handlers registered for graceful shutdown")
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        logger.warning("Asyncio signal handlers not supported on this platform")
        signal.signal(signal.SIGTERM, lambda s, f: shadow.stop())
        signal.signal(signal.SIGINT, lambda s, f: shadow.stop())

    try:
        await shadow.run()
    finally:
        # Remove signal handlers on exit
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(sig)
        except (NotImplementedError, ValueError):
            pass


if __name__ == '__main__':
    asyncio.run(main())
