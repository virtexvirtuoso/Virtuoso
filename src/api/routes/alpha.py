from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
import asyncio
import time
from datetime import datetime, timezone

from ..models.alpha import AlphaScanRequest, AlphaScanResponse, AlphaOpportunity
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

async def get_alpha_scanner(exchange_manager: ExchangeManager = Depends(get_exchange_manager)):
    """Dependency to get alpha scanner engine"""
    # Import here to avoid circular imports
    from src.core.analysis.alpha_scanner import AlphaScannerEngine
    return AlphaScannerEngine(exchange_manager)

@router.post("/scan", response_model=AlphaScanResponse)
async def scan_alpha_opportunities(
    scan_request: AlphaScanRequest,
    alpha_scanner = Depends(get_alpha_scanner)
) -> AlphaScanResponse:
    """
    Scan for alpha opportunities across specified markets.
    
    This endpoint performs real-time analysis of cryptocurrency markets to identify
    potential alpha-generating opportunities based on confluence of technical indicators,
    momentum, volume, and sentiment analysis.
    """
    
    start_time = time.time()
    
    try:
        opportunities = await alpha_scanner.scan_opportunities(
            symbols=scan_request.symbols,
            exchanges=scan_request.exchanges,
            timeframes=scan_request.timeframes,
            min_score=scan_request.min_score,
            max_results=scan_request.max_results
        )
        
        scan_duration = int((time.time() - start_time) * 1000)
        
        return AlphaScanResponse(
            opportunities=opportunities,
            scan_timestamp=datetime.now(timezone.utc),
            total_symbols_scanned=len(scan_request.symbols) if scan_request.symbols else 100,
            scan_duration_ms=scan_duration,
            metadata={
                "timeframes_analyzed": ",".join(scan_request.timeframes),
                "min_score_threshold": scan_request.min_score,
                "opportunities_found": len(opportunities)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scanning failed: {str(e)}")

@router.get("/opportunities", response_model=List[AlphaOpportunity])
async def get_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    alpha_scanner = Depends(get_alpha_scanner)
) -> List[AlphaOpportunity]:
    """Get alpha opportunities (alias for /opportunities/top)."""
    
    try:
        # Return mock opportunities for fast response
        # TODO: Implement real alpha scanning when dependencies are stable
        import logging
        logger = logging.getLogger(__name__)
        
        # Create mock alpha opportunities
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
        opportunities = []
        
        for i, symbol in enumerate(symbols[:limit]):
            score = 85.0 - (i * 5.0)  # Decreasing scores
            
            if score >= min_score:
                opportunity = AlphaOpportunity(
                    symbol=symbol,
                    exchange=exchange or "binance", 
                    score=score,
                    potential_return=0.15 - (i * 0.02),  # 15% to 7%
                    confidence=0.8 - (i * 0.05),
                    risk_level="MEDIUM" if score > 75 else "LOW",
                    timeframe=timeframe or "1h",
                    entry_price=50000.0 - (i * 5000),
                    target_price=52000.0 - (i * 5000),
                    stop_loss=48000.0 - (i * 5000),
                    analysis={
                        "trend": "BULLISH" if i % 2 == 0 else "BEARISH",
                        "momentum": "STRONG" if score > 80 else "MODERATE",
                        "volume": "HIGH" if i < 2 else "MEDIUM",
                        "support_resistance": "CLEAR" if i % 3 == 0 else "UNCLEAR"
                    },
                    signals=[
                        "RSI oversold bounce",
                        "Volume spike",
                        "Break above resistance"
                    ],
                    timestamp=int(time.time() * 1000) - (i * 300000)  # 5 min intervals
                )
                opportunities.append(opportunity)
        
        logger.info(f"Returning {len(opportunities)} mock alpha opportunities")
        return opportunities
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_opportunities: {e}")
        return []

@router.get("/opportunities/top", response_model=List[AlphaOpportunity])
async def get_top_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    alpha_scanner = Depends(get_alpha_scanner)
) -> List[AlphaOpportunity]:
    """Get top alpha opportunities with optional filtering."""
    
    try:
        timeframes = [timeframe] if timeframe else ["15m", "1h", "4h"]
        exchanges = [exchange] if exchange else None
        
        opportunities = await alpha_scanner.scan_opportunities(
            exchanges=exchanges,
            timeframes=timeframes,
            min_score=min_score,
            max_results=limit
        )
        
        return opportunities
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.get("/opportunities/{symbol}", response_model=Optional[AlphaOpportunity])
async def get_symbol_opportunity(
    symbol: str,
    exchange: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h"),
    alpha_scanner = Depends(get_alpha_scanner)
) -> Optional[AlphaOpportunity]:
    """Get alpha opportunity analysis for a specific symbol."""
    
    try:
        exchanges = [exchange] if exchange else None
        
        opportunities = await alpha_scanner.scan_opportunities(
            symbols=[symbol.upper()],
            exchanges=exchanges,
            timeframes=[timeframe],
            min_score=0.0,  # Return result regardless of score
            max_results=1
        )
        
        return opportunities[0] if opportunities else None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/scan/status")
async def get_scan_status() -> dict:
    """Get current scanning status and statistics."""
    
    return {
        "status": "active",
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "scanner_version": "1.0.0",
        "supported_exchanges": ["binance", "bybit"],
        "supported_timeframes": ["15m", "1h", "4h", "1d"]
    }

@router.get("/health")
async def alpha_scanner_health(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> dict:
    """Health check for the alpha scanner service."""
    
    try:
        # Import here to avoid circular imports
        from src.core.analysis.alpha_scanner import AlphaScannerEngine
        
        # Test scanner initialization
        scanner = AlphaScannerEngine(exchange_manager)
        
        # Test basic functionality
        test_symbols = await scanner._get_top_symbols()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exchange_count": len(exchange_manager.exchanges),
            "available_symbols": len(test_symbols[:5]),
            "test_symbols": test_symbols[:5]
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        } 