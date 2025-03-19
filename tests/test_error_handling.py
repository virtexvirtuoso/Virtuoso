import pytest
from src.utils.error_handling import (
    TradingError,
    ValidationError,
    MarketDataError,
    handle_errors,
    validate_input
)

def test_trading_error():
    """Test basic TradingError functionality."""
    error = TradingError("Test error", "ERR001")
    assert error.message == "Test error"
    assert error.error_code == "ERR001"
    assert error.timestamp is not None

def test_validation_error():
    """Test ValidationError as a subclass of TradingError."""
    error = ValidationError("Invalid data")
    assert isinstance(error, TradingError)
    assert str(error) == "Invalid data"

def test_market_data_error():
    """Test MarketDataError as a subclass of TradingError."""
    error = MarketDataError("Market data unavailable")
    assert isinstance(error, TradingError)
    assert str(error) == "Market data unavailable"

def test_handle_errors_decorator_with_return():
    """Test handle_errors decorator with error return value."""
    @handle_errors(error_return={"status": "error"})
    def problematic_function():
        raise ValueError("Test error")
    
    result = problematic_function()
    assert result == {"status": "error"}

def test_handle_errors_decorator_reraise():
    """Test handle_errors decorator with error reraising."""
    @handle_errors()
    def problematic_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        problematic_function()

def test_handle_errors_decorator_specific_exceptions():
    """Test handle_errors decorator with specific exception types."""
    @handle_errors(error_return=None, expected_exceptions=(ValueError,))
    def problematic_function(raise_type):
        if raise_type == "value":
            raise ValueError("Value error")
        else:
            raise TypeError("Type error")
    
    # Should be caught and reraised
    with pytest.raises(ValueError):
        problematic_function("value")
    
    # Should not be caught
    with pytest.raises(TypeError):
        problematic_function("type")

def test_validate_input_decorator():
    """Test validate_input decorator."""
    def validation_func(*args, **kwargs):
        return len(args) > 0 and args[0] > 0
    
    @validate_input(validation_func)
    def process_positive_number(num):
        return num * 2
    
    # Valid input
    assert process_positive_number(5) == 10
    
    # Invalid input
    with pytest.raises(ValidationError):
        process_positive_number(-1)

def test_error_handling_integration():
    """Test combination of error handling decorators."""
    def validate_data(data):
        return isinstance(data, dict) and "value" in data
    
    @handle_errors(error_return={"status": "error"})
    @validate_input(validate_data)
    def process_data(data):
        return {"status": "success", "result": data["value"] * 2}
    
    # Valid case
    result = process_data({"value": 5})
    assert result == {"status": "success", "result": 10}
    
    # Invalid case - validation error
    result = process_data({"wrong_key": 5})
    assert result == {"status": "error"} 