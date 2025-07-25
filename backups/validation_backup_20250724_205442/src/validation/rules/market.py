"""Market-specific validation rules."""

import dataclasses
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, time
import re
import logging

from ..core.models import ValidationRule, ValidationLevel
from ..core.base import ValidationContext, ValidationResult

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class TimeRangeRule(ValidationRule):
    """Validates time range parameters."""
    
    name: str = "time_range"
    max_duration: timedelta = dataclasses.field(default_factory=lambda: timedelta(days=7))
    min_duration: timedelta = dataclasses.field(default_factory=lambda: timedelta(minutes=5))
    allowed_timezones: List[str] = dataclasses.field(default_factory=lambda: ['UTC'])
    market_hours: Dict[str, tuple] = dataclasses.field(default_factory=dict)

    async def validate(self, data: Dict[str, Any], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate time range parameters."""
        result = ValidationResult(success=True)
        
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not isinstance(start_time, datetime):
            result.add_error("start_time must be a datetime")
            return result
            
        if not isinstance(end_time, datetime):
            result.add_error("end_time must be a datetime")
            return result
            
        duration = end_time - start_time
        
        if start_time >= end_time:
            result.add_error("start_time must be before end_time")
            return result
            
        if duration > self.max_duration:
            result.add_error(
                f"Duration {duration} exceeds maximum {self.max_duration}"
            )
            return result
            
        if duration < self.min_duration:
            result.add_error(
                f"Duration {duration} below minimum {self.min_duration}"
            )
            return result
            
        return result

@dataclasses.dataclass
class SymbolRule(ValidationRule):
    """Validates symbol format."""
    
    name: str = "symbol"
    min_length: int = 1
    max_length: int = 20
    pattern: str = r'^[A-Z0-9-]+$'
    reserved_words: List[str] = dataclasses.field(default_factory=lambda: ['TEST', 'DEMO', 'INVALID'])
    exchange_prefixes: List[str] = dataclasses.field(default_factory=lambda: ['NYSE:', 'NASDAQ:'])

    def __post_init__(self):
        """Add debug logging for rule configuration"""
        logger.debug(
            "\n=== SymbolRule Configuration ==="
            f"\nMin length: {self.min_length}"
            f"\nMax length: {self.max_length}"
            f"\nPattern: {self.pattern}"
            "\n==============================="
        )
        # Validate pattern compile time
        try:
            re.compile(self.pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{self.pattern}': {str(e)}")
            raise

    async def validate(self, data: Dict[str, Any], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate symbol format."""
        result = ValidationResult(success=True)
        
        symbol = data.get('symbol', '')
        logger.debug(f"Validating symbol: {symbol}")
        
        if not isinstance(symbol, str):
            result.add_error("Symbol must be a string")
            return result
        
        # Strip exchange prefix if present
        original_symbol = symbol
        for prefix in self.exchange_prefixes:
            if symbol.startswith(prefix):
                symbol = symbol[len(prefix):]
                break
        
        # Length validation
        if len(symbol) < self.min_length:
            result.add_error(f"Symbol length {len(symbol)} below minimum {self.min_length}")
            return result
            
        if len(symbol) > self.max_length:
            result.add_error(f"Symbol length {len(symbol)} exceeds maximum {self.max_length}")
            return result
            
        # Pattern validation
        if not re.match(self.pattern, symbol):
            result.add_error(f"Symbol {symbol} does not match pattern {self.pattern}")
            return result
        
        # Reserved word validation
        if symbol in self.reserved_words:
            result.add_error(f"Symbol {symbol} is a reserved word")
            return result
            
        return result

@dataclasses.dataclass
class NumericRangeRule(ValidationRule):
    """Validates numeric value ranges."""
    
    name: str = "numeric_range"
    min_value: float = 0
    max_value: float = float('inf')
    field_name: str = "price"

    async def validate(self, data: Dict[str, Any], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate numeric value ranges."""
        result = ValidationResult(success=True)
        
        value = data.get(self.field_name)
        if value is None:
            result.add_error(f"Missing required field: {self.field_name}")
            return result
            
        try:
            value = float(value)
        except (ValueError, TypeError):
            result.add_error(f"Invalid numeric value for {self.field_name}")
            return result
            
        if value < self.min_value:
            result.add_error(f"Value {value} below minimum {self.min_value}")
            return result
            
        if value > self.max_value:
            result.add_error(f"Value {value} exceeds maximum {self.max_value}")
            return result
            
        return result

@dataclasses.dataclass
class CrossFieldValidationRule(ValidationRule):
    """Validates relationships between multiple fields."""
    
    name: str = "cross_field"

    async def validate(self, data: Dict[str, Any], context: Optional[ValidationContext] = None) -> ValidationResult:
        """Validate cross-field relationships."""
        result = ValidationResult(success=True)
        
        # Symbol and exchange compatibility
        symbol = data.get('symbol', '')
        exchange = data.get('exchange', '')
        
        if exchange and symbol and not symbol.startswith(f"{exchange}:"):
            result.add_warning(f"Symbol {symbol} should have {exchange}: prefix")
            
        # Time range and data frequency compatibility
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        frequency = data.get('frequency', '')
        
        if all(isinstance(t, datetime) for t in [start_time, end_time]):
            duration = end_time - start_time
            
            # Minimum durations for different frequencies
            min_durations = {
                '1m': timedelta(hours=1),
                '5m': timedelta(hours=4), 
                '15m': timedelta(hours=12),
                '1h': timedelta(days=2),
                '1d': timedelta(days=7)
            }
            
            min_required = min_durations.get(frequency)
            if min_required and duration < min_required:
                result.add_error(
                    f"Duration {duration} too short for {frequency} frequency. "
                    f"Minimum required: {min_required}"
                )
        
        return result