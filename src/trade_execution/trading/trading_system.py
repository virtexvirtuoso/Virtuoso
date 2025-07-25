"""Trading system module.

This module provides functionality for executing trades.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.validation import (
    ValidationResult,
    ValidationRule,
    ValidationService,
    AsyncValidationService,
    ValidationContext
)

logger = logging.getLogger(__name__)

class TradingSystem:
    """Manages trade execution."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        validation_service: Optional[AsyncValidationService] = None
    ):
        """Initialize trading system.
        
        Args:
            config: Configuration dictionary
            validation_service: Optional validation service
        """
        self.config = config
        self._validation_service = validation_service or AsyncValidationService()
        self.logger = logging.getLogger(__name__)
        
        # Initialize trading state
        self._active_trades = {}
        self._pending_orders = {}
        self._trade_history = []
        
        # Initialize statistics
        self._stats = {
            'trades_executed': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'errors': 0
        }
        
        # Initialize components
        self.data_manager = DataManager(config.get('data_manager', {}))
        self.position_manager = PositionManager(config.get('position_manager', {}))
        self.order_manager = OrderManager(config.get('order_manager', {}))
        self.risk_manager = RiskManager(config.get('risk_manager', {}))
        self.strategy_manager = StrategyManager(config.get('strategy_manager', {}))
        
        # State tracking
        self.initialized = False
        self.active_symbols: Set[str] = set()
        self.trading_enabled = False
        
        # Configuration
        self.max_symbols = config.get('max_symbols', 10)
        self.update_interval = config.get('update_interval', 1)  # 1 second
        self.risk_check_interval = config.get('risk_check_interval', 5)  # 5 seconds
        
        logger.debug("TradingSystem initialized with:")
        logger.debug(f"- Max symbols: {self.max_symbols}")
        logger.debug(f"- Update interval: {self.update_interval}s")
        logger.debug(f"- Risk check interval: {self.risk_check_interval}s")
        
    async def initialize(self) -> bool:
        """Initialize trading system components."""
        try:
            if self.initialized:
                return True
                
            logger.info("Initializing trading system")
            
            # Initialize components
            if not await self.data_manager.initialize():
                logger.error("Failed to initialize data manager")
                return False
                
            if not await self.position_manager.initialize():
                logger.error("Failed to initialize position manager")
                return False
                
            if not await self.order_manager.initialize():
                logger.error("Failed to initialize order manager")
                return False
                
            if not await self.risk_manager.initialize():
                logger.error("Failed to initialize risk manager")
                return False
                
            if not await self.strategy_manager.initialize():
                logger.error("Failed to initialize strategy manager")
                return False
                
            self.initialized = True
            logger.info("✓ Trading system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing trading system: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def cleanup(self) -> None:
        """Cleanup trading system components."""
        try:
            # Disable trading
            self.trading_enabled = False
            
            # Close all positions
            await self.close_all_positions()
            
            # Cancel all orders
            await self.cancel_all_orders()
            
            # Cleanup components
            await self.data_manager.cleanup()
            await self.position_manager.cleanup()
            await self.order_manager.cleanup()
            await self.risk_manager.cleanup()
            await self.strategy_manager.cleanup()
            
            self.initialized = False
            logger.info("✓ Trading system cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up trading system: {str(e)}")
            logger.debug(traceback.format_exc())
            
    async def start_trading(self) -> bool:
        """Start trading operations."""
        try:
            if not self.initialized:
                logger.error("Trading system not initialized")
                return False
                
            if self.trading_enabled:
                logger.warning("Trading already enabled")
                return True
                
            # Start trading tasks
            self.trading_enabled = True
            asyncio.create_task(self._update_loop())
            asyncio.create_task(self._risk_check_loop())
            
            logger.info("✓ Trading started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting trading: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def stop_trading(self) -> bool:
        """Stop trading operations."""
        try:
            if not self.trading_enabled:
                logger.warning("Trading already disabled")
                return True
                
            # Disable trading
            self.trading_enabled = False
            
            # Close all positions
            await self.close_all_positions()
            
            # Cancel all orders
            await self.cancel_all_orders()
            
            logger.info("✓ Trading stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping trading: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def add_symbol(self, symbol: str) -> bool:
        """Add symbol for trading.
        
        Args:
            symbol: Trading symbol to add
            
        Returns:
            bool: True if symbol added successfully
        """
        try:
            if len(self.active_symbols) >= self.max_symbols:
                logger.error(f"Maximum symbols ({self.max_symbols}) reached")
                return False
                
            if symbol in self.active_symbols:
                logger.warning(f"Symbol {symbol} already traded")
                return True
                
            # Add to data manager
            if not await self.data_manager.add_symbol(symbol):
                logger.error(f"Failed to add {symbol} to data manager")
                return False
                
            # Initialize position tracking
            if not await self.position_manager.add_symbol(symbol):
                logger.error(f"Failed to add {symbol} to position manager")
                return False
                
            # Initialize order tracking
            if not await self.order_manager.add_symbol(symbol):
                logger.error(f"Failed to add {symbol} to order manager")
                return False
                
            # Initialize risk tracking
            if not await self.risk_manager.add_symbol(symbol):
                logger.error(f"Failed to add {symbol} to risk manager")
                return False
                
            # Initialize strategy
            if not await self.strategy_manager.add_symbol(symbol):
                logger.error(f"Failed to add {symbol} to strategy manager")
                return False
                
            self.active_symbols.add(symbol)
            logger.info(f"✓ Added symbol {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding symbol {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def remove_symbol(self, symbol: str) -> bool:
        """Remove symbol from trading.
        
        Args:
            symbol: Trading symbol to remove
            
        Returns:
            bool: True if symbol removed successfully
        """
        try:
            if symbol not in self.active_symbols:
                logger.warning(f"Symbol {symbol} not traded")
                return True
                
            # Close positions
            await self.close_positions(symbol)
            
            # Cancel orders
            await self.cancel_orders(symbol)
            
            # Remove from components
            await self.data_manager.remove_symbol(symbol)
            await self.position_manager.remove_symbol(symbol)
            await self.order_manager.remove_symbol(symbol)
            await self.risk_manager.remove_symbol(symbol)
            await self.strategy_manager.remove_symbol(symbol)
            
            self.active_symbols.remove(symbol)
            logger.info(f"✓ Removed symbol {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing symbol {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def close_positions(self, symbol: str) -> bool:
        """Close all positions for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            bool: True if positions closed successfully
        """
        try:
            return await self.position_manager.close_positions(symbol)
            
        except Exception as e:
            logger.error(f"Error closing positions for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def close_all_positions(self) -> bool:
        """Close all positions."""
        try:
            success = True
            for symbol in self.active_symbols:
                if not await self.close_positions(symbol):
                    success = False
            return success
            
        except Exception as e:
            logger.error(f"Error closing all positions: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def cancel_orders(self, symbol: str) -> bool:
        """Cancel all orders for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            bool: True if orders cancelled successfully
        """
        try:
            return await self.order_manager.cancel_orders(symbol)
            
        except Exception as e:
            logger.error(f"Error cancelling orders for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def cancel_all_orders(self) -> bool:
        """Cancel all orders."""
        try:
            success = True
            for symbol in self.active_symbols:
                if not await self.cancel_orders(symbol):
                    success = False
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling all orders: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
            
    async def _update_loop(self) -> None:
        """Update trading state."""
        try:
            while self.trading_enabled:
                for symbol in self.active_symbols:
                    try:
                        # Update market data
                        data = await self.data_manager.get_initial_data(symbol)
                        if not data:
                            continue
                            
                        # Update strategy
                        signals = await self.strategy_manager.update(symbol, data)
                        
                        # Check risk limits
                        if not await self.risk_manager.check_limits(symbol):
                            continue
                            
                        # Execute trades
                        if signals:
                            await self.execute_trades(symbol, signals)
                            
                    except Exception as e:
                        logger.error(f"Error updating {symbol}: {str(e)}")
                        logger.debug(traceback.format_exc())
                        
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in update loop: {str(e)}")
            logger.debug(traceback.format_exc())
            
    async def _risk_check_loop(self) -> None:
        """Check risk limits."""
        try:
            while self.trading_enabled:
                for symbol in self.active_symbols:
                    try:
                        if not await self.risk_manager.check_limits(symbol):
                            # Close positions if risk limits exceeded
                            await self.close_positions(symbol)
                            
                    except Exception as e:
                        logger.error(f"Error checking risk for {symbol}: {str(e)}")
                        logger.debug(traceback.format_exc())
                        
                await asyncio.sleep(self.risk_check_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in risk check loop: {str(e)}")
            logger.debug(traceback.format_exc())
            
    async def execute_trades(self, symbol: str, signals: Dict[str, Any]) -> bool:
        """Execute trading signals.
        
        Args:
            symbol: Trading symbol
            signals: Trading signals
            
        Returns:
            bool: True if trades executed successfully
        """
        try:
            # Validate signals
            if not signals:
                return True
                
            # Check risk limits
            if not await self.risk_manager.check_limits(symbol):
                return False
                
            # Execute orders
            return await self.order_manager.execute_signals(symbol, signals)
            
        except Exception as e:
            logger.error(f"Error executing trades for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return False 