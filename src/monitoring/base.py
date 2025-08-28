"""
Base classes and interfaces for the monitoring system.

This module provides the foundational abstractions for the monitoring components,
ensuring consistent interfaces and promoting loose coupling between modules.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import asyncio


class MonitoringComponent(ABC):
    """Base class for all monitoring components."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the monitoring component.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._initialized = False
        self._running = False
    
    async def initialize(self) -> bool:
        """Initialize the component.
        
        Returns:
            bool: True if initialization was successful
        """
        if self._initialized:
            self.logger.warning(f"{self.__class__.__name__} already initialized")
            return True
        
        try:
            await self._perform_initialization()
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
            return False
    
    @abstractmethod
    async def _perform_initialization(self) -> None:
        """Perform component-specific initialization.
        
        This method should be implemented by subclasses.
        """
        pass
    
    async def start(self) -> None:
        """Start the component."""
        if not self._initialized:
            await self.initialize()
        
        if self._running:
            self.logger.warning(f"{self.__class__.__name__} already running")
            return
        
        self._running = True
        await self._on_start()
        self.logger.info(f"{self.__class__.__name__} started")
    
    async def stop(self) -> None:
        """Stop the component."""
        if not self._running:
            self.logger.warning(f"{self.__class__.__name__} not running")
            return
        
        self._running = False
        await self._on_stop()
        self.logger.info(f"{self.__class__.__name__} stopped")
    
    async def _on_start(self) -> None:
        """Hook for component-specific start logic."""
        pass
    
    async def _on_stop(self) -> None:
        """Hook for component-specific stop logic."""
        pass
    
    @property
    def is_running(self) -> bool:
        """Check if the component is running."""
        return self._running
    
    @property
    def is_initialized(self) -> bool:
        """Check if the component is initialized."""
        return self._initialized


class DataProvider(ABC):
    """Interface for components that provide market data."""
    
    @abstractmethod
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Market data dictionary
        """
        pass
    
    @abstractmethod
    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch market data for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dictionary mapping symbols to their market data
        """
        pass


class DataValidator(ABC):
    """Interface for components that validate data."""
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data.
        
        Args:
            data: Data to validate
            
        Returns:
            bool: True if data is valid
        """
        pass
    
    @abstractmethod
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics.
        
        Returns:
            Dictionary of validation statistics
        """
        pass


class SignalProcessor(ABC):
    """Interface for components that process signals."""
    
    @abstractmethod
    async def process(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process market data to generate signals.
        
        Args:
            market_data: Market data to process
            
        Returns:
            List of generated signals
        """
        pass


class AlertDispatcher(ABC):
    """Interface for components that dispatch alerts."""
    
    @abstractmethod
    async def dispatch(self, signals: List[Dict[str, Any]]) -> None:
        """Dispatch alerts based on signals.
        
        Args:
            signals: List of signals to process for alerts
        """
        pass
    
    @abstractmethod
    async def send_alert(self, level: str, message: str, details: Dict[str, Any]) -> None:
        """Send a single alert.
        
        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
            details: Additional alert details
        """
        pass


class MetricsCollector(ABC):
    """Interface for components that collect metrics."""
    
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics.
        
        Returns:
            Dictionary of metrics
        """
        pass


class WebSocketHandler(ABC):
    """Interface for WebSocket handling components."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to WebSocket.
        
        Returns:
            bool: True if connection was successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str], channels: List[str]) -> None:
        """Subscribe to WebSocket channels.
        
        Args:
            symbols: List of symbols to subscribe to
            channels: List of channels to subscribe to
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status.
        
        Returns:
            Dictionary containing connection status
        """
        pass


class ValidationRule(ABC):
    """Base class for validation rules."""
    
    def __init__(self, name: str):
        """Initialize the validation rule.
        
        Args:
            name: Name of the validation rule
        """
        self.name = name
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data against the rule.
        
        Args:
            data: Data to validate
            
        Returns:
            bool: True if data passes validation
        """
        pass
    
    def __str__(self) -> str:
        """String representation of the rule."""
        return f"ValidationRule({self.name})"


class Signal:
    """Represents a trading signal."""
    
    def __init__(
        self,
        symbol: str,
        action: str,
        strength: float,
        confidence: float,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a signal.
        
        Args:
            symbol: Trading pair symbol
            action: Signal action (buy, sell, hold)
            strength: Signal strength (0-100)
            confidence: Signal confidence (0-1)
            timestamp: Signal timestamp
            metadata: Optional additional metadata
        """
        self.symbol = symbol
        self.action = action
        self.strength = strength
        self.confidence = confidence
        self.timestamp = timestamp
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary.
        
        Returns:
            Dictionary representation of the signal
        """
        return {
            'symbol': self.symbol,
            'action': self.action,
            'strength': self.strength,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    def __str__(self) -> str:
        """String representation of the signal."""
        return (
            f"Signal({self.symbol}, {self.action}, "
            f"strength={self.strength:.2f}, confidence={self.confidence:.2f})"
        )


class Alert:
    """Represents an alert."""
    
    def __init__(
        self,
        level: str,
        message: str,
        timestamp: datetime,
        symbol: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize an alert.
        
        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
            timestamp: Alert timestamp
            symbol: Optional trading pair symbol
            details: Optional additional details
        """
        self.level = level
        self.message = message
        self.timestamp = timestamp
        self.symbol = symbol
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary.
        
        Returns:
            Dictionary representation of the alert
        """
        return {
            'level': self.level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'details': self.details
        }
    
    def __str__(self) -> str:
        """String representation of the alert."""
        symbol_str = f" [{self.symbol}]" if self.symbol else ""
        return f"Alert({self.level.upper()}{symbol_str}): {self.message}"