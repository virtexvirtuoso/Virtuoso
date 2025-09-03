from typing import Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionCalculator:
    """Position Calculator for Risk Management"""
    
    def __init__(self):
        self.default_risk_percentage = 1.0  # Default risk of 1% per trade
        self.max_risk_percentage = 2.0  # Maximum risk of 2% per trade
        self.min_position_size = 0.001  # Minimum position size in base currency
        
    async def calculate_position_size(
        self,
        exchange_id: str,
        symbol: str,
        risk_percentage: Optional[float] = None,
        stop_loss: Optional[float] = None,
        entry_price: Optional[float] = None,
        account_balance: Optional[float] = None
    ) -> float:
        """Calculate position size based on risk parameters"""
        try:
            # Validate and set risk percentage
            risk_percentage = self._validate_risk_percentage(risk_percentage)
            
            # If no account balance provided, return minimum position size
            if not account_balance:
                logger.warning("No account balance provided, using minimum position size")
                return self.min_position_size
                
            # Calculate risk amount in quote currency
            risk_amount = account_balance * (risk_percentage / 100)
            
            # If stop loss and entry price provided, calculate based on actual risk
            if stop_loss and entry_price:
                risk_per_unit = abs(entry_price - stop_loss)
                if risk_per_unit > 0:
                    position_size = risk_amount / risk_per_unit
                else:
                    logger.warning("Invalid risk per unit, using minimum position size")
                    return self.min_position_size
            else:
                # Use a default 2% price movement as risk
                position_size = risk_amount / (entry_price * 0.02)
                
            # Apply minimum position size constraint
            position_size = max(position_size, self.min_position_size)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            raise
            
    def _validate_risk_percentage(self, risk_percentage: Optional[float]) -> float:
        """Validate and normalize risk percentage"""
        if risk_percentage is None:
            return self.default_risk_percentage
            
        if risk_percentage <= 0:
            logger.warning("Risk percentage must be positive, using default")
            return self.default_risk_percentage
            
        if risk_percentage > self.max_risk_percentage:
            logger.warning(f"Risk percentage exceeds maximum ({self.max_risk_percentage}%), using maximum")
            return self.max_risk_percentage
            
        return risk_percentage
        
    async def calculate_stop_loss(
        self,
        entry_price: float,
        risk_percentage: float,
        atr_value: Optional[float] = None,
        position_type: str = "long"
    ) -> float:
        """Calculate stop loss price based on risk parameters"""
        try:
            # Validate inputs
            if entry_price <= 0:
                raise ValueError("Entry price must be positive")
                
            # If ATR available, use it for stop loss calculation
            if atr_value:
                # Use 2x ATR for stop loss distance
                stop_distance = atr_value * 2
            else:
                # Use risk percentage of entry price
                stop_distance = entry_price * (risk_percentage / 100)
                
            # Calculate stop loss price based on position type
            if position_type.lower() == "long":
                stop_loss = entry_price - stop_distance
            else:  # Short position
                stop_loss = entry_price + stop_distance
                
            return max(stop_loss, 0)  # Ensure stop loss is not negative
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {str(e)}")
            raise
            
    async def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        risk_reward_ratio: float = 2.0,
        position_type: str = "long"
    ) -> float:
        """Calculate take profit price based on risk/reward ratio"""
        try:
            # Validate inputs
            if entry_price <= 0:
                raise ValueError("Entry price must be positive")
            if stop_loss <= 0:
                raise ValueError("Stop loss must be positive")
            if risk_reward_ratio <= 0:
                raise ValueError("Risk/reward ratio must be positive")
                
            # Calculate risk (distance to stop loss)
            risk_distance = abs(entry_price - stop_loss)
            
            # Calculate take profit distance based on risk/reward ratio
            take_profit_distance = risk_distance * risk_reward_ratio
            
            # Calculate take profit price based on position type
            if position_type.lower() == "long":
                take_profit = entry_price + take_profit_distance
            else:  # Short position
                take_profit = entry_price - take_profit_distance
                
            return max(take_profit, 0)  # Ensure take profit is not negative
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {str(e)}")
            raise
            
    async def calculate_position_metrics(
        self,
        position_size: float,
        entry_price: float,
        current_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_type: str = "long"
    ) -> Dict:
        """Calculate various position metrics"""
        try:
            # Calculate position value
            position_value = position_size * current_price
            
            # Calculate unrealized PnL
            if position_type.lower() == "long":
                pnl = position_size * (current_price - entry_price)
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:  # Short position
                pnl = position_size * (entry_price - current_price)
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                
            # Calculate risk metrics if stop loss provided
            risk_amount = None
            reward_amount = None
            risk_reward_ratio = None
            
            if stop_loss:
                risk_amount = abs(position_size * (entry_price - stop_loss))
                if take_profit:
                    reward_amount = abs(position_size * (take_profit - entry_price))
                    if risk_amount > 0:
                        risk_reward_ratio = reward_amount / risk_amount
                        
            return {
                'position_value': position_value,
                'unrealized_pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'risk_amount': risk_amount,
                'reward_amount': reward_amount,
                'risk_reward_ratio': risk_reward_ratio,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error calculating position metrics: {str(e)}")
            raise 