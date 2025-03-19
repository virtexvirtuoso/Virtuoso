"""Test validation system."""

import unittest
import logging
from datetime import datetime, timedelta
from core.validation import (
    ValidationResult,
    ValidationRule,
    AsyncValidationService,
    ValidationContext
)
from core.validation.rules import TimeRangeRule, SymbolRule, NumericRangeRule

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TestValidationSystem(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test cases."""
        self.validation_service = AsyncValidationService(
            max_errors=10,
            strict_mode=False
        )
        
        # Add validation rules
        self.time_range_rule = TimeRangeRule(
            max_duration=timedelta(days=30),
            min_duration=timedelta(minutes=1)
        )
        self.validation_service.register_rule(self.time_range_rule)
        
        self.symbol_rule = SymbolRule(
            min_length=1,
            max_length=20,
            pattern=r'^[A-Z0-9-]+$'
        )
        self.validation_service.register_rule(self.symbol_rule)
        
        self.numeric_rule = NumericRangeRule(
            min_value=0,
            max_value=float('inf'),
            field_name='price'
        )
        self.validation_service.register_rule(self.numeric_rule)

    async def test_time_range_validation(self):
        """Test time range validation."""
        now = datetime.now()
        context = ValidationContext(data_type="time_range")
        
        # Valid time range
        result = await self.validation_service.validate(
            {
                'start_time': now,
                'end_time': now + timedelta(days=1)
            },
            context=context
        )
        self.assertTrue(result.success)
        
        # Invalid time range - too long
        result = await self.validation_service.validate(
            {
                'start_time': now,
                'end_time': now + timedelta(days=31)
            },
            context=context
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)
        
        # Invalid time range - negative duration
        result = await self.validation_service.validate(
            {
                'start_time': now,
                'end_time': now - timedelta(minutes=1)
            },
            context=context
        )
        self.assertFalse(result.success)
        self.assertEqual(len(result.errors), 1)

    def test_symbol_validation(self):
        """Test symbol validation."""
        context = ValidationContext(data_type="symbol")
        
        # Valid symbol
        result = self.validation_service.validate(
            {
                'symbol': 'BTC-USD'
            },
            context=context
        )
        self.assertTrue(result.is_valid)
        
        # Invalid symbol - too short
        result = self.validation_service.validate(
            {
                'symbol': ''
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        
        # Invalid symbol - too long
        result = self.validation_service.validate(
            {
                'symbol': 'A' * 21
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        
        # Invalid symbol - wrong pattern
        result = self.validation_service.validate(
            {
                'symbol': 'btc-usd'
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)

    def test_numeric_range_validation(self):
        """Test numeric range validation."""
        context = ValidationContext(data_type="price")
        
        # Valid price
        result = self.validation_service.validate(
            {
                'price': 100.0
            },
            context=context
        )
        self.assertTrue(result.is_valid)
        
        # Invalid price - negative
        result = self.validation_service.validate(
            {
                'price': -1.0
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        
        # Invalid price - wrong type
        result = self.validation_service.validate(
            {
                'price': 'not a number'
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)

    def test_multiple_validations(self):
        """Test multiple validations at once."""
        now = datetime.now()
        context = ValidationContext(data_type="market_data")
        
        # All valid
        result = self.validation_service.validate(
            {
                'start_time': now,
                'end_time': now + timedelta(days=1),
                'symbol': 'BTC-USD',
                'price': 50000.0
            },
            context=context
        )
        self.assertTrue(result.is_valid)
        
        # Multiple invalid fields
        result = self.validation_service.validate(
            {
                'start_time': now,
                'end_time': now + timedelta(days=31),
                'symbol': 'invalid-symbol!',
                'price': -1.0
            },
            context=context
        )
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 3)

if __name__ == '__main__':
    unittest.main() 