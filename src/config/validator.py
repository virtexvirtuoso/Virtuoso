"""
Configuration Validation Schema and Validator

Provides comprehensive validation for the Virtuoso CCXT configuration
to ensure system reliability and proper parameter ranges.
"""

import logging
import os
import yaml
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a configuration validation error."""
    path: str
    message: str
    severity: str = "error"  # error, warning, info


class ConfigValidator:
    """
    Validates configuration files against predefined schemas.

    Ensures all configuration parameters are within valid ranges and
    required sections are present for system operation.
    """

    # Define the configuration schema
    SCHEMA = {
        "system": {
            "required": True,
            "type": dict,
            "fields": {
                "environment": {"type": str, "required": True, "values": ["development", "staging", "production"]},
                "log_level": {"type": str, "required": True, "values": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "enable_reporting": {"type": bool, "required": False, "default": True},
                "version": {"type": str, "required": True},
                "base_dir": {"type": str, "required": False, "default": "."},
                "cache_dir": {"type": str, "required": False, "default": "cache"},
                "data_dir": {"type": str, "required": False, "default": "data"},
                "reports_dir": {"type": str, "required": False, "default": "./reports"}
            }
        },
        "websocket": {
            "required": False,
            "type": dict,
            "fields": {
                "enabled": {"type": bool, "required": False, "default": True},
                "reconnect_attempts": {"type": int, "required": False, "default": 5, "min": 1, "max": 20},
                "ping_interval": {"type": int, "required": False, "default": 30, "min": 5, "max": 300},
                "timeout": {"type": int, "required": False, "default": 10, "min": 1, "max": 60},
                "log_level": {"type": str, "required": False, "default": "INFO", "values": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "channels": {
                    "type": dict,
                    "required": False,
                    "fields": {
                        "ticker": {"type": bool, "required": False, "default": True},
                        "kline": {"type": bool, "required": False, "default": True},
                        "orderbook": {"type": bool, "required": False, "default": True},
                        "trade": {"type": bool, "required": False, "default": True},
                        "liquidation": {"type": bool, "required": False, "default": True}
                    }
                }
            }
        },
        "analysis": {
            "required": False,
            "type": dict,
            "fields": {
                "indicators": {
                    "type": dict,
                    "required": False,
                    "fields": {
                        "orderbook": {
                            "type": dict,
                            "required": False,
                            "fields": {
                                "parameters": {
                                    "type": dict,
                                    "required": False,
                                    "fields": {
                                        "depth_levels": {"type": int, "required": False, "default": 25, "min": 5, "max": 100}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "trading": {
            "required": False,
            "type": dict,
            "fields": {
                "enabled": {"type": bool, "required": False, "default": False},
                "risk_management": {
                    "type": dict,
                    "required": False,
                    "fields": {
                        "max_position_size_pct": {"type": float, "required": False, "default": 0.1, "min": 0.01, "max": 1.0},
                        "max_daily_loss_pct": {"type": float, "required": False, "default": 0.05, "min": 0.01, "max": 0.5},
                        "stop_loss_pct": {"type": float, "required": False, "default": 0.02, "min": 0.005, "max": 0.2}
                    }
                }
            }
        },
        "exchanges": {
            "required": False,
            "type": dict,
            "fields": {
                "default": {"type": str, "required": False, "default": "bybit"},
                "bybit": {
                    "type": dict,
                    "required": False,
                    "fields": {
                        "sandbox": {"type": bool, "required": False, "default": True},
                        "rate_limit": {"type": int, "required": False, "default": 10, "min": 1, "max": 100}
                    }
                },
                "binance": {
                    "type": dict,
                    "required": False,
                    "fields": {
                        "sandbox": {"type": bool, "required": False, "default": True},
                        "rate_limit": {"type": int, "required": False, "default": 10, "min": 1, "max": 100}
                    }
                }
            }
        }
    }

    def __init__(self):
        """Initialize the configuration validator."""
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary against the schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate against schema
        self._validate_section(config, self.SCHEMA, "")

        # Additional custom validations
        self._validate_environment_specific(config)
        self._validate_dependencies(config)

        return len(self.errors) == 0

    def _validate_section(self, config: Dict[str, Any], schema: Dict[str, Any], path: str):
        """Recursively validate a configuration section."""

        for key, definition in schema.items():
            current_path = f"{path}.{key}" if path else key

            # Check if required field is present
            if definition.get("required", False) and key not in config:
                self.errors.append(ValidationError(
                    path=current_path,
                    message=f"Required field '{key}' is missing"
                ))
                continue

            # Skip if field is not present and not required
            if key not in config:
                continue

            value = config[key]

            # Validate type
            expected_type = definition.get("type")
            if expected_type and not isinstance(value, expected_type):
                self.errors.append(ValidationError(
                    path=current_path,
                    message=f"Expected type {expected_type.__name__}, got {type(value).__name__}"
                ))
                continue

            # Validate allowed values
            if "values" in definition:
                if value not in definition["values"]:
                    self.errors.append(ValidationError(
                        path=current_path,
                        message=f"Value '{value}' not in allowed values: {definition['values']}"
                    ))

            # Validate numeric ranges
            if isinstance(value, (int, float)):
                if "min" in definition and value < definition["min"]:
                    self.errors.append(ValidationError(
                        path=current_path,
                        message=f"Value {value} is less than minimum {definition['min']}"
                    ))

                if "max" in definition and value > definition["max"]:
                    self.errors.append(ValidationError(
                        path=current_path,
                        message=f"Value {value} exceeds maximum {definition['max']}"
                    ))

            # Recursive validation for nested objects
            if isinstance(value, dict) and "fields" in definition:
                self._validate_section(value, definition["fields"], current_path)

    def _validate_environment_specific(self, config: Dict[str, Any]):
        """Validate environment-specific constraints."""

        system = config.get("system", {})
        environment = system.get("environment")

        if environment == "production":
            # Production-specific validations
            if system.get("log_level") == "DEBUG":
                self.warnings.append(ValidationError(
                    path="system.log_level",
                    message="DEBUG logging not recommended in production",
                    severity="warning"
                ))

            # Check for required production settings
            trading = config.get("trading", {})
            if trading.get("enabled") and not config.get("exchanges", {}).get("bybit", {}).get("sandbox", True):
                self.warnings.append(ValidationError(
                    path="exchanges.bybit.sandbox",
                    message="Consider using sandbox=false only in production with proper risk management",
                    severity="warning"
                ))

    def _validate_dependencies(self, config: Dict[str, Any]):
        """Validate dependencies between configuration sections."""

        # Check WebSocket and analysis dependencies
        websocket = config.get("websocket", {})
        analysis = config.get("analysis", {})

        if websocket.get("enabled") and not analysis:
            self.warnings.append(ValidationError(
                path="analysis",
                message="Analysis section recommended when WebSocket is enabled",
                severity="warning"
            ))

        # Check trading dependencies
        trading = config.get("trading", {})
        exchanges = config.get("exchanges", {})

        if trading.get("enabled") and not exchanges:
            self.errors.append(ValidationError(
                path="exchanges",
                message="Exchanges configuration required when trading is enabled"
            ))

    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive validation report.

        Returns:
            Dictionary containing validation results and recommendations
        """
        return {
            "valid": len(self.errors) == 0,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [
                {"path": e.path, "message": e.message, "severity": e.severity}
                for e in self.errors
            ],
            "warnings": [
                {"path": w.path, "message": w.message, "severity": w.severity}
                for w in self.warnings
            ],
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate configuration recommendations."""
        recommendations = []

        if self.warnings:
            recommendations.append("Review warnings to optimize configuration")

        if any("sandbox" in w.path for w in self.warnings):
            recommendations.append("Verify exchange sandbox settings for your environment")

        if any("log_level" in w.path for w in self.warnings):
            recommendations.append("Consider adjusting log level for production")

        return recommendations


def validate_config_file(config_path: str) -> Dict[str, Any]:
    """
    Validate a YAML configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Validation report dictionary
    """
    validator = ConfigValidator()

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if not config:
            return {
                "valid": False,
                "error_count": 1,
                "warning_count": 0,
                "errors": [{"path": "root", "message": "Configuration file is empty", "severity": "error"}],
                "warnings": [],
                "recommendations": ["Ensure configuration file contains valid YAML"]
            }

        validator.validate_config(config)
        return validator.get_validation_report()

    except FileNotFoundError:
        return {
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"path": "file", "message": f"Configuration file not found: {config_path}", "severity": "error"}],
            "warnings": [],
            "recommendations": ["Create a valid configuration file"]
        }
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"path": "yaml", "message": f"YAML parsing error: {str(e)}", "severity": "error"}],
            "warnings": [],
            "recommendations": ["Fix YAML syntax errors"]
        }
    except Exception as e:
        return {
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"path": "system", "message": f"Validation error: {str(e)}", "severity": "error"}],
            "warnings": [],
            "recommendations": ["Check configuration file format and permissions"]
        }


def get_config_health() -> Dict[str, Any]:
    """
    Get overall configuration health status.

    Returns:
        Health status dictionary
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "config.yaml")

    health = {
        "timestamp": __import__("datetime").datetime.now(timezone.utc).isoformat(),
        "config_file": config_path,
        "status": "unknown"
    }

    if not os.path.exists(config_path):
        health.update({
            "status": "error",
            "message": "Configuration file not found",
            "file_exists": False
        })
        return health

    health["file_exists"] = True
    health["file_size"] = os.path.getsize(config_path)
    health["last_modified"] = os.path.getmtime(config_path)

    # Validate configuration
    validation_result = validate_config_file(config_path)
    health.update({
        "status": "healthy" if validation_result["valid"] else "error",
        "validation": validation_result
    })

    return health


if __name__ == "__main__":
    # Test the validator
    config_path = "../config/config.yaml"
    result = validate_config_file(config_path)

    print("Configuration Validation Report:")
    print(f"Valid: {result['valid']}")
    print(f"Errors: {result['error_count']}")
    print(f"Warnings: {result['warning_count']}")

    for error in result.get("errors", []):
        print(f"ERROR: {error['path']} - {error['message']}")

    for warning in result.get("warnings", []):
        print(f"WARNING: {warning['path']} - {warning['message']}")

    for rec in result.get("recommendations", []):
        print(f"RECOMMENDATION: {rec}")