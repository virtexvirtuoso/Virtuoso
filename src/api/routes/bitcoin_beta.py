from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/status")
async def get_bitcoin_beta_status() -> Dict[str, Any]:
    """Get Bitcoin Beta analysis status and latest metrics."""
    try:
        # Import here to avoid circular imports
        from src.reports.bitcoin_beta_report import BitcoinBetaReport
        
        # Initialize reporter
        reporter = BitcoinBetaReport()
        
        # Get latest beta analysis
        try:
            beta_data = await reporter.get_latest_beta_analysis()
            
            return {
                "status": "active",
                "timestamp": datetime.utcnow().isoformat(),
                "beta_coefficient": beta_data.get("beta_coefficient", 0.0),
                "correlation": beta_data.get("correlation", 0.0),
                "r_squared": beta_data.get("r_squared", 0.0),
                "alpha": beta_data.get("alpha", 0.0),
                "volatility_ratio": beta_data.get("volatility_ratio", 0.0),
                "last_update": beta_data.get("timestamp", datetime.utcnow().isoformat()),
                "analysis_period": beta_data.get("analysis_period", "30d"),
                "market_regime": beta_data.get("market_regime", "neutral"),
                "confidence_level": beta_data.get("confidence_level", 0.0)
            }
            
        except Exception as e:
            logger.warning(f"Could not get latest beta analysis: {e}")
            # Return default/mock data if analysis fails
            return {
                "status": "inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "beta_coefficient": 0.0,
                "correlation": 0.0,
                "r_squared": 0.0,
                "alpha": 0.0,
                "volatility_ratio": 0.0,
                "last_update": datetime.utcnow().isoformat(),
                "analysis_period": "30d",
                "market_regime": "neutral",
                "confidence_level": 0.0,
                "message": "Beta analysis temporarily unavailable"
            }
            
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Bitcoin Beta status: {str(e)}")

@router.get("/analysis")
async def get_bitcoin_beta_analysis() -> Dict[str, Any]:
    """Get detailed Bitcoin Beta analysis."""
    try:
        from src.reports.bitcoin_beta_report import BitcoinBetaReporter
        
        reporter = BitcoinBetaReporter()
        analysis = await reporter.generate_analysis()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis: {str(e)}")

@router.get("/health")
async def bitcoin_beta_health() -> Dict[str, Any]:
    """Health check for Bitcoin Beta service."""
    try:
        from src.reports.bitcoin_beta_report import BitcoinBetaReporter
        
        # Test reporter initialization
        reporter = BitcoinBetaReporter()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "bitcoin_beta",
            "version": "1.0.0"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "bitcoin_beta",
            "error": str(e)
        } 