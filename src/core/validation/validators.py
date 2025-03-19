"""Validation system validators.

This module provides validator implementations:
- Validator: Base validator class
- TimeSeriesValidator: Time series data validation
- OrderBookValidator: Order book data validation
- TradesValidator: Trade data validation
"""

import logging
import jsonschema
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Union
from datetime import datetime

from .base import ValidationResult, ValidationContext
from .models import ValidationRule, ValidationLevel, ValidationError

logger = logging.getLogger(__name__)

class Validator(ABC):
    """Base validator class.
    
    Provides common functionality for validators.
    """
    
    @abstractmethod
    async def validate(
        self,
        data: Any,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate data with context.
        
        Args:
            data: Data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        pass

class TimeSeriesValidator(Validator):
    """Time series data validator.
    
    Validates time series data format and content.
    """
    
    def __init__(self):
        """Initialize time series validator."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    async def validate(
        self,
        data: Dict[str, Any],
        context: ValidationContext
    ) -> ValidationResult:
        """Validate time series data.
        
        Args:
            data: Time series data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        result = ValidationResult(success=True)
        
        try:
            # Check required fields
            required_fields = ['timestamp', 'symbol']
            for field in required_fields:
                if field not in data:
                    result.add_error(f"Missing required field: {field}")
                    return result
                    
            # Validate timestamp
            timestamp = data['timestamp']
            if not isinstance(timestamp, (int, float, datetime)):
                result.add_error("Invalid timestamp type")
                return result
                
            # Convert timestamp to datetime if needed
            if isinstance(timestamp, (int, float)):
                try:
                    # Handle millisecond timestamps
                    if timestamp > 1e12:
                        timestamp = datetime.fromtimestamp(timestamp / 1000)
                    else:
                        timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError) as e:
                    result.add_error(f"Invalid timestamp value: {str(e)}")
                    return result
                    
            # Validate symbol
            symbol = data['symbol']
            if not isinstance(symbol, str) or not symbol:
                result.add_error("Invalid symbol")
                return result
                
            # Validate numeric fields if present
            numeric_fields = ['price', 'volume', 'open', 'high', 'low', 'close']
            for field in numeric_fields:
                if field in data:
                    try:
                        value = float(data[field])
                        if value < 0:
                            result.add_error(f"Negative value not allowed for {field}")
                            return result
                    except (ValueError, TypeError):
                        result.add_error(f"Invalid numeric value for {field}")
                        return result
                        
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating time series data: {str(e)}")
            result.add_error(f"Validation error: {str(e)}")
            return result

class OrderBookValidator(Validator):
    """Order book data validator.
    
    Validates order book data format and content.
    """
    
    def __init__(self):
        """Initialize order book validator."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    async def validate(
        self,
        data: Dict[str, Any],
        context: ValidationContext
    ) -> ValidationResult:
        """Validate order book data.
        
        Args:
            data: Order book data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        result = ValidationResult(success=True)
        
        try:
            # Check required fields
            required_fields = ['symbol', 'bids', 'asks']
            for field in required_fields:
                if field not in data:
                    result.add_error(f"Missing required field: {field}")
                    return result
                    
            # Validate symbol
            symbol = data['symbol']
            if not isinstance(symbol, str) or not symbol:
                result.add_error("Invalid symbol")
                return result
                
            # Validate bids and asks
            for side in ['bids', 'asks']:
                orders = data[side]
                if not isinstance(orders, list):
                    result.add_error(f"Invalid {side} format")
                    return result
                    
                for order in orders:
                    if not isinstance(order, list) or len(order) < 2:
                        result.add_error(f"Invalid order format in {side}")
                        return result
                        
                    try:
                        price = float(order[0])
                        size = float(order[1])
                        
                        if price < 0 or size < 0:
                            result.add_error(f"Negative values not allowed in {side}")
                            return result
                            
                    except (ValueError, TypeError):
                        result.add_error(f"Invalid numeric values in {side}")
                        return result
                        
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating order book data: {str(e)}")
            result.add_error(f"Validation error: {str(e)}")
            return result

class TradesValidator(Validator):
    """Trade data validator.
    
    Validates trade data format and content.
    """
    
    def __init__(self):
        """Initialize trades validator."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    async def validate(
        self,
        data: Dict[str, Any],
        context: ValidationContext
    ) -> ValidationResult:
        """Validate trade data.
        
        Args:
            data: Trade data to validate
            context: Validation context
            
        Returns:
            ValidationResult: Result of validation
        """
        result = ValidationResult(success=True)
        
        try:
            # Check required fields
            required_fields = ['symbol', 'price', 'size', 'side', 'timestamp']
            for field in required_fields:
                if field not in data:
                    result.add_error(f"Missing required field: {field}")
                    return result
                    
            # Validate symbol
            symbol = data['symbol']
            if not isinstance(symbol, str) or not symbol:
                result.add_error("Invalid symbol")
                return result
                
            # Validate numeric fields
            try:
                price = float(data['price'])
                size = float(data['size'])
                
                if price < 0 or size < 0:
                    result.add_error("Negative values not allowed for price or size")
                    return result
                    
            except (ValueError, TypeError):
                result.add_error("Invalid numeric values for price or size")
                return result
                
            # Validate side
            side = data['side'].lower()
            if side not in ['buy', 'sell']:
                result.add_error("Invalid trade side")
                return result
                
            # Validate timestamp
            timestamp = data['timestamp']
            if not isinstance(timestamp, (int, float, datetime)):
                result.add_error("Invalid timestamp type")
                return result
                
            # Convert timestamp to datetime if needed
            if isinstance(timestamp, (int, float)):
                try:
                    # Handle millisecond timestamps
                    if timestamp > 1e12:
                        timestamp = datetime.fromtimestamp(timestamp / 1000)
                    else:
                        timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, OSError) as e:
                    result.add_error(f"Invalid timestamp value: {str(e)}")
                    return result
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating trade data: {str(e)}")
            result.add_error(f"Validation error: {str(e)}")
            return result 