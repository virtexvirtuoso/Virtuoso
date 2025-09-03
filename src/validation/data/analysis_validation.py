"""Validation service for analysis components."""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
import logging
import re
import pytz

from .models import AnalysisResult

class ValidationRule(Protocol):
    """Protocol for validation rules."""
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate data and return list of error messages."""
        ...

@dataclass
class SymbolValidationRule:
    """Enhanced symbol validation rule."""
    
    min_length: int = 1
    max_length: int = 20
    pattern: str = r'^[A-Z0-9-]+$'
    reserved_words: List[str] = field(default_factory=lambda: ['TEST', 'DEMO', 'INVALID'])
    exchange_prefixes: List[str] = field(default_factory=lambda: ['NYSE:', 'NASDAQ:'])
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate symbol format and constraints."""
        errors = []
        symbol = data.get('symbol', '')
        
        if not isinstance(symbol, str):
            errors.append("Symbol must be a string")
            return errors
            
        # Strip exchange prefix if present
        for prefix in self.exchange_prefixes:
            if symbol.startswith(prefix):
                symbol = symbol[len(prefix):]
                break
        
        # Length validation
        if len(symbol) < self.min_length:
            errors.append(f"Symbol length {len(symbol)} below minimum {self.min_length}")
        if len(symbol) > self.max_length:
            errors.append(f"Symbol length {len(symbol)} exceeds maximum {self.max_length}")
            
        # Pattern validation
        if not re.match(self.pattern, symbol):
            errors.append(f"Symbol {symbol} does not match pattern {self.pattern}")
            
        # Reserved word validation
        if symbol in self.reserved_words:
            errors.append(f"Symbol {symbol} is a reserved word")
            
        return errors

