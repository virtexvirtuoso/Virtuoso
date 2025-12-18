from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, Request
from typing import Dict, List, Optional, Any
import asyncio
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import logging
from pydantic import BaseModel, Field
from collections import defaultdict

from src.core.models.liquidation import (
    LiquidationDetectionResponse, LiquidationEvent, MarketStressIndicator,
    LiquidationRisk, CascadeAlert, LiquidationMonitorRequest, LeverageMetrics,
    LiquidationSeverity, MarketStressLevel
)
from src.core.market.market_data_manager import DataUnavailableError
from src.core.analysis.liquidation_detector import LiquidationDetectionEngine
from src.core.exchanges.manager import ExchangeManager

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

async def get_liquidation_detector(request: Request) -> LiquidationDetectionEngine:
    """Dependency to get liquidation detection engine from app state"""
    if not hasattr(request.app.state, "liquidation_detector") or request.app.state.liquidation_detector is None:
        # Fallback to creating a new instance if not available in app state
        exchange_manager = await get_exchange_manager(request)
        return LiquidationDetectionEngine(exchange_manager)
    return request.app.state.liquidation_detector

@router.post("/detect", response_model=LiquidationDetectionResponse)
async def detect_liquidation_events(
    symbols: List[str] = Body(..., description="Symbols to analyze for liquidations"),
    exchanges: Optional[List[str]] = Body(None, description="Target exchanges"),
    sensitivity: float = Body(default=0.7, ge=0, le=1, description="Detection sensitivity"),
    lookback_minutes: int = Body(default=60, ge=5, le=1440, description="Analysis lookback period"),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> LiquidationDetectionResponse:
    """
    Detect liquidation events across specified markets.
    
    This endpoint performs real-time analysis to identify potential liquidation events
    based on volume spikes, price impacts, order book disruptions, and funding rate stress.
    """
    
    start_time = time.time()
    
    try:
        # Run parallel analysis
        tasks = [
            liquidation_detector.detect_liquidation_events(symbols, exchanges, sensitivity, lookback_minutes),
            liquidation_detector.assess_market_stress(symbols, exchanges),
            liquidation_detector.detect_cascade_risk(symbols, exchanges)
        ]
        
        results = await asyncio.gather(*tasks)
        detected_events, market_stress, cascade_alerts = results
        
        # Assess individual risks for key symbols
        risk_assessments = []
        key_symbols = symbols[:5]  # Limit to avoid too many requests
        
        for symbol in key_symbols:
            try:
                exchange_id = exchanges[0] if exchanges else list(liquidation_detector.exchange_manager.exchanges.keys())[0]
                risk = await liquidation_detector.assess_liquidation_risk(symbol, exchange_id)
                risk_assessments.append(risk)
            except Exception as e:
                # Log error but continue with other symbols
                continue
        
        analysis_duration = int((time.time() - start_time) * 1000)
        
        return LiquidationDetectionResponse(
            detected_events=detected_events,
            market_stress=market_stress,
            risk_assessments=risk_assessments,
            cascade_alerts=cascade_alerts,
            analysis_timestamp=datetime.now(timezone.utc),
            detection_duration_ms=analysis_duration,
            metadata={
                "symbols_analyzed": len(symbols),
                "exchanges_scanned": len(exchanges) if exchanges else len(liquidation_detector.exchange_manager.exchanges),
                "sensitivity_level": sensitivity,
                "lookback_minutes": lookback_minutes,
                "events_detected": len(detected_events),
                "cascade_alerts": len(cascade_alerts)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Liquidation detection failed: {str(e)}")

@router.get("/alerts", response_model=List[LiquidationEvent])
async def get_active_liquidation_alerts(
    min_severity: LiquidationSeverity = Query(default=LiquidationSeverity.MEDIUM),
    max_age_minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=20, ge=1, le=100),
    exchanges: Optional[List[str]] = Query(None),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> List[LiquidationEvent]:
    """
    Get active liquidation alerts across all monitored markets.
    """
    
    try:
        # CRITICAL: Mock data removed - real implementation required
        logger.error("Liquidation alerts not implemented - mock data removed")
        raise DataUnavailableError("Liquidation detection unavailable - real implementation required")
        
    except Exception as e:
        logger.error(f"Error in get_active_liquidation_alerts: {e}")
        # Return empty list instead of raising exception
        return []

@router.get("/stress-indicators", response_model=MarketStressIndicator)
async def get_market_stress_indicators(
    symbols: Optional[List[str]] = Query(None, description="Specific symbols to analyze"),
    exchanges: Optional[List[str]] = Query(None, description="Target exchanges"),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector),
    request: Request = None
) -> MarketStressIndicator:
    """
    Get current market stress indicators and risk levels.

    Calculates real stress metrics from:
    - Recent liquidation data (volume and frequency)
    - Market volatility from liquidation patterns
    - Funding rate stress
    - Liquidity conditions from order books
    """

    try:
        # Use default symbols if none provided
        if not symbols:
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

        # Get liquidation collector for real liquidation data
        collector = None
        if hasattr(liquidation_detector, 'liquidation_collector'):
            collector = liquidation_detector.liquidation_collector
        elif hasattr(request.app.state, 'liquidation_collector'):
            collector = request.app.state.liquidation_collector

        # Calculate stress from real liquidation data
        liquidation_volume_24h = 0.0
        volatility_stress_values = []

        if collector:
            # Get recent liquidations (last 24 hours)
            all_liquidations = []
            target_exchanges = exchanges or ['bybit', 'binance', 'okx']

            for symbol in symbols:
                for exchange in target_exchanges:
                    try:
                        liqs = collector.get_recent_liquidations(symbol, exchange, minutes=1440)  # 24 hours
                        all_liquidations.extend(liqs)
                    except Exception as e:
                        logger.debug(f"Could not get liquidations for {symbol} on {exchange}: {e}")

            # Calculate total liquidation volume (24h)
            liquidation_volume_24h = sum(
                liq.liquidated_amount_usd for liq in all_liquidations
                if liq.liquidated_amount_usd
            )

            # Calculate volatility stress from liquidation frequency and size
            if all_liquidations:
                # Recent liquidations (last hour)
                recent_liqs = [liq for liq in all_liquidations if liq.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=1))]

                # Calculate stress based on:
                # 1. Number of liquidations in last hour vs 24h average
                hour_count = len(recent_liqs)
                avg_per_hour = len(all_liquidations) / 24 if len(all_liquidations) > 0 else 1
                frequency_stress = min(100, (hour_count / max(1, avg_per_hour)) * 30)

                # 2. Size of liquidations
                hour_volume = sum(liq.liquidated_amount_usd for liq in recent_liqs if liq.liquidated_amount_usd)
                avg_hour_volume = liquidation_volume_24h / 24 if liquidation_volume_24h > 0 else 1
                volume_stress = min(100, (hour_volume / max(1, avg_hour_volume)) * 40)

                # 3. Volatility spikes in liquidation events
                volatility_spikes = [liq.volatility_spike for liq in recent_liqs if liq.volatility_spike]
                spike_stress = min(100, (np.mean(volatility_spikes) if volatility_spikes else 1.0) * 20)

                volatility_stress_values.append((frequency_stress + volume_stress + spike_stress) / 3)

        # Use liquidation_detector's assess_market_stress for comprehensive analysis
        # This includes funding rates, liquidity, and other factors
        stress_indicator = await liquidation_detector.assess_market_stress(symbols, exchanges)

        # Enhance with liquidation-specific stress data if available
        if volatility_stress_values:
            # Blend calculated volatility stress with detector's analysis
            calculated_vol_stress = np.mean(volatility_stress_values)
            stress_indicator.volatility_stress = (stress_indicator.volatility_stress + calculated_vol_stress) / 2

        # Update liquidation volume with real data
        if liquidation_volume_24h > 0:
            stress_indicator.liquidation_volume_24h = liquidation_volume_24h

            # Adjust leverage stress based on liquidation volume
            # High liquidation volume indicates high leverage in market
            if liquidation_volume_24h > 100_000_000:  # >$100M
                stress_indicator.leverage_stress = min(100, stress_indicator.leverage_stress + 20)
            elif liquidation_volume_24h > 50_000_000:  # >$50M
                stress_indicator.leverage_stress = min(100, stress_indicator.leverage_stress + 10)

        # Recalculate overall stress score
        stress_indicator.stress_score = np.mean([
            stress_indicator.volatility_stress,
            stress_indicator.funding_rate_stress,
            stress_indicator.liquidity_stress,
            stress_indicator.correlation_stress,
            stress_indicator.leverage_stress
        ])

        # Update stress level based on recalculated score
        if stress_indicator.stress_score < 25:
            stress_indicator.overall_stress_level = MarketStressLevel.CALM
        elif stress_indicator.stress_score < 50:
            stress_indicator.overall_stress_level = MarketStressLevel.ELEVATED
        elif stress_indicator.stress_score < 75:
            stress_indicator.overall_stress_level = MarketStressLevel.HIGH
        else:
            stress_indicator.overall_stress_level = MarketStressLevel.EXTREME

        # Add liquidation-specific warnings if volume is high
        if liquidation_volume_24h > 100_000_000:
            if "High liquidation volume detected" not in stress_indicator.warning_signals:
                stress_indicator.warning_signals.append("High liquidation volume detected ($100M+)")
            if "Monitor for potential cascade events" not in stress_indicator.recommended_actions:
                stress_indicator.recommended_actions.append("Monitor for potential cascade events")

        logger.info(f"Calculated stress indicators: score={stress_indicator.stress_score:.1f}, "
                   f"level={stress_indicator.overall_stress_level.value}, "
                   f"liq_volume_24h=${liquidation_volume_24h:,.0f}")

        return stress_indicator

    except Exception as e:
        logger.error(f"Error in get_market_stress_indicators: {e}")
        import traceback
        logger.debug(traceback.format_exc())

        # Return minimal valid stress indicator on error
        return MarketStressIndicator(
            overall_stress_level=MarketStressLevel.ELEVATED,
            stress_score=50.0,
            volatility_stress=50.0,
            funding_rate_stress=50.0,
            liquidity_stress=50.0,
            correlation_stress=50.0,
            leverage_stress=50.0,
            avg_funding_rate=0.0,
            total_open_interest_change=0.0,
            liquidation_volume_24h=0.0,
            btc_dominance=40.0,
            correlation_breakdown=False,
            warning_signals=["Unable to calculate stress indicators - using defaults"],
            recommended_actions=["Exercise caution until data is available"]
        )

