"""
Configuration validation utilities using Pydantic schemas.
Integrates with existing ConfigManager for comprehensive validation.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import yaml
from pydantic import ValidationError

from .schema import VirtuosoConfig, validate_config


logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message)
        self.errors = errors or []


class ConfigValidator:
    """Validates configuration files against Pydantic schemas."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_config_file(self, config_path: Path) -> Tuple[bool, List[str], Optional[VirtuosoConfig]]:
        """
        Validate configuration file against schema.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, error_messages, validated_config)
        """
        try:
            # Load configuration
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            # Resolve environment variables
            config_dict = _resolve_env_vars(config_dict)
            
            return self.validate_config_dict(config_dict)
            
        except FileNotFoundError:
            return False, [f"Configuration file not found: {config_path}"], None
        except yaml.YAMLError as e:
            return False, [f"YAML parsing error: {str(e)}"], None
        except Exception as e:
            return False, [f"Unexpected error loading config: {str(e)}"], None
    
    def validate_config_dict(self, config_dict: Dict[str, Any]) -> Tuple[bool, List[str], Optional[VirtuosoConfig]]:
        """
        Validate configuration dictionary against schema.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_messages, validated_config)
        """
        try:
            # Validate against Pydantic schema
            validated_config = validate_config(config_dict)
            self.logger.info("Configuration validation successful")
            return True, [], validated_config
            
        except ValidationError as e:
            error_messages = self._format_validation_errors(e)
            self.logger.error(f"Configuration validation failed: {len(error_messages)} errors")
            for msg in error_messages:
                self.logger.error(f"  - {msg}")
            return False, error_messages, None
        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            self.logger.error(error_msg)
            return False, [error_msg], None
    
    def _format_validation_errors(self, validation_error: ValidationError) -> List[str]:
        """
        Format Pydantic validation errors into readable messages.
        
        Args:
            validation_error: Pydantic ValidationError
            
        Returns:
            List of formatted error messages
        """
        error_messages = []
        
        for error in validation_error.errors():
            location = " -> ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            error_type = error['type']
            
            if 'input' in error:
                input_value = error['input']
                error_msg = f"{location}: {message} (got: {input_value}, type: {error_type})"
            else:
                error_msg = f"{location}: {message} (type: {error_type})"
            
            error_messages.append(error_msg)
        
        return error_messages
    
    def validate_partial_config(self, config_section: str, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a specific configuration section.
        
        Args:
            config_section: Name of the configuration section
            config_data: Configuration data for the section
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            # Create a minimal config with just this section
            minimal_config = self._create_minimal_config()
            minimal_config[config_section] = config_data
            
            # Validate the minimal config
            is_valid, errors, _ = self.validate_config_dict(minimal_config)
            
            # Filter errors to only include this section
            section_errors = [err for err in errors if err.startswith(config_section)]
            
            return len(section_errors) == 0, section_errors
            
        except Exception as e:
            return False, [f"Error validating section {config_section}: {str(e)}"]
    
    def _create_minimal_config(self) -> Dict[str, Any]:
        """
        Create a minimal valid configuration for partial validation.
        
        Returns:
            Minimal configuration dictionary
        """
        return {
            "alpha_scanning_optimized": {
                "enabled": True,
                "alpha_tiers": {},
                "filtering": {"min_alert_value_score": 0.0, "volume_confirmation": {}},
                "pattern_weights": {
                    "alpha_breakout": 0.2, "beta_compression": 0.2, "beta_expansion": 0.2,
                    "correlation_breakdown": 0.2, "cross_timeframe": 0.2
                },
                "throttling": {"emergency_override": {}, "max_total_alerts_per_day": 1, "max_total_alerts_per_hour": 1},
                "value_scoring": {
                    "alpha_weight": 0.2, "confidence_weight": 0.2, "pattern_weight": 0.2,
                    "risk_weight": 0.2, "volume_weight": 0.2
                }
            },
            "analysis": {
                "confluence_reference": "test",
                "indicators": {
                    "orderbook": {"parameters": {}},
                    "orderflow": {},
                    "price_structure": {},
                    "sentiment": {},
                    "technical": {},
                    "volume": {}
                }
            },
            "bitcoin_beta_analysis": {
                "alpha_detection": {
                    "alerts": {"cooldown_minutes": 1, "enabled": True, "min_confidence": 0.0},
                    "enabled": True,
                    "thresholds": {
                        "alpha_threshold": 0.0, "beta_divergence": 0.0, "confidence_threshold": 0.0,
                        "correlation_breakdown": 0.0, "reversion_beta": 0.0, "rolling_beta_change": 0.0,
                        "sector_correlation": 0.0, "timeframe_consensus": 0.0
                    }
                },
                "reports": {"enabled": True, "output_dir": "test", "schedule_enabled": True, "schedule_times": []},
                "timeframes": {}
            },
            "confluence": {
                "thresholds": {"buy": 70.0, "neutral_buffer": 0.0, "sell": 30.0},
                "weights": {
                    "components": {
                        "orderbook": 0.16, "orderflow": 0.16, "price_structure": 0.16,
                        "sentiment": 0.16, "technical": 0.18, "volume": 0.18
                    },
                    "sub_components": {
                        "orderbook": {"test": 1.0}, "orderflow": {"test": 1.0}, "price_structure": {"test": 1.0},
                        "sentiment": {"test": 1.0}, "technical": {"test": 1.0}, "volume": {"test": 1.0}
                    }
                }
            },
            "data_processing": {
                "batch_size": 1, "enabled": True, "max_history": 1, "max_workers": 1, "mode": "test",
                "update_interval": 1.0, "volatility_threshold": 0.0, "window_size": 1,
                "error_handling": {"log_errors": True, "max_retries": 0, "retry_delay": 0.0},
                "feature_engineering": {"market_impact": True, "orderbook_features": True, "technical_indicators": True},
                "performance": {"cache_enabled": True, "cache_size": 1, "parallel_processing": True},
                "pipeline": [],
                "storage": {"compression": "none", "format": "json", "partition_by": []},
                "time_weights": {"base": 1.0, "htf": 1.0, "ltf": 1.0, "mtf": 1.0},
                "validation": {"check_duplicates": True, "check_missing": True, "check_outliers": True}
            },
            "database": {
                "influxdb": {"bucket": "test", "org": "test", "timeout": 1000, "token": "test", "url": "test"},
                "url": "test"
            },
            "exchanges": {
                "bybit": {
                    "api_credentials": {"api_key": "test", "api_secret": "test"},
                    "enabled": True, "primary": True, "testnet": False, "rest_endpoint": "test",
                    "rate_limits": {"requests_per_minute": 1, "requests_per_second": 1},
                    "websocket": {"keep_alive": True, "ping_interval": 1, "public": "test", "reconnect_attempts": 1}
                }
            },
            "logging": {
                "disable_existing_loggers": False, "version": 1,
                "formatters": {"test": {"datefmt": "test", "format": "test"}},
                "handlers": {"test": {"class": "test", "formatter": "test", "level": "INFO"}},
                "loggers": {"test": {"handlers": ["test"], "level": "INFO", "propagate": True}}
            },
            "market": {},
            "market_data": {},
            "monitoring": {},
            "portfolio": {
                "performance": {"max_turnover": 1.0},
                "rebalancing": {"enabled": True, "frequency": "test", "threshold": 0.5},
                "target_allocation": {"TEST": 1.0}
            },
            "reporting": {},
            "risk": {
                "default_risk_percentage": 1.0, "long_stop_percentage": 1.0, "max_risk_percentage": 1.0,
                "min_risk_percentage": 1.0, "risk_free_rate": 0.0, "risk_reward_ratio": 1.0, "short_stop_percentage": 1.0,
                "risk_limits": {"max_drawdown": 0.5, "max_leverage": 1.0, "max_position_size": 0.5},
                "stop_loss": {"activation_percentage": 0.0, "default": 0.0, "trailing": True},
                "take_profit": {"activation_percentage": 0.0, "default": 0.0, "trailing": True}
            },
            "rollout": {},
            "signal_frequency_tracking": {},
            "signal_tracking": {},
            "system": {
                "base_dir": "test", "cache_dir": "test", "data_dir": "test", "enable_reporting": True,
                "environment": "development", "log_level": "INFO", "reports_dir": "test", "version": "test"
            },
            "timeframes": {},
            "web_server": {},
            "websocket": {}
        }


def validate_current_config() -> Tuple[bool, List[str], Optional[VirtuosoConfig]]:
    """
    Validate the current configuration file.
    
    Returns:
        Tuple of (is_valid, error_messages, validated_config)
    """
    validator = ConfigValidator()
    
    # Try to find config file in standard locations
    config_locations = [
        Path("config/config.yaml"),
        Path("src/config/config.yaml"),
        Path("src/config.yaml")
    ]
    
    for config_path in config_locations:
        if config_path.exists():
            return validator.validate_config_file(config_path)
    
    return False, ["Configuration file not found in any standard location"], None


def _resolve_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve environment variables in configuration."""
    import os
    import re
    
    def resolve_value(value):
        if isinstance(value, str):
            # Handle ${VAR} and ${VAR:default} patterns
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            for match in matches:
                if ':' in match:
                    var_name, default = match.split(':', 1)
                else:
                    var_name, default = match, ''
                
                env_value = os.getenv(var_name, default)
                
                # Convert boolean strings
                if env_value.lower() in ('true', 'false'):
                    env_value = env_value.lower() == 'true'
                
                value = value.replace(f'${{{match}}}', str(env_value))
            
            return value
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        else:
            return value
    
    return resolve_value(config_dict)


if __name__ == "__main__":
    # Command-line validation
    is_valid, errors, config = validate_current_config()
    
    if is_valid:
        print("✅ Configuration validation successful!")
        print(f"Validated configuration with {len(config.__dict__)} sections")
    else:
        print("❌ Configuration validation failed!")
        print(f"Found {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")