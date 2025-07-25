"""
Merged validation module
Merged from: data_processing/market_validator.py and validation/validators/market_validator.py
"""

from ..core.base import ValidationResult, ValidationContext
from datetime import datetime, timedelta, timezone
from src.core.error.models import ErrorSeverity
from src.core.error.context import ErrorContext
from ..services.sync_service import ValidationService
from ..services.async_service import AsyncValidationService
from .timeseries_validator import TimeSeriesValidator
from .orderbook_validator import OrderBookValidator
from .trades_validator import TradesValidator
from typing import Any, Optional
from typing import Dict, Any, Optional, List
import json
import logging
import numpy as np
import pandas as pd
import traceback

class MarketDataValidator:
    """Validates market data using the validation system."""

    def __init__(self, validation_service: Optional[AsyncValidationService]=None, config: Optional[Dict[str, Any]]=None):
        """Initialize the market data validator.
        
        Args:
            validation_service: Optional pre-configured validation service
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self._validation_service = validation_service or AsyncValidationService()
        self._time_series_validator = TimeSeriesValidator()
        self._orderbook_validator = OrderBookValidator()
        self._trades_validator = TradesValidator()
        self._validation_service.register_validator('time_series', self._time_series_validator)
        self._validation_service.register_validator('orderbook', self._orderbook_validator)
        self._validation_service.register_validator('trades', self._trades_validator)
        self.logger = logging.getLogger(__name__)
        logger.info('MarketDataValidator initialized')

    async def validate_market_message(self, data: Dict[str, Any], data_type: str, strict: bool=False) -> bool:
        """Validate market data message based on type.
        
        Args:
            data: Market data to validate
            data_type: Type of market data
            strict: Whether to use strict validation
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        try:
            result = None
            if data_type == 'kline':
                result = await self.validate_kline(data, strict)
            elif data_type == 'trade':
                result = await self.validate_trade(data, strict)
            elif data_type == 'orderbook':
                result = await self.validate_orderbook(data, strict)
            elif data_type == 'ticker':
                result = await self.validate_ticker(data, strict)
            elif data_type == 'funding':
                result = await self.validate_ticker(data, strict)
            elif data_type == 'open_interest':
                result = await self.validate_ticker(data, strict)
            else:
                self.logger.error(f'Unknown data type: {data_type}')
                return False
            return result.success if result else False
        except Exception as e:
            self.logger.error(f'Error validating market message: {str(e)}')
            self.logger.debug(traceback.format_exc())
            return False

    async def validate_kline(self, kline: Dict[str, Any], strict: bool=False) -> ValidationResult:
        """Validate kline/candlestick data.
        
        Args:
            kline: Kline data to validate
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult containing validation outcome
        """
        context = ValidationContext(data_type='kline', timestamp=datetime.now())
        if not isinstance(kline.get('list', []), list) or len(kline.get('list', [])) == 0:
            self.logger.error('Invalid kline data format')
            return ValidationResult(False, ['Invalid kline data format'])
        candle = kline['list'][0]
        timestamp = int(candle[0])
        start_time = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1000000000000.0 else datetime.fromtimestamp(timestamp)
        validation_data = {'symbol': kline.get('symbol', ''), 'price': float(candle[4]), 'volume': float(candle[5]), 'start_time': start_time, 'end_time': start_time + timedelta(minutes=1)}
        if not all((isinstance(x, str) for x in candle)):
            self.logger.error('Invalid kline data types')
            return ValidationResult(False, ['Invalid kline data types'])
        try:
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                self.logger.error('Invalid OHLC price relationship')
                return ValidationResult(False, ['Invalid OHLC price relationship'])
        except (ValueError, TypeError) as e:
            self.logger.error(f'Error parsing kline prices: {str(e)}')
            return ValidationResult(False, [f'Error parsing kline prices: {str(e)}'])
        return await self._validation_service.validate(validation_data, context)

    async def validate_trade(self, trade: Dict[str, Any], strict: bool=False) -> ValidationResult:
        """Validate trade data.
        
        Args:
            trade: Trade data to validate
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult containing validation outcome
        """
        context = ValidationContext(data_type='trade', symbol=trade.get('symbol'))
        return await self._validation_service.validate(trade, context)

    async def validate_orderbook(self, orderbook: Dict[str, Any], strict: bool=False) -> ValidationResult:
        """Validate orderbook data.
        
        Args:
            orderbook: Orderbook data to validate
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult containing validation outcome
        """
        context = ValidationContext(data_type='orderbook', strict_mode=strict)
        return await self._validation_service.validate(orderbook, context)

    async def validate_ticker(self, ticker: Dict[str, Any], strict: bool=False) -> ValidationResult:
        """Validate ticker data.
        
        Args:
            ticker: Ticker data to validate
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult containing validation outcome
        """
        context = ValidationContext(data_type='ticker')
        return await self._validation_service.validate(ticker, context)

    async def validate_batch(self, items: List[Dict[str, Any]], data_type: str, strict: bool=False) -> List[ValidationResult]:
        """Validate a batch of items.
        
        Args:
            items: List of items to validate
            data_type: Type of data to validate
            strict: Whether to use strict validation
            
        Returns:
            List of validation results
        """
        results = []
        for item in items:
            if data_type == 'kline':
                result = await self.validate_kline(item, strict)
            elif data_type == 'trade':
                result = await self.validate_trade(item, strict)
            elif data_type == 'orderbook':
                result = await self.validate_orderbook(item, strict)
            elif data_type == 'ticker':
                result = await self.validate_ticker(item, strict)
            else:
                self.logger.error(f'Unknown data type: {data_type}')
                result = ValidationResult(False, [f'Unknown data type: {data_type}'])
            results.append(result)
        return results

def __init__(self, validation_service: Optional[AsyncValidationService]=None, config: Optional[Dict[str, Any]]=None):
    """Initialize the market data validator.
        
        Args:
            validation_service: Optional pre-configured validation service
            config: Optional configuration dictionary
        """
    self._config = config or {}
    self._validation_service = validation_service or AsyncValidationService()
    self._time_series_validator = TimeSeriesValidator()
    self._orderbook_validator = OrderBookValidator()
    self._trades_validator = TradesValidator()
    self._validation_service.register_validator('time_series', self._time_series_validator)
    self._validation_service.register_validator('orderbook', self._orderbook_validator)
    self._validation_service.register_validator('trades', self._trades_validator)
    self.logger = logging.getLogger(__name__)
    logger.info('MarketDataValidator initialized')