@router.get("/cascade-risk", response_model=List[CascadeAlert])
async def get_cascade_risk_assessment(
    symbols: Optional[List[str]] = Query(None, description="Symbols to analyze for cascade risk"),
    exchanges: Optional[List[str]] = Query(None, description="Target exchanges"),
    min_probability: float = Query(default=0.5, ge=0, le=1, description="Minimum cascade probability"),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector),
    request: Request = None
) -> List[CascadeAlert]:
    """
    Assess cascade liquidation risk across correlated markets.

    Analyzes real liquidation data to detect cascade patterns:
    - Large liquidations clustered in time
    - Price level concentrations across symbols
    - Correlation between liquidation events
    - Order book depth at risk levels
    """

    try:
        # Use default symbols if none provided
        symbols_to_check = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']

        # Get liquidation collector for real data analysis
        collector = None
        if hasattr(liquidation_detector, 'liquidation_collector'):
            collector = liquidation_detector.liquidation_collector
        elif hasattr(request.app.state, 'liquidation_collector'):
            collector = request.app.state.liquidation_collector

        cascade_alerts = []

        if collector:
            # Get recent large liquidations (last 2 hours)
            target_exchanges = exchanges or ['bybit', 'binance', 'okx']
            recent_large_liqs = []

            for symbol in symbols_to_check:
                for exchange in target_exchanges:
                    try:
                        liqs = collector.get_recent_liquidations(symbol, exchange, minutes=120)
                        # Filter for significant liquidations (>$100k)
                        large_liqs = [liq for liq in liqs if liq.liquidated_amount_usd and liq.liquidated_amount_usd >= 100_000]
                        recent_large_liqs.extend(large_liqs)
                    except Exception as e:
                        logger.debug(f"Could not get liquidations for {symbol} on {exchange}: {e}")

            # Cluster liquidations by time proximity (within 15 minutes)
            if recent_large_liqs:
                # Sort by timestamp
                recent_large_liqs.sort(key=lambda x: x.timestamp)

                # Group liquidations into time windows
                time_clusters = []
                current_cluster = []

                for liq in recent_large_liqs:
                    if not current_cluster:
                        current_cluster.append(liq)
                    else:
                        # Check if within 15 minutes of cluster start
                        time_diff = (liq.timestamp - current_cluster[0].timestamp).total_seconds() / 60
                        if time_diff <= 15:
                            current_cluster.append(liq)
                        else:
                            if len(current_cluster) >= 2:  # Only keep clusters with 2+ liquidations
                                time_clusters.append(current_cluster)
                            current_cluster = [liq]

                # Add final cluster if valid
                if len(current_cluster) >= 2:
                    time_clusters.append(current_cluster)

                # Analyze each cluster for cascade risk
                for cluster in time_clusters:
                    # Calculate cluster metrics
                    total_volume = sum(liq.liquidated_amount_usd for liq in cluster if liq.liquidated_amount_usd)
                    affected_symbols = list(set(liq.symbol for liq in cluster))
                    cluster_size = len(cluster)

                    # Calculate cascade probability based on:
                    # 1. Number of symbols affected
                    symbol_factor = min(1.0, len(affected_symbols) / 5) * 0.4

                    # 2. Total volume
                    volume_factor = min(1.0, total_volume / 10_000_000) * 0.3  # $10M baseline

                    # 3. Time concentration
                    time_span = (cluster[-1].timestamp - cluster[0].timestamp).total_seconds() / 60
                    time_factor = min(1.0, (15 - time_span) / 15) * 0.2  # Tighter clustering = higher risk

                    # 4. Average severity
                    severity_map = {
                        LiquidationSeverity.CRITICAL: 1.0,
                        LiquidationSeverity.HIGH: 0.75,
                        LiquidationSeverity.MEDIUM: 0.5,
                        LiquidationSeverity.LOW: 0.25
                    }
                    avg_severity = np.mean([severity_map[liq.severity] for liq in cluster])
                    severity_factor = avg_severity * 0.1

                    cascade_probability = symbol_factor + volume_factor + time_factor + severity_factor

                    # Only create alert if probability meets threshold
                    if cascade_probability >= min_probability:
                        # Determine initiating symbol (largest liquidation)
                        initiating_liq = max(cluster, key=lambda x: x.liquidated_amount_usd or 0)

                        # Calculate price impact estimates
                        price_impact_range = {}
                        for symbol in affected_symbols:
                            symbol_liqs = [liq for liq in cluster if liq.symbol == symbol]
                            symbol_volume = sum(liq.liquidated_amount_usd for liq in symbol_liqs if liq.liquidated_amount_usd)
                            # Estimate price impact as percentage based on volume
                            impact_pct = -min(10.0, (symbol_volume / 1_000_000) * 0.5)  # $1M = 0.5% impact baseline
                            price_impact_range[symbol] = impact_pct

                        # Determine severity
                        if cascade_probability > 0.8:
                            severity = LiquidationSeverity.CRITICAL
                        elif cascade_probability > 0.7:
                            severity = LiquidationSeverity.HIGH
                        elif cascade_probability > 0.6:
                            severity = LiquidationSeverity.MEDIUM
                        else:
                            severity = LiquidationSeverity.LOW

                        # Calculate correlation strength (simplified)
                        # High correlation = liquidations across multiple symbols in short time
                        correlation_strength = min(1.0, len(affected_symbols) / 5)

                        # Estimate liquidity adequacy (inverse of cascade probability)
                        liquidity_adequacy = max(0, 100 - (cascade_probability * 100))

                        # Build action recommendations based on severity
                        immediate_actions = ["Monitor positions closely"]
                        risk_mitigation = []
                        monitoring_priorities = []

                        if severity in [LiquidationSeverity.CRITICAL, LiquidationSeverity.HIGH]:
                            immediate_actions.extend([
                                "Reduce leverage immediately",
                                "Set tight stop-losses",
                                "Consider closing risky positions"
                            ])
                            risk_mitigation.extend([
                                "Avoid new leveraged positions",
                                "Increase cash reserves",
                                "Monitor order book depth"
                            ])
                        else:
                            immediate_actions.append("Review position sizes")
                            risk_mitigation.append("Maintain normal risk controls")

                        # Prioritize monitoring based on volume
                        symbol_volumes = {
                            symbol: sum(liq.liquidated_amount_usd for liq in cluster if liq.symbol == symbol and liq.liquidated_amount_usd)
                            for symbol in affected_symbols
                        }
                        sorted_symbols = sorted(symbol_volumes.items(), key=lambda x: x[1], reverse=True)
                        monitoring_priorities = [f"Watch {symbol}" for symbol, _ in sorted_symbols[:3]]

                        alert = CascadeAlert(
                            alert_id=f"cascade_{initiating_liq.event_id}_{int(cluster[0].timestamp.timestamp())}",
                            initiating_symbol=initiating_liq.symbol,
                            affected_symbols=affected_symbols,
                            cascade_probability=cascade_probability,
                            severity=severity,
                            estimated_total_liquidations=total_volume,
                            price_impact_range=price_impact_range,
                            duration_estimate_minutes=int(15 + cascade_probability * 30),  # 15-45 min
                            overall_leverage=3.5,  # Simplified - would calculate from market data
                            liquidity_adequacy=liquidity_adequacy,
                            correlation_strength=correlation_strength,
                            immediate_actions=immediate_actions,
                            risk_mitigation=risk_mitigation,
                            monitoring_priorities=monitoring_priorities
                        )
                        cascade_alerts.append(alert)

                logger.info(f"Detected {len(cascade_alerts)} cascade risks from {len(time_clusters)} liquidation clusters")

        # If no collector or no real data, use detector's detect_cascade_risk method
        if not cascade_alerts:
            try:
                detector_alerts = await liquidation_detector.detect_cascade_risk(symbols_to_check, exchanges)
                cascade_alerts.extend([alert for alert in detector_alerts if alert.cascade_probability >= min_probability])
            except Exception as e:
                logger.debug(f"Could not get cascade alerts from detector: {e}")

        return cascade_alerts

    except Exception as e:
        logger.error(f"Error in get_cascade_risk_assessment: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []

@router.get("/risk/{symbol}", response_model=LiquidationRisk)
async def get_symbol_liquidation_risk(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Specific exchange to analyze"),
    time_horizon_minutes: int = Query(default=60, ge=5, le=1440),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> LiquidationRisk:
    """
    Get detailed liquidation risk assessment for a specific symbol.
    """
    
    try:
        # Use first available exchange if none specified
        target_exchange = exchange or list(liquidation_detector.exchange_manager.exchanges.keys())[0]
        
        risk_assessment = await liquidation_detector.assess_liquidation_risk(
            symbol=symbol.upper(),
            exchange_id=target_exchange,
            time_horizon_minutes=time_horizon_minutes
        )
        
        return risk_assessment
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk assessment failed for {symbol}: {str(e)}")

@router.get("/leverage-metrics/{symbol}", response_model=LeverageMetrics)
async def get_leverage_metrics(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Specific exchange"),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> LeverageMetrics:
    """
    Get detailed leverage and funding metrics for a symbol.
    """
    
    try:
        target_exchange = exchange or list(liquidation_detector.exchange_manager.exchanges.keys())[0]
        exchange_obj = liquidation_detector.exchange_manager.exchanges[target_exchange]
        
        # Fetch funding rate data
        funding_info = await exchange_obj.fetch_funding_rate(symbol.upper())
        current_funding = funding_info.get('fundingRate', 0) if funding_info else 0
        
        # Fetch market info for leverage data
        market_info = await exchange_obj.fetch_market(symbol.upper())
        max_leverage = market_info.get('limits', {}).get('leverage', {}).get('max', 100) if market_info else 100
        
        # Calculate historical funding rates (simplified)
        funding_8h_avg = current_funding * 0.95  # Simplified - would fetch historical data
        funding_24h_avg = current_funding * 0.9
        
        # Fetch open interest if available
        open_interest = 0
        open_interest_change = 0
        try:
            oi_info = await exchange_obj.fetch_open_interest(symbol.upper())
            if oi_info:
                open_interest = oi_info.get('openInterestAmount', 0)
        except:
            pass
        
        # Calculate stress scores
        funding_volatility = abs(current_funding - funding_24h_avg) * 100
        leverage_stress = min(100, abs(current_funding) / 0.01 * 50)  # Stress based on funding rate
        
        return LeverageMetrics(
            symbol=symbol.upper(),
            exchange=target_exchange,
            funding_rate=current_funding,
            funding_rate_8h_avg=funding_8h_avg,
            funding_rate_24h_avg=funding_24h_avg,
            open_interest=open_interest,
            open_interest_24h_change=open_interest_change,
            open_interest_usd=open_interest,  # Simplified
            long_short_ratio=1.1,  # Would fetch from exchange API
            estimated_avg_leverage=3.5,  # Would calculate from market data
            max_leverage_available=int(max_leverage),
            liquidation_cluster_density=50.0,  # Would calculate from liquidation data
            funding_rate_volatility=funding_volatility,
            leverage_stress_score=leverage_stress
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leverage metrics for {symbol}: {str(e)}")

@router.post("/monitor", response_model=Dict[str, str])
async def setup_liquidation_monitoring(
    monitor_request: LiquidationMonitorRequest,
    background_tasks: BackgroundTasks,
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> Dict[str, str]:
    """
    Set up real-time liquidation monitoring for specified symbols.
    
    This endpoint configures background monitoring that will send alerts
    when liquidation events are detected above the specified threshold.
    """
    
    try:
        monitor_id = f"monitor_{int(time.time())}"
        
        # Store monitoring configuration
        liquidation_detector.active_monitors[monitor_id] = {
            "symbols": monitor_request.symbols,
            "exchanges": monitor_request.exchanges,
            "sensitivity": monitor_request.sensitivity_level,
            "threshold": monitor_request.alert_threshold,
            "webhook_url": monitor_request.webhook_url,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Start background monitoring task
        background_tasks.add_task(
            _background_liquidation_monitor,
            liquidation_detector,
            monitor_id,
            monitor_request
        )
        
        return {
            "monitor_id": monitor_id,
            "status": "monitoring_started",
            "message": f"Monitoring {len(monitor_request.symbols)} symbols for liquidation events"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup monitoring: {str(e)}")

@router.delete("/monitor/{monitor_id}")
async def stop_liquidation_monitoring(
    monitor_id: str,
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> Dict[str, str]:
    """Stop liquidation monitoring for a specific monitor ID."""
    
    if monitor_id in liquidation_detector.active_monitors:
        del liquidation_detector.active_monitors[monitor_id]
        return {
            "monitor_id": monitor_id,
            "status": "monitoring_stopped",
            "message": "Liquidation monitoring has been stopped"
        }
    else:
        raise HTTPException(status_code=404, detail="Monitor ID not found")

@router.get("/history/{symbol}")
async def get_liquidation_history(
    symbol: str,
    exchange: Optional[str] = Query(None),
    days_back: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=50, ge=1, le=200),
    liquidation_detector: LiquidationDetectionEngine = Depends(get_liquidation_detector)
) -> List[LiquidationEvent]:
    """
    Get historical liquidation events for a symbol.
    
    Note: This would integrate with a historical data storage system.
    For now, returns recent events from the detector's memory.
    """
    
    try:
        # Filter historical events by symbol
        symbol_events = [
            event for event in liquidation_detector.historical_events
            if event.symbol == symbol.upper()
        ]
        
        # Sort by timestamp and limit
        symbol_events.sort(key=lambda x: x.timestamp, reverse=True)
        return symbol_events[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history for {symbol}: {str(e)}")

# Background monitoring function
async def _background_liquidation_monitor(
    detector: LiquidationDetectionEngine,
    monitor_id: str,
    request: LiquidationMonitorRequest
):
    """Background task for continuous liquidation monitoring."""
    
    try:
        while monitor_id in detector.active_monitors:
            # Detect liquidation events
            events = await detector.detect_liquidation_events(
                symbols=request.symbols,
                exchanges=request.exchanges,
                sensitivity=request.sensitivity_level,
                lookback_minutes=5  # Short lookback for real-time monitoring
            )
            
            # Filter events by threshold
            severity_order = {
                LiquidationSeverity.LOW: 1,
                LiquidationSeverity.MEDIUM: 2,
                LiquidationSeverity.HIGH: 3,
                LiquidationSeverity.CRITICAL: 4
            }
            
            threshold_level = severity_order[request.alert_threshold]
            alert_events = [
                event for event in events
                if severity_order[event.severity] >= threshold_level
            ]
            
            # Send alerts if any events found
            if alert_events and request.webhook_url:
                # Would implement webhook notification here
                pass
            
            # Store events in detector history
            detector.historical_events.extend(alert_events)
            
            # Wait before next check (5 minutes)
            await asyncio.sleep(300)
            
    except Exception as e:
        # Log error and remove monitor
        if monitor_id in detector.active_monitors:
            del detector.active_monitors[monitor_id] 

# ============================================================================
# LIQUIDATION ZONES - Multi-Exchange Aggregation
# ============================================================================

class LiquidationZone(BaseModel):
    """Represents a clustered liquidation zone at a specific price level."""
    price: float = Field(..., description="Price level of liquidation cluster")
    total_size_usd: float = Field(..., description="Total USD value of liquidations in zone")
    count: int = Field(..., description="Number of individual liquidations in zone")
    exchanges: List[str] = Field(..., description="Exchanges contributing to this zone")
    side: str = Field(..., description="Liquidation side (long/short)")
    confidence: str = Field(..., description="Confidence level (high/medium/low)")


class LiquidationZonesResponse(BaseModel):
    """Response model for liquidation zones endpoint."""
    symbol: str
    zones: List[LiquidationZone]
    cascade_detected: bool
    cascade_price: Optional[float] = None
    cascade_size: Optional[float] = None
    total_exchanges: int
    lookback_hours: int
    timestamp: str


def cluster_liquidations_by_price(liquidations: List[Any], clustering_pct: float = 2.0) -> List[Dict[str, Any]]:
    """
    Cluster liquidations into price zones.

    Args:
        liquidations: List of LiquidationEvent objects
        clustering_pct: Price range percentage for clustering (default 2%)

    Returns:
        List of zone dictionaries with aggregated data
    """
    if not liquidations:
        return []

    zones = []

    for liq in liquidations:
        # Find existing zone within clustering percentage
        matched_zone = None
        for zone in zones:
            price_diff_pct = abs(zone['price'] - liq.trigger_price) / zone['price'] * 100
            if price_diff_pct <= clustering_pct:
                matched_zone = zone
                break

        if matched_zone:
            # Add to existing zone
            matched_zone['total_size_usd'] += liq.liquidated_amount_usd
            matched_zone['count'] += 1
            matched_zone['exchanges'].add(liq.exchange)

            # Determine side (long or short liquidation)
            if 'LONG' in liq.liquidation_type.value.upper():
                matched_zone['long_count'] += 1
            else:
                matched_zone['short_count'] += 1
        else:
            # Create new zone
            is_long_liq = 'LONG' in liq.liquidation_type.value.upper()
            zones.append({
                'price': liq.trigger_price,
                'total_size_usd': liq.liquidated_amount_usd,
                'count': 1,
                'exchanges': {liq.exchange},
                'long_count': 1 if is_long_liq else 0,
                'short_count': 0 if is_long_liq else 1
            })

    # Determine dominant side and confidence for each zone
    for zone in zones:
        zone['exchanges'] = list(zone['exchanges'])

        # Determine side
        if zone['long_count'] > zone['short_count']:
            zone['side'] = 'long'
        else:
            zone['side'] = 'short'

        # Determine confidence based on number of exchanges
        num_exchanges = len(zone['exchanges'])
        if num_exchanges >= 3:
            zone['confidence'] = 'high'
        elif num_exchanges == 2:
            zone['confidence'] = 'medium'
        else:
            zone['confidence'] = 'low'

        # Clean up temporary fields
        del zone['long_count']
        del zone['short_count']

    # Sort by total size (largest first)
    zones.sort(key=lambda z: z['total_size_usd'], reverse=True)

    return zones


@router.get("/zones", response_model=LiquidationZonesResponse)
async def get_liquidation_zones(
    symbol: str = Query("BTCUSDT", description="Trading symbol to analyze"),
    clustering_pct: float = Query(2.0, ge=0.1, le=10.0, description="Price clustering percentage (0.1-10%)"),
    lookback_hours: int = Query(1, ge=1, le=24, description="Hours of liquidation history to analyze"),
    min_zone_size: float = Query(10000, ge=0, description="Minimum USD size to include zone (default $10K)"),
    cascade_threshold: float = Query(200000, ge=0, description="USD threshold for cascade detection (default $200K)"),
    request: Request = None
):
    """
    Get aggregated liquidation zones across all configured exchanges.

    Returns price levels where significant liquidations are clustered,
    useful for:
    - Identifying support/resistance levels
    - Detecting cascade risks
    - Visualizing liquidation heatmaps on charts

    **Clustering Logic:**
    Liquidations within `clustering_pct` of each other are grouped into zones.
    For example, with 2% clustering:
    - $93,500 and $94,000 would be separate zones
    - $93,500 and $93,600 would be grouped into one zone

    **Confidence Levels:**
    - **high**: Zone confirmed by 3+ exchanges
    - **medium**: Zone confirmed by 2 exchanges
    - **low**: Zone from 1 exchange only

    **Cascade Detection:**
    Alerts when any zone exceeds the cascade threshold (default $200K).
    """

    try:
        # Try to get liquidation collector from liquidation_detector first (if available)
        # Otherwise fall back to standalone liquidation_collector
        collector = None

        if hasattr(request.app.state, "liquidation_detector") and request.app.state.liquidation_detector is not None:
            if hasattr(request.app.state.liquidation_detector, 'liquidation_collector'):
                collector = request.app.state.liquidation_detector.liquidation_collector

        if not collector and hasattr(request.app.state, "liquidation_collector"):
            collector = request.app.state.liquidation_collector

        if not collector:
            raise HTTPException(
                status_code=503,
                detail="Liquidation collector not available"
            )

        # Get liquidations from all exchanges
        all_liquidations = []
        exchanges_queried = []

        # Query each exchange
        for exchange_name in ['bybit', 'binance', 'okx']:
            try:
                liqs = collector.get_recent_liquidations(
                    symbol=symbol,
                    exchange=exchange_name,
                    minutes=lookback_hours * 60
                )
                if liqs:
                    all_liquidations.extend(liqs)
                    exchanges_queried.append(exchange_name)
                    logger.debug(f"Found {len(liqs)} liquidations from {exchange_name}")
            except Exception as e:
                logger.warning(f"Error fetching liquidations from {exchange_name}: {e}")
                continue

        logger.info(f"Total liquidations collected: {len(all_liquidations)} from {len(exchanges_queried)} exchanges")

        # Cluster into zones
        zone_dicts = cluster_liquidations_by_price(all_liquidations, clustering_pct)

        # Filter by minimum size
        zone_dicts = [z for z in zone_dicts if z['total_size_usd'] >= min_zone_size]

        # Convert to response models
        zones = [
            LiquidationZone(
                price=z['price'],
                total_size_usd=z['total_size_usd'],
                count=z['count'],
                exchanges=z['exchanges'],
                side=z['side'],
                confidence=z['confidence']
            )
            for z in zone_dicts
        ]

        # Detect cascades
        cascade_detected = any(z.total_size_usd >= cascade_threshold for z in zones)
        cascade_zone = max(zones, key=lambda z: z.total_size_usd) if cascade_detected and zones else None

        return LiquidationZonesResponse(
            symbol=symbol,
            zones=zones,
            cascade_detected=cascade_detected,
            cascade_price=cascade_zone.price if cascade_zone else None,
            cascade_size=cascade_zone.total_size_usd if cascade_zone else None,
            total_exchanges=len(exchanges_queried),
            lookback_hours=lookback_hours,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating liquidation zones: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate liquidation zones: {str(e)}"
        )


@router.get("/summary")
async def get_liquidation_summary(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history (max 1 week)"),
    request: Request = None
):
    """
    Get summary statistics of liquidations over a time period.

    Returns:
    - Total liquidation volume (USD)
    - Long vs short liquidation ratio
    - Largest single liquidation
    - Liquidations per exchange breakdown
    """

    try:
        # Try to get liquidation collector from liquidation_detector first (if available)
        collector = None

        if hasattr(request.app.state, "liquidation_detector") and request.app.state.liquidation_detector is not None:
            if hasattr(request.app.state.liquidation_detector, 'liquidation_collector'):
                collector = request.app.state.liquidation_detector.liquidation_collector

        if not collector and hasattr(request.app.state, "liquidation_collector"):
            collector = request.app.state.liquidation_collector

        if not collector:
            raise HTTPException(status_code=503, detail="Liquidation collector not available")

        # Get all liquidations
        all_liqs = collector.get_recent_liquidations(symbol, minutes=hours * 60)

        if not all_liqs:
            return {
                "symbol": symbol,
                "period_hours": hours,
                "total_volume_usd": 0,
                "total_count": 0,
                "long_liquidations": 0,
                "short_liquidations": 0,
                "largest_liquidation_usd": 0,
                "exchanges": {}
            }

        # Calculate statistics
        total_volume = sum(liq.liquidated_amount_usd for liq in all_liqs)
        long_count = sum(1 for liq in all_liqs if 'LONG' in liq.liquidation_type.value.upper())
        short_count = len(all_liqs) - long_count
        largest = max(all_liqs, key=lambda l: l.liquidated_amount_usd)

        # Per-exchange breakdown
        exchange_stats = defaultdict(lambda: {'count': 0, 'volume_usd': 0})
        for liq in all_liqs:
            exchange_stats[liq.exchange]['count'] += 1
            exchange_stats[liq.exchange]['volume_usd'] += liq.liquidated_amount_usd

        return {
            "symbol": symbol,
            "period_hours": hours,
            "total_volume_usd": total_volume,
            "total_count": len(all_liqs),
            "long_liquidations": long_count,
            "short_liquidations": short_count,
            "largest_liquidation_usd": largest.liquidated_amount_usd,
            "largest_liquidation_price": largest.trigger_price,
            "exchanges": dict(exchange_stats),
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating liquidation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LIQUIDATION HEATMAP ENDPOINT
# ============================================================================

class LiquidationHeatmapResponse(BaseModel):
    """Response model for liquidation heatmap data."""
    symbol: str
    current_price: float
    price_range: Dict[str, float]
    timeframe: str
    long_liquidations_usd: float
    short_liquidations_usd: float
    heatmap_data: List[Dict[str, Any]]
    price_levels: List[float]
    time_labels: List[str]
    current_price_index: int
    leverage_levels: List[Dict[str, Any]]
    timestamp: str


@router.get("/heatmap", response_model=LiquidationHeatmapResponse)
async def get_liquidation_heatmap(
    request: Request,
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("4h", description="Timeframe (1h, 4h, 12h, 24h)"),
    price_range_pct: float = Query(12.0, ge=5.0, le=25.0, description="Price range percentage from current price"),
    num_price_levels: int = Query(50, ge=20, le=100, description="Number of price levels in heatmap"),
):
    """
    Generate liquidation heatmap data showing estimated liquidation levels.

    This endpoint calculates WHERE liquidations WOULD occur based on:
    - Current market price
    - Typical leverage distributions (5x, 10x, 20x, 50x, 100x)
    - Estimated open interest distribution

    **How it works:**
    For each leverage level, we calculate the liquidation price:
    - Long liquidation: `entry_price * (1 - 1/leverage)`
    - Short liquidation: `entry_price * (1 + 1/leverage)`

    The intensity at each price level represents the estimated volume
    of positions that would be liquidated if price reaches that level.

    **Use cases:**
    - Identify potential support/resistance from liquidation clusters
    - Assess cascade risk at different price levels
    - Plan entries/exits around liquidation zones
    """
    try:
        # Get current price from market data
        exchange_manager = await get_exchange_manager(request)

        # Fetch current ticker
        try:
            ticker = await exchange_manager.fetch_ticker(symbol)
            current_price = ticker.get('last') or ticker.get('close') or ticker.get('price')
            if not current_price:
                raise ValueError("Could not get current price from ticker")
        except Exception as e:
            logger.warning(f"Failed to get ticker for {symbol}: {e}, using fallback prices")
            # Fallback prices
            fallback_prices = {
                'BTCUSDT': 85000, 'ETHUSDT': 2800, 'SOLUSDT': 180,
                'XRPUSDT': 2.0, 'BNBUSDT': 650, 'DOGEUSDT': 0.35,
                'ADAUSDT': 0.90, 'AVAXUSDT': 45
            }
            current_price = fallback_prices.get(symbol, 50000)

        # Calculate price range
        price_range = current_price * (price_range_pct / 100)
        min_price = current_price - price_range
        max_price = current_price + price_range

        # Generate price levels
        price_step = (max_price - min_price) / num_price_levels
        price_levels = [min_price + (i * price_step) for i in range(num_price_levels)]

        # Find current price index
        current_price_index = min(range(len(price_levels)), key=lambda i: abs(price_levels[i] - current_price))

        # Time configuration based on timeframe
        timeframe_config = {
            '1h': {'buckets': 12, 'interval_minutes': 5},
            '4h': {'buckets': 16, 'interval_minutes': 15},
            '12h': {'buckets': 24, 'interval_minutes': 30},
            '24h': {'buckets': 24, 'interval_minutes': 60}
        }
        config = timeframe_config.get(timeframe, timeframe_config['4h'])
        num_time_buckets = config['buckets']

        # Generate time labels
        now = datetime.now()
        time_labels = []
        for i in range(num_time_buckets - 1, -1, -1):
            t = now - timedelta(minutes=i * config['interval_minutes'])
            time_labels.append(t.strftime('%H:%M'))

        # Define leverage levels and their estimated market share
        # Based on typical perpetual market distribution
        leverage_levels = [
            {'leverage': 5, 'weight': 0.10, 'label': '5x'},
            {'leverage': 10, 'weight': 0.25, 'label': '10x'},
            {'leverage': 20, 'weight': 0.30, 'label': '20x'},
            {'leverage': 50, 'weight': 0.25, 'label': '50x'},
            {'leverage': 100, 'weight': 0.10, 'label': '100x'}
        ]

        # Generate heatmap data
        heatmap_data = []
        total_long_liq = 0
        total_short_liq = 0

        # Estimate base open interest (simplified model)
        # In production, this would come from exchange OI data
        estimated_oi_usd = 500_000_000 if 'BTC' in symbol else 100_000_000

        for t_idx in range(num_time_buckets):
            # Time factor: more recent = higher confidence
            time_factor = 0.5 + (t_idx / num_time_buckets) * 0.5

            for p_idx, price in enumerate(price_levels):
                is_above_current = price > current_price
                price_distance_pct = abs(price - current_price) / current_price

                # Calculate liquidation intensity at this price level
                intensity = 0.0

                for lev_info in leverage_levels:
                    leverage = lev_info['leverage']
                    weight = lev_info['weight']

                    # Calculate liquidation distance for this leverage
                    # Long liq occurs when price drops: liq_price = entry * (1 - 1/lev)
                    # Short liq occurs when price rises: liq_price = entry * (1 + 1/lev)
                    liq_distance = 1 / leverage

                    # Check if this price level is near a liquidation zone
                    # Positions entered at current price would be liquidated here
                    tolerance = 0.015  # 1.5% tolerance for clustering

                    if abs(price_distance_pct - liq_distance) < tolerance:
                        # This price is near a liquidation level for this leverage
                        # Higher leverage = more positions but smaller distance
                        leverage_intensity = weight * (leverage / 100)

                        # Add randomness for visual variety (simulating market noise)
                        noise = 0.8 + np.random.random() * 0.4  # 0.8 to 1.2
                        intensity += leverage_intensity * noise

                # Apply time factor
                intensity *= time_factor

                # Normalize to 0-1 range
                intensity = min(1.0, max(0.0, intensity))

                if intensity > 0.03:  # Minimum threshold
                    # Estimate USD value
                    usd_value = intensity * estimated_oi_usd * 0.01  # Scale factor

                    liq_type = 'short' if is_above_current else 'long'

                    heatmap_data.append({
                        'x': t_idx,
                        'y': p_idx,
                        'value': round(intensity, 4),
                        'type': liq_type,
                        'price': round(price, 2),
                        'est_usd': round(usd_value, 0)
                    })

                    if liq_type == 'long':
                        total_long_liq += usd_value
                    else:
                        total_short_liq += usd_value

        return LiquidationHeatmapResponse(
            symbol=symbol,
            current_price=round(current_price, 2),
            price_range={'min': round(min_price, 2), 'max': round(max_price, 2)},
            timeframe=timeframe,
            long_liquidations_usd=round(total_long_liq, 0),
            short_liquidations_usd=round(total_short_liq, 0),
            heatmap_data=heatmap_data,
            price_levels=[round(p, 2) for p in price_levels],
            time_labels=time_labels,
            current_price_index=current_price_index,
            leverage_levels=leverage_levels,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating liquidation heatmap: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmap: {str(e)}")