@dataclass
class TimeRangeRule:
    """Enhanced time range validation with proper timeframe configuration."""
    
    max_duration: timedelta = timedelta(days=30)  # Default from config
    min_duration: timedelta = timedelta(minutes=1)  # Default from config
    allowed_timezones: List[str] = field(default_factory=lambda: ['UTC'])
    market_hours: Dict[str, tuple[time, time]] = field(
        default_factory=lambda: {
            'default': (time(0, 0), time(23, 59))
        }
    )
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'TimeRangeRule':
        """Create TimeRangeRule from configuration."""
        validation_config = config.get('monitoring', {}).get('validation', {}).get('rules', {})
        time_range_config = validation_config.get('time_range', {})
        
        # Get session configuration
        session_config = config.get('session_analysis', {}).get('reports', {})
        market_hours = {}
        
        # Add configured sessions
        for session, settings in session_config.items():
            if settings.get('enabled', False):
                start_str = settings.get('start', '00:00')
                end_str = settings.get('end', '23:59')
                try:
                    start_time = datetime.strptime(start_str, '%H:%M').time()
                    end_time = datetime.strptime(end_str, '%H:%M').time()
                    market_hours[session] = (start_time, end_time)
                except ValueError:
                    continue
        
        # Add default if no sessions configured
        if not market_hours:
            market_hours['default'] = (time(0, 0), time(23, 59))
        
        return cls(
            max_duration=timedelta(
                days=int(time_range_config.get('max_duration_days', 30))
            ),
            min_duration=timedelta(
                minutes=int(time_range_config.get('min_duration_minutes', 1))
            ),
            allowed_timezones=['UTC', 'America/New_York'],  # Default timezones
            market_hours=market_hours
        )
    
    def validate(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate time range parameters with proper timezone handling."""
        result = ValidationResult(
            success=True,
            errors=[],
            warnings=[],
            context=context.data_type if context else self.rule_name
        )
        
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        timezone_name = data.get('timezone', 'UTC')
        
        # Validate timezone
        if timezone_name not in self.allowed_timezones:
            result.add_error(f"Timezone {timezone_name} not in allowed timezones: {self.allowed_timezones}")
            return result
        
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
        
        # Validate against market hours if applicable
        session = data.get('session', 'default')
        if session in self.market_hours:
            session_start, session_end = self.market_hours[session]
            start_time_check = start_time.time()
            end_time_check = end_time.time()
            
            if not (session_start <= start_time_check <= session_end):
                result.add_warning(
                    f"Start time {start_time_check} outside {session} session hours "
                    f"({session_start} - {session_end})"
                )
                
            if not (session_start <= end_time_check <= session_end):
                result.add_warning(
                    f"End time {end_time_check} outside {session} session hours "
                    f"({session_start} - {session_end})"
                )
            
        return result

@dataclass
class CrossFieldValidationRule:
    """Validates relationships between multiple fields."""
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate cross-field relationships."""
        errors = []
        
        # Symbol and exchange compatibility
        symbol = data.get('symbol', '')
        exchange = data.get('exchange', '')
        
        if exchange and not symbol.startswith(f"{exchange}:"):
            errors.append(f"Symbol {symbol} should have {exchange}: prefix")
            
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
            
            if frequency in min_durations:
                if duration < min_durations[frequency]:
                    errors.append(
                        f"Duration {duration} too short for {frequency} frequency"
                    )
                    
        # Price range validation
        price_min = data.get('price_min')
        price_max = data.get('price_max')
        
        if all(isinstance(p, (int, float)) for p in [price_min, price_max]):
            if price_min >= price_max:
                errors.append("price_min must be less than price_max")
            if price_min < 0:
                errors.append("price_min cannot be negative")
                
        return errors

@dataclass
class NumericRangeRule:
    """Validates numeric range parameters."""
    
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    field_name: str = "value"
    required: bool = True
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate numeric range."""
        errors = []
        value = data.get(self.field_name)
        
        if value is None:
            if self.required:
                errors.append(f"{self.field_name} is required")
            return errors
            
        if not isinstance(value, (int, float)):
            errors.append(f"{self.field_name} must be numeric")
            return errors
            
        if self.min_value is not None and value < self.min_value:
            errors.append(
                f"{self.field_name} must be at least {self.min_value}"
            )
            
        if self.max_value is not None and value > self.max_value:
            errors.append(
                f"{self.field_name} must be at most {self.max_value}"
            )
            
        return errors

@dataclass
class ValidationService:
    """Centralized validation service."""
    
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("ValidationService")
    )
    
    _rules: Dict[str, List[ValidationRule]] = field(default_factory=dict)
    _rule_cache: Dict[str, Dict[Type[ValidationRule], ValidationRule]] = field(
        default_factory=dict
    )
    
    def register_rules(self, 
                      data_type: str,
                      rules: List[ValidationRule]) -> None:
        """Register validation rules for a data type."""
        self._rules[data_type] = rules
        self._rule_cache[data_type] = {
            type(rule): rule for rule in rules
        }
    
    def get_rule(self,
                data_type: str,
                rule_type: Type[ValidationRule]) -> Optional[ValidationRule]:
        """Get a specific rule for a data type."""
        return self._rule_cache.get(data_type, {}).get(rule_type)
    
    def validate(self, 
                data_type: str,
                data: Dict[str, Any]) -> AnalysisResult:
        """Validate data against registered rules."""
        result = AnalysisResult()
        
        if data_type not in self._rules:
            result.add_error(f"No validation rules for {data_type}")
            return result
            
        for rule in self._rules[data_type]:
            try:
                errors = rule.validate(data)
                for error in errors:
                    result.add_error(error)
            except Exception as e:
                self.logger.error(f"Error in validation rule: {e}")
                result.add_error(f"Validation error: {str(e)}")
                
        return result
    
    def validate_field(self,
                      data_type: str,
                      field_name: str,
                      value: Any) -> List[str]:
        """Validate a single field value."""
        return self.validate(data_type, {field_name: value}).errors 