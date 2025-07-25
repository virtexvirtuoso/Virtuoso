"""
Merged validation module
Merged from: core/config/validators/binance_validator.py and validation/validators/binance_validator.py
"""

from ..core.base import ValidationResult, ValidationContext
from ..core.exceptions import BinanceValidationError
from dataclasses import dataclass
from typing import Any, Optional, Dict
from typing import Dict, Any, List, Optional
import logging
import re

class BinanceConfigValidator:
    """
    Comprehensive validator for Binance configuration settings.
    
    Validates:
    - API credentials format and requirements
    - Rate limiting configuration
    - Endpoint URLs and formats
    - WebSocket configuration
    - Market type settings
    - Data quality filters
    - Environment variable integration
    """

    def __init__(self):
        """Initialize the validator."""
        self.logger = logger
        self.valid_market_types = ['spot', 'futures', 'margin', 'options']
        self.valid_quote_currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'BUSD', 'USDC', 'DAI', 'TUSD']
        self.rate_limit_bounds = {'requests_per_minute': {'min': 1, 'max': 1200}, 'requests_per_second': {'min': 1, 'max': 20}, 'weight_per_minute': {'min': 1, 'max': 6000}}
        self.required_sections = ['api_credentials', 'rate_limits', 'websocket']

    def validate_full_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete Binance configuration.
        
        Args:
            config: Binance configuration dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        try:
            for section in self.required_sections:
                if section not in config:
                    errors.append(BinanceValidationError(field=section, message=f"Required section '{section}' is missing", severity='error'))
            if 'api_credentials' in config:
                section_result = self.validate_api_credentials(config['api_credentials'])
                errors.extend(section_result.errors)
                warnings.extend(section_result.warnings)
            if 'rate_limits' in config:
                section_result = self.validate_rate_limits(config['rate_limits'])
                errors.extend(section_result.errors)
                warnings.extend(section_result.warnings)
            if 'websocket' in config:
                section_result = self.validate_websocket_config(config['websocket'])
                errors.extend(section_result.errors)
                warnings.extend(section_result.warnings)
            if 'market_types' in config:
                section_result = self.validate_market_types(config['market_types'])
                errors.extend(section_result.errors)
                warnings.extend(section_result.warnings)
            if 'data_preferences' in config:
                section_result = self.validate_data_preferences(config['data_preferences'])
                errors.extend(section_result.errors)
                warnings.extend(section_result.warnings)
            top_level_result = self.validate_top_level_settings(config)
            errors.extend(top_level_result.errors)
            warnings.extend(top_level_result.warnings)
            return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
        except Exception as e:
            self.logger.error(f'Error during configuration validation: {str(e)}')
            errors.append(BinanceValidationError(field='validation', message=f'Validation failed: {str(e)}', severity='error'))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

    def validate_api_credentials(self, credentials: Dict[str, Any]) -> ValidationResult:
        """Validate API credentials configuration."""
        errors = []
        warnings = []
        api_key = credentials.get('api_key', '')
        api_secret = credentials.get('api_secret', '')
        if not api_key and (not api_secret):
            warnings.append(BinanceValidationError(field='api_credentials', message='No API credentials provided - will use public access only', severity='warning'))
        elif api_key and (not api_secret):
            errors.append(BinanceValidationError(field='api_secret', message='API secret is required when API key is provided', severity='error'))
        elif not api_key and api_secret:
            errors.append(BinanceValidationError(field='api_key', message='API key is required when API secret is provided', severity='error'))
        else:
            if api_key and len(api_key) not in [0, 64]:
                warnings.append(BinanceValidationError(field='api_key', message='API key length is unusual (expected 64 characters for Binance)', severity='warning'))
            if api_secret and len(api_secret) not in [0, 64]:
                warnings.append(BinanceValidationError(field='api_secret', message='API secret length is unusual (expected 64 characters for Binance)', severity='warning'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_rate_limits(self, rate_limits: Dict[str, Any]) -> ValidationResult:
        """Validate rate limiting configuration."""
        errors = []
        warnings = []
        required_fields = ['requests_per_minute', 'requests_per_second']
        for field in required_fields:
            if field not in rate_limits:
                errors.append(BinanceValidationError(field=field, message=f"Required rate limit field '{field}' is missing", severity='error'))
        for field, bounds in self.rate_limit_bounds.items():
            if field in rate_limits:
                value = rate_limits[field]
                if not isinstance(value, (int, float)) or value <= 0:
                    errors.append(BinanceValidationError(field=field, message=f'{field} must be a positive number', severity='error'))
                elif value < bounds['min'] or value > bounds['max']:
                    warnings.append(BinanceValidationError(field=field, message=f"{field} value {value} is outside recommended range {bounds['min']}-{bounds['max']}", severity='warning'))
        rpm = rate_limits.get('requests_per_minute', 0)
        rps = rate_limits.get('requests_per_second', 0)
        if rpm > 0 and rps > 0:
            max_rps_from_rpm = rpm / 60
            if rps > max_rps_from_rpm:
                warnings.append(BinanceValidationError(field='rate_limits', message=f'requests_per_second ({rps}) exceeds what requests_per_minute allows ({max_rps_from_rpm:.2f})', severity='warning'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_websocket_config(self, websocket: Dict[str, Any]) -> ValidationResult:
        """Validate WebSocket configuration."""
        errors = []
        warnings = []
        required_fields = ['public']
        for field in required_fields:
            if field not in websocket:
                errors.append(BinanceValidationError(field=f'websocket.{field}', message=f"Required WebSocket field '{field}' is missing", severity='error'))
        url_fields = ['public', 'testnet_public']
        for field in url_fields:
            if field in websocket:
                url = websocket[field]
                if not self._is_valid_websocket_url(url):
                    errors.append(BinanceValidationError(field=f'websocket.{field}', message=f'Invalid WebSocket URL format: {url}', severity='error'))
        numeric_fields = {'ping_interval': {'min': 1, 'max': 300}, 'reconnect_attempts': {'min': 1, 'max': 10}}
        for field, bounds in numeric_fields.items():
            if field in websocket:
                value = websocket[field]
                if not isinstance(value, (int, float)) or value < bounds['min'] or value > bounds['max']:
                    warnings.append(BinanceValidationError(field=f'websocket.{field}', message=f"{field} should be between {bounds['min']} and {bounds['max']}", severity='warning'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_market_types(self, market_types: List[str]) -> ValidationResult:
        """Validate market types configuration."""
        errors = []
        warnings = []
        if not isinstance(market_types, list):
            errors.append(BinanceValidationError(field='market_types', message='market_types must be a list', severity='error'))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        if not market_types:
            warnings.append(BinanceValidationError(field='market_types', message='No market types specified - defaulting to spot', severity='warning'))
        for market_type in market_types:
            if market_type not in self.valid_market_types:
                errors.append(BinanceValidationError(field='market_types', message=f"Invalid market type '{market_type}'. Valid types: {self.valid_market_types}", severity='error'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_data_preferences(self, preferences: Dict[str, Any]) -> ValidationResult:
        """Validate data preferences configuration."""
        errors = []
        warnings = []
        if 'preferred_quote_currencies' in preferences:
            quote_currencies = preferences['preferred_quote_currencies']
            if not isinstance(quote_currencies, list):
                errors.append(BinanceValidationError(field='data_preferences.preferred_quote_currencies', message='preferred_quote_currencies must be a list', severity='error'))
            else:
                for currency in quote_currencies:
                    if currency not in self.valid_quote_currencies:
                        warnings.append(BinanceValidationError(field='data_preferences.preferred_quote_currencies', message=f"Unusual quote currency '{currency}'. Common currencies: {self.valid_quote_currencies[:5]}", severity='warning'))
        if 'min_24h_volume' in preferences:
            volume = preferences['min_24h_volume']
            if not isinstance(volume, (int, float)) or volume < 0:
                errors.append(BinanceValidationError(field='data_preferences.min_24h_volume', message='min_24h_volume must be a non-negative number', severity='error'))
            elif volume < 100000:
                warnings.append(BinanceValidationError(field='data_preferences.min_24h_volume', message='Very low volume threshold may include illiquid markets', severity='warning'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_top_level_settings(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate top-level configuration settings."""
        errors = []
        warnings = []
        boolean_fields = ['enabled', 'primary', 'data_only', 'testnet']
        for field in boolean_fields:
            if field in config and (not isinstance(config[field], bool)):
                if isinstance(config[field], str):
                    if config[field].lower() in ['true', 'false']:
                        warnings.append(BinanceValidationError(field=field, message=f"{field} should be boolean, not string '{config[field]}'", severity='warning'))
                    else:
                        errors.append(BinanceValidationError(field=field, message=f'{field} must be boolean (true/false)', severity='error'))
                else:
                    errors.append(BinanceValidationError(field=field, message=f'{field} must be boolean (true/false)', severity='error'))
        endpoint_fields = ['rest_endpoint', 'testnet_endpoint']
        for field in endpoint_fields:
            if field in config:
                url = config[field]
                if not self._is_valid_http_url(url):
                    errors.append(BinanceValidationError(field=field, message=f'Invalid URL format: {url}', severity='error'))
        if config.get('primary', False) and config.get('data_only', True):
            warnings.append(BinanceValidationError(field='configuration', message='Primary exchange is set to data_only mode - this may limit functionality', severity='warning'))
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _is_valid_websocket_url(self, url: str) -> bool:
        """Check if URL is a valid WebSocket URL."""
        if not isinstance(url, str):
            return False
        return url.startswith(('ws://', 'wss://')) and len(url) > 6

    def _is_valid_http_url(self, url: str) -> bool:
        """Check if URL is a valid HTTP/HTTPS URL."""
        if not isinstance(url, str):
            return False
        return url.startswith(('http://', 'https://')) and len(url) > 8

    def get_validation_summary(self, result: ValidationResult) -> str:
        """Get a human-readable validation summary."""
        if result.is_valid:
            status = '✅ VALID'
        else:
            status = '❌ INVALID'
        summary = f'{status} - {len(result.errors)} errors, {len(result.warnings)} warnings'
        if result.errors:
            summary += '\n\nErrors:'
            for error in result.errors:
                summary += f'\n  ❌ {error.field}: {error.message}'
        if result.warnings:
            summary += '\n\nWarnings:'
            for warning in result.warnings:
                summary += f'\n  ⚠️  {warning.field}: {warning.message}'
        return summary

@dataclass
class BinanceValidationError:
    """Configuration validation error."""
    field: str
    message: str
    severity: str = 'error'

@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[BinanceValidationError]
    warnings: List[BinanceValidationError]

def __init__(self):
    """Initialize the validator."""
    self.logger = logger
    self.valid_market_types = ['spot', 'futures', 'margin', 'options']
    self.valid_quote_currencies = ['USDT', 'BTC', 'ETH', 'BNB', 'BUSD', 'USDC', 'DAI', 'TUSD']
    self.rate_limit_bounds = {'requests_per_minute': {'min': 1, 'max': 1200}, 'requests_per_second': {'min': 1, 'max': 20}, 'weight_per_minute': {'min': 1, 'max': 6000}}
    self.required_sections = ['api_credentials', 'rate_limits', 'websocket']

def _is_valid_http_url(self, url: str) -> bool:
    """Check if URL is a valid HTTP/HTTPS URL."""
    if not isinstance(url, str):
        return False
    return url.startswith(('http://', 'https://')) and len(url) > 8

def _is_valid_websocket_url(self, url: str) -> bool:
    """Check if URL is a valid WebSocket URL."""
    if not isinstance(url, str):
        return False
    return url.startswith(('ws://', 'wss://')) and len(url) > 6

def get_validation_summary(self, result: ValidationResult) -> str:
    """Get a human-readable validation summary."""
    if result.is_valid:
        status = '✅ VALID'
    else:
        status = '❌ INVALID'
    summary = f'{status} - {len(result.errors)} errors, {len(result.warnings)} warnings'
    if result.errors:
        summary += '\n\nErrors:'
        for error in result.errors:
            summary += f'\n  ❌ {error.field}: {error.message}'
    if result.warnings:
        summary += '\n\nWarnings:'
        for warning in result.warnings:
            summary += f'\n  ⚠️  {warning.field}: {warning.message}'
    return summary

def validate(self, data: Dict[str, Any], context: Optional[ValidationContext]=None) -> ValidationResult:
    """Validate Binance configuration."""
    result = ValidationResult(success=True)
    return result

def validate_api_credentials(self, credentials: Dict[str, Any]) -> ValidationResult:
    """Validate API credentials configuration."""
    errors = []
    warnings = []
    api_key = credentials.get('api_key', '')
    api_secret = credentials.get('api_secret', '')
    if not api_key and (not api_secret):
        warnings.append(BinanceValidationError(field='api_credentials', message='No API credentials provided - will use public access only', severity='warning'))
    elif api_key and (not api_secret):
        errors.append(BinanceValidationError(field='api_secret', message='API secret is required when API key is provided', severity='error'))
    elif not api_key and api_secret:
        errors.append(BinanceValidationError(field='api_key', message='API key is required when API secret is provided', severity='error'))
    else:
        if api_key and len(api_key) not in [0, 64]:
            warnings.append(BinanceValidationError(field='api_key', message='API key length is unusual (expected 64 characters for Binance)', severity='warning'))
        if api_secret and len(api_secret) not in [0, 64]:
            warnings.append(BinanceValidationError(field='api_secret', message='API secret length is unusual (expected 64 characters for Binance)', severity='warning'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

def validate_binance_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate Binance configuration.
    
    Args:
        config: Binance configuration dictionary
        
    Returns:
        ValidationResult with validation results
    """
    validator = BinanceConfigValidator()
    return validator.validate_full_config(config)

def validate_data_preferences(self, preferences: Dict[str, Any]) -> ValidationResult:
    """Validate data preferences configuration."""
    errors = []
    warnings = []
    if 'preferred_quote_currencies' in preferences:
        quote_currencies = preferences['preferred_quote_currencies']
        if not isinstance(quote_currencies, list):
            errors.append(BinanceValidationError(field='data_preferences.preferred_quote_currencies', message='preferred_quote_currencies must be a list', severity='error'))
        else:
            for currency in quote_currencies:
                if currency not in self.valid_quote_currencies:
                    warnings.append(BinanceValidationError(field='data_preferences.preferred_quote_currencies', message=f"Unusual quote currency '{currency}'. Common currencies: {self.valid_quote_currencies[:5]}", severity='warning'))
    if 'min_24h_volume' in preferences:
        volume = preferences['min_24h_volume']
        if not isinstance(volume, (int, float)) or volume < 0:
            errors.append(BinanceValidationError(field='data_preferences.min_24h_volume', message='min_24h_volume must be a non-negative number', severity='error'))
        elif volume < 100000:
            warnings.append(BinanceValidationError(field='data_preferences.min_24h_volume', message='Very low volume threshold may include illiquid markets', severity='warning'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

def validate_full_config(self, config: Dict[str, Any]) -> ValidationResult:
    """
        Validate complete Binance configuration.
        
        Args:
            config: Binance configuration dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
    errors = []
    warnings = []
    try:
        for section in self.required_sections:
            if section not in config:
                errors.append(BinanceValidationError(field=section, message=f"Required section '{section}' is missing", severity='error'))
        if 'api_credentials' in config:
            section_result = self.validate_api_credentials(config['api_credentials'])
            errors.extend(section_result.errors)
            warnings.extend(section_result.warnings)
        if 'rate_limits' in config:
            section_result = self.validate_rate_limits(config['rate_limits'])
            errors.extend(section_result.errors)
            warnings.extend(section_result.warnings)
        if 'websocket' in config:
            section_result = self.validate_websocket_config(config['websocket'])
            errors.extend(section_result.errors)
            warnings.extend(section_result.warnings)
        if 'market_types' in config:
            section_result = self.validate_market_types(config['market_types'])
            errors.extend(section_result.errors)
            warnings.extend(section_result.warnings)
        if 'data_preferences' in config:
            section_result = self.validate_data_preferences(config['data_preferences'])
            errors.extend(section_result.errors)
            warnings.extend(section_result.warnings)
        top_level_result = self.validate_top_level_settings(config)
        errors.extend(top_level_result.errors)
        warnings.extend(top_level_result.warnings)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    except Exception as e:
        self.logger.error(f'Error during configuration validation: {str(e)}')
        errors.append(BinanceValidationError(field='validation', message=f'Validation failed: {str(e)}', severity='error'))
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

def validate_market_types(self, market_types: List[str]) -> ValidationResult:
    """Validate market types configuration."""
    errors = []
    warnings = []
    if not isinstance(market_types, list):
        errors.append(BinanceValidationError(field='market_types', message='market_types must be a list', severity='error'))
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    if not market_types:
        warnings.append(BinanceValidationError(field='market_types', message='No market types specified - defaulting to spot', severity='warning'))
    for market_type in market_types:
        if market_type not in self.valid_market_types:
            errors.append(BinanceValidationError(field='market_types', message=f"Invalid market type '{market_type}'. Valid types: {self.valid_market_types}", severity='error'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

def validate_rate_limits(self, rate_limits: Dict[str, Any]) -> ValidationResult:
    """Validate rate limiting configuration."""
    errors = []
    warnings = []
    required_fields = ['requests_per_minute', 'requests_per_second']
    for field in required_fields:
        if field not in rate_limits:
            errors.append(BinanceValidationError(field=field, message=f"Required rate limit field '{field}' is missing", severity='error'))
    for field, bounds in self.rate_limit_bounds.items():
        if field in rate_limits:
            value = rate_limits[field]
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(BinanceValidationError(field=field, message=f'{field} must be a positive number', severity='error'))
            elif value < bounds['min'] or value > bounds['max']:
                warnings.append(BinanceValidationError(field=field, message=f"{field} value {value} is outside recommended range {bounds['min']}-{bounds['max']}", severity='warning'))
    rpm = rate_limits.get('requests_per_minute', 0)
    rps = rate_limits.get('requests_per_second', 0)
    if rpm > 0 and rps > 0:
        max_rps_from_rpm = rpm / 60
        if rps > max_rps_from_rpm:
            warnings.append(BinanceValidationError(field='rate_limits', message=f'requests_per_second ({rps}) exceeds what requests_per_minute allows ({max_rps_from_rpm:.2f})', severity='warning'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

def validate_top_level_settings(self, config: Dict[str, Any]) -> ValidationResult:
    """Validate top-level configuration settings."""
    errors = []
    warnings = []
    boolean_fields = ['enabled', 'primary', 'data_only', 'testnet']
    for field in boolean_fields:
        if field in config and (not isinstance(config[field], bool)):
            if isinstance(config[field], str):
                if config[field].lower() in ['true', 'false']:
                    warnings.append(BinanceValidationError(field=field, message=f"{field} should be boolean, not string '{config[field]}'", severity='warning'))
                else:
                    errors.append(BinanceValidationError(field=field, message=f'{field} must be boolean (true/false)', severity='error'))
            else:
                errors.append(BinanceValidationError(field=field, message=f'{field} must be boolean (true/false)', severity='error'))
    endpoint_fields = ['rest_endpoint', 'testnet_endpoint']
    for field in endpoint_fields:
        if field in config:
            url = config[field]
            if not self._is_valid_http_url(url):
                errors.append(BinanceValidationError(field=field, message=f'Invalid URL format: {url}', severity='error'))
    if config.get('primary', False) and config.get('data_only', True):
        warnings.append(BinanceValidationError(field='configuration', message='Primary exchange is set to data_only mode - this may limit functionality', severity='warning'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

def validate_websocket_config(self, websocket: Dict[str, Any]) -> ValidationResult:
    """Validate WebSocket configuration."""
    errors = []
    warnings = []
    required_fields = ['public']
    for field in required_fields:
        if field not in websocket:
            errors.append(BinanceValidationError(field=f'websocket.{field}', message=f"Required WebSocket field '{field}' is missing", severity='error'))
    url_fields = ['public', 'testnet_public']
    for field in url_fields:
        if field in websocket:
            url = websocket[field]
            if not self._is_valid_websocket_url(url):
                errors.append(BinanceValidationError(field=f'websocket.{field}', message=f'Invalid WebSocket URL format: {url}', severity='error'))
    numeric_fields = {'ping_interval': {'min': 1, 'max': 300}, 'reconnect_attempts': {'min': 1, 'max': 10}}
    for field, bounds in numeric_fields.items():
        if field in websocket:
            value = websocket[field]
            if not isinstance(value, (int, float)) or value < bounds['min'] or value > bounds['max']:
                warnings.append(BinanceValidationError(field=f'websocket.{field}', message=f"{field} should be between {bounds['min']} and {bounds['max']}", severity='warning'))
    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
