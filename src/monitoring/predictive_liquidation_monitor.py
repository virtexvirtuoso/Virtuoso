#!/usr/bin/env python3
"""
Predictive Liquidation Monitor

Monitors leading indicators (funding rates, open interest, price action) to generate
PREDICTIVE alerts before liquidation cascades occur, providing 30-60+ minutes of lead time.

Key Features:
- Funding Rate Alerts: Detects crowded trades before they unwind
- Leverage Build-Up Alerts: Monitors OI + price divergence
- Multi-Symbol Cluster Alerts: Detects correlated risk across markets
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict, deque
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FundingRateData:
    """Structure for funding rate tracking"""
    symbol: str
    rate: float
    annualized: float
    direction: str
    timestamp: float


@dataclass
class OpenInterestData:
    """Structure for open interest tracking"""
    symbol: str
    oi_value: float
    oi_change_pct: float
    price: float
    price_change_pct: float
    timestamp: float


class PredictiveLiquidationMonitor:
    """
    Monitors leading indicators and generates predictive alerts
    before liquidation cascades occur.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        alert_manager: Any,
        exchange_manager: Any,
        symbols: List[str] = None
    ):
        """
        Initialize the predictive liquidation monitor.

        Args:
            config: Configuration dictionary (predictive_alerts section)
            alert_manager: AlertManager instance for sending Discord alerts
            exchange_manager: ExchangeManager instance for fetching data
            symbols: List of symbols to monitor
        """
        self.config = config
        self.alert_manager = alert_manager
        self.exchange_manager = exchange_manager
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

        self.logger = logging.getLogger(__name__)
        self.running = False

        # Data storage
        self.funding_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.oi_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.risk_scores: Dict[str, float] = {}

        # Alert cooldowns
        self.last_alerts: Dict[str, float] = {}

        # Load config
        self._load_config_defaults()

        # Stats
        self.stats = {
            "alerts_sent": 0,
            "funding_checks": 0,
            "oi_checks": 0,
            "cluster_checks": 0,
            "errors": 0
        }

        self.logger.info(f"Initialized PredictiveLiquidationMonitor for: {self.symbols}")

    def _load_config_defaults(self):
        """Load configuration with defaults"""
        self.check_interval = self.config.get("check_interval_seconds", 60)

        # Funding rate config
        fr_config = self.config.get("funding_rate", {})
        self.funding_enabled = fr_config.get("enabled", True)
        self.funding_thresholds = fr_config.get("thresholds", {
            "warning": 0.03,
            "high": 0.05,
            "critical": 0.08
        })
        self.funding_cooldown = fr_config.get("cooldown_minutes", 60) * 60

        # Leverage build-up config
        lb_config = self.config.get("leverage_buildup", {})
        self.leverage_enabled = lb_config.get("enabled", True)
        self.leverage_timeframe_hours = lb_config.get("timeframe_hours", 4)
        self.leverage_thresholds = lb_config.get("thresholds", {
            "oi_change_warning": 0.08,
            "oi_change_high": 0.12,
            "oi_change_critical": 0.18,
            "price_change_min": 0.02
        })
        self.leverage_cooldown = lb_config.get("cooldown_minutes", 30) * 60

        # Cluster risk config
        cr_config = self.config.get("cluster_risk", {})
        self.cluster_enabled = cr_config.get("enabled", True)
        self.cluster_min_symbols = {
            "warning": cr_config.get("min_symbols_warning", 2),
            "high": cr_config.get("min_symbols_high", 3),
            "critical": cr_config.get("min_symbols_critical", 4)
        }
        self.cluster_risk_threshold = cr_config.get("risk_threshold", 0.5)
        self.cluster_cooldown = cr_config.get("cooldown_minutes", 30) * 60

    async def start(self):
        """Start the predictive monitoring loop"""
        self.running = True
        self.logger.info("Starting Predictive Liquidation Monitor...")

        try:
            while self.running:
                try:
                    await self._fetch_all_data()

                    if self.funding_enabled:
                        await self._check_funding_rates()

                    if self.leverage_enabled:
                        await self._check_leverage_buildup()

                    if self.cluster_enabled:
                        await self._check_cluster_risk()

                    await asyncio.sleep(self.check_interval)

                except asyncio.CancelledError:
                    self.logger.info("Predictive monitor cancelled")
                    break
                except Exception as e:
                    self.stats["errors"] += 1
                    self.logger.error(f"Error in predictive monitoring loop: {e}")
                    await asyncio.sleep(30)

        except Exception as e:
            self.logger.error(f"Fatal error in predictive monitor: {e}")
        finally:
            self.running = False
            self.logger.info("Predictive Liquidation Monitor stopped")

    async def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        self.logger.info("Stopping Predictive Liquidation Monitor...")

    async def _fetch_all_data(self):
        """Fetch funding rates, OI, and prices for all symbols"""
        for symbol in self.symbols:
            try:
                funding_data = await self._fetch_funding_rate(symbol)
                if funding_data:
                    self.funding_history[symbol].append(funding_data)

                oi_data = await self._fetch_open_interest(symbol)
                if oi_data:
                    self.oi_history[symbol].append(oi_data)
                    self.price_history[symbol].append({
                        "price": oi_data.price,
                        "timestamp": time.time()
                    })

            except Exception as e:
                self.logger.warning(f"Error fetching data for {symbol}: {e}")

    async def _fetch_funding_rate(self, symbol: str) -> Optional[FundingRateData]:
        """Fetch funding rate for a symbol"""
        try:
            result = await self.exchange_manager.fetch_funding_rate(symbol)

            if result and "funding_rate" in result:
                rate = float(result.get("funding_rate", 0))
                annualized = rate * 3 * 365 * 100
                direction = "LONGS_PAYING" if rate > 0 else "SHORTS_PAYING"

                return FundingRateData(
                    symbol=symbol,
                    rate=rate,
                    annualized=annualized,
                    direction=direction,
                    timestamp=time.time()
                )
        except Exception as e:
            self.logger.debug(f"Error fetching funding rate for {symbol}: {e}")

        return None

    async def _fetch_open_interest(self, symbol: str) -> Optional[OpenInterestData]:
        """Fetch open interest and calculate changes"""
        try:
            oi_result = await self.exchange_manager.fetch_open_interest(symbol)
            ticker = await self.exchange_manager.fetch_ticker(symbol)

            if oi_result and ticker:
                current_oi = float(oi_result.get("open_interest", 0))
                current_price = float(ticker.get("last", ticker.get("close", 0)))

                oi_change_pct = 0.0
                price_change_pct = 0.0

                lookback_seconds = self.leverage_timeframe_hours * 3600
                cutoff_time = time.time() - lookback_seconds

                if symbol in self.oi_history and len(self.oi_history[symbol]) > 0:
                    old_data = None
                    for data in self.oi_history[symbol]:
                        if data.timestamp <= cutoff_time:
                            old_data = data
                            break

                    if old_data is None and len(self.oi_history[symbol]) > 0:
                        old_data = self.oi_history[symbol][0]

                    if old_data and old_data.oi_value > 0:
                        oi_change_pct = (current_oi - old_data.oi_value) / old_data.oi_value
                    if old_data and old_data.price > 0:
                        price_change_pct = (current_price - old_data.price) / old_data.price

                return OpenInterestData(
                    symbol=symbol,
                    oi_value=current_oi,
                    oi_change_pct=oi_change_pct,
                    price=current_price,
                    price_change_pct=price_change_pct,
                    timestamp=time.time()
                )

        except Exception as e:
            self.logger.debug(f"Error fetching OI for {symbol}: {e}")

        return None

    async def _check_funding_rates(self):
        """Check funding rates for extreme readings"""
        self.stats["funding_checks"] += 1

        for symbol in self.symbols:
            if symbol not in self.funding_history or len(self.funding_history[symbol]) == 0:
                continue

            latest = self.funding_history[symbol][-1]
            rate_abs = abs(latest.rate)

            severity = None
            if rate_abs >= self.funding_thresholds["critical"]:
                severity = AlertSeverity.CRITICAL
            elif rate_abs >= self.funding_thresholds["high"]:
                severity = AlertSeverity.HIGH
            elif rate_abs >= self.funding_thresholds["warning"]:
                severity = AlertSeverity.WARNING

            if severity:
                await self._send_funding_alert(symbol, latest, severity)

    async def _send_funding_alert(self, symbol: str, data: FundingRateData, severity: AlertSeverity):
        """Send funding rate alert"""
        alert_key = f"funding:{symbol}"

        if not self._check_cooldown(alert_key, self.funding_cooldown):
            return

        if data.rate > 0:
            risk_type = "LONG SQUEEZE"
            crowd = "Longs paying shorts"
            warning = "Over-leveraged longs vulnerable if price drops"
        else:
            risk_type = "SHORT SQUEEZE"
            crowd = "Shorts paying longs"
            warning = "Over-leveraged shorts vulnerable if price rises"

        rate_pct = data.rate * 100
        severity_emoji = "🔴" if severity == AlertSeverity.CRITICAL else "🟠" if severity == AlertSeverity.HIGH else "🟡"

        embed_data = {
            "title": f"{severity_emoji} FUNDING RATE {severity.value.upper()}: {symbol}",
            "color": self._severity_color(severity),
            "fields": [
                {"name": "Current Funding", "value": f"{rate_pct:.4f}% (every 8h)", "inline": True},
                {"name": "Annualized", "value": f"{data.annualized:.1f}%", "inline": True},
                {"name": "Direction", "value": data.direction.replace("_", " "), "inline": True},
                {"name": "⚠️ Risk Assessment", "value": f"**{risk_type} RISK**\n{crowd}\n{warning}", "inline": False},
                {"name": "📊 Context", "value": f"Normal: -0.01% to +0.01%\nCurrent: {abs(rate_pct/0.01):.1f}x elevated", "inline": False},
                {"name": "⏰ Lead Time", "value": "2-8 hours before potential cascade", "inline": True}
            ],
            "footer": "Predictive Liquidation Alert • Virtuoso Trading"
        }

        await self._send_discord_alert(
            embed_data, severity,
            symbol=symbol,
            alert_subtype="funding",
            details={
                "funding_rate": data.rate,
                "annualized": data.annualized,
                "direction": data.direction,
                "risk_type": risk_type
            }
        )
        self._mark_alert_sent(alert_key)
        self.stats["alerts_sent"] += 1

        self.logger.info(f"Sent funding rate alert for {symbol}: {rate_pct:.4f}% ({severity.value})")

    async def _check_leverage_buildup(self):
        """Check for leverage build-up (OI + price divergence)"""
        self.stats["oi_checks"] += 1

        for symbol in self.symbols:
            if symbol not in self.oi_history or len(self.oi_history[symbol]) == 0:
                continue

            latest = self.oi_history[symbol][-1]

            if abs(latest.price_change_pct) < self.leverage_thresholds["price_change_min"]:
                continue

            oi_change = latest.oi_change_pct
            price_change = latest.price_change_pct

            # Both positive or OI up with price down = leverage building
            if oi_change > 0:
                severity = None
                if oi_change >= self.leverage_thresholds["oi_change_critical"]:
                    severity = AlertSeverity.CRITICAL
                elif oi_change >= self.leverage_thresholds["oi_change_high"]:
                    severity = AlertSeverity.HIGH
                elif oi_change >= self.leverage_thresholds["oi_change_warning"]:
                    severity = AlertSeverity.WARNING

                if severity:
                    await self._send_leverage_alert(symbol, latest, severity)

    async def _send_leverage_alert(self, symbol: str, data: OpenInterestData, severity: AlertSeverity):
        """Send leverage build-up alert"""
        alert_key = f"leverage:{symbol}"

        if not self._check_cooldown(alert_key, self.leverage_cooldown):
            return

        if data.price_change_pct > 0:
            position_risk = "LONG"
            risk_warning = "New leveraged LONG positions being opened"
        else:
            position_risk = "SHORT"
            risk_warning = "New leveraged SHORT positions being opened"

        severity_emoji = "🔴" if severity == AlertSeverity.CRITICAL else "🟠" if severity == AlertSeverity.HIGH else "🟡"

        embed_data = {
            "title": f"{severity_emoji} LEVERAGE BUILD-UP: {symbol}",
            "color": self._severity_color(severity),
            "fields": [
                {"name": "📈 OI Change", "value": f"{data.oi_change_pct*100:+.1f}%", "inline": True},
                {"name": "📈 Price Change", "value": f"{data.price_change_pct*100:+.1f}%", "inline": True},
                {"name": "Timeframe", "value": f"{self.leverage_timeframe_hours}h", "inline": True},
                {"name": "⚠️ Risk Assessment", "value": f"**{position_risk} LIQUIDATION RISK**\n{risk_warning}\nThis creates liquidation fuel if price reverses", "inline": False},
                {"name": "Current Price", "value": f"${data.price:,.2f}", "inline": True},
                {"name": "⏰ Lead Time", "value": "2-6 hours before potential cascade", "inline": True}
            ],
            "footer": "Predictive Liquidation Alert • Virtuoso Trading"
        }

        await self._send_discord_alert(
            embed_data, severity,
            symbol=symbol,
            alert_subtype="leverage",
            details={
                "oi_change_pct": data.oi_change_pct,
                "price_change_pct": data.price_change_pct,
                "price": data.price,
                "position_risk": position_risk
            }
        )
        self._mark_alert_sent(alert_key)
        self.stats["alerts_sent"] += 1

        self.logger.info(f"Sent leverage alert for {symbol}: OI {data.oi_change_pct*100:+.1f}% ({severity.value})")

    async def _check_cluster_risk(self):
        """Check for multi-symbol risk clustering"""
        self.stats["cluster_checks"] += 1

        high_risk_symbols = []
        risk_details = {}

        for symbol in self.symbols:
            risk_score = self._calculate_symbol_risk(symbol)
            self.risk_scores[symbol] = risk_score

            if risk_score >= self.cluster_risk_threshold:
                high_risk_symbols.append(symbol)
                risk_details[symbol] = {
                    "risk_score": risk_score,
                    "funding": self._get_latest_funding(symbol),
                    "oi_change": self._get_latest_oi_change(symbol)
                }

        num_high_risk = len(high_risk_symbols)

        severity = None
        if num_high_risk >= self.cluster_min_symbols["critical"]:
            severity = AlertSeverity.CRITICAL
        elif num_high_risk >= self.cluster_min_symbols["high"]:
            severity = AlertSeverity.HIGH
        elif num_high_risk >= self.cluster_min_symbols["warning"]:
            severity = AlertSeverity.WARNING

        if severity:
            await self._send_cluster_alert(high_risk_symbols, risk_details, severity)

    def _calculate_symbol_risk(self, symbol: str) -> float:
        """Calculate composite risk score for a symbol (0-1 scale)"""
        risk_components = []

        funding = self._get_latest_funding(symbol)
        if funding:
            funding_risk = min(1.0, abs(funding) / 0.1)
            risk_components.append(funding_risk * 0.4)

        oi_change = self._get_latest_oi_change(symbol)
        if oi_change is not None:
            oi_risk = min(1.0, abs(oi_change) / 0.2)
            risk_components.append(oi_risk * 0.4)

        price_change = self._get_latest_price_change(symbol)
        if price_change is not None:
            vol_risk = min(1.0, abs(price_change) / 0.1)
            risk_components.append(vol_risk * 0.2)

        return sum(risk_components) if risk_components else 0.0

    def _get_latest_funding(self, symbol: str) -> Optional[float]:
        """Get latest funding rate for symbol"""
        if symbol in self.funding_history and len(self.funding_history[symbol]) > 0:
            return self.funding_history[symbol][-1].rate
        return None

    def _get_latest_oi_change(self, symbol: str) -> Optional[float]:
        """Get latest OI change percentage for symbol"""
        if symbol in self.oi_history and len(self.oi_history[symbol]) > 0:
            return self.oi_history[symbol][-1].oi_change_pct
        return None

    def _get_latest_price_change(self, symbol: str) -> Optional[float]:
        """Get latest price change percentage for symbol"""
        if symbol in self.oi_history and len(self.oi_history[symbol]) > 0:
            return self.oi_history[symbol][-1].price_change_pct
        return None

    async def _send_cluster_alert(self, symbols: List[str], details: Dict, severity: AlertSeverity):
        """Send multi-symbol cluster risk alert"""
        alert_key = "cluster:global"

        if not self._check_cooldown(alert_key, self.cluster_cooldown):
            return

        symbols_table = []
        for symbol in symbols:
            d = details.get(symbol, {})
            funding = d.get("funding", 0) or 0
            oi_change = d.get("oi_change", 0) or 0
            risk = d.get("risk_score", 0)
            symbols_table.append(f"**{symbol}**: Risk {risk*100:.0f}% | FR {funding*100:.3f}% | OI {oi_change*100:+.1f}%")

        avg_risk = np.mean([details[s]["risk_score"] for s in symbols])
        cascade_prob = min(1.0, avg_risk * 1.2)

        severity_emoji = "🔴" if severity == AlertSeverity.CRITICAL else "🟠"

        embed_data = {
            "title": f"{severity_emoji} GLOBAL CASCADE RISK",
            "color": self._severity_color(severity),
            "description": f"**{len(symbols)} symbols** showing elevated liquidation risk simultaneously",
            "fields": [
                {"name": "📊 Affected Symbols", "value": "\n".join(symbols_table), "inline": False},
                {"name": "🎲 Cascade Probability", "value": f"{cascade_prob*100:.0f}%", "inline": True},
                {"name": "⏰ Time to Event", "value": "30-60 minutes", "inline": True},
                {"name": "⚠️ Recommendation", "value": "Consider reducing leverage. This pattern precedes market-wide cascades.", "inline": False}
            ],
            "footer": "Predictive Liquidation Alert • Virtuoso Trading"
        }

        await self._send_discord_alert(
            embed_data, severity,
            symbol="GLOBAL",
            alert_subtype="cluster",
            details={
                "affected_symbols": symbols,
                "symbol_count": len(symbols),
                "cascade_probability": cascade_prob,
                "avg_risk": avg_risk,
                "symbol_details": details
            }
        )
        self._mark_alert_sent(alert_key)
        self.stats["alerts_sent"] += 1

        self.logger.info(f"Sent cluster alert: {len(symbols)} symbols at risk ({severity.value})")

    async def _send_discord_alert(self, embed_data: Dict, severity: AlertSeverity,
                                    symbol: str = "MULTI", alert_subtype: str = "predictive",
                                    details: Optional[Dict] = None):
        """Send alert through the alert manager and store in SQLite for dashboard"""
        try:
            if hasattr(self.alert_manager, "send_predictive_alert"):
                await self.alert_manager.send_predictive_alert(embed_data, severity.value)
            elif hasattr(self.alert_manager, "_send_discord_embed"):
                from discord_webhook import DiscordEmbed

                embed = DiscordEmbed(
                    title=embed_data.get("title", "Predictive Alert"),
                    description=embed_data.get("description", ""),
                    color=embed_data.get("color", 0xFFFF00)
                )

                for field in embed_data.get("fields", []):
                    embed.add_embed_field(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        inline=field.get("inline", True)
                    )

                embed.set_footer(text=embed_data.get("footer", "Virtuoso Trading"))
                embed.set_timestamp()

                await self.alert_manager._send_discord_embed(embed, alert_type="predictive")
            else:
                await self.alert_manager.send_alert({
                    "type": "predictive",
                    "title": embed_data.get("title"),
                    "message": embed_data.get("description", ""),
                    "severity": severity.value,
                    "data": embed_data
                })

            # Store in SQLite for mobile dashboard
            if hasattr(self.alert_manager, "_store_and_cache_alert_direct"):
                # Map severity to alert level
                level_map = {
                    AlertSeverity.INFO: "INFO",
                    AlertSeverity.WARNING: "WARNING",
                    AlertSeverity.HIGH: "HIGH",
                    AlertSeverity.CRITICAL: "CRITICAL"
                }

                # Extract field values for details
                field_details = {}
                for field in embed_data.get("fields", []):
                    key = field.get("name", "").replace("📈", "").replace("📊", "").replace("⚠️", "").replace("⏰", "").replace("🎲", "").strip()
                    field_details[key] = field.get("value", "")

                storage_details = {
                    "alert_subtype": alert_subtype,
                    "severity": severity.value,
                    "color": embed_data.get("color"),
                    "fields": field_details,
                    **(details or {})
                }

                await self.alert_manager._store_and_cache_alert_direct(
                    alert_type=f"predictive_{alert_subtype}",
                    symbol=symbol,
                    message=embed_data.get("title", "Predictive Alert"),
                    level=level_map.get(severity, "WARNING"),
                    details=storage_details
                )

        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {e}")

    def _check_cooldown(self, alert_key: str, cooldown_seconds: float) -> bool:
        """Check if we can send an alert (cooldown expired)"""
        last_sent = self.last_alerts.get(alert_key, 0)
        return (time.time() - last_sent) >= cooldown_seconds

    def _mark_alert_sent(self, alert_key: str):
        """Mark an alert as sent"""
        self.last_alerts[alert_key] = time.time()

    def _severity_color(self, severity: AlertSeverity) -> int:
        """Get Discord embed color for severity"""
        colors = {
            AlertSeverity.INFO: 0x3498DB,
            AlertSeverity.WARNING: 0xF1C40F,
            AlertSeverity.HIGH: 0xE67E22,
            AlertSeverity.CRITICAL: 0xE74C3C
        }
        return colors.get(severity, 0xFFFFFF)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            **self.stats,
            "running": self.running,
            "symbols_monitored": len(self.symbols),
            "current_risk_scores": dict(self.risk_scores),
            "last_check": datetime.now(timezone.utc).isoformat()
        }
