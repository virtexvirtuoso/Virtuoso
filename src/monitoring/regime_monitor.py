#!/usr/bin/env python3
"""
Market Regime Monitor

Monitors market regime changes and sends alerts to Discord and stores in alert.db.
Only sends alerts on regime CHANGES, not on every detection.

Key Features:
- Tracks regime state per symbol
- Detects regime transitions
- Sends formatted Discord alerts
- Stores alerts in SQLite for dashboard display
- Provides API-compatible regime data
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from collections import defaultdict, deque
from enum import Enum

from discord_webhook import DiscordWebhook, DiscordEmbed

# Shared cache for cross-service data flow
try:
    from src.core.cache.shared_cache_bridge import (
        get_shared_cache_bridge,
        DataSource
    )
    SHARED_CACHE_AVAILABLE = True
except ImportError:
    SHARED_CACHE_AVAILABLE = False

# External data provider for enhanced regime detection
try:
    from src.core.analysis.external_regime_data import (
        ExternalRegimeDataProvider,
        ExternalRegimeSignals
    )
    EXTERNAL_DATA_AVAILABLE = True
except ImportError:
    EXTERNAL_DATA_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class RegimeState:
    """Current regime state for a symbol."""
    symbol: str
    regime: str
    confidence: float
    trend_direction: float
    volatility_percentile: float
    liquidity_score: float
    mtf_aligned: bool
    conflict_type: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeChange:
    """Record of a regime change event."""
    symbol: str
    previous_regime: str
    new_regime: str
    previous_confidence: float
    new_confidence: float
    timestamp: float
    trigger: str  # What caused the change (mtf, liquidation, price_action)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegimeMonitor:
    """
    Monitors market regimes and alerts on changes.

    Usage:
        monitor = RegimeMonitor(alert_manager, config)
        await monitor.update_regime('BTCUSDT', detection)  # From MarketRegimeDetector
    """

    # Regime display configuration
    REGIME_EMOJI = {
        'strong_uptrend': '🚀',
        'moderate_uptrend': '📈',
        'ranging': '↔️',
        'moderate_downtrend': '📉',
        'strong_downtrend': '🔻',
        'high_volatility': '⚡',
        'low_liquidity': '💧',
    }

    REGIME_COLORS = {
        'strong_uptrend': 0x00FF00,      # Green
        'moderate_uptrend': 0x90EE90,    # Light green
        'ranging': 0xFFD700,             # Gold
        'moderate_downtrend': 0xFFA07A,  # Light salmon
        'strong_downtrend': 0xFF0000,    # Red
        'high_volatility': 0xFF4500,     # Orange red
        'low_liquidity': 0x4169E1,       # Royal blue
    }

    # Regime significance classification
    # High-impact transitions that should ALWAYS show in dashboard
    BULLISH_REGIMES = {'strong_uptrend', 'moderate_uptrend'}
    BEARISH_REGIMES = {'strong_downtrend', 'moderate_downtrend'}
    STRONG_REGIMES = {'strong_uptrend', 'strong_downtrend'}
    NOISE_REGIMES = {'ranging', 'high_volatility', 'low_liquidity', 'sideways'}

    # Major symbols that always get regime alerts (others filtered for significance)
    MAJOR_SYMBOLS = {'BTCUSDT', 'ETHUSDT', 'SOLUSDT'}

    def __init__(
        self,
        alert_manager: Any = None,
        config: Dict[str, Any] = None,
        discord_webhook_url: str = None,
        enable_external_data: bool = True
    ):
        """
        Initialize the regime monitor.

        Args:
            alert_manager: AlertManager instance for storing alerts
            config: Configuration dictionary
            discord_webhook_url: Direct webhook URL (optional, can use alert_manager's)
            enable_external_data: Whether to fetch external data (perps-tracker, CoinGecko, F&G)
        """
        self.alert_manager = alert_manager
        self.config = config or {}
        self.discord_webhook_url = discord_webhook_url
        self.logger = logging.getLogger(__name__)

        # State tracking per symbol
        self.current_regimes: Dict[str, RegimeState] = {}
        self.regime_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.regime_changes: deque = deque(maxlen=500)  # Global change history

        # Alert cooldowns (prevent spam)
        self.last_alert_time: Dict[str, float] = {}

        # Get regime config from monitoring.alerts.regime or use legacy flat keys
        regime_config = self.config.get('monitoring', {}).get('alerts', {}).get('regime', {})

        # Cooldown: check new config path first, then legacy, then default
        self.alert_cooldown = regime_config.get('cooldown',
            self.config.get('regime_alert_cooldown', 1800))  # 30 min default

        # Confidence threshold for Discord alerts - 80% default
        # Note: Regime confidence range is 0.30-0.95 (geometric mean based)
        self.confidence_threshold = regime_config.get('discord_confidence_threshold',
            self.config.get('regime_confidence_threshold', 0.80))

        # Dashboard significance filtering - same threshold for consistency
        # Only high-confidence changes appear in the mobile dashboard
        self.dashboard_confidence_threshold = regime_config.get('dashboard_confidence_threshold',
            self.config.get('regime_dashboard_confidence', 0.80))  # 80% for dashboard

        self.filter_noise_transitions = self.config.get('regime_filter_noise', True)  # Filter ranging↔volatility oscillations
        self.major_symbols_only = self.config.get('regime_major_symbols_only', False)  # If True, only BTC/ETH/SOL

        # External data provider for enhanced regime detection
        self.external_data_provider: Optional[ExternalRegimeDataProvider] = None
        self.external_signals: Optional[ExternalRegimeSignals] = None
        self.external_signals_timestamp: float = 0
        self.external_signals_ttl: float = 60  # Refresh every 60 seconds

        if enable_external_data and EXTERNAL_DATA_AVAILABLE:
            try:
                self.external_data_provider = ExternalRegimeDataProvider(config)
                self.logger.info("✅ External data provider initialized (perps-tracker, CoinGecko, Fear/Greed)")
            except Exception as e:
                self.logger.warning(f"⚠️ External data provider init failed: {e}")
        elif not EXTERNAL_DATA_AVAILABLE:
            self.logger.info("External data provider not available (module not found)")

        # Stats
        self.stats = {
            'regimes_tracked': 0,
            'changes_detected': 0,
            'alerts_sent': 0,
            'external_data_fetches': 0,
            'last_update': None
        }

        self.logger.info(
            f"RegimeMonitor initialized (cooldown={self.alert_cooldown}s, "
            f"confidence_threshold={self.confidence_threshold:.0%}, "
            f"dashboard_threshold={self.dashboard_confidence_threshold:.0%}, "
            f"filter_noise={self.filter_noise_transitions})"
        )

    def _is_significant_for_dashboard(self, change: 'RegimeChange') -> bool:
        """
        Determine if a regime change is significant enough for the mobile dashboard.

        Significance criteria (must pass ALL):
        1. Confidence meets dashboard threshold (70%+)
        2. NOT a noise transition (ranging↔high_volatility↔low_liquidity)
        3. Either: major symbol OR significant transition type

        Significant transition types:
        - Reversals: bullish → bearish or bearish → bullish
        - Strong trends: any → strong_uptrend/strong_downtrend
        - Major symbols get more lenient filtering

        Returns:
            True if alert should appear in dashboard, False otherwise
        """
        # 1. Confidence check - stricter for dashboard
        if change.new_confidence < self.dashboard_confidence_threshold:
            self.logger.debug(
                f"[DASH FILTER] {change.symbol}: confidence {change.new_confidence:.0%} < {self.dashboard_confidence_threshold:.0%}"
            )
            return False

        # 2. Noise transition filter (optional but default ON)
        if self.filter_noise_transitions:
            # Filter out ranging ↔ high_volatility ↔ low_liquidity oscillations
            if change.previous_regime in self.NOISE_REGIMES and change.new_regime in self.NOISE_REGIMES:
                # Exception: major symbols always show volatility spikes
                if change.symbol not in self.MAJOR_SYMBOLS:
                    self.logger.debug(
                        f"[DASH FILTER] {change.symbol}: noise transition {change.previous_regime} → {change.new_regime}"
                    )
                    return False

        # 3. Major symbols check (if enabled)
        if self.major_symbols_only and change.symbol not in self.MAJOR_SYMBOLS:
            self.logger.debug(f"[DASH FILTER] {change.symbol}: not a major symbol")
            return False

        # 4. Bonus: Always show true reversals and strong trends
        is_reversal = (
            (change.previous_regime in self.BULLISH_REGIMES and change.new_regime in self.BEARISH_REGIMES) or
            (change.previous_regime in self.BEARISH_REGIMES and change.new_regime in self.BULLISH_REGIMES)
        )
        is_strong_trend = change.new_regime in self.STRONG_REGIMES

        # For non-major symbols, require either reversal or strong trend
        if change.symbol not in self.MAJOR_SYMBOLS:
            if not (is_reversal or is_strong_trend):
                # Additional check: at least one regime must be directional (not noise)
                prev_directional = change.previous_regime not in self.NOISE_REGIMES
                new_directional = change.new_regime not in self.NOISE_REGIMES
                if not (prev_directional or new_directional):
                    self.logger.debug(
                        f"[DASH FILTER] {change.symbol}: not significant enough (no direction)"
                    )
                    return False

        self.logger.debug(
            f"[DASH PASS] {change.symbol}: {change.previous_regime} → {change.new_regime} "
            f"(reversal={is_reversal}, strong={is_strong_trend})"
        )
        return True

    async def update_regime(
        self,
        symbol: str,
        detection: Any,  # RegimeDetection from MarketRegimeDetector
        trigger: str = 'price_action'
    ) -> Optional[RegimeChange]:
        """
        Update regime state for a symbol and alert if changed.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            detection: RegimeDetection object from MarketRegimeDetector
            trigger: What caused this update ('mtf', 'liquidation', 'price_action')

        Returns:
            RegimeChange if regime changed, None otherwise
        """
        try:
            now = time.time()
            regime_value = detection.regime.value if hasattr(detection.regime, 'value') else str(detection.regime)

            # Build current state
            new_state = RegimeState(
                symbol=symbol,
                regime=regime_value,
                confidence=detection.confidence,
                trend_direction=detection.trend_direction,
                volatility_percentile=detection.volatility_percentile,
                liquidity_score=detection.liquidity_score,
                mtf_aligned=detection.metadata.get('mtf_available', False),
                conflict_type=detection.metadata.get('conflict_type', 'UNKNOWN'),
                timestamp=now,
                metadata=detection.metadata
            )

            # Check if regime changed
            previous_state = self.current_regimes.get(symbol)
            regime_changed = False

            if previous_state is None:
                # First detection for this symbol
                self.logger.info(f"Initial regime for {symbol}: {regime_value} ({detection.confidence:.1%})")
                regime_changed = False  # Don't alert on first detection
            elif previous_state.regime != new_state.regime:
                # Regime changed!
                regime_changed = True
                self.logger.info(
                    f"REGIME CHANGE: {symbol} {previous_state.regime} → {new_state.regime} "
                    f"(conf: {previous_state.confidence:.1%} → {new_state.confidence:.1%})"
                )

            # Update state
            self.current_regimes[symbol] = new_state
            self.regime_history[symbol].append(new_state)
            self.stats['regimes_tracked'] = len(self.current_regimes)
            self.stats['last_update'] = now

            # Publish to shared cache for cross-service access (web_server.py can read this)
            await self._publish_to_shared_cache()

            # Handle regime change
            if regime_changed:
                # Check confidence threshold FIRST - filter out low-confidence changes globally
                if new_state.confidence < self.confidence_threshold:
                    self.logger.debug(
                        f"Skipping regime change for {symbol}: {previous_state.regime} → {new_state.regime} "
                        f"(confidence {new_state.confidence:.1%} < {self.confidence_threshold:.0%})"
                    )
                    return None  # Don't store, don't alert

                change = RegimeChange(
                    symbol=symbol,
                    previous_regime=previous_state.regime,
                    new_regime=new_state.regime,
                    previous_confidence=previous_state.confidence,
                    new_confidence=new_state.confidence,
                    timestamp=now,
                    trigger=trigger,
                    metadata={
                        'conflict_type': new_state.conflict_type,
                        'mtf_aligned': new_state.mtf_aligned,
                        'trend_direction': new_state.trend_direction,
                        'volatility_percentile': new_state.volatility_percentile,
                    }
                )

                self.regime_changes.append(change)
                self.stats['changes_detected'] += 1

                # Send alert (with cooldown)
                await self._send_regime_change_alert(change)

                return change

            return None

        except Exception as e:
            self.logger.error(f"Error updating regime for {symbol}: {e}")
            return None

    async def _send_regime_change_alert(self, change: RegimeChange) -> bool:
        """
        Send regime change alert to Discord and store in database.

        Args:
            change: RegimeChange object

        Returns:
            True if alert sent successfully
        """
        try:
            # Check cooldown (confidence threshold already checked in update_regime)
            last_alert = self.last_alert_time.get(change.symbol, 0)
            if time.time() - last_alert < self.alert_cooldown:
                self.logger.debug(f"Skipping Discord alert for {change.symbol} (cooldown)")
                return False

            # Build Discord embed
            embed = self._build_regime_change_embed(change)

            # Send to Discord
            discord_sent = await self._send_discord_alert(embed)

            # Store in database
            await self._store_alert(change)

            # Update cooldown
            self.last_alert_time[change.symbol] = time.time()
            self.stats['alerts_sent'] += 1

            return discord_sent

        except Exception as e:
            self.logger.error(f"Error sending regime change alert: {e}")
            return False

    def _build_regime_change_embed(self, change: RegimeChange) -> DiscordEmbed:
        """Build Discord embed for regime change alert."""

        prev_emoji = self.REGIME_EMOJI.get(change.previous_regime, '❓')
        new_emoji = self.REGIME_EMOJI.get(change.new_regime, '❓')
        color = self.REGIME_COLORS.get(change.new_regime, 0xFFFFFF)

        # Determine if this is bullish/bearish transition
        bullish_regimes = {'strong_uptrend', 'moderate_uptrend'}
        bearish_regimes = {'strong_downtrend', 'moderate_downtrend'}

        if change.previous_regime in bearish_regimes and change.new_regime in bullish_regimes:
            transition_type = "🟢 BULLISH REVERSAL"
        elif change.previous_regime in bullish_regimes and change.new_regime in bearish_regimes:
            transition_type = "🔴 BEARISH REVERSAL"
        elif change.new_regime == 'high_volatility':
            transition_type = "⚡ VOLATILITY SPIKE"
        elif change.new_regime == 'ranging':
            transition_type = "↔️ CONSOLIDATION"
        else:
            transition_type = "📊 REGIME SHIFT"

        embed = DiscordEmbed(
            title=f"{transition_type}: {change.symbol}",
            description=f"{prev_emoji} **{change.previous_regime.upper()}** → {new_emoji} **{change.new_regime.upper()}**",
            color=color
        )

        # Add fields
        embed.add_embed_field(
            name="Confidence",
            value=f"{change.previous_confidence:.0%} → {change.new_confidence:.0%}",
            inline=True
        )

        embed.add_embed_field(
            name="Trigger",
            value=change.trigger.replace('_', ' ').title(),
            inline=True
        )

        # Add conflict type if available
        conflict_type = change.metadata.get('conflict_type', 'UNKNOWN')
        if conflict_type != 'UNKNOWN':
            embed.add_embed_field(
                name="MTF Analysis",
                value=conflict_type.replace('_', ' '),
                inline=True
            )

        # Trading implication
        implications = {
            'strong_uptrend': "Strong LONG bias - favor continuation",
            'moderate_uptrend': "Moderate bullish - balanced approach",
            'ranging': "WAIT - prefer mean reversion or sit out",
            'moderate_downtrend': "Moderate bearish - balanced approach",
            'strong_downtrend': "Strong SHORT bias - favor continuation",
            'high_volatility': "CAUTION - reduce position size",
            'low_liquidity': "CAUTION - thin orderbook, wide stops",
        }

        implication = implications.get(change.new_regime, "Monitor closely")
        embed.add_embed_field(
            name="💡 Trading Implication",
            value=implication,
            inline=False
        )

        embed.set_footer(text="Regime Monitor • Virtuoso Trading")
        embed.set_timestamp()

        return embed

    async def _send_discord_alert(self, embed: DiscordEmbed) -> bool:
        """Send embed to Discord webhook."""
        try:
            import os

            # Priority 1: Direct webhook URL passed to constructor
            webhook_url = self.discord_webhook_url

            # Priority 2: Dedicated regime webhook from environment
            if not webhook_url:
                webhook_url = os.getenv('REGIME_ALERTS_WEBHOOK_URL')
                if webhook_url:
                    self.logger.debug("Using REGIME_ALERTS_WEBHOOK_URL from environment")

            # Priority 3: Try to get from alert_manager
            if not webhook_url and self.alert_manager:
                if hasattr(self.alert_manager, 'regime_webhook_url') and self.alert_manager.regime_webhook_url:
                    webhook_url = self.alert_manager.regime_webhook_url
                elif hasattr(self.alert_manager, 'discord_webhook_url') and self.alert_manager.discord_webhook_url:
                    webhook_url = self.alert_manager.discord_webhook_url
                    self.logger.debug("Falling back to main Discord webhook")

            if not webhook_url:
                self.logger.warning("No Discord webhook URL configured for regime alerts")
                return False

            webhook = DiscordWebhook(url=webhook_url)
            webhook.add_embed(embed)

            response = webhook.execute()

            if response and hasattr(response, 'status_code'):
                if response.status_code in [200, 204]:
                    self.logger.info(f"✅ Regime change alert sent to Discord")
                    return True
                else:
                    self.logger.warning(f"Discord webhook returned {response.status_code}")

            return False

        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {e}")
            return False

    async def _store_alert(self, change: RegimeChange) -> Optional[str]:
        """Store regime change alert in database.

        ALL regime alerts are stored in SQLite for historical analysis.
        Significant alerts are also cached for dashboard display.
        """
        import time
        import sqlite3
        import json
        import os

        try:
            # Check if this change is significant enough for the dashboard
            is_significant = self._is_significant_for_dashboard(change)

            alert_details = {
                'previous_regime': change.previous_regime,
                'new_regime': change.new_regime,
                'previous_confidence': change.previous_confidence,
                'new_confidence': change.new_confidence,
                'trigger': change.trigger,
                'conflict_type': change.metadata.get('conflict_type'),
                'trend_direction': change.metadata.get('trend_direction'),
                'volatility_percentile': change.metadata.get('volatility_percentile'),
                'dashboard_significant': is_significant,
                'confidence': change.new_confidence,  # For dashboard filtering
            }

            alert_id = f"regime_{int(time.time() * 1000)}_{hash(change.symbol) % 10000}"
            timestamp_ms = int(time.time() * 1000)
            message = f"Regime: {change.previous_regime} → {change.new_regime}"
            severity = 'WARNING' if change.new_regime == 'high_volatility' else 'INFO'

            # METHOD 1: Try alert_manager's storage method (preferred)
            stored = False
            if self.alert_manager:
                try:
                    if hasattr(self.alert_manager, '_store_and_cache_alert_direct'):
                        result = await self.alert_manager._store_and_cache_alert_direct(
                            alert_type='regime_change',
                            symbol=change.symbol,
                            message=message,
                            level=severity,
                            details=alert_details
                        )
                        if result:
                            alert_id = result
                            stored = True
                            self.logger.info(f"✅ Regime alert stored via alert_manager: {change.symbol}")
                except Exception as e:
                    self.logger.warning(f"alert_manager storage failed: {e}")

            # METHOD 2: Direct SQLite storage (fallback/backup)
            if not stored:
                try:
                    # MIGRATION 2025-12-06: Changed from alerts.db to virtuoso.db
                    db_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'data', 'virtuoso.db'
                    )

                    if os.path.exists(db_path):
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()

                        # Ensure table exists
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS alerts (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                alert_id TEXT UNIQUE,
                                alert_type TEXT,
                                symbol TEXT,
                                message TEXT,
                                severity TEXT,
                                timestamp INTEGER,
                                details TEXT,
                                sent_to_discord INTEGER DEFAULT 0,
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                            )
                        ''')

                        cursor.execute('''
                            INSERT OR REPLACE INTO alerts
                            (alert_id, alert_type, symbol, message, severity, timestamp, details, sent_to_discord)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            alert_id,
                            'regime_change',
                            change.symbol,
                            message,
                            severity,
                            timestamp_ms,
                            json.dumps(alert_details),
                            1  # Discord already sent
                        ))

                        conn.commit()
                        conn.close()
                        stored = True
                        self.logger.info(f"✅ Regime alert stored directly to SQLite: {change.symbol}")
                    else:
                        self.logger.warning(f"Database not found at {db_path}")

                except Exception as e:
                    self.logger.error(f"Direct SQLite storage failed: {e}")

            if stored:
                if is_significant:
                    self.logger.info(
                        f"📊 Significant regime change: {change.symbol} "
                        f"{change.previous_regime} → {change.new_regime} ({change.new_confidence:.0%})"
                    )
                else:
                    self.logger.debug(
                        f"📊 Regime change stored: {change.symbol} "
                        f"{change.previous_regime} → {change.new_regime}"
                    )
            else:
                self.logger.error(f"❌ Failed to store regime alert for {change.symbol}")

            return alert_id if stored else None

        except Exception as e:
            self.logger.error(f"Error storing regime alert: {e}", exc_info=True)
            return None

    async def _publish_to_shared_cache(self) -> None:
        """
        Publish current regime data to shared cache for cross-service access.

        This enables web_server.py to read regime data that was computed
        by the MarketMonitor in main.py.
        """
        if not SHARED_CACHE_AVAILABLE:
            return

        try:
            bridge = get_shared_cache_bridge()

            # Publish current regimes for all symbols
            regimes_data = self.get_current_regimes()
            await bridge.publish_data_update(
                key='regime:current',
                data=regimes_data,
                source=DataSource.ANALYSIS_ENGINE,
                ttl=120  # 2 minutes - regime data should be refreshed frequently
            )

            # Publish recent changes
            changes_data = self.get_recent_changes(limit=50)
            await bridge.publish_data_update(
                key='regime:changes',
                data=changes_data,
                source=DataSource.ANALYSIS_ENGINE,
                ttl=300  # 5 minutes for historical changes
            )

            # Publish stats
            # TTL increased from 60s to 300s to survive analysis cycle gaps
            # caused by rate limiting and API timeouts (2026-01-15)
            stats_data = self.get_stats()
            await bridge.publish_data_update(
                key='regime:stats',
                data=stats_data,
                source=DataSource.ANALYSIS_ENGINE,
                ttl=300
            )

            self.logger.debug(f"Published regime data to shared cache: {len(regimes_data)} symbols")

        except Exception as e:
            self.logger.debug(f"Failed to publish to shared cache: {e}")

    # ========================================
    # API Methods
    # ========================================

    def get_current_regimes(self) -> Dict[str, Dict[str, Any]]:
        """Get current regime state for all tracked symbols (for API)."""
        return {
            symbol: {
                'regime': state.regime,
                'confidence': state.confidence,
                'trend_direction': state.trend_direction,
                'volatility_percentile': state.volatility_percentile,
                'liquidity_score': state.liquidity_score,
                'mtf_aligned': state.mtf_aligned,
                'conflict_type': state.conflict_type,
                'timestamp': state.timestamp,
                'timestamp_iso': datetime.fromtimestamp(state.timestamp, tz=timezone.utc).isoformat(),
            }
            for symbol, state in self.current_regimes.items()
        }

    def get_regime_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current regime for a specific symbol."""
        state = self.current_regimes.get(symbol)
        if not state:
            return None

        return {
            'regime': state.regime,
            'confidence': state.confidence,
            'trend_direction': state.trend_direction,
            'volatility_percentile': state.volatility_percentile,
            'liquidity_score': state.liquidity_score,
            'mtf_aligned': state.mtf_aligned,
            'conflict_type': state.conflict_type,
            'timestamp': state.timestamp,
            'timestamp_iso': datetime.fromtimestamp(state.timestamp, tz=timezone.utc).isoformat(),
            'emoji': self.REGIME_EMOJI.get(state.regime, '❓'),
        }

    def get_recent_changes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent regime changes (for API)."""
        changes = list(self.regime_changes)[-limit:]
        return [
            {
                'symbol': c.symbol,
                'previous_regime': c.previous_regime,
                'new_regime': c.new_regime,
                'previous_confidence': c.previous_confidence,
                'new_confidence': c.new_confidence,
                'trigger': c.trigger,
                'conflict_type': c.metadata.get('conflict_type'),
                'timestamp': c.timestamp,
                'timestamp_iso': datetime.fromtimestamp(c.timestamp, tz=timezone.utc).isoformat(),
            }
            for c in reversed(changes)
        ]

    def get_symbol_history(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get regime history for a specific symbol."""
        history = list(self.regime_history.get(symbol, []))[-limit:]
        return [
            {
                'regime': state.regime,
                'confidence': state.confidence,
                'trend_direction': state.trend_direction,
                'timestamp': state.timestamp,
                'timestamp_iso': datetime.fromtimestamp(state.timestamp, tz=timezone.utc).isoformat(),
            }
            for state in reversed(history)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        stats = {
            **self.stats,
            'symbols_tracked': list(self.current_regimes.keys()),
            'changes_in_memory': len(self.regime_changes),
            'external_data_enabled': self.external_data_provider is not None,
        }

        # Add external data stats if available
        if self.external_signals:
            stats['external_data'] = {
                'overall_bias': self.external_signals.overall_bias.value,
                'confidence_modifier': self.external_signals.confidence_modifier,
                'volatility_warning': self.external_signals.volatility_warning,
                'data_quality': self.external_signals.data_quality,
                'last_fetch': self.external_signals_timestamp,
                'derivatives': {
                    'funding_rate': self.external_signals.derivatives.funding_rate,
                    'funding_sentiment': self.external_signals.derivatives.funding_sentiment,
                    'basis_pct': self.external_signals.derivatives.basis_pct,
                    'long_short_ratio': f"{self.external_signals.derivatives.long_pct:.1f}/{self.external_signals.derivatives.short_pct:.1f}",
                },
                'sentiment': {
                    'fear_greed_value': self.external_signals.sentiment.value,
                    'fear_greed_label': self.external_signals.sentiment.classification,
                },
                'global_market': {
                    'btc_dominance': self.external_signals.global_market.btc_dominance,
                    'market_cap_change_24h': self.external_signals.global_market.market_cap_change_24h,
                }
            }

        return stats

    async def fetch_external_signals(self) -> Optional['ExternalRegimeSignals']:
        """
        Fetch external market data signals for regime enhancement.

        Returns cached data if still fresh, otherwise fetches new data from:
        - crypto-perps-tracker: Derivatives sentiment
        - CoinGecko: Global market structure
        - Alternative.me: Fear & Greed Index

        Returns:
            ExternalRegimeSignals or None if fetch fails
        """
        if not self.external_data_provider:
            return None

        now = time.time()

        # Return cached signals if still fresh
        if (self.external_signals and
            (now - self.external_signals_timestamp) < self.external_signals_ttl):
            return self.external_signals

        try:
            self.external_signals = await self.external_data_provider.get_external_signals()
            self.external_signals_timestamp = now
            self.stats['external_data_fetches'] += 1

            self.logger.debug(
                f"External signals fetched: bias={self.external_signals.overall_bias.value}, "
                f"quality={self.external_signals.data_quality:.1%}"
            )

            return self.external_signals

        except Exception as e:
            self.logger.warning(f"Failed to fetch external signals: {e}")
            return self.external_signals  # Return stale data if available

    def get_external_signals_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current external market signals.

        Useful for dashboard display and API endpoints.
        """
        if not self.external_signals:
            return {
                'available': False,
                'message': 'External data not available'
            }

        return {
            'available': True,
            'overall_bias': self.external_signals.overall_bias.value,
            'confidence_modifier': round(self.external_signals.confidence_modifier, 2),
            'volatility_warning': self.external_signals.volatility_warning,
            'liquidity_warning': self.external_signals.liquidity_warning,
            'data_quality': round(self.external_signals.data_quality, 2),
            'derivatives': {
                'funding_rate': round(self.external_signals.derivatives.funding_rate, 6),
                'funding_sentiment': self.external_signals.derivatives.funding_sentiment,
                'basis_pct': round(self.external_signals.derivatives.basis_pct, 4),
                'basis_status': self.external_signals.derivatives.basis_status,
                'long_pct': round(self.external_signals.derivatives.long_pct, 1),
                'short_pct': round(self.external_signals.derivatives.short_pct, 1),
            },
            'global_market': {
                'btc_dominance': round(self.external_signals.global_market.btc_dominance, 2),
                'eth_dominance': round(self.external_signals.global_market.eth_dominance, 2),
                'market_cap_change_24h': round(self.external_signals.global_market.market_cap_change_24h, 2),
            },
            'sentiment': {
                'fear_greed_value': self.external_signals.sentiment.value,
                'fear_greed_label': self.external_signals.sentiment.classification,
            },
            'timestamp': self.external_signals_timestamp,
            'timestamp_iso': datetime.fromtimestamp(
                self.external_signals_timestamp, tz=timezone.utc
            ).isoformat() if self.external_signals_timestamp else None,
        }
