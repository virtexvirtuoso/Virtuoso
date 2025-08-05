"""
Worker Pool Manager for efficient multiprocessing integration.

This module provides a hybrid async/multiprocessing architecture that:
1. Keeps I/O operations async (API calls, WebSocket, database)
2. Offloads CPU-intensive calculations to worker processes
3. Manages worker lifecycle and error handling
"""

import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Optional, Callable
import logging
import pickle
import time
from functools import partial
from dataclasses import dataclass
import queue
import threading

logger = logging.getLogger(__name__)


@dataclass
class WorkerTask:
    """Represents a task for worker processing."""
    task_id: str
    function_name: str
    args: tuple
    kwargs: dict
    priority: int = 0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
            
    def __lt__(self, other):
        """For priority queue ordering (higher priority first)."""
        return self.priority > other.priority


class WorkerPoolManager:
    """Manages a pool of worker processes for CPU-intensive tasks."""
    
    def __init__(self, num_workers: Optional[int] = None, max_tasks_per_worker: int = 100):
        """
        Initialize the worker pool manager.
        
        Args:
            num_workers: Number of worker processes (defaults to CPU count - 2)
            max_tasks_per_worker: Maximum tasks before worker restart
        """
        self.num_workers = num_workers or max(2, mp.cpu_count() - 2)
        self.max_tasks_per_worker = max_tasks_per_worker
        self.executor = None
        self.task_counter = {}
        self.is_running = False
        self._loop = None
        self._registered_functions = {}
        
        logger.info(f"WorkerPoolManager configured with {self.num_workers} workers")
        
    def register_function(self, name: str, func: Callable):
        """Register a function that can be called by workers."""
        self._registered_functions[name] = func
        logger.debug(f"Registered function: {name}")
        
    async def start(self):
        """Start the worker pool."""
        if self.is_running:
            return
            
        self._loop = asyncio.get_event_loop()
        self.executor = ProcessPoolExecutor(
            max_workers=self.num_workers,
            initializer=self._worker_init,
            initargs=(self._registered_functions,)
        )
        self.is_running = True
        logger.info("Worker pool started")
        
    async def stop(self):
        """Stop the worker pool gracefully."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
        logger.info("Worker pool stopped")
        
    async def submit_task(self, function_name: str, *args, **kwargs) -> Any:
        """
        Submit a task to the worker pool.
        
        Args:
            function_name: Name of registered function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
        """
        if not self.is_running:
            raise RuntimeError("Worker pool is not running")
            
        if function_name not in self._registered_functions:
            raise ValueError(f"Function {function_name} not registered")
            
        # Execute in worker process
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            self.executor,
            _worker_execute,
            function_name,
            args,
            kwargs
        )
        
        return await future
        
    async def map_tasks(self, function_name: str, items: List[Any]) -> List[Any]:
        """
        Map a function over multiple items in parallel.
        
        Args:
            function_name: Name of registered function
            items: List of items to process
            
        Returns:
            List of results
        """
        tasks = [
            self.submit_task(function_name, item)
            for item in items
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    @staticmethod
    def _worker_init(registered_functions):
        """Initialize worker process."""
        # Store functions in global scope for worker access
        globals()['_worker_functions'] = registered_functions
        
        # Configure logging for worker
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
        )


def _worker_execute(function_name: str, args: tuple, kwargs: dict) -> Any:
    """Execute function in worker process."""
    try:
        func = globals()['_worker_functions'][function_name]
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Worker execution error: {e}")
        raise


# Specialized functions for trading operations
def calculate_confluence_indicators(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate confluence indicators (CPU-intensive).
    This runs in a worker process.
    """
    import numpy as np
    import pandas as pd
    
    results = {}
    
    try:
        # Technical indicators
        if 'candles' in market_data:
            candles = market_data['candles']
            closes = [c['close'] for c in candles]
            
            # RSI calculation
            rsi = calculate_rsi(closes)
            results['rsi'] = rsi
            
            # MACD calculation
            macd_line, signal_line = calculate_macd(closes)
            results['macd'] = {'line': macd_line, 'signal': signal_line}
            
        # Volume analysis
        if 'volume' in market_data:
            volume_score = analyze_volume_profile(market_data['volume'])
            results['volume_score'] = volume_score
            
        # Orderbook analysis
        if 'orderbook' in market_data:
            orderbook_score = analyze_orderbook_depth(market_data['orderbook'])
            results['orderbook_score'] = orderbook_score
            
    except Exception as e:
        logger.error(f"Indicator calculation error: {e}")
        
    return results


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)."""
    import numpy as np
    
    if len(prices) < period + 1:
        return 50.0
        
    deltas = np.diff(prices)
    gains = deltas.copy()
    losses = deltas.copy()
    
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = abs(losses)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi)


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD indicator."""
    import numpy as np
    
    if len(prices) < slow:
        return 0.0, 0.0
        
    prices_array = np.array(prices)
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices_array, fast)
    ema_slow = calculate_ema(prices_array, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    
    return float(macd_line[-1]), float(signal_line[-1])


def calculate_ema(data, period: int):
    """Calculate Exponential Moving Average."""
    import numpy as np
    
    data = np.array(data) if not isinstance(data, np.ndarray) else data
    alpha = 2 / (period + 1)
    ema = np.zeros_like(data)
    ema[0] = data[0]
    
    for i in range(1, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
    return ema


def analyze_volume_profile(volume_data: Dict[str, Any]) -> float:
    """Analyze volume profile for scoring."""
    try:
        if not volume_data:
            return 0.5
            
        # Extract volume metrics
        current_volume = volume_data.get('current', 0)
        avg_volume = volume_data.get('average', 0)
        volume_trend = volume_data.get('trend', [])
        
        score = 0.5  # Neutral base
        
        # Volume spike detection
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio > 2.0:
                score += 0.2  # High volume
            elif volume_ratio > 1.5:
                score += 0.1  # Above average
            elif volume_ratio < 0.5:
                score -= 0.1  # Low volume
                
        # Volume trend analysis
        if len(volume_trend) >= 3:
            recent_trend = volume_trend[-3:]
            if all(recent_trend[i] < recent_trend[i+1] for i in range(len(recent_trend)-1)):
                score += 0.1  # Increasing volume
            elif all(recent_trend[i] > recent_trend[i+1] for i in range(len(recent_trend)-1)):
                score -= 0.1  # Decreasing volume
                
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        logger.error(f"Volume analysis error: {e}")
        return 0.5


def analyze_orderbook_depth(orderbook: Dict[str, Any]) -> float:
    """Analyze orderbook depth and imbalance."""
    try:
        if not orderbook:
            return 0.5
            
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        if not bids or not asks:
            return 0.5
            
        # Calculate bid/ask volumes
        bid_volume = sum(float(bid[1]) for bid in bids[:10])  # Top 10 levels
        ask_volume = sum(float(ask[1]) for ask in asks[:10])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.5
            
        # Calculate imbalance
        imbalance = (bid_volume - ask_volume) / total_volume
        
        # Calculate spread
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        spread_bps = ((best_ask - best_bid) / best_bid) * 10000
        
        # Score based on imbalance and spread
        score = 0.5  # Neutral base
        
        # Imbalance contribution
        score += imbalance * 0.3  # -0.3 to +0.3 range
        
        # Spread contribution (tighter spread = higher score)
        if spread_bps < 5:
            score += 0.1
        elif spread_bps < 10:
            score += 0.05
        elif spread_bps > 20:
            score -= 0.1
            
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        logger.error(f"Orderbook analysis error: {e}")
        return 0.5