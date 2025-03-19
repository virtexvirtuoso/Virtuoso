"""Market data reporting module.

This module provides functionality for generating market reports:
- Market summaries
- Trading pair statistics
- Risk metrics calculation
- Report formatting for various outputs (Discord, etc.)
"""

import logging
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import random
import os
import json
import math
import discord
from src.core.exchanges.manager import ExchangeManager
from src.config.manager import ConfigManager
import traceback

logger = logging.getLogger(__name__)

class MarketReporter:
    """Class for generating market reports and summaries."""
    
    def __init__(
        self,
        top_symbols_manager=None,
        alert_manager=None,
        logger=None
    ):
        """Initialize market reporter.
        
        Args:
            top_symbols_manager: Manager for getting top trading symbols
            alert_manager: Alert manager for sending notifications
            logger: Optional logger instance
        """
        self.top_symbols_manager = top_symbols_manager
        self.alert_manager = alert_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize cache for storing metrics
        self.cache = {}
        
        # Initialize report scheduling
        self.report_times = self._calculate_report_times()
        self.last_report_time = None
        self.report_count = 0
        
        # Load report configuration
        self._load_report_config()
    
    def _load_report_config(self):
        """Load report configuration from environment or defaults."""
        # Default to 4 reports per day at market significant times
        self.report_hours = [0, 8, 16, 20]  # UTC hours
        
        # Throttling: minimum time between reports in seconds
        self.report_throttle = 300  # 5 minutes
        
        # Report customization
        self.report_config = {
            'include_btc_betas': True,
            'include_risk_metrics': True,
            'include_orderbook_analysis': True,
            'include_market_regime': True,
            'include_smart_money': True,
            'include_whale_activity': True,
        }
        
        self.logger.info(f"Market reports scheduled for: {', '.join(t.strftime('%H:%M UTC') for t in self.report_times)}")
    
    def _calculate_report_times(self) -> list:
        """Calculate the daily report times in UTC.
        
        Returns:
            List of datetime.time objects for scheduled reports
        """
        # Calculate report times based on configured hours
        base_time = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Define specific hours for reports (default: 00:00, 08:00, 16:00, 20:00 UTC)
        report_hours = getattr(self, 'report_hours', [0, 8, 16, 20])
        
        report_times = [
            (base_time + timedelta(hours=h)).time()
            for h in report_hours
        ]
        
        return report_times
        
    def is_report_time(self) -> bool:
        """Check if it's time to generate a report.
        
        Returns:
            True if it's time for a report, False otherwise
        """
        # If no previous report, generate one
        if self.last_report_time is None:
            return True
            
        current_time = datetime.now(timezone.utc)
        
        # Check throttling: don't generate reports too frequently
        if self.last_report_time and (current_time - self.last_report_time).total_seconds() < self.report_throttle:
            return False
            
        # Check if current time is within 1 minute of any scheduled report time
        current_time_obj = current_time.time()
        for report_time in self.report_times:
            # Calculate time difference in seconds
            current_seconds = current_time_obj.hour * 3600 + current_time_obj.minute * 60 + current_time_obj.second
            report_seconds = report_time.hour * 3600 + report_time.minute * 60 + report_time.second
            
            # Handle day boundary cases
            if abs(current_seconds - report_seconds) > 43200:  # More than 12 hours difference
                diff = 86400 - max(current_seconds, report_seconds) + min(current_seconds, report_seconds)
            else:
                diff = abs(current_seconds - report_seconds)
                
            if diff < 60:  # Within 1 minute of a scheduled time
                return True
                
        return False
    
    async def generate_market_summary(self) -> Dict[str, Any]:
        """Generate market summary report."""
        
        # Start tracking time for performance monitoring
        start_time = time.time()
        self.logger.info(f"Starting market report generation at {datetime.now()}")
        
        try:
            # Get top traded symbols
            self.logger.info("Getting top traded symbols...")
            top_pairs = await self.top_symbols_manager.get_top_traded_symbols(limit=15)
            
            self.logger.info(f"Found {len(top_pairs)} top traded pairs")
            
            # Run calculations in parallel
            self.logger.info("Running market calculations in parallel...")
            calculation_tasks = [
                self._calculate_market_overview(top_pairs),
                self._calculate_market_regime(top_pairs[:10]),
                self._calculate_btc_futures_premium(),
                self._calculate_smart_money_index(top_pairs[:5]),
                self._calculate_whale_activity(top_pairs[:5]),
                self._calculate_performance_metrics(top_pairs[:15])
            ]
            
            # Execute all calculation tasks in parallel
            overview, market_regime, futures_premium, smart_money, whale_activity, performance_metrics = await asyncio.gather(*calculation_tasks)
            
            # Additional calculations that depend on configuration settings
            additional_tasks = []
            btc_betas = None
            orderbook_analysis = None
            
            # Add BTC betas calculation if enabled
            if self.report_config.get('include_btc_betas', True):
                self.logger.info("Calculating BTC betas...")
                additional_tasks.append(self._calculate_btc_betas(top_pairs[:10]))
            else:
                additional_tasks.append(None)
                
            # Add orderbook analysis if enabled
            if self.report_config.get('include_orderbook_analysis', True):
                self.logger.info("Analyzing orderbooks...")
                additional_tasks.append(self._analyze_all_orderbooks(top_pairs[:10]))
            else:
                additional_tasks.append(None)
            
            # Run additional tasks in parallel if any are enabled
            if additional_tasks:
                btc_betas, orderbook_analysis = await asyncio.gather(*[task for task in additional_tasks if task is not None])
            
            # Format the report
            self.logger.info("Formatting market report...")
            report = await self.format_market_report(
                overview=overview,
                top_pairs=top_pairs,
                market_regime=market_regime,
                futures_premium=futures_premium,
                smart_money=smart_money,
                whale_activity=whale_activity,
                btc_betas=btc_betas,
                orderbook_analysis=orderbook_analysis,
                performance_metrics=performance_metrics
            )
            
            # Update reporting state
            self.last_report_time = datetime.now(timezone.utc)
            self.report_count += 1
            
            # Log performance
            elapsed = time.time() - start_time
            self.logger.info(f"Market report #{self.report_count} generated in {elapsed:.2f} seconds (parallel processing)")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating market summary: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            return None

    async def format_market_report(self, overview: Dict[str, Any], top_pairs: List[str], 
                           market_regime: Dict[str, Any] = None,
                           futures_premium: Dict[str, Any] = None,
                           smart_money: Dict[str, Any] = None,
                           whale_activity: Dict[str, Any] = None,
                           btc_betas: List[Tuple[str, float]] = None,
                           orderbook_analysis: Dict[str, Dict[str, Any]] = None,
                           performance_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format the market report data into a structured report.
        
        This method takes various market data components and formats them into a 
        structured report suitable for display or transmission.
        """
        try:
            # Extract key metrics
            if market_regime is None:
                market_regime = {"regime": "NEUTRAL", "trend_strength": 0.5, "volatility": 0.3}
            
            if smart_money is None:
                smart_money = {"index_value": 50, "status": "NEUTRAL", "institutional_flow": 0}
            
            regime = market_regime.get("regime", "NEUTRAL").replace("_", " ").title()
            trend_strength = market_regime.get("trend_strength", 0.5)
            volatility = market_regime.get("volatility", 0.3)
            
            smart_money_value = smart_money.get("index_value", 50)
            smart_money_status = smart_money.get("status", "NEUTRAL")
            
            # Format progress bars
            trend_bar = self._create_progress_bar(trend_strength * 100, 0, 100, 10)
            volatility_bar = self._create_progress_bar(volatility * 100, 0, 100, 10)
            smart_money_bar = self._create_progress_bar(smart_money_value, 0, 100, 10)
            
            # Format section content
            market_cycle = (
                f"**Regime:** {regime}\n"
                f"**Trend Strength:** {trend_strength * 100:.1f}%\n{trend_bar}\n"
                f"**Volatility:** {volatility * 100:.1f}%\n{volatility_bar}\n"
            )
            
            # Format BTC Futures Premium section
            futures_premium_section = ""
            if futures_premium:
                status = futures_premium.get('status', 'Unknown')
                premium_emoji = "📈" if status == "Contango" else "📉" if status == "Backwardation" else "⚖️"
                
                futures_premium_section = (
                    f"**BTC Futures Premium:** {premium_emoji} {status}\n"
                    f"**Spot Price:** ${futures_premium.get('spot_price', 0):,.2f}\n"
                    f"**Perp Price:** ${futures_premium.get('futures_price', 0):,.2f}\n"
                    f"**Premium:** {futures_premium.get('premium_percent', 0):+.4f}%\n"
                )
                
                if futures_premium.get('quarterly_futures', 0) > 0:
                    futures_premium_section += (
                        f"**Quarterly Price:** ${futures_premium.get('quarterly_futures', 0):,.2f}\n"
                        f"**Quarterly Basis:** {futures_premium.get('basis', 0):+.4f}%\n"
                    )
            
            smart_money_analysis = (
                f"**Smart Money Index:** {smart_money_value:.1f}/100 ({smart_money_status})\n"
                f"{smart_money_bar}\n"
                f"**Institutional Flow:** {smart_money.get('institutional_flow', 0):+.1f}%\n"
            )
            
            # Add accumulation zones if available
            accumulation_zones = smart_money.get('accumulation_zones', {})
            if accumulation_zones:
                zones_list = []
                for symbol, zones in accumulation_zones.items():
                    if zones:
                        # Format price levels with volume
                        formatted_zones = [f"${z['price']:.2f} (${self._format_compact_number(z['volume'])})" for z in zones]
                        zones_list.append(f"{symbol}: {', '.join(formatted_zones[:3])}")
                
                if zones_list:
                    smart_money_analysis += "\n**Key Accumulation Zones:**\n" + "\n".join(zones_list[:3])
                else:
                    smart_money_analysis += "\n**Key Accumulation Zones:** No significant zones detected"
            else:
                smart_money_analysis += "\n**Key Accumulation Zones:** No significant zones detected"
            
            # Format market metrics
            total_volume = overview.get('total_volume', 0)
            total_turnover = overview.get('total_turnover', 0)
            total_open_interest = overview.get('total_open_interest', 0)
            
            volume_wow = overview.get('volume_wow', 0)
            turnover_wow = overview.get('turnover_wow', 0)
            open_interest_wow = overview.get('open_interest_wow', 0)
            
            market_metrics = (
                f"**Total Volume:** {self._format_number(total_volume, prefix='$')} "
                f"({self._format_percentage(volume_wow)} WoW)\n"
                f"**Turnover:** {self._format_number(total_turnover, prefix='$')} "
                f"({self._format_percentage(turnover_wow)} WoW)\n"
                f"**Open Interest:** {self._format_number(total_open_interest, prefix='$')} "
                f"({self._format_percentage(open_interest_wow)} WoW)\n"
            )
            
            # Generate market outlook
            market_outlook = self._generate_market_outlook(market_regime, smart_money, overview)
            
            # Compile the full report
            report = {
                "market_cycle": market_cycle,
                "market_metrics": market_metrics,
                "futures_premium": futures_premium_section,
                "smart_money": smart_money_analysis,
                "market_outlook": market_outlook,
            }
            
            # Add orderbook analysis if available
            if orderbook_analysis:
                report["orderbook_analysis"] = self._format_orderbook_analysis(orderbook_analysis)
            
            # Add BTC betas if available
            if btc_betas:
                report["btc_betas"] = self._format_btc_betas(btc_betas)
            
            # Add whale activity if available
            if whale_activity:
                report["whale_activity"] = self._format_whale_activity(whale_activity)
            
            # Add performance metrics if available
            if performance_metrics:
                report["performance_metrics"] = self._format_performance_metrics(performance_metrics)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error formatting market report: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "market_cycle": "Error: Could not format market cycle data",
                "market_metrics": "Error: Could not format market metrics data",
                "smart_money": "Error: Could not format smart money data",
                "market_outlook": "Error: Could not generate market outlook"
            }

    def _format_number(self, num: float, prefix: str = "") -> str:
        """Format number for display with appropriate suffix based on size."""
        if num is None or math.isnan(num):
            return f"{prefix}0.00"
            
        # Handle negative numbers properly
        sign = "-" if num < 0 else ""
        num = abs(num)
        
        if num >= 1_000_000_000:
            return f"{prefix}{sign}${num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{prefix}{sign}${num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{prefix}{sign}${num / 1_000:.2f}K"
        else:
            return f"{prefix}{sign}${num:.2f}"
    
    async def _extract_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant market data metrics from the provided market data.
        
        Args:
            market_data: Dictionary containing market data information
            
        Returns:
            Dictionary with extracted metrics
        """
        metrics = {
            'last_price': None,
            'high': None,
            'low': None,
            'change_24h': None,
            'change_24h_pct': None,
            'volume': None,
            'turnover': None,
            'open_interest': None
        }
        
        try:
            # Extract price data if available
            price_data = market_data.get('price')
            ticker_data = market_data.get('ticker')
            raw_ticker = market_data.get('raw_ticker', {})
            
            # Log for debugging
            self.logger.debug(f"Extracting market data from: price_data={bool(price_data)}, ticker_data={bool(ticker_data)}, raw_ticker={bool(raw_ticker)}")
            
            # If we have raw_ticker data, use it as primary source
            if raw_ticker:
                # Extract original API response data from raw_data
                raw_data = raw_ticker.get('raw_data', {})
                
                # Extract last price
                if 'last' in raw_ticker:
                    try:
                        metrics['last_price'] = float(raw_ticker['last'])
                    except (ValueError, TypeError):
                        pass
                
                # Extract high and low
                if 'high' in raw_ticker:
                    try:
                        metrics['high'] = float(raw_ticker['high'])
                    except (ValueError, TypeError):
                        pass
                        
                if 'low' in raw_ticker:
                    try:
                        metrics['low'] = float(raw_ticker['low'])
                    except (ValueError, TypeError):
                        pass
                
                # Extract open interest
                if 'open_interest' in raw_ticker:
                    try:
                        metrics['open_interest'] = float(raw_ticker['open_interest'])
                    except (ValueError, TypeError):
                        pass
                
                # Extract volume and turnover
                if 'volume' in raw_ticker:
                    try:
                        metrics['volume'] = float(raw_ticker['volume'])
                        self.logger.debug(f"Extracted volume: {metrics['volume']}")
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error parsing volume: {e}")
                
                if 'turnover' in raw_ticker:
                    try:
                        metrics['turnover'] = float(raw_ticker['turnover'])
                        self.logger.debug(f"Extracted turnover: {metrics['turnover']}")
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error parsing turnover: {e}")
                
                # Extract/calculate 24h absolute change and percentage
                if raw_data and 'price24hPcnt' in raw_data:
                    try:
                        # Convert from decimal to percentage (e.g., -0.020419 to -2.0419%)
                        metrics['change_24h_pct'] = float(raw_data['price24hPcnt']) * 100
                        self.logger.debug(f"Extracted price24hPcnt: {raw_data['price24hPcnt']} → {metrics['change_24h_pct']}%")
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error parsing price24hPcnt: {e}")
                elif 'percentage' in raw_ticker:
                    try:
                        metrics['change_24h_pct'] = float(raw_ticker['percentage'])
                        self.logger.debug(f"Extracted percentage: {metrics['change_24h_pct']}%")
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error parsing percentage: {e}")
                
                # Calculate absolute change
                if raw_data and 'prevPrice24h' in raw_data and 'lastPrice' in raw_data:
                    try:
                        last_price = float(raw_data['lastPrice'])
                        prev_price = float(raw_data['prevPrice24h'])
                        metrics['change_24h'] = last_price - prev_price
                        self.logger.debug(f"Calculated change_24h: {metrics['change_24h']} (last: {last_price}, prev: {prev_price})")
                    except (ValueError, TypeError) as e:
                        self.logger.error(f"Error calculating price change: {e}")
            
            # If we still have missing data, try to get it from price_data or ticker_data
            # Last price
            if metrics['last_price'] is None:
                if price_data and isinstance(price_data, dict) and 'last' in price_data:
                    metrics['last_price'] = price_data['last']
                elif ticker_data and 'last_price' in ticker_data:
                    metrics['last_price'] = ticker_data['last_price']
                elif ticker_data and 'last' in ticker_data:
                    metrics['last_price'] = ticker_data['last']
            
            # High & Low
            if metrics['high'] is None:
                if price_data and isinstance(price_data, dict) and 'high' in price_data:
                    metrics['high'] = price_data['high']
                elif ticker_data and 'high' in ticker_data:
                    metrics['high'] = ticker_data['high']
            
            if metrics['low'] is None:
                if price_data and isinstance(price_data, dict) and 'low' in price_data:
                    metrics['low'] = price_data['low']
                elif ticker_data and 'low' in ticker_data:
                    metrics['low'] = ticker_data['low']
                    
            # Volume & Turnover
            if metrics['volume'] is None:
                if ticker_data and 'volume_24h' in ticker_data:
                    metrics['volume'] = ticker_data['volume_24h']
                elif ticker_data and 'volume' in ticker_data:
                    metrics['volume'] = ticker_data['volume']
                
            if metrics['turnover'] is None and ticker_data and 'turnover' in ticker_data:
                metrics['turnover'] = ticker_data['turnover']
            
            # Sanity check for change percentage - cap at reasonable values
            if metrics['change_24h_pct'] is not None:
                # Cap at ±100% for sanity unless in extreme market conditions
                if abs(metrics['change_24h_pct']) > 100:
                    self.logger.warning(f"Unrealistic 24h change detected: {metrics['change_24h_pct']}%, capping at ±100%")
                    metrics['change_24h_pct'] = 100 if metrics['change_24h_pct'] > 0 else -100
                    
                    # Recalculate absolute change if possible
                    if metrics['last_price'] is not None:
                        prev_price = metrics['last_price'] / (1 + metrics['change_24h_pct'] / 100)
                        metrics['change_24h'] = metrics['last_price'] - prev_price
                        
            # Finally, print the extracted metrics for debugging
            self.logger.debug(f"Extracted metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error extracting market data: {str(e)}")
            self.logger.debug("Extract market data error details:", exc_info=True)
            return metrics
    
    def _deep_search_metrics(self, data, result):
        """Deep search for metrics in nested structures"""
        if not isinstance(data, dict):
            return
        
        # Check each key in the data
        for key, value in data.items():
            # Handle nested dictionaries
            if isinstance(value, dict):
                self._deep_search_metrics(value, result)
                continue
                
            # Skip non-numeric values
            if not isinstance(value, (int, float, str)) or value == '':
                continue
                
            try:
                # Convert to float if it's a string
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                
                # Check for price related fields
                if result['last'] == 0 and any(price_term in key.lower() for price_term in ['price', 'last', 'close', 'current']):
                    if 'mark' not in key.lower() and 'index' not in key.lower():  # Exclude mark and index prices
                        result['last'] = value
                
                # Check for volume related fields
                if result['volume'] == 0 and any(vol_term in key.lower() for vol_term in ['vol', 'amount', 'qty']) and 'quote' not in key.lower():
                    if key.lower() in ['volume', 'volume24h', 'volume_24h']:
                        result['volume'] = value
                
                # Check for turnover related fields
                if result['turnover'] == 0 and any(turn_term in key.lower() for turn_term in ['turnover', 'quotevol', 'quoteamount']):
                    result['turnover'] = value
                
                # Check for high price related fields
                if result['high'] == 0 and any(high_term in key.lower() for high_term in ['high', 'max']):
                    result['high'] = value
                
                # Check for low price related fields
                if result['low'] == 0 and any(low_term in key.lower() for low_term in ['low', 'min']):
                    result['low'] = value
                
                # Check for open interest related fields
                if result['open_interest'] == 0 and any(oi_term in key.lower() for oi_term in ['openinterest', 'open_interest', 'oi']):
                    result['open_interest'] = value
                    self.logger.debug(f"Found open interest via deep search in [{key}]: {value}")
            except (ValueError, TypeError):
                continue

    async def _calculate_market_overview(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate market overview statistics.
        
        This method calculates various market overview statistics based on the
        given top trading pairs, including total volume, turnover, and 
        week-over-week comparisons.
        
        Args:
            top_pairs: List of trading pair symbols to analyze
            
        Returns:
            Dictionary containing market overview statistics
        """
        try:
            # Initialize overview metrics
            total_volume = 0.0
            total_turnover = 0.0
            total_open_interest = 0.0
            symbols_with_data = 0
            
            # Historical data for week-over-week comparison
            week_ago_date = datetime.now() - timedelta(days=7)
            week_ago_timestamp = int(week_ago_date.timestamp() * 1000)  # Convert to milliseconds
            
            historical_volume = await self._get_historical_metric('volume', week_ago_timestamp)
            historical_turnover = await self._get_historical_metric('turnover', week_ago_timestamp)
            historical_open_interest = await self._get_historical_metric('open_interest', week_ago_timestamp)
            
            self.logger.debug(f"Historical metrics: volume={historical_volume}, turnover={historical_turnover}, open_interest={historical_open_interest}")
            
            # Process each symbol to gather metrics
            for symbol in top_pairs:
                try:
                    # Get market data for the symbol
                    market_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not market_data:
                        self.logger.warning(f"No market data available for {symbol}")
                        continue

                    # Extract metrics from market data
                    metrics = await self._extract_market_data(market_data)
                    
                    # Skip if we don't have valid volume data
                    if not metrics.get('volume'):
                        continue

                    # Add to totals
                    total_volume += metrics.get('volume', 0)
                    total_turnover += metrics.get('turnover', 0) if metrics.get('turnover') else 0
                    total_open_interest += metrics.get('open_interest', 0) if metrics.get('open_interest') else 0
                    symbols_with_data += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for market overview: {str(e)}")
                    continue

            # Calculate week-over-week changes
            volume_wow = ((total_volume - historical_volume) / historical_volume * 100) if historical_volume > 0 else 0.0
            turnover_wow = ((total_turnover - historical_turnover) / historical_turnover * 100) if historical_turnover > 0 else 0.0
            open_interest_wow = ((total_open_interest - historical_open_interest) / historical_open_interest * 100) if historical_open_interest > 0 else 0.0
            
            # Set fallback values if calculations result in extreme values
            if abs(volume_wow) > 500:
                self.logger.warning(f"Extreme volume_wow value detected: {volume_wow}%. Using fallback.")
                volume_wow = 10.0 if volume_wow > 0 else -10.0
                
            if abs(turnover_wow) > 500:
                self.logger.warning(f"Extreme turnover_wow value detected: {turnover_wow}%. Using fallback.")
                turnover_wow = 10.0 if turnover_wow > 0 else -10.0
                
            if abs(open_interest_wow) > 500:
                self.logger.warning(f"Extreme open_interest_wow value detected: {open_interest_wow}%. Using fallback.")
                open_interest_wow = 10.0 if open_interest_wow > 0 else -10.0
            
            # Store current metrics for future comparisons
            await self._store_current_metrics(total_volume, total_turnover, total_open_interest)
            
            # Return the calculated overview
            return {
                "total_volume": total_volume,
                "total_turnover": total_turnover,
                "total_open_interest": total_open_interest,
                "volume_wow": volume_wow,
                "turnover_wow": turnover_wow,
                "open_interest_wow": open_interest_wow,
                "symbols_with_data": symbols_with_data
            }

        except Exception as e:
            self.logger.error(f"Error calculating market overview: {str(e)}")
            self.logger.debug("Calculate market overview error details:", exc_info=True)
            return {
                "total_volume": 0.0,
                "total_turnover": 0.0,
                "total_open_interest": 0.0,
                "volume_wow": 0.0,
                "turnover_wow": 0.0,
                "open_interest_wow": 0.0,
                "symbols_with_data": 0
            }
    
    async def _get_historical_metric(self, metric_name: str, timestamp: int) -> float:
        """Get historical metric value from database or cache.
        
        Args:
            metric_name: Name of the metric to retrieve
            timestamp: Timestamp to retrieve metric value for
            
        Returns:
            Historical metric value, or 0.0 if not available
        """
        try:
            # Check if we have a database connection
            if hasattr(self, 'db') and self.db:
                # Query the database for historical metric
                query = f"SELECT value FROM market_metrics WHERE metric_name = %s AND timestamp <= %s ORDER BY timestamp DESC LIMIT 1"
                result = await self.db.fetch_one(query, (metric_name, timestamp))
                if result:
                    return float(result['value'])
            
            # If we don't have a database or no result, try cache
            cache_key = f"historical_{metric_name}_{timestamp}"
            cached_value = self.cache.get(cache_key)
            if cached_value is not None:
                return float(cached_value)
            
            # For simplicity, return a fallback value if no historical data
            # In a real system, you might use a different approach
            if metric_name == 'volume':
                return 5000000000.0  # 5 billion as fallback
            elif metric_name == 'turnover':
                return 10000000000.0  # 10 billion as fallback
            elif metric_name == 'open_interest':
                return 3000000000.0  # 3 billion as fallback
            else:
                return 0.0
            
        except Exception as e:
            self.logger.error(f"Error retrieving historical {metric_name}: {str(e)}")
            return 0.0
    
    async def _store_current_metrics(self, volume: float, turnover: float, open_interest: float) -> None:
        """Store current metrics for future historical comparisons.
        
        Args:
            volume: Total market volume
            turnover: Total market turnover
            open_interest: Total open interest
        """
        try:
            current_timestamp = int(datetime.now().timestamp() * 1000)
            
            # Store in database if available
            if hasattr(self, 'db') and self.db:
                # Insert current metrics into database
                query = "INSERT INTO market_metrics (metric_name, value, timestamp) VALUES (%s, %s, %s)"
                
                # Execute queries to store each metric
                await self.db.execute(query, ('volume', volume, current_timestamp))
                await self.db.execute(query, ('turnover', turnover, current_timestamp))
                await self.db.execute(query, ('open_interest', open_interest, current_timestamp))
            
            # Also cache the current values for future use
            self.cache['current_volume'] = volume
            self.cache['current_turnover'] = turnover
            self.cache['current_open_interest'] = open_interest
            self.cache['metrics_timestamp'] = current_timestamp
            
        except Exception as e:
            self.logger.error(f"Error storing current metrics: {str(e)}")
            # Continue execution even if storage fails

    def _format_risk_metrics(self, risk_metrics: Dict[str, Any]) -> str:
        """Format risk metrics for display."""
        if not risk_metrics:
            return "Risk metrics calculation failed"
            
        lines = []
        
        # High Volatility Pairs
        if risk_metrics.get('volatility'):
            vol_pairs = sorted(
                risk_metrics['volatility'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if vol_pairs:
                lines.append("**High Volatility:**")
                for symbol, vol in vol_pairs:
                    lines.append(f"• {symbol}: {vol:.1f}% 24h")
        
        # Extreme Funding Rates
        if risk_metrics.get('funding_rates'):
            extreme_funding = [
                (s, r) for s, r in risk_metrics['funding_rates'].items()
                if abs(r) > 0.1  # More than 0.1% funding rate
            ]
            if extreme_funding:
                lines.append("\n**Notable Funding Rates:**")
                for symbol, rate in sorted(extreme_funding, key=lambda x: abs(x[1]), reverse=True)[:3]:
                    lines.append(f"• {symbol}: {rate:+.3f}%")
        
        # Large Liquidations
        if risk_metrics.get('liquidations'):
            significant_liqs = []
            for symbol, liq_data in risk_metrics['liquidations'].items():
                total_liqs = liq_data['long_liq'] + liq_data['short_liq']
                if total_liqs > 1000000:  # More than $1M
                    significant_liqs.append((symbol, total_liqs))
            
            if significant_liqs:
                lines.append("\n**Significant Liquidations (24h):**")
                for symbol, amount in sorted(significant_liqs, key=lambda x: x[1], reverse=True)[:3]:
                    lines.append(f"• {symbol}: ${amount/1e6:.1f}M")
        
        # Market Risk Level
        market_volatility = risk_metrics.get('market_volatility', 0)
        risk_level = "🟢 Low" if market_volatility < 50 else "🟡 Medium" if market_volatility < 80 else "🔴 High"
        lines.append(f"\n**Market Risk Level:** {risk_level}")
        
        return "\n".join(lines)

    async def _calculate_market_regime(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate current market regime characteristics.
        
        This method analyzes price trends, volatility, and correlation
        to determine the current market regime.
        """
        try:
            # Initialize regime metrics
            volatility_readings = []
            volume_change = []
            price_trends = []
            correlation_values = []
            price_strengths = []
            
            # Get BTC data as reference
            btc_data = await self.top_symbols_manager.get_market_data("BTC/USDT")
            btc_ohlcv = None
            if btc_data and 'ohlcv' in btc_data:
                btc_ohlcv = btc_data['ohlcv'].get('base', {}).get('data')
            
            # Analyze data across top pairs
            for symbol in top_pairs:
                try:
                    # Extract market data metrics
                    market_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Get price change data
                    metrics = await self._extract_market_data(market_data)
                    
                    # Skip if key metrics are missing
                    if metrics.get('last_price') is None:
                        self.logger.warning(f"Missing last price for {symbol}, skipping")
                        continue
                    
                    change_24h_pct = metrics.get('change_24h_pct')
                    if change_24h_pct is None:
                        self.logger.warning(f"Missing 24h change percentage for {symbol}, using 0")
                        change_24h_pct = 0
                    
                    # Determine price trend (positive/negative)
                    price_trends.append(1 if change_24h_pct > 0 else -1)
                    price_strengths.append(abs(change_24h_pct))
                    
                    # Get OHLCV data if available
                    ohlcv = None
                    if 'ohlcv' in market_data:
                        ohlcv = market_data['ohlcv'].get('base', {}).get('data')
                    
                    if isinstance(ohlcv, pd.DataFrame) and not ohlcv.empty and len(ohlcv) >= 14:
                        # Calculate volatility (ATR as % of price)
                        high_low = ohlcv['high'] - ohlcv['low']
                        high_close = abs(ohlcv['high'] - ohlcv['close'].shift(1))
                        low_close = abs(ohlcv['low'] - ohlcv['close'].shift(1))
                        ranges = pd.concat([high_low, high_close, low_close], axis=1)
                        true_range = ranges.max(axis=1)
                        atr = true_range.rolling(14).mean().iloc[-1]
                        current_price = ohlcv['close'].iloc[-1]
                        volatility_readings.append(atr / current_price * 100)
                    
                        # Calculate volume change
                        if len(ohlcv) >= 7:
                            recent_vol = ohlcv['volume'].iloc[-7:].mean()
                            prev_vol = ohlcv['volume'].iloc[-14:-7].mean()
                            if prev_vol > 0:
                                vol_change_pct = ((recent_vol - prev_vol) / prev_vol) * 100
                                volume_change.append(vol_change_pct)
                    
                        # Calculate correlation with BTC if both datasets available
                        if isinstance(btc_ohlcv, pd.DataFrame) and not btc_ohlcv.empty and len(btc_ohlcv) >= 14:
                            # Ensure same length for correlation calculation
                            min_len = min(len(ohlcv), len(btc_ohlcv))
                            if min_len >= 14:
                                btc_returns = btc_ohlcv['close'].iloc[-min_len:].pct_change().dropna()
                                pair_returns = ohlcv['close'].iloc[-min_len:].pct_change().dropna()
                                
                                if len(btc_returns) == len(pair_returns) and len(btc_returns) >= 5:
                                    corr = btc_returns.corr(pair_returns)
                                    if not np.isnan(corr):
                                        correlation_values.append(corr)
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for market regime: {str(e)}")
                    continue
            
            # If we don't have enough data, use defaults
            if len(price_trends) == 0:
                self.logger.warning("No valid price trends found for market regime calculation, using defaults")
                return {
                    "regime": "NEUTRAL",
                    "trend_regime": "SIDEWAYS",
                    "volatility_regime": "MODERATE",
                    "correlation_regime": "MODERATE",
                    "trend_strength": 0.5,
                    "volatility": 0.3,
                    "avg_correlation": 0.5
                }
            
            # Calculate average metrics
            avg_volatility = sum(volatility_readings) / max(len(volatility_readings), 1) if volatility_readings else 2.5
            avg_volume_change = sum(volume_change) / max(len(volume_change), 1) if volume_change else 0
            avg_correlation = sum(correlation_values) / max(len(correlation_values), 1) if correlation_values else 0.5
            
            # Calculate trend bias (-1 to 1 scale)
            trend_bias = sum(price_trends) / max(len(price_trends), 1)
            
            # Calculate average price strength
            avg_price_strength = sum(price_strengths) / max(len(price_strengths), 1) if price_strengths else 1.5
            
            # Log metrics for debugging
            self.logger.debug(f"Market regime metrics: volatility={avg_volatility:.2f}, trend_bias={trend_bias:.2f}, price_strength={avg_price_strength:.2f}")
            
            # Determine market regime components
            
            # Volatility regime
            if avg_volatility > 4:
                volatility_regime = "HIGH"
            elif avg_volatility > 2:
                volatility_regime = "MODERATE"
            else:
                volatility_regime = "LOW"
                
            # Trend regime
            if trend_bias > 0.5 and avg_price_strength > 3:
                trend_regime = "STRONG_BULLISH"
            elif trend_bias > 0.2:
                trend_regime = "BULLISH"
            elif trend_bias < -0.5 and avg_price_strength > 3:
                trend_regime = "STRONG_BEARISH"
            elif trend_bias < -0.2:
                trend_regime = "BEARISH"
            else:
                trend_regime = "SIDEWAYS"
                
            # Correlation regime
            if avg_correlation > 0.7:
                correlation_regime = "HIGH"
            elif avg_correlation > 0.4:
                correlation_regime = "MODERATE"
            else:
                correlation_regime = "LOW"
            
            # Determine overall market regime
            if trend_regime in ("STRONG_BULLISH", "BULLISH") and volatility_regime == "HIGH":
                regime = "BULLISH_TRENDING"
            elif trend_regime in ("STRONG_BULLISH", "BULLISH") and volatility_regime != "HIGH":
                regime = "BULLISH_SIDEWAYS"
            elif trend_regime in ("STRONG_BEARISH", "BEARISH") and volatility_regime == "HIGH":
                regime = "BEARISH_TRENDING"
            elif trend_regime in ("STRONG_BEARISH", "BEARISH") and volatility_regime != "HIGH":
                regime = "BEARISH_SIDEWAYS"
            elif trend_regime == "SIDEWAYS" and trend_bias >= 0:
                regime = "ACCUMULATION"
            elif trend_regime == "SIDEWAYS" and trend_bias < 0:
                regime = "DISTRIBUTION"
            else:
                regime = "NEUTRAL"
                
            # Calculate normalized trend strength (0-1)
            trend_strength = (abs(trend_bias) * (1 + avg_price_strength / 10)) / 2
            trend_strength = min(max(trend_strength, 0.1), 0.95)  # Ensure minimum value is 0.1
            
            # Calculate normalized volatility (0-1)
            volatility = min(avg_volatility / 8, 0.95)
            # Ensure volatility is never zero or extremely low
            volatility = max(volatility, 0.1)
            
            self.logger.debug(f"Calculated market regime: {regime}, trend_strength={trend_strength:.2f}, volatility={volatility:.2f}")
            
            return {
                "regime": regime,
                "trend_regime": trend_regime,
                "volatility_regime": volatility_regime,
                "correlation_regime": correlation_regime,
                "trend_strength": trend_strength,
                "volatility": volatility,
                "avg_correlation": avg_correlation
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating market regime: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "regime": "NEUTRAL",
                "trend_regime": "SIDEWAYS",
                "volatility_regime": "MODERATE",
                "correlation_regime": "MODERATE",
                "trend_strength": 0.5,
                "volatility": 0.3,  # Default non-zero volatility
                "avg_correlation": 0.5
            }

    async def _calculate_smart_money_index(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate smart money index based on market data analysis.
        
        This method analyzes various market data points to calculate a smart money index,
        which provides insights into institutional trading activity.
        
        Args:
            top_pairs: List of trading pair symbols to analyze
            
        Returns:
            Dictionary containing smart money index data
        """
        try:
            # Initialize smart money data with default values
            smart_money_data = {
                "index_value": 50.0,  # Neutral default
                "institutional_flow": 0.0,  # Neutral default
                "accumulation_zones": {},
                "first_vs_last_hour": 0.0,
                "status": "NEUTRAL"
            }
            
            # Collect market data for analysis
            market_data_list = []
            orderbook_bids_list = []
            
            # Process each symbol to gather metrics
            for symbol in top_pairs:
                try:
                    # Get market data for the symbol
                    data = await self.top_symbols_manager.get_market_data(symbol)
                    if not data:
                        continue
                    
                    # Extract metrics from market data
                    extracted = await self._extract_market_data(data)
                    
                    # Skip if we don't have valid price change data
                    if extracted.get('change_24h_pct') is None:
                        continue
                    
                    market_data_list.append({
                        'symbol': symbol,
                        'change_24h_pct': extracted.get('change_24h_pct', 0),
                        'volume': extracted.get('volume', 0),
                        'open_interest': extracted.get('open_interest', 0)
                    })
                    
                    # Collect orderbook data for later analysis if available
                    if 'orderbook' in data and isinstance(data['orderbook'], dict):
                        orderbook = data['orderbook']
                        if 'bids' in orderbook and isinstance(orderbook['bids'], list):
                            orderbook_bids_list.append({
                                'symbol': symbol,
                                'bids': orderbook['bids']
                            })
                    
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for smart money index: {str(e)}")
                    continue
            
            # If we have enough data, calculate index
            if len(market_data_list) > 0:
                # Calculate percentage of positive changes
                positive_changes = sum(1 for data in market_data_list if data['change_24h_pct'] > 0)
                percent_positive = (positive_changes / len(market_data_list)) * 100
                
                # Update index value (scale from 0-100 where 50 is neutral)
                smart_money_data['index_value'] = 40 + (percent_positive / 5)  # Range: 40-60 based on % positive
                
                # Calculate institutional flow (-25 to +25 range centered at 0)
                smart_money_data['institutional_flow'] = percent_positive - 50
                
                # Analyze BTC data specifically if available (as proxy for market)
                btc_data = next((data for data in market_data_list if data['symbol'].startswith('BTC')), None)
                if btc_data:
                    # Adjust index based on BTC metrics
                    if btc_data['change_24h_pct'] > 3:
                        smart_money_data['index_value'] += 5  # Strong BTC bullish sentiment
                    elif btc_data['change_24h_pct'] < -3:
                        smart_money_data['index_value'] -= 5  # Strong BTC bearish sentiment
                
                # Analyze trades for large buyer/seller influence
                try:
                    # Get trade data for a top pair (BTC preferred)
                    btc_market_data = await self.top_symbols_manager.get_market_data('BTC/USDT')
                    if btc_market_data and 'trades' in btc_market_data:
                        trades = btc_market_data['trades']
                        if isinstance(trades, list) and len(trades) > 0:
                            # Calculate buy vs sell pressure from large trades
                            large_buys = sum(trade['amount'] for trade in trades if trade.get('side') == 'buy' and trade.get('amount', 0) > 1.0)
                            large_sells = sum(trade['amount'] for trade in trades if trade.get('side') == 'sell' and trade.get('amount', 0) > 1.0)
                            
                            if large_buys + large_sells > 0:
                                # Calculate buy ratio and adjust index
                                buy_ratio = large_buys / (large_buys + large_sells)
                                if buy_ratio > 0.6:  # Strong buying
                                    smart_money_data['index_value'] += (buy_ratio - 0.5) * 20
                                elif buy_ratio < 0.4:  # Strong selling
                                    smart_money_data['index_value'] -= (0.5 - buy_ratio) * 20
                except Exception as e:
                    self.logger.warning(f"Error analyzing trade data: {str(e)}")
                
                # Analyze orderbook bid/ask imbalances
                try:
                    btc_orderbook = next((ob for ob in orderbook_bids_list if ob['symbol'].startswith('BTC')), None)
                    if btc_orderbook and 'bids' in btc_orderbook:
                        # Identify accumulation zones
                        bid_clusters = self._find_orderbook_clusters(btc_orderbook['bids'])
                        if bid_clusters:
                            # Store significant bid clusters as accumulation zones
                            smart_money_data['accumulation_zones']['BTC/USDT'] = bid_clusters[:3]  # Top 3 clusters
                            
                            # Adjust index based on bid strength
                            total_bid_volume = sum(cluster['volume'] for cluster in bid_clusters)
                            if total_bid_volume > 1000000:  # Significant bid support
                                smart_money_data['index_value'] += 5
                except Exception as e:
                    self.logger.warning(f"Error analyzing orderbook: {str(e)}")
            
            # Ensure index value is within bounds
            smart_money_data['index_value'] = max(0, min(100, smart_money_data['index_value']))
            
            # Determine status based on index value
            if smart_money_data['index_value'] >= 70:
                smart_money_data['status'] = "STRONGLY_BULLISH"
            elif smart_money_data['index_value'] >= 60:
                smart_money_data['status'] = "BULLISH"
            elif smart_money_data['index_value'] <= 30:
                smart_money_data['status'] = "STRONGLY_BEARISH"
            elif smart_money_data['index_value'] <= 40:
                smart_money_data['status'] = "BEARISH"
            else:
                smart_money_data['status'] = "NEUTRAL"
            
            return smart_money_data
            
        except Exception as e:
            self.logger.error(f"Error calculating smart money index: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "index_value": 50.0,
                "institutional_flow": 0.0,
                "accumulation_zones": {},
                "status": "NEUTRAL"
            }

    async def _calculate_whale_activity(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate whale activity metrics based on trade data and order book.
        
        This method analyzes large trades and order book data to identify
        potential whale activity in the market, including accumulation and 
        distribution patterns.
        
        Args:
            top_pairs: List of trading pair symbols to analyze
            
        Returns:
            Dictionary containing whale activity metrics
        """
        try:
            # Initialize activity structure
            whale_activity = {
                "large_trades": {},
                "buy_sell_ratio": {},
                "significant_movements": []
            }
            
            # Define whale transaction thresholds by symbol
            thresholds = {
                "BTC/USDT": 1000000,  # $1M+ for BTC
                "ETH/USDT": 500000,   # $500K+ for ETH
                "default": 100000    # $100K+ for other coins
            }
            
            # Process each top trading pair
            for symbol in top_pairs:
                data = await self.top_symbols_manager.get_market_data(symbol)
                if not data:
                    continue
                    
                # Get threshold for this symbol
                threshold = thresholds.get(symbol, thresholds["default"])
                
                # Analyze trades
                trades = data.get('trades', [])
                if trades:
                    # Find whale transactions
                    whale_trades = []
                    try:
                        whale_trades = [t for t in trades if float(t.get('amount', 0)) * float(t.get('price', 0)) >= threshold]
                    except (ValueError, TypeError):
                        self.logger.warning(f"Error processing trades for {symbol}")
                        continue
                        
                    if whale_trades:
                        # Calculate total volume
                        total_volume = sum(float(t.get('amount', 0)) * float(t.get('price', 0)) for t in whale_trades)
                        
                        # Calculate buy vs sell ratio
                        buy_volume = sum(float(t.get('amount', 0)) * float(t.get('price', 0)) for t in whale_trades if t.get('side') == 'buy')
                        sell_volume = sum(float(t.get('amount', 0)) * float(t.get('price', 0)) for t in whale_trades if t.get('side') == 'sell')
                        
                        # Store data in large_trades format
                        whale_activity["large_trades"][symbol] = {
                            "buy_volume": buy_volume,
                            "sell_volume": sell_volume,
                            "total_volume": total_volume
                        }
                        
                        # Calculate buy/sell ratio
                        if sell_volume > 0:
                            buy_sell_ratio = buy_volume / sell_volume
                            whale_activity["buy_sell_ratio"][symbol] = buy_sell_ratio
                        
                        # Determine if this is a significant movement
                        if total_volume >= threshold * 5:
                            # Get price change data if available
                            metrics = await self._extract_market_data(data)
                            change_pct = metrics.get('change_24h_pct', 0)
                            
                            # Add to significant movements if meaningful change
                            if abs(change_pct) >= 2:
                                whale_activity["significant_movements"].append({
                                    "symbol": symbol,
                                    "change_pct": change_pct,
                                    "volume": total_volume,
                                    "time_period": "24h"
                                })
                
                # Analyze order book for large orders
                orderbook = data.get('orderbook', {})
                if orderbook:
                    bids = orderbook.get('bids', [])
                    asks = orderbook.get('asks', [])
                    
                    try:
                        # Check for large bid clusters (potential whale accumulation zones)
                        if bids:
                            bid_clusters = self._find_orderbook_clusters(bids)
                            if bid_clusters and len(bid_clusters) > 0:
                                largest_cluster = bid_clusters[0]  # First is largest
                                
                                if largest_cluster['volume'] >= threshold * 3:
                                    # Check if this symbol is already in significant movements
                                    if not any(m['symbol'] == symbol for m in whale_activity["significant_movements"]):
                                        whale_activity["significant_movements"].append({
                                            "symbol": symbol,
                                            "change_pct": 0,  # No change yet, potential future move
                                            "volume": largest_cluster['volume'],
                                            "time_period": "orderbook"
                                        })
                    except Exception as e:
                        self.logger.warning(f"Error analyzing order book clusters for {symbol}: {str(e)}")
            
            return whale_activity
            
        except Exception as e:
            self.logger.error(f"Error calculating whale activity: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "large_trades": {},
                "buy_sell_ratio": {},
                "significant_movements": []
            } 

    def _validate_report_data(self, webhook_message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the report contains real data before sending.
        
        Returns a dict with:
            - score: 0-100 quality score
            - issues: list of identified issues
        """
        score = 100
        issues = []
        
        # Check if we have embeds
        embeds = webhook_message.get('embeds', [])
        if not embeds:
            return {'score': 0, 'issues': ['No embeds found in webhook message']}
        
        # Track what sections we've found
        found_sections = {
            'market_metrics': False,
            'performance': False,
            'risk_metrics': False,
            'smart_money': False,
            'whale_activity': False
        }
        
        # Check for placeholder values in market metrics
        for embed in embeds:
            embed_title = embed.get('title', '')
            
            # Check market metrics section
            if "MARKET METRICS" in embed_title:
                found_sections['market_metrics'] = True
                
                for field in embed.get('fields', []):
                    field_name = field.get('name', '')
                    field_value = field.get('value', '')
                    
                    # Check turnover
                    if "Turnover" in field_name:
                        if "$10.00B" in field_value:
                            score -= 20
                            issues.append("Turnover shows placeholder value ($10.00B)")
                        elif "$0.00" in field_value:
                            score -= 15
                            issues.append("Turnover shows zero value")
                    
                    # Check open interest
                    if "Open Interest" in field_name:
                        if "$5.00B" in field_value:
                            score -= 20
                            issues.append("Open Interest shows placeholder value ($5.00B)")
                        elif "$0.00" in field_value:
                            score -= 15
                            issues.append("Open Interest shows zero value")
            
            # Check performance section
            elif "MARKET PERFORMANCE" in embed_title:
                found_sections['performance'] = True
                
                # Check if we have winners and losers
                winners_found = False
                losers_found = False
                zero_volume_count = 0
                
                for field in embed.get('fields', []):
                    field_name = field.get('name', '')
                    field_value = field.get('value', '')
                    
                    if "WINNERS" in field_name:
                        winners_found = True
                        if field_value.strip() == "":
                            score -= 10
                            issues.append("No winners listed in performance section")
                    
                    if "LOSERS" in field_name:
                        losers_found = True
                        if field_value.strip() == "":
                            score -= 10
                            issues.append("No losers listed in performance section")
                    
                    # Check for zero volume/OI in assets
                    if "Vol: $0.00" in field_value:
                        zero_volume_count += 1
                
                if zero_volume_count > 3:
                    score -= 15
                    issues.append(f"Found {zero_volume_count} assets with $0.00 volume")
                
                if not winners_found and not losers_found:
                    score -= 20
                    issues.append("Performance section missing winners and losers")
            
            # Check risk metrics
            elif "RISK METRICS" in embed_title:
                found_sections['risk_metrics'] = True
                
                for field in embed.get('fields', []):
                    field_name = field.get('name', '')
                    field_value = field.get('value', '')
                    
                    # Check volatility
                    if "Volatility" in field_name and "0.00" in field_value:
                        score -= 5
                        issues.append("Volatility shows zero value")
            
            # Check smart money section
            elif "SMART MONEY" in embed_title:
                found_sections['smart_money'] = True
                
                # Check if we have order book imbalance data
                has_imbalance_data = False
                for field in embed.get('fields', []):
                    if "Imbalance" in field.get('name', ''):
                        has_imbalance_data = True
                        break
                
                if not has_imbalance_data:
                    score -= 5
                    issues.append("Smart money section missing order book imbalance data")
            
            # Check whale activity
            elif "WHALE ACTIVITY" in embed_title:
                found_sections['whale_activity'] = True
        
        # Check for missing sections
        for section, found in found_sections.items():
            if not found:
                score -= 10
                issues.append(f"Missing {section.replace('_', ' ')} section")
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        self.logger.info(f"Report validation score: {score}/100")
        if issues:
            self.logger.warning(f"Report validation issues: {', '.join(issues)}")
        
        return {
            'score': score,
            'issues': issues
            } 

    async def _analyze_orderbook(self, symbol: str, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze orderbook data to detect market microstructure patterns.
        
        This analysis looks for:
        - Bid/ask imbalances (buying or selling pressure)
        - Large orders/walls that might prevent price movement
        - Book depth analysis (thin vs. thick books)
        - Potential stop hunting zones
        - Hidden liquidity patterns
        
        Args:
            symbol: Trading pair symbol
            orderbook_data: Dictionary containing orderbook data
            
        Returns:
            Dictionary with orderbook analysis results
        """
        try:
            if not orderbook_data:
                return {}
                
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            if not bids or not asks:
                self.logger.warning(f"Incomplete orderbook for {symbol}: missing bids or asks")
                return {}
                
            # Convert to float values if they're strings
            try:
                bids = [[float(price), float(amount)] for price, amount in bids]
                asks = [[float(price), float(amount)] for price, amount in asks]
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid orderbook format for {symbol}")
                return {}
                
            # Get best bid and ask
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            
            if best_bid == 0 or best_ask == 0:
                self.logger.warning(f"Invalid bid/ask for {symbol}: {best_bid}/{best_ask}")
                return {}
                
            # Calculate mid price
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate spread
            spread = (best_ask - best_bid) / mid_price * 100  # Spread as percentage
            
            # Calculate liquidity within 0.5% of mid price
            bid_liquidity = sum(amt for price, amt in bids if price > mid_price * 0.995)
            ask_liquidity = sum(amt for price, amt in asks if price < mid_price * 1.005)
            
            # Calculate overall book depth (sum of bid and ask quantities within 1%)
            total_bid_depth = sum(amt for price, amt in bids if price > mid_price * 0.99)
            total_ask_depth = sum(amt for price, amt in asks if price < mid_price * 1.01)
            
            # Calculate imbalance
            if bid_liquidity + ask_liquidity > 0:
                imbalance = (bid_liquidity - ask_liquidity) / (bid_liquidity + ask_liquidity)
            else:
                imbalance = 0
                
            # Identify large orders (walls) that are 5x the average order size
            bid_sizes = [amt for _, amt in bids[:20]]
            ask_sizes = [amt for _, amt in asks[:20]]
            
            avg_bid_size = sum(bid_sizes) / len(bid_sizes) if bid_sizes else 0
            avg_ask_size = sum(ask_sizes) / len(ask_sizes) if ask_sizes else 0
            
            bid_walls = [(price, amt) for price, amt in bids[:20] if amt > avg_bid_size * 5]
            ask_walls = [(price, amt) for price, amt in asks[:20] if amt > avg_ask_size * 5]
            
            # Identify potential stop clusters (significant drops in liquidity)
            bid_clusters = []
            for i in range(1, min(len(bids), 20)):
                if i < len(bids) - 1:
                    if bids[i][1] < bids[i-1][1] * 0.3 and bids[i][1] < bids[i+1][1] * 0.3:
                        bid_clusters.append(bids[i][0])
                        
            ask_clusters = []
            for i in range(1, min(len(asks), 20)):
                if i < len(asks) - 1:
                    if asks[i][1] < asks[i-1][1] * 0.3 and asks[i][1] < asks[i+1][1] * 0.3:
                        ask_clusters.append(asks[i][0])
            
            # Determine market pressure
            if imbalance > 0.2:
                pressure = "BUYING"
                pressure_strength = min(abs(imbalance) * 5, 1.0)  # Scale from 0 to 1
            elif imbalance < -0.2:
                pressure = "SELLING"
                pressure_strength = min(abs(imbalance) * 5, 1.0)  # Scale from 0 to 1
            else:
                pressure = "NEUTRAL"
                pressure_strength = 0.0
                
            # Calculate book health metric (based on liquidity and spread)
            book_health = 1.0
            if spread > 0.1:  # Spread > 0.1% reduces health
                book_health -= min(spread / 2, 0.5)
                
            if total_bid_depth + total_ask_depth < mid_price * 0.01:  # Low depth reduces health
                book_health -= 0.3
                
            # Bound health between 0 and 1
            book_health = max(min(book_health, 1.0), 0.0)
            
            # Return comprehensive analysis
            return {
                'symbol': symbol,
                'mid_price': mid_price,
                'spread': spread,
                'bid_liquidity': bid_liquidity,
                'ask_liquidity': ask_liquidity,
                'total_bid_depth': total_bid_depth,
                'total_ask_depth': total_ask_depth,
                'imbalance': imbalance,
                'pressure': pressure,
                'pressure_strength': pressure_strength,
                'bid_walls': bid_walls,
                'ask_walls': ask_walls,
                'bid_clusters': bid_clusters,
                'ask_clusters': ask_clusters,
                'book_health': book_health,
                'health_category': 'HIGH' if book_health > 0.8 else 'MEDIUM' if book_health > 0.5 else 'LOW',
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing orderbook for {symbol}: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {}
            
    async def _analyze_all_orderbooks(self, top_pairs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Analyze orderbooks for all top pairs.
        
        Args:
            top_pairs: List of trading pairs to analyze
            
        Returns:
            Dictionary mapping symbols to their orderbook analysis
        """
        all_analyses = {}
        
        for symbol in top_pairs:
            try:
                # Fetch market data for the symbol
                market_data = await self.top_symbols_manager.get_market_data(symbol)
                if not market_data or 'orderbook' not in market_data:
                    continue
                    
                # Get orderbook data
                orderbook = market_data.get('orderbook', {})
                
                # Analyze the orderbook
                analysis = await self._analyze_orderbook(symbol, orderbook)
                
                if analysis:
                    all_analyses[symbol] = analysis
                    
            except Exception as e:
                self.logger.error(f"Error analyzing orderbook for {symbol}: {str(e)}")
                
        return all_analyses
        
    def _format_orderbook_analysis(self, analyses: Dict[str, Dict[str, Any]]) -> str:
        """Format orderbook analysis for display in reports.
        
        Args:
            analyses: Dictionary of orderbook analyses by symbol
            
        Returns:
            Formatted string for display
        """
        if not analyses:
            return "No orderbook data available for analysis"
            
        # Sort by pressure strength to show most notable imbalances first
        sorted_analyses = sorted(
            analyses.items(),
            key=lambda x: abs(x[1].get('pressure_strength', 0)),
            reverse=True
        )
        
        lines = []
        
        for symbol, analysis in sorted_analyses[:5]:  # Show top 5 most interesting orderbooks
            pressure = analysis.get('pressure', 'NEUTRAL')
            strength = analysis.get('pressure_strength', 0) * 100
            
            # Add emoji based on pressure
            if pressure == "BUYING":
                emoji = "📈"
            elif pressure == "SELLING":
                emoji = "📉"
            else:
                emoji = "➖"
                
            imbalance = analysis.get('imbalance', 0) * 100
            bid_walls = analysis.get('bid_walls', [])
            ask_walls = analysis.get('ask_walls', [])
            
            wall_text = ""
            if bid_walls:
                wall_text += f" Bid walls: {len(bid_walls)}"
            if ask_walls:
                wall_text += f" Ask walls: {len(ask_walls)}"
                
            lines.append(
                f"{emoji} **{symbol}**: {pressure} pressure ({abs(imbalance):.1f}%){wall_text}"
            )
            
        return "\n".join(lines)

    async def run_scheduled_reports(self) -> None:
        """Run scheduled reports according to configured times.
        
        This method continuously checks if it's time to generate a report based on
        the configured schedule. It will run in a loop until stopped.
        """
        self.logger.info("Starting scheduled market report service")
        self.logger.info(f"Configured report times: {[t.strftime('%H:%M UTC') for t in self.report_times]}")
        self.logger.info(f"Report throttle period: {self.report_throttle} seconds")
        
        try:
            # Generate an initial report on startup
            self.logger.info("Generating initial market report on startup")
            report = await self.generate_market_summary()
            
            if report:
                if self.alert_manager:
                    self.logger.info(f"Alert manager available, handlers: {self.alert_manager.handlers if hasattr(self.alert_manager, 'handlers') else 'unknown'}")
                    # Send via webhook if possible
                    if hasattr(self.alert_manager, 'send_discord_webhook_message'):
                        self.logger.info("Sending initial report via Discord webhook")
                        # Format the report for Discord webhook
                        discord_report = self._format_discord_webhook(report)
                        await self.alert_manager.send_discord_webhook_message(discord_report)
                        self.logger.info("Discord webhook message sent successfully")
                    else:
                        # Fall back to regular alert
                        self.logger.info("Discord webhook not available, falling back to regular alert")
                        await self.alert_manager.send_alert(
                            level='INFO',
                            message='Market Summary Report',
                            details={
                                'type': 'market_summary',
                                'webhook_message': report,
                                'timestamp': int(time.time() * 1000)
                            }
                        )
                        self.logger.info("Regular alert sent successfully")
                    self.logger.info("Initial market report generated successfully")
                else:
                    self.logger.warning("Alert manager not available - report generated but not sent")
                    self.logger.debug(f"Report data: {json.dumps(report)[:500]}...")
        except Exception as e:
            self.logger.error(f"Error generating initial report: {str(e)}")
            self.logger.error("Stack trace:", exc_info=True)
            
        # Main scheduling loop
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                # Log the current time and the next check in a human-readable format
                self.logger.debug(f"Scheduler check at {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                if self.last_report_time:
                    time_since_last = (current_time - self.last_report_time).total_seconds()
                    self.logger.debug(f"Time since last report: {time_since_last:.2f} seconds")
                    
                # Check if it's time to generate a report
                report_time_check = self.is_report_time()
                self.logger.debug(f"is_report_time() returned: {report_time_check}")
                
                if report_time_check:
                    self.logger.info(f"Scheduled report time reached - generating market report at {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    report = await self.generate_market_summary()
                    
                    if report:
                        if self.alert_manager:
                            self.logger.info(f"Alert manager available for scheduled report, handlers: {self.alert_manager.handlers if hasattr(self.alert_manager, 'handlers') else 'unknown'}")
                            # Send via webhook if possible
                            if hasattr(self.alert_manager, 'send_discord_webhook_message'):
                                self.logger.info("Sending scheduled report via Discord webhook")
                                # Format the report for Discord webhook
                                discord_report = self._format_discord_webhook(report)
                                await self.alert_manager.send_discord_webhook_message(discord_report)
                                self.logger.info("Discord webhook message sent successfully for scheduled report")
                            else:
                                # Fall back to regular alert
                                self.logger.info("Discord webhook not available for scheduled report, falling back to regular alert")
                                await self.alert_manager.send_alert(
                                    level='INFO',
                                    message='Market Summary Report',
                                    details={
                                        'type': 'market_summary',
                                        'webhook_message': report,
                                        'timestamp': int(time.time() * 1000)
                                    }
                                )
                                self.logger.info("Regular alert sent successfully for scheduled report")
                            self.logger.info(f"Scheduled report #{self.report_count} sent successfully")
                        else:
                            self.logger.warning("Alert manager not available - scheduled report generated but not sent")
                            self.logger.debug(f"Report data: {json.dumps(report)[:500]}...")
                else:
                    # Log why report time check failed if we have a last report time
                    if self.last_report_time:
                        time_diff = (current_time - self.last_report_time).total_seconds()
                        if time_diff < self.report_throttle:
                            self.logger.debug(f"Not generating report - throttle period ({self.report_throttle}s) not elapsed. Current: {time_diff:.2f}s")
                        else:
                            # Check if we're close to any report times
                            closest_time_diff = float('inf')
                            closest_report_time = None
                            for report_time in self.report_times:
                                # Calculate time difference in seconds
                                current_time_obj = current_time.time()
                                current_seconds = current_time_obj.hour * 3600 + current_time_obj.minute * 60 + current_time_obj.second
                                report_seconds = report_time.hour * 3600 + report_time.minute * 60 + report_time.second
                                
                                # Handle day boundary cases
                                if abs(current_seconds - report_seconds) > 43200:  # More than 12 hours difference
                                    diff = 86400 - max(current_seconds, report_seconds) + min(current_seconds, report_seconds)
                                else:
                                    diff = abs(current_seconds - report_seconds)
                                
                                if diff < closest_time_diff:
                                    closest_time_diff = diff
                                    closest_report_time = report_time
                            
                            self.logger.debug(f"Not report time. Closest time: {closest_report_time.strftime('%H:%M UTC')}, difference: {closest_time_diff:.2f} seconds")
                
                # Sleep for a shorter interval to check schedule more frequently
                self.logger.debug(f"Scheduler sleeping for 60 seconds until next check")
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                self.logger.info("Scheduled report service cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in scheduled report service: {str(e)}")
                self.logger.error("Stack trace:", exc_info=True)
                await asyncio.sleep(300)  # Sleep longer on error to avoid spam
                
        self.logger.info("Scheduled report service stopped")

    async def _fetch_market_data_direct(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch market data directly from exchange as a fallback when top symbols manager fails.
        """
        try:
            logger.debug(f"Fetching market data directly for {symbol}")
            
            # Use existing exchange_manager or create a new one with ConfigManager
            if hasattr(self, 'exchange_manager') and self.exchange_manager:
                exchange_manager = self.exchange_manager
            else:
                config_manager = ConfigManager()
                exchange_manager = ExchangeManager(config_manager)
                # Initialize the exchange manager if needed
                if not hasattr(exchange_manager, 'initialized') or not exchange_manager.initialized:
                    await exchange_manager.initialize()
            
            # Get primary exchange
            exchange = await exchange_manager.get_primary_exchange()
            if not exchange:
                logger.warning(f"Failed to get exchange for direct market data fetching for {symbol}")
                return None
            
            # Attempt to get ticker data with retries
            max_attempts = 3
            ticker_data = None
            for attempt in range(1, max_attempts + 1):
                try:
                    ticker_data = await exchange.fetch_ticker(symbol)
                    if ticker_data:
                        logger.debug(f"Successfully fetched ticker data for {symbol} - attempt {attempt}")
                        break
                except Exception as e:
                    logger.warning(f"Error fetching ticker for {symbol} (attempt {attempt}/{max_attempts}): {e}")
                    if attempt == max_attempts:
                        logger.error(f"Failed to fetch ticker for {symbol} after {max_attempts} attempts")
                        return None
                    await asyncio.sleep(1)  # Small delay before retry
            
            if not ticker_data:
                logger.warning(f"No ticker data retrieved for {symbol}")
                return None
                
            # Structure the result into a more accessible format
            timestamp = int(time.time() * 1000)
            
            # Create enhanced data with calculated fields if needed
            enhanced_data = {
                'symbol': symbol,
                'timestamp': timestamp,
                'ticker': {
                    'last_price': ticker_data.get('last', 0.0),
                    'mark_price': ticker_data.get('mark', 0.0),
                    'index_price': ticker_data.get('index', 0.0),
                    'funding_rate': ticker_data.get('fundingRate', 0.0),
                    'volume_24h': ticker_data.get('volume', 0.0),
                    'timestamp': int(time.time() * 1000)
                },
                'raw_ticker': ticker_data  # Include the complete raw ticker data for direct access
            }
            
            # Explicitly add open interest to the ticker structure
            if 'openInterest' in ticker_data or 'open_interest' in ticker_data:
                oi_value = ticker_data.get('openInterest', ticker_data.get('open_interest', 0.0))
                enhanced_data['ticker']['open_interest'] = float(oi_value)
                logger.debug(f"Added open interest to ticker: {enhanced_data['ticker']['open_interest']}")
                
            if 'openInterestValue' in ticker_data or 'open_interest_value' in ticker_data:
                oiv_value = ticker_data.get('openInterestValue', ticker_data.get('open_interest_value', 0.0))
                enhanced_data['ticker']['open_interest_value'] = float(oiv_value)
                logger.debug(f"Added open interest value to ticker: {enhanced_data['ticker']['open_interest_value']}")
            
            # Calculate derived metrics like turnover from volume and price if missing
            price = ticker_data.get('last', 0.0)
            volume = ticker_data.get('volume', 0.0)
            turnover = ticker_data.get('turnover', price * volume)
            
            # Create price structure for easier access
            enhanced_data['price'] = {
                'last': price,
                'high': ticker_data.get('high', 0.0),
                'low': ticker_data.get('low', 0.0),
                'change_24h': ticker_data.get('percentage', 0.0),
                'volume': volume,
                'turnover': turnover
            }
            
            # Add open interest to the price structure too for redundancy
            if 'openInterest' in ticker_data or 'open_interest' in ticker_data:
                oi_value = ticker_data.get('openInterest', ticker_data.get('open_interest', 0.0))
                enhanced_data['price']['open_interest'] = float(oi_value)
                logger.debug(f"Added open interest to price: {enhanced_data['price']['open_interest']}")
            
            return enhanced_data
        except Exception as e:
            logger.exception(f"Error in direct market data fetch for {symbol}: {e}")
            return None

    async def _get_last_known_turnover(self) -> float:
        """Get the last known good turnover value."""
        try:
            # Implement file-based storage for simplicity
            cache_file = "cache/last_turnover.txt"
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    value = float(f.read().strip())
                    self.logger.info(f"Retrieved last known turnover: {value}")
                    return value
            else:
                # Return a reasonable default if no cached value exists
                self.logger.warning("No cached turnover value found, using default")
                return 20000000000.0  # 20 billion default
        except Exception as e:
            self.logger.error(f"Error getting last known turnover: {str(e)}")
            return 20000000000.0  # 20 billion default
        
    async def _get_last_known_oi(self) -> float:
        """Get the last known good open interest value."""
        try:
            # Implement file-based storage for simplicity
            cache_file = "cache/last_oi.txt"
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    value = float(f.read().strip())
                    self.logger.info(f"Retrieved last known OI: {value}")
                    return value
            else:
                # Return a reasonable default if no cached value exists
                self.logger.warning("No cached OI value found, using default")
                return 5000000000.0  # 5 billion default
        except Exception as e:
            self.logger.error(f"Error getting last known OI: {str(e)}")
            return 5000000000.0  # 5 billion default
        
    async def _save_good_turnover(self, value: float) -> None:
        """Save a good turnover value for future use."""
        try:
            # Ensure directory exists
            os.makedirs("cache", exist_ok=True)
            with open("cache/last_turnover.txt", "w") as f:
                f.write(str(value))
            self.logger.debug(f"Saved good turnover value: {value}")
        except Exception as e:
            self.logger.error(f"Error saving turnover value: {str(e)}")
            
    async def _save_good_oi(self, value: float) -> None:
        """Save a good OI value for future use."""
        try:
            # Ensure directory exists
            os.makedirs("cache", exist_ok=True)
            with open("cache/last_oi.txt", "w") as f:
                f.write(str(value))
            self.logger.debug(f"Saved good OI value: {value}")
        except Exception as e:
            self.logger.error(f"Error saving OI value: {str(e)}")

    async def _calculate_btc_betas(self, top_pairs: List[str], lookback_periods: int = 20) -> List[Tuple[str, float]]:
        """Calculate beta coefficients relative to BTC."""
        try:
            # Get BTC data
            btc_data = await self.top_symbols_manager.get_market_data('BTCUSDT')
            if not btc_data or 'ohlcv' not in btc_data:
                self.logger.warning("No BTC data available for beta calculation")
                return []

            # Get base timeframe DataFrame
            btc_df = btc_data['ohlcv'].get('base', {}).get('data')
            if not isinstance(btc_df, pd.DataFrame):
                self.logger.warning("BTC data is not in DataFrame format")
                return []
            
            if len(btc_df) < lookback_periods:
                self.logger.debug(f"Insufficient BTC OHLCV data: {len(btc_df)} periods")
                return []

            # Calculate BTC returns
            btc_df['returns'] = btc_df['close'].pct_change() * 100
            btc_returns = btc_df['returns'].dropna().tail(lookback_periods).values
            btc_mean = btc_returns.mean()

            # Calculate betas for all pairs
            betas = []
            for symbol in top_pairs:
                if symbol == 'BTCUSDT':
                    continue

                try:
                    pair_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not pair_data or 'ohlcv' not in pair_data:
                        continue

                    # Get pair DataFrame
                    pair_df = pair_data['ohlcv'].get('base', {}).get('data')
                    if not isinstance(pair_df, pd.DataFrame):
                        continue

                    if len(pair_df) < lookback_periods:
                        continue

                    # Calculate pair returns
                    pair_df['returns'] = pair_df['close'].pct_change() * 100
                    returns = pair_df['returns'].dropna().tail(lookback_periods).values

                    if len(returns) != len(btc_returns):
                        continue

                    # Calculate beta using numpy operations
                    mean_return = returns.mean()
                    covariance = np.mean((returns - mean_return) * (btc_returns - btc_mean))
                    variance = np.var(btc_returns)

                    if variance != 0:
                        beta = covariance / variance
                        betas.append((symbol, beta))

                except Exception as e:
                    self.logger.debug(f"Error calculating beta for {symbol}: {str(e)}")
                    continue

            return sorted(betas, key=lambda x: abs(x[1]), reverse=True)

        except Exception as e:
            self.logger.error(f"Error calculating BTC betas: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return []

    async def _calculate_risk_metrics(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate risk metrics for the market."""
        try:
            metrics = {
                'volatility': {},
                'funding_rates': {},
                'liquidations': {},
                'market_sentiment': 0,
                'risk_level': 'MODERATE',
                'risk_trend': 'STABLE',
                'market_volatility': 50
            }
            
            # Calculate market-wide metrics
            for symbol in top_pairs:
                data = await self.top_symbols_manager.get_market_data(symbol)
                if not data:
                    continue
                    
                # Get OHLCV data
                ohlcv = data.get('ohlcv', {}).get('base', {}).get('data')
                if isinstance(ohlcv, pd.DataFrame) and not ohlcv.empty:
                    # Calculate volatility (20-period standard deviation of returns)
                    returns = ohlcv['close'].pct_change()
                    vol = returns.std() * 100  # Convert to percentage
                    metrics['volatility'][symbol] = vol
                    
                # Get funding rate
                funding_rate = float(data.get('ticker', {}).get('funding_rate', 0)) * 100
                metrics['funding_rates'][symbol] = funding_rate
                
                # Get liquidation data
                liquidations = data.get('liquidations', {})
                if liquidations:
                    metrics['liquidations'][symbol] = {
                        'long_liq': float(liquidations.get('long_liquidations', 0)),
                        'short_liq': float(liquidations.get('short_liquidations', 0))
                    }
            
            # Calculate average volatility and set risk level
            if metrics['volatility']:
                avg_vol = sum(metrics['volatility'].values()) / max(len(metrics['volatility']), 1)
                metrics['market_volatility'] = avg_vol
                
                if avg_vol > 80:
                    metrics['risk_level'] = 'HIGH'
                elif avg_vol < 50:
                    metrics['risk_level'] = 'LOW'
                else:
                    metrics['risk_level'] = 'MODERATE'
            
            # Calculate bull/bear ratio based on price trends
            bull_count = 0
            bear_count = 0
            for symbol in top_pairs:
                data = await self.top_symbols_manager.get_market_data(symbol)
                if not data or 'ohlcv' not in data:
                    continue
                    
                ohlcv = data['ohlcv'].get('base', {}).get('data')
                if not isinstance(ohlcv, pd.DataFrame) or ohlcv.empty or len(ohlcv) < 21:
                    continue
                    
                ema8 = ohlcv['close'].ewm(span=8).mean().iloc[-1]
                ema21 = ohlcv['close'].ewm(span=21).mean().iloc[-1]
                if ema8 > ema21:
                    bull_count += 1
                else:
                    bear_count += 1
            
            total_count = bull_count + bear_count
            if total_count > 0:
                metrics['bull_bear_ratio'] = bull_count / total_count
            else:
                metrics['bull_bear_ratio'] = 0.5
            
            # Identify major liquidations
            major_liquidations = []
            for symbol, liq_data in metrics.get('liquidations', {}).items():
                total_liq = liq_data.get('long_liq', 0) + liq_data.get('short_liq', 0)
                if total_liq > 1000000:  # More than $1M
                    major_liquidations.append((symbol, total_liq))
            
            metrics['major_liquidations'] = sorted(major_liquidations, key=lambda x: x[1], reverse=True)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                'volatility': {},
                'funding_rates': {},
                'liquidations': {},
                'market_sentiment': 0,
                'risk_level': 'MODERATE',
                'risk_trend': 'STABLE',
                'market_volatility': 50,
                'bull_bear_ratio': 0.5,
                'major_liquidations': []
            }

    def _find_orderbook_clusters(self, orderbook_side):
        """Find clusters of orders in the orderbook.
        
        Args:
            orderbook_side: List of [price, size] entries from orderbook
            
        Returns:
            List of dictionaries with price and volume for each cluster
        """
        if not orderbook_side or not isinstance(orderbook_side, list):
            return []
            
        # Group close price levels
        price_levels = {}
        for order in orderbook_side:
            if len(order) >= 2:
                try:
                    price = float(order[0])
                    size = float(order[1])
                    
                    # Round price to create clusters
                    # For BTC, round to nearest $100, for others use appropriate precision
                    price_magnitude = math.floor(math.log10(price))
                    if price > 10000:  # BTC-like prices
                        rounded_price = round(price, -2)  # Round to hundreds
                    elif price > 100:  # ETH-like prices
                        rounded_price = round(price, 0)   # Round to ones
                    elif price > 1:    # Mid-range prices
                        rounded_price = round(price, 1)   # Round to 0.1
                    else:              # Very small prices
                        rounded_price = round(price, 3)   # Round to 0.001
                        
                    if rounded_price not in price_levels:
                        price_levels[rounded_price] = 0
                    price_levels[rounded_price] += size * price  # Use notional value (size * price)
                except (ValueError, TypeError):
                    continue
        
        # Find significant clusters
        clusters = []
        if price_levels:
            # Sort by volume
            sorted_levels = sorted(price_levels.items(), key=lambda x: x[1], reverse=True)
            # Return top clusters
            for price, volume in sorted_levels[:5]:  # Take top 5 clusters
                clusters.append({
                    "price": price,
                    "volume": volume
                })
                
        return clusters

    def _create_progress_bar(self, value: float, min_val: float, max_val: float, segments: int = 10) -> str:
        """Create a visual progress bar for metrics.
        
        Args:
            value: Current value to represent
            min_val: Minimum value in the range
            max_val: Maximum value in the range
            segments: Number of segments in the bar
            
        Returns:
            String containing the progress bar
        """
        if min_val >= max_val:
            return "Error: min must be less than max"
            
        # Ensure value is within range
        value = max(min_val, min(max_val, value))
        
        # Calculate how many segments to fill
        fill_ratio = (value - min_val) / (max_val - min_val)
        filled_segments = round(fill_ratio * segments)
        
        # Create the bar using square block characters
        filled_blocks = "■" * filled_segments
        empty_blocks = "□" * (segments - filled_segments)
        
        return filled_blocks + empty_blocks

    def _generate_market_outlook(self, 
                              market_regime: Dict[str, Any], 
                              smart_money: Dict[str, Any], 
                              overview: Dict[str, Any]) -> str:
        """Generate a market outlook based on analyzed market conditions.
        
        This method combines market regime, smart money analysis, and market overview
        data to generate a meaningful outlook statement that describes current market
        conditions and potential future direction.
        
        Args:
            market_regime: Market regime data
            smart_money: Smart money analysis data
            overview: Market overview data
            
        Returns:
            String containing market outlook analysis
        """
        try:
            # Extract key metrics
            regime = market_regime.get('regime', 'NEUTRAL')
            trend_strength = market_regime.get('trend_strength', 0.5)
            volatility = market_regime.get('volatility', 0.3)
            
            smart_money_index = smart_money.get('index_value', 50)
            institutional_flow = smart_money.get('institutional_flow', 0)
            
            # Format trend strength as a percentage
            trend_strength_pct = trend_strength * 100
            volatility_pct = volatility * 100
            
            # Determine market structure based on regime
            structure_phrases = {
                'BULLISH_TRENDING': "strong upward trend",
                'BULLISH_SIDEWAYS': "consolidation with bullish bias",
                'BEARISH_TRENDING': "strong downward trend",
                'BEARISH_SIDEWAYS': "consolidation with bearish bias",
                'ACCUMULATION': "accumulation phase",
                'DISTRIBUTION': "distribution phase",
                'NEUTRAL': "sideways movement"
            }
            
            market_structure = structure_phrases.get(regime, "mixed pattern")
            
            # Determine flow description based on smart money
            if smart_money_index > 70:
                flow_desc = "strong institutional buying"
            elif smart_money_index > 60:
                flow_desc = "moderate institutional buying"
            elif smart_money_index > 50:
                flow_desc = "slight institutional buying"
            elif smart_money_index < 30:
                flow_desc = "strong institutional selling"
            elif smart_money_index < 40:
                flow_desc = "moderate institutional selling"
            elif smart_money_index < 50:
                flow_desc = "slight institutional selling"
            else:
                flow_desc = "neutral institutional activity"
                
            # Generate risk assessment
            if volatility_pct > 5:
                risk_level = "high"
            elif volatility_pct > 2.5:
                risk_level = "moderate"
            else:
                risk_level = "low"
                
            # Determine market condition detail
            if regime in ('BULLISH_TRENDING', 'BULLISH_SIDEWAYS') and smart_money_index > 55:
                condition = "bullish momentum supported by institutional buying"
            elif regime in ('BULLISH_TRENDING', 'BULLISH_SIDEWAYS') and smart_money_index < 45:
                condition = "price strength with institutional distribution"
            elif regime in ('BEARISH_TRENDING', 'BEARISH_SIDEWAYS') and smart_money_index < 45:
                condition = "bearish pressure reinforced by institutional selling"
            elif regime in ('BEARISH_TRENDING', 'BEARISH_SIDEWAYS') and smart_money_index > 55:
                condition = "price weakness with institutional accumulation"
            elif regime == 'ACCUMULATION' and smart_money_index > 55:
                condition = "strong accumulation phase likely preceding an uptrend"
            elif regime == 'DISTRIBUTION' and smart_money_index < 45:
                condition = "distribution phase indicating potential trend reversal"
            else:
                condition = "mixed signals with no clear directional bias"
                
            # Generate future outlook based on conditions
            if condition.startswith("bullish") or condition.startswith("strong accumulation"):
                future = "continued upside momentum"
            elif condition.startswith("bearish") or condition.startswith("distribution phase"):
                future = "further downside pressure"
            elif "institutional accumulation" in condition:
                future = "potential bottoming process"
            elif "institutional distribution" in condition:
                future = "potential topping pattern"
            else:
                future = "range-bound price action"
                
            # Build the outlook string
            outlook = f"Market structure showing {market_structure} with {trend_strength_pct:.1f}% trend strength. "
            outlook += f"Current volatility at {volatility_pct:.1f}% indicates {risk_level} risk environment. "
            outlook += f"Analysis suggests {condition}, with {flow_desc}. "
            outlook += f"Near-term outlook points to {future}."
            
            return outlook
            
        except Exception as e:
            self.logger.error(f"Error generating market outlook: {str(e)}")
            return "Market analysis currently unavailable due to insufficient data."

    def _format_smart_money(self, smart_money: Dict[str, Any]) -> str:
        """Format smart money analysis data for display in a Discord embed.
        
        Args:
            smart_money: Smart money analysis data
            
        Returns:
            Formatted string with smart money analysis
        """
        try:
            # Extract key metrics
            index_value = smart_money.get("index_value", 50.0)
            institutional_flow = smart_money.get("institutional_flow", 0.0)
            accumulation_zones = smart_money.get("accumulation_zones", {})
            status = smart_money.get("status", "NEUTRAL")
            
            # Create progress bar for Smart Money Index
            smi_bar = self._create_progress_bar(index_value, 0, 100, 10)
            
            # Format institutional flow with direction and strength
            flow_emoji = "➡️"
            if institutional_flow > 15:
                flow_emoji = "🔼🔼"  # Strong inflow
            elif institutional_flow > 5:
                flow_emoji = "🔼"    # Moderate inflow
            elif institutional_flow < -15:
                flow_emoji = "🔽🔽"  # Strong outflow
            elif institutional_flow < -5:
                flow_emoji = "🔽"    # Moderate outflow
                
            # Format accumulation zones
            zones_text = ""
            if accumulation_zones:
                zones_list = []
                for symbol, zones in accumulation_zones.items():
                    if zones:
                        # Format price levels with volume
                        formatted_zones = [f"${z['price']:.2f} (${self._format_compact_number(z['volume'])})" for z in zones]
                        zones_list.append(f"{symbol}: {', '.join(formatted_zones[:3])}")
                
                if zones_list:
                    zones_text = "\n\n**Key Accumulation Zones:**\n" + "\n".join(zones_list[:3])
                else:
                    zones_text = "\n\n**Key Accumulation Zones:** No significant zones detected"
            else:
                zones_text = "\n\n**Key Accumulation Zones:** No significant zones detected"
            
            # Create formatted output
            result = (
                f"**Smart Money Index:** {index_value:.1f}/100 ({status})\n"
                f"{smi_bar}\n\n"
                f"**Institutional Flow:** {flow_emoji} {institutional_flow:+.1f}%"
                f"{zones_text}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error formatting smart money data: {str(e)}")
            return "Smart money analysis not available"
    
    def _format_compact_number(self, num: float) -> str:
        """Format a number in a compact way (K, M, B, T) for display.
        
        Args:
            num: Number to format
            
        Returns:
            Formatted string
        """
        if num is None:
            return "0"
            
        if abs(num) >= 1_000_000_000_000:
            return f"{num/1_000_000_000_000:.1f}T"
        elif abs(num) >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:.0f}"

    def _get_cycle_emoji(self, regime: str) -> str:
        """Get an appropriate emoji for the given market regime.
        
        Args:
            regime: The market regime string
            
        Returns:
            Emoji representing the market regime
        """
        regime_emojis = {
            'BULLISH_TRENDING': "🚀",
            'BULLISH_SIDEWAYS': "📈",
            'BEARISH_TRENDING': "📉",
            'BEARISH_SIDEWAYS': "🔻",
            'ACCUMULATION': "🧠",
            'DISTRIBUTION': "🦈",
            'NEUTRAL': "⚖️"
        }
        
        return regime_emojis.get(regime, "🔄")

    def _format_btc_betas(self, btc_betas: List[Tuple[str, float]]) -> str:
        """Format BTC beta values for display in market report.
        
        Args:
            btc_betas: List of (symbol, beta) tuples
            
        Returns:
            Formatted string with BTC beta analysis
        """
        if not btc_betas:
            return "No BTC beta data available"
        
        # Sort by absolute beta value (highest correlation/inverse correlation first)
        sorted_betas = sorted(btc_betas, key=lambda x: abs(x[1]), reverse=True)
        
        # Format each beta entry
        beta_lines = []
        for symbol, beta in sorted_betas[:5]:  # Show top 5
            # Determine emoji based on beta value
            if beta > 1.5:
                emoji = "🔺🔺"  # Very high beta
            elif beta > 1.0:
                emoji = "🔺"    # High beta
            elif beta > 0.5:
                emoji = "↗️"    # Medium beta
            elif beta >= 0:
                emoji = "➡️"    # Low beta
            elif beta > -0.5:
                emoji = "↘️"    # Low negative beta
            elif beta > -1.0:
                emoji = "🔻"    # Medium negative beta
            else:
                emoji = "🔻🔻"  # High negative beta
                
            # Format the line
            beta_lines.append(f"{emoji} **{symbol}**: {beta:.2f}")
        
        # Add explanatory text
        result = (
            "**Bitcoin Sensitivity (Beta):**\n" + 
            "\n".join(beta_lines) + 
            "\n\n*Beta > 1: Higher volatility than BTC*\n" +
            "*Beta < 0: Moves opposite to BTC*"
        )
        
        return result

    def _format_whale_activity(self, whale_activity: Dict[str, Any]) -> str:
        """Format whale activity data for display in market report.
        
        Args:
            whale_activity: Dictionary containing whale activity data
            
        Returns:
            Formatted string with whale activity analysis
        """
        if not whale_activity:
            return "No whale activity data available"
        
        # Extract key metrics
        large_trades = whale_activity.get('large_trades', {})
        buy_sell_ratio = whale_activity.get('buy_sell_ratio', {})
        significant_movements = whale_activity.get('significant_movements', [])
        
        # Format large trades section
        large_trades_lines = []
        for symbol, trades in large_trades.items():
            if trades:
                buy_volume = trades.get('buy_volume', 0)
                sell_volume = trades.get('sell_volume', 0)
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    buy_percentage = (buy_volume / total_volume) * 100
                    emoji = "🐳" if buy_percentage > 60 else "🦈" if buy_percentage > 40 else "🐟"
                    large_trades_lines.append(f"{emoji} **{symbol}**: {buy_percentage:.1f}% buying ({self._format_compact_number(total_volume)} total)")
        
        # Format buy/sell ratio section
        ratio_lines = []
        for symbol, ratio in buy_sell_ratio.items():
            if ratio > 0:  # Ensure we have valid data
                if ratio > 1.5:
                    emoji = "💚"  # Strong buying
                elif ratio > 1.2:
                    emoji = "✅"  # Moderate buying
                elif ratio > 0.8:
                    emoji = "⚖️"  # Balanced
                elif ratio > 0.5:
                    emoji = "❎"  # Moderate selling
                else:
                    emoji = "❌"  # Strong selling
                
                ratio_lines.append(f"{emoji} **{symbol}**: {ratio:.2f}x")
        
        # Format significant movements
        movement_lines = []
        for movement in significant_movements[:3]:  # Show top 3
            symbol = movement.get('symbol', 'Unknown')
            change = movement.get('change_pct', 0)
            volume = movement.get('volume', 0)
            time_period = movement.get('time_period', 'recent')
            
            emoji = "🚀" if change > 0 else "💥"
            movement_lines.append(f"{emoji} **{symbol}**: {change:+.1f}% on {self._format_compact_number(volume)} volume ({time_period})")
        
        # Compile the sections
        sections = []
        
        if large_trades_lines:
            sections.append("**Large Trade Activity:**\n" + "\n".join(large_trades_lines[:3]))
        
        if ratio_lines:
            sections.append("**Buy/Sell Ratio:**\n" + "\n".join(ratio_lines[:3]))
        
        if movement_lines:
            sections.append("**Significant Movements:**\n" + "\n".join(movement_lines))
            
        if not sections:
            return "No significant whale activity detected"
            
        return "\n\n".join(sections)

    async def _calculate_performance_metrics(self, top_pairs: List[str]) -> Dict[str, Any]:
        """Calculate performance metrics for top trading pairs.
        
        This method analyzes the performance of trading pairs to identify
        top gainers and losers based on price changes.
        
        Args:
            top_pairs: List of trading pair symbols to analyze
            
        Returns:
            Dictionary containing performance metrics and formatted text
        """
        try:
            # Initialize performance data structures
            performance_data = []
            
            # Process each trading pair
            for symbol in top_pairs:
                try:
                    # Get market data
                    market_data = await self.top_symbols_manager.get_market_data(symbol)
                    if not market_data:
                        self.logger.warning(f"No market data available for {symbol}")
                        continue
                    
                    # Extract metrics
                    metrics = await self._extract_market_data(market_data)
                    
                    # Skip if we don't have the key metrics
                    if metrics.get('last_price') is None or metrics.get('change_24h_pct') is None:
                        self.logger.warning(f"Missing key metrics for {symbol}")
                        continue
                    
                    # Get essential metrics
                    last_price = metrics.get('last_price', 0)
                    change_24h_pct = metrics.get('change_24h_pct', 0)
                    volume = metrics.get('volume', 0)
                    open_interest = metrics.get('open_interest', 0)
                    
                    # Append to performance data
                    performance_data.append({
                        'symbol': symbol,
                        'last_price': last_price,
                        'change_24h_pct': change_24h_pct,
                        'volume': volume,
                        'open_interest': open_interest
                    })
                
                except Exception as e:
                    self.logger.warning(f"Error processing {symbol} for performance metrics: {str(e)}")
                    continue
            
            # Sort for winners (top gainers)
            winners = sorted(
                [p for p in performance_data if p['change_24h_pct'] > 0],
                key=lambda x: x['change_24h_pct'],
                reverse=True
            )[:5]  # Top 5 winners
            
            # Sort for losers (top losers)
            losers = sorted(
                [p for p in performance_data if p['change_24h_pct'] < 0],
                key=lambda x: x['change_24h_pct']
            )[:5]  # Top 5 losers
            
            # If we don't have enough winners or losers, get most active by volume
            if len(winners) < 5 or len(losers) < 5:
                most_active = sorted(
                    performance_data,
                    key=lambda x: x['volume'],
                    reverse=True
                )[:10]  # Top 10 most active
                
                # Fill in winners if needed
                while len(winners) < 5 and most_active:
                    candidate = most_active.pop(0)
                    if candidate not in winners and candidate not in losers:
                        # Mark it as a volume-based entry
                        candidate['selected_by'] = 'volume'
                        winners.append(candidate)
                
                # Fill in losers if needed
                while len(losers) < 5 and most_active:
                    candidate = most_active.pop(0)
                    if candidate not in winners and candidate not in losers:
                        # Mark it as a volume-based entry
                        candidate['selected_by'] = 'volume'
                        losers.append(candidate)
            
            # Format the winners text
            winners_text = ""
            for winner in winners:
                symbol = winner['symbol']
                price = winner['last_price']
                change = winner['change_24h_pct']
                volume = winner['volume']
                
                # Skip if price or change is None
                if price is None or change is None:
                    continue
                
                # Format with appropriate arrows and signs
                arrow = "🔼" if change > 5 else "↗️"
                winners_text += f"{arrow} **{symbol}**: ${price:.4f} (+{change:.2f}%)\n"
                winners_text += f"  Vol: {self._format_number(volume, prefix='$')}\n"
            
            # Format the losers text
            losers_text = ""
            for loser in losers:
                symbol = loser['symbol']
                price = loser['last_price']
                change = loser['change_24h_pct']
                volume = loser['volume']
                
                # Skip if price or change is None
                if price is None or change is None:
                    continue
                
                # Format with appropriate arrows and signs (change is already negative)
                arrow = "🔻" if change < -5 else "↘️"
                losers_text += f"{arrow} **{symbol}**: ${price:.4f} ({change:.2f}%)\n"
                losers_text += f"  Vol: {self._format_number(volume, prefix='$')}\n"
            
            # Create performance fields
            performance_fields = []
            
            if winners_text:
                performance_fields.append({
                    "name": "🏆 WINNERS",
                    "value": winners_text,
                    "inline": True
                })
            else:
                performance_fields.append({
                    "name": "🏆 WINNERS",
                    "value": "No significant gainers found",
                    "inline": True
                })
            
            if losers_text:
                performance_fields.append({
                    "name": "💔 LOSERS",
                    "value": losers_text,
                    "inline": True
                })
            else:
                performance_fields.append({
                    "name": "💔 LOSERS",
                    "value": "No significant losers found",
                    "inline": True
                })
            
            # Return the performance metrics
            return {
                "winners": winners,
                "losers": losers,
                "fields": performance_fields,
                "text": winners_text + "\n" + losers_text  # Combined text for simple display
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                "winners": [],
                "losers": [],
                "fields": [],
                "text": "Error calculating performance metrics"
            }

    def _format_performance_metrics(self, performance_metrics: Dict[str, Any]) -> str:
        """Format performance metrics for the market report.
        
        This method takes the performance metrics dictionary and formats it
        into a string suitable for display in the market report.
        
        Args:
            performance_metrics: Dictionary containing performance metrics
            
        Returns:
            Formatted string with performance metrics
        """
        try:
            if not performance_metrics:
                return "No performance data available"
                
            # Check if we have the formatted fields
            if "fields" in performance_metrics and performance_metrics["fields"]:
                winners_field = next((f for f in performance_metrics["fields"] if f["name"] == "🏆 WINNERS"), None)
                losers_field = next((f for f in performance_metrics["fields"] if f["name"] == "💔 LOSERS"), None)
                
                winners_text = winners_field["value"] if winners_field else "No significant gainers found"
                losers_text = losers_field["value"] if losers_field else "No significant losers found"
                
                return f"**Top Performers**\n\n{winners_text}\n\n**Worst Performers**\n\n{losers_text}"
            
            # Otherwise, use the text
            text = performance_metrics.get("text", "")
            if text:
                return f"**Market Performance**\n\n{text}"
            
            return "No performance data available"
        except Exception as e:
            self.logger.error(f"Error formatting performance metrics: {str(e)}")
            return "Error formatting performance metrics"

    def _format_percentage(self, value: float) -> str:
        """Format percentage value with + or - prefix."""
        if value is None or math.isnan(value):
            return "0.0%"
        return f"{'+' if value > 0 else ''}{value:.1f}%"
        
    def _format_discord_webhook(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Format the report into a Discord webhook compatible message.
        
        Args:
            report: Dictionary containing the market report data
            
        Returns:
            Dictionary formatted as a Discord webhook message
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Format the date for the report
            date_str = current_time.strftime('%B %d, %Y')
            time_str = current_time.strftime('%H:%M UTC')
            report_num = int(time.time()) % 1000
            
            # Initialize embeds list for structured reporting
            embeds = []
            
            # Define color codes for different sections
            # Using Discord's color system (decimal color codes)
            BLUE = 3447003        # Market overview & cycle
            GREEN = 5763719       # Performance & metrics
            GOLD = 15844367       # Risk metrics
            PURPLE = 10181046     # Smart money
            TEAL = 1752220        # Whale activity
            DARK_BLUE = 2123412   # Market outlook
            DARK_GREEN = 2067276  # System status
            
            # Main header embed
            main_embed = {
                "title": "🌐 VIRTUOSO MARKET INTELLIGENCE",
                "description": f"Your comprehensive market analysis for {date_str}",
                "color": BLUE,
                "timestamp": current_time.isoformat(),
                "footer": {
                    "text": f"Report #{report_num} | {time_str}"
                },
                "thumbnail": {
                    "url": "https://raw.githubusercontent.com/virtuoso-dev/virtuoso/main/assets/logo.png"
                }
            }
            embeds.append(main_embed)
            
            # Market cycle embed
            if report.get("market_cycle"):
                cycle_embed = {
                    "title": "📊 MARKET CYCLE",
                    "description": report["market_cycle"],
                    "color": BLUE
                }
                embeds.append(cycle_embed)
            
            # Market metrics embed
            if report.get("market_metrics"):
                metrics_embed = {
                    "title": "📈 MARKET METRICS",
                    "description": report["market_metrics"],
                    "color": GREEN
                }
                embeds.append(metrics_embed)
            
            # Futures premium embed
            if report.get("futures_premium"):
                futures_embed = {
                    "title": "📊 FUTURES PREMIUM",
                    "description": report["futures_premium"],
                    "color": GOLD
                }
                embeds.append(futures_embed)
            
            # Smart money embed
            if report.get("smart_money"):
                smart_money_embed = {
                    "title": "🧠 SMART MONEY",
                    "description": report["smart_money"],
                    "color": PURPLE
                }
                embeds.append(smart_money_embed)
            
            # Whale activity embed
            if report.get("whale_activity"):
                whale_embed = {
                    "title": "🐋 WHALE ACTIVITY",
                    "description": report["whale_activity"],
                    "color": TEAL
                }
                embeds.append(whale_embed)
            
            # BTC betas embed
            if report.get("btc_betas"):
                betas_embed = {
                    "title": "🔗 BTC CORRELATIONS",
                    "description": report["btc_betas"],
                    "color": BLUE
                }
                embeds.append(betas_embed)
            
            # Orderbook analysis embed
            if report.get("orderbook_analysis"):
                orderbook_embed = {
                    "title": "📖 ORDERBOOK ANALYSIS",
                    "description": report["orderbook_analysis"],
                    "color": GOLD
                }
                embeds.append(orderbook_embed)
            
            # Performance metrics embed
            if report.get("performance_metrics"):
                performance_embed = {
                    "title": "🔍 PERFORMANCE METRICS",
                    "description": report["performance_metrics"],
                    "color": GREEN
                }
                embeds.append(performance_embed)
            
            # Market outlook embed
            if report.get("market_outlook"):
                outlook_embed = {
                    "title": "🔮 MARKET OUTLOOK",
                    "description": report["market_outlook"],
                    "color": DARK_BLUE
                }
                embeds.append(outlook_embed)
            
            # System status embed
            status_desc = [
                "✅ Market Monitor: Active",
                "✅ Data Collection: Running", 
                "✅ Analysis Engine: Ready"
            ]
            
            status_embed = {
                "title": "🖥️ SYSTEM STATUS",
                "description": "\n".join(status_desc),
                "color": DARK_GREEN
            }
            embeds.append(status_embed)
            
            # Create final webhook message
            webhook_message = {
                "username": "Virtuoso Market Monitor",
                "avatar_url": "https://raw.githubusercontent.com/virtuoso-dev/virtuoso/main/assets/logo.png",
                "embeds": embeds
            }
            
            self.logger.info(f"Formatted Discord webhook with {len(embeds)} embeds")
            return webhook_message
            
        except Exception as e:
            self.logger.error(f"Error formatting Discord webhook: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Return a simplified error message
            return {
                "username": "Virtuoso Market Monitor",
                "content": f"⚠️ Error generating market report: {str(e)}"
            }

    async def _calculate_btc_futures_premium(self) -> Dict[str, Any]:
        """Calculate BTC futures premium to determine contango/backwardation.
        
        This method fetches spot and futures prices for Bitcoin to calculate the premium
        percentage, which indicates if the market is in contango (futures > spot) or
        backwardation (spot > futures).
        
        Returns:
            Dictionary containing futures premium data and market status
        """
        try:
            self.logger.info("Calculating BTC futures premium (contango/backwardation)")
            
            # Initialize with default values
            futures_premium = {
                'spot_price': 0,
                'futures_price': 0,
                'premium_percent': 0,
                'status': 'Unknown',
                'quarterly_futures': 0,
                'basis': 0
            }
            
            # Use existing exchange_manager or create a new one
            if hasattr(self, 'exchange_manager') and self.exchange_manager:
                exchange_manager = self.exchange_manager
            else:
                config_manager = ConfigManager()
                exchange_manager = ExchangeManager(config_manager)
                if not hasattr(exchange_manager, 'initialized') or not exchange_manager.initialized:
                    await exchange_manager.initialize()
            
            # Get exchange
            exchange = await exchange_manager.get_primary_exchange()
            if not exchange:
                self.logger.warning("Failed to get exchange for futures premium calculation")
                return futures_premium
            
            # Fetch spot BTC price
            spot_data = None
            try:
                # Try to fetch spot ticker from exchange
                spot_data = await exchange._make_request('GET', '/v5/market/tickers', {'category': 'spot', 'symbol': 'BTCUSDT'})
                self.logger.debug(f"Spot data response: {spot_data is not None}")
            except Exception as e:
                self.logger.warning(f"Error fetching spot BTC ticker: {e}")
            
            # Fetch futures BTC price (perpetual)
            futures_data = None
            try:
                # Try to fetch perpetual futures ticker
                futures_data = await exchange._make_request('GET', '/v5/market/tickers', {'category': 'linear', 'symbol': 'BTCUSDT'})
                self.logger.debug(f"Futures data response: {futures_data is not None}")
            except Exception as e:
                self.logger.warning(f"Error fetching futures BTC ticker: {e}")
            
            # Fetch quarterly futures if available
            quarterly_data = None
            try:
                # Try to fetch quarterly futures ticker
                # First try the specific quarterly contract (e.g., BTCUSD0628)
                quarterly_data = await exchange._make_request('GET', '/v5/market/tickers', 
                                                            {'category': 'linear', 'symbol': 'BTCUSD0628'})
                
                if not quarterly_data or 'result' not in quarterly_data or not quarterly_data['result'].get('list'):
                    # If specific contract not found, try to find any quarterly contract
                    contracts_data = await exchange._make_request('GET', '/v5/market/tickers', {'category': 'linear'})
                    if contracts_data and 'result' in contracts_data and 'list' in contracts_data['result']:
                        quarterly_candidates = [
                            item for item in contracts_data['result']['list'] 
                            if 'BTCUSD' in item['symbol'] and item['symbol'] != 'BTCUSDT'
                        ]
                        if quarterly_candidates:
                            # Sort by expiry date (if in format BTCUSDMMDD)
                            quarterly_data = {'result': {'list': [quarterly_candidates[0]]}}
            except Exception as e:
                self.logger.warning(f"Error fetching quarterly futures data: {e}")
            
            # Process spot data
            spot_btc = None
            if spot_data and isinstance(spot_data, dict) and 'result' in spot_data and 'list' in spot_data['result']:
                spot_list = spot_data['result']['list']
                if spot_list:
                    spot_btc = spot_list[0]
                    self.logger.debug(f"Found spot BTC ticker: {spot_btc['symbol'] if spot_btc else 'None'}")
            
            # Process futures data
            futures_btc = None
            if futures_data and isinstance(futures_data, dict) and 'result' in futures_data and 'list' in futures_data['result']:
                futures_list = futures_data['result']['list']
                if futures_list:
                    futures_btc = futures_list[0]
                    self.logger.debug(f"Found futures BTC ticker: {futures_btc['symbol'] if futures_btc else 'None'}")
            
            # Process quarterly futures data
            quarterly_btc = None
            if quarterly_data and isinstance(quarterly_data, dict) and 'result' in quarterly_data and 'list' in quarterly_data['result']:
                quarterly_list = quarterly_data['result']['list']
                if quarterly_list:
                    quarterly_btc = quarterly_list[0]
                    self.logger.debug(f"Found quarterly BTC ticker: {quarterly_btc['symbol'] if quarterly_btc else 'None'}")
            
            # Calculate premium
            if spot_btc and futures_btc:
                try:
                    spot_price = float(spot_btc['lastPrice'])
                    futures_price = float(futures_btc['lastPrice'])
                    
                    # Calculate premium percentage
                    premium_percent = ((futures_price - spot_price) / spot_price) * 100
                    
                    # Update futures premium data
                    futures_premium.update({
                        'spot_price': spot_price,
                        'futures_price': futures_price,
                        'premium_percent': premium_percent,
                        'status': 'Contango' if premium_percent > 0 else 'Backwardation'
                    })
                    
                    self.logger.info(f"BTC futures premium: {premium_percent:+.4f}% ({futures_premium['status']})")
                    
                    # Add quarterly futures data if available
                    if quarterly_btc:
                        quarterly_price = float(quarterly_btc['lastPrice'])
                        basis = ((quarterly_price - spot_price) / spot_price) * 100
                        
                        futures_premium.update({
                            'quarterly_futures': quarterly_price,
                            'basis': basis,
                            'quarterly_symbol': quarterly_btc['symbol']
                        })
                        
                        self.logger.info(f"BTC quarterly basis ({quarterly_btc['symbol']}): {basis:+.4f}%")
                    
                except (ValueError, KeyError) as e:
                    self.logger.error(f"Error calculating futures premium: {e}")
            else:
                self.logger.warning("Could not calculate futures premium - missing spot or futures data")
            
            return futures_premium
            
        except Exception as e:
            self.logger.error(f"Error in BTC futures premium calculation: {str(e)}")
            self.logger.debug("Stack trace:", exc_info=True)
            return {
                'spot_price': 0,
                'futures_price': 0,
                'premium_percent': 0,
                'status': 'Unknown',
                'quarterly_futures': 0,
                'basis': 0
            }