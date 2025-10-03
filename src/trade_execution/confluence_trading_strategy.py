import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from src.core.analysis.confluence import ConfluenceAnalyzer
from src.trade_execution.confluence_position_manager import ConfluenceBasedPositionManager
from src.utils.task_tracker import create_tracked_task

logger = logging.getLogger(__name__)

class ConfluenceTradingStrategy:
    """Trading strategy based on confluence scores"""
    
    def __init__(self, config: Dict[str, Any], confluence_analyzer=None, position_manager=None):
        """Initialize the confluence-based trading strategy
        
        Args:
            config: Configuration dictionary
            confluence_analyzer: Optional ConfluenceAnalyzer instance
            position_manager: Optional ConfluenceBasedPositionManager instance
        """
        self.config = config
        self.confluence_analyzer = confluence_analyzer
        self.position_manager = position_manager
        
        # Trading parameters
        strategy_config = config.get('strategy', {})
        # Use explicit thresholds for long and short positions
        self.long_threshold = strategy_config.get('long_threshold', 70)
        self.short_threshold = strategy_config.get('short_threshold', 30)
        self.max_active_positions = strategy_config.get('max_active_positions', 5)
        self.update_interval = strategy_config.get('update_interval', 60)  # seconds
        
        # State tracking
        self.active_symbols = set()
        self.last_analysis = {}
        self.enabled = False
        self.data_fetcher = None
        
        logger.info(f"Strategy configured with long threshold: {self.long_threshold}, short threshold: {self.short_threshold}")
        
    async def initialize(self, confluence_analyzer=None, position_manager=None) -> bool:
        """Initialize the strategy.
        
        Args:
            confluence_analyzer: Optional analyzer override
            position_manager: Optional position manager override
            
        Returns:
            True if initialization was successful
        """
        if confluence_analyzer:
            self.confluence_analyzer = confluence_analyzer
            
        if position_manager:
            self.position_manager = position_manager
        
        # Create components if not provided
        if not self.confluence_analyzer:
            try:
                self.confluence_analyzer = ConfluenceAnalyzer(self.config)
                logger.info("Created new ConfluenceAnalyzer instance")
            except Exception as e:
                logger.error(f"Failed to create ConfluenceAnalyzer: {str(e)}")
                return False
            
        if not self.position_manager:
            try:
                self.position_manager = ConfluenceBasedPositionManager(self.config)
                await self.position_manager.initialize()
                logger.info("Created and initialized new ConfluenceBasedPositionManager instance")
            except Exception as e:
                logger.error(f"Failed to create ConfluenceBasedPositionManager: {str(e)}")
                return False
        
        logger.info("Confluence trading strategy initialized")
        return True
    
    async def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to the trading strategy.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if the symbol was added
        """
        if symbol in self.active_symbols:
            logger.warning(f"Symbol {symbol} already being traded")
            return True
            
        self.active_symbols.add(symbol)
        self.last_analysis[symbol] = {
            'timestamp': 0,
            'score': 50,
            'action': 'none'
        }
        
        logger.info(f"Added {symbol} to trading strategy")
        return True
    
    async def start(self) -> bool:
        """Start the trading strategy.
        
        Returns:
            True if the strategy was started
        """
        if self.enabled:
            logger.warning("Strategy already running")
            return True
            
        self.enabled = True
        create_tracked_task(self._trading_loop(), name="auto_tracked_task")
        
        logger.info("Started confluence trading strategy")
        return True
    
    async def stop(self) -> bool:
        """Stop the trading strategy.
        
        Returns:
            True if the strategy was stopped
        """
        if not self.enabled:
            logger.warning("Strategy not running")
            return True
            
        self.enabled = False
        
        # Close all positions
        if self.position_manager:
            await self.position_manager.close_all_positions()
        
        logger.info("Stopped confluence trading strategy")
        return True
    
    async def evaluate_market(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate market conditions for a symbol.
        
        Args:
            symbol: Trading symbol
            market_data: Market data
            
        Returns:
            Evaluation results
        """
        try:
            # Analyze market data with confluence analyzer
            analyzer = getattr(self, 'confluence_analyzer', None)
            if not (analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze'))):
                logger.debug("confluence_analyzer missing or analyze() not callable; returning neutral signal")
                return {
                    'action': 'none',
                    'score': 50,
                    'reason': 'analyzer_unavailable',
                    'timestamp': time.time() * 1000
                }

            try:
                analysis = await analyzer.analyze(market_data)
            except Exception as e:
                logger.debug(f"confluence_analyzer.analyze error: {e}")
                return {
                    'action': 'none',
                    'score': 50,
                    'reason': f'analysis_error: {e}',
                    'timestamp': time.time() * 1000
                }
            
            # Get confluence score
            score = analysis.get('score', 50)
            
            # Determine action based on score with explicit thresholds
            action = 'none'
            if score >= self.long_threshold:
                action = 'buy'
                logger.info(f"Long signal detected: score {score} >= threshold {self.long_threshold}")
            elif score <= self.short_threshold:
                action = 'sell'
                logger.info(f"Short signal detected: score {score} <= threshold {self.short_threshold}")
                
            # Store last analysis
            self.last_analysis[symbol] = {
                'timestamp': time.time(),
                'score': score,
                'action': action,
                'analysis': analysis
            }
            
            logger.info(f"Market evaluation for {symbol}: score={score}, action={action}")
            
            return {
                'symbol': symbol,
                'score': score,
                'action': action,
                'details': analysis
            }
            
        except Exception as e:
            logger.error(f"Error evaluating market for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'score': 50,
                'action': 'none',
                'error': str(e)
            }
    
    async def execute_signals(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading signals.
        
        Args:
            signals: Trading signals
            
        Returns:
            Execution results
        """
        try:
            symbol = signals.get('symbol')
            action = signals.get('action', 'none')
            score = signals.get('score', 50)
            
            if action == 'none':
                logger.debug(f"No action for {symbol}")
                return {'status': 'no_action'}
            
            # Check if we can take more positions
            active_positions = await self.position_manager.get_active_positions()
            if len(active_positions) >= self.max_active_positions:
                logger.warning(f"Maximum positions ({self.max_active_positions}) reached, skipping trade")
                return {'status': 'max_positions_reached'}
            
            # Execute the trade
            if action in ['buy', 'sell']:
                result = await self.position_manager.open_position(
                    symbol=symbol,
                    side=action,
                    confluence_score=score
                )
                
                logger.info(f"Executed {action} signal for {symbol}: {result}")
                return result
            
            return {'status': 'unknown_action', 'action': action}
            
        except Exception as e:
            logger.error(f"Error executing signals: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    async def _trading_loop(self) -> None:
        """Main trading loop."""
        try:
            logger.info("Starting trading loop")
            
            while self.enabled:
                for symbol in self.active_symbols:
                    try:
                        # Fetch market data
                        market_data = await self._fetch_market_data(symbol)
                        
                        # Evaluate market
                        signals = await self.evaluate_market(symbol, market_data)
                        
                        # Execute signals
                        if signals['action'] != 'none':
                            await self.execute_signals(signals)
                            
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
                
                # Update trailing stops
                await self.position_manager.update_trailing_stops()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
        except Exception as e:
            logger.error(f"Error in trading loop: {str(e)}")
    
    async def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data for analysis.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data
        """
        try:
            # Initialize data fetcher on first call
            if not self.data_fetcher:
                # Import here to avoid circular imports
                from src.data_acquisition.bybit_data_fetcher import BybitDataFetcher
                
                # Use the linked exchange from the position manager
                exchange = getattr(self.position_manager, 'exchange', None)
                if not exchange:
                    logger.error("No exchange available for data fetching")
                    return self._get_minimal_market_data(symbol)
                
                self.data_fetcher = BybitDataFetcher(exchange)
                logger.info("Created BybitDataFetcher instance")
            
            # Fetch complete market data
            market_data = await self.data_fetcher.fetch_complete_market_data(symbol)
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            return self._get_minimal_market_data(symbol)
    
    def _get_minimal_market_data(self, symbol: str) -> Dict[str, Any]:
        """Generate minimal market data structure.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Minimal market data
        """
        return {
            'symbol': symbol,
            'timestamp': int(time.time() * 1000),
            'exchange': 'bybit'
        } 