"""
Risk Management API Routes

Provides endpoints for:
- Kill switch status and control
- Risk metrics and monitoring
- Position sizing information
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/kill-switch/status")
async def get_kill_switch_status() -> Dict[str, Any]:
    """
    Get current kill switch status and performance metrics.

    Returns:
        Dictionary containing:
        - state: Current kill switch state (monitoring/active/inactive)
        - is_active: Boolean indicating if kill switch is triggered
        - performance: SHORT signal performance metrics
        - thresholds: Trigger thresholds
        - multipliers: Current and available multiplier values
    """
    try:
        # Import kill switch module
        from src.core.risk.kill_switch import get_kill_switch
        from src.config.manager import ConfigManager

        # Get configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Get kill switch instance
        kill_switch = get_kill_switch(config)

        # Get current status
        status = kill_switch.get_status()

        return status

    except Exception as e:
        logger.error(f"Error getting kill switch status: {e}")

        # Return mock data if kill switch not available
        return {
            'state': 'monitoring',
            'is_active': False,
            'last_check_time': None,
            'performance': {
                'win_rate': 0.0,
                'closed_count': 0,
                'total_count': 0,
                'lookback_days': 7
            },
            'thresholds': {
                'min_win_rate': 0.35,
                'min_closed_signals': 20
            },
            'multipliers': {
                'legacy': {
                    'cvd': 35.0,
                    'oi': 30.0
                },
                'new': {
                    'cvd': 50.0,
                    'oi': 45.0
                },
                'current_mode': 'new'
            },
            'error': str(e),
            'note': 'Kill switch module not fully initialized'
        }


@router.post("/kill-switch/activate")
async def activate_kill_switch() -> Dict[str, Any]:
    """
    Manually activate the kill switch (revert to legacy multipliers).

    This endpoint requires authentication in production.
    Use with caution as it changes system behavior.

    Returns:
        Success status and updated kill switch state
    """
    try:
        from src.core.risk.kill_switch import get_kill_switch
        from src.config.manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.get_config()

        kill_switch = get_kill_switch(config)

        # Attempt activation
        success = kill_switch.activate()

        return {
            'success': success,
            'message': 'Kill switch activated' if success else 'Kill switch activation failed',
            'status': kill_switch.get_status()
        }

    except Exception as e:
        logger.error(f"Error activating kill switch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch() -> Dict[str, Any]:
    """
    Manually deactivate the kill switch (re-enable new multipliers).

    This endpoint requires authentication and manual override in production.
    Only use after investigating why the kill switch triggered.

    Returns:
        Success status and updated kill switch state
    """
    try:
        from src.core.risk.kill_switch import get_kill_switch
        from src.config.manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.get_config()

        kill_switch = get_kill_switch(config)

        # Attempt deactivation with manual override
        success = kill_switch.deactivate(manual_override=True)

        return {
            'success': success,
            'message': 'Kill switch deactivated' if success else 'Kill switch deactivation failed',
            'status': kill_switch.get_status()
        }

    except Exception as e:
        logger.error(f"Error deactivating kill switch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position-sizing")
async def get_position_sizing_info() -> Dict[str, Any]:
    """
    Get current position sizing configuration and validation status.

    Returns:
        Position sizing settings and risk parameters
    """
    try:
        from src.config.manager import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Extract position sizing config
        position_config = config.get('position_sizing', {})
        risk_config = config.get('risk_management', {})

        return {
            'position_sizing': {
                'enabled': position_config.get('enabled', False),
                'max_position_size_pct': position_config.get('max_position_size_pct', 0.0),
                'risk_per_trade_pct': position_config.get('risk_per_trade_pct', 0.0),
                'validation_mode': position_config.get('validation_mode', False)
            },
            'risk_management': {
                'max_drawdown_pct': risk_config.get('max_drawdown_pct', 0.0),
                'max_daily_loss_pct': risk_config.get('max_daily_loss_pct', 0.0),
                'max_concurrent_positions': risk_config.get('max_concurrent_positions', 0)
            },
            'timestamp': None
        }

    except Exception as e:
        logger.error(f"Error getting position sizing info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
