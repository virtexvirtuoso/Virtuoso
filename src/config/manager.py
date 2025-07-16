"""Centralized configuration management."""

import os
import yaml
from yaml import SafeLoader
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration loading and access.
    
    This class handles:
    - Loading configuration from YAML
    - Environment variable substitution
    - Configuration validation
    - Caching configuration
    - Providing typed access to config sections
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the ConfigManager if not already initialized."""
        if not self._initialized:
            self._config = self.load_config()
            self._initialized = True
    
    @staticmethod
    def _find_config_file() -> str:
        """Locate the config.yaml file relative to project root."""
        try:
            # Start from current file's directory
            current_dir = Path(__file__).parent
            
            # Look for config in standard locations
            potential_paths = [
                current_dir.parent.parent / "config" / "config.yaml",  # /project_root/config/config.yaml
                current_dir.parent / "config.yaml",                    # /project_root/src/config.yaml
                current_dir / "config.yaml"                           # /project_root/src/config/config.yaml
            ]
            
            for path in potential_paths:
                if path.exists():
                    logger.debug(f"Found config file at: {path}")
                    return str(path)
            
            raise FileNotFoundError(
                "config.yaml not found in expected locations:\n" +
                "\n".join(f"- {p}" for p in potential_paths)
            )
            
        except Exception as e:
            logger.error(f"Error locating config file: {str(e)}")
            raise
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Load configuration from file with proper error handling."""
        try:
            config_path = ConfigManager._find_config_file()
            
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found at {config_path}")
                
            with open(config_path, 'r') as f:
                try:
                    # Use SafeLoader for security
                    config = yaml.load(f, Loader=SafeLoader)
                    logger.info(f"Successfully loaded configuration from {config_path}")
                    
                    # Process environment variables
                    config = ConfigManager._process_env_variables(config)
                    
                    # Validate configuration
                    ConfigManager._validate_config(config)
                    
                    return config
                    
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML configuration: {str(e)}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def _process_env_variables(config: Dict) -> Dict:
        """Process environment variables in configuration recursively."""
        if isinstance(config, dict):
            return {
                key: ConfigManager._process_env_variables(value)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [ConfigManager._process_env_variables(item) for item in config]
        elif isinstance(config, str):
            # Handle ${VAR:default} format
            if config.startswith('${') and config.endswith('}'):
                env_spec = config[2:-1]  # Remove ${ and }
                
                # Check if there's a default value specified
                if ':' in env_spec:
                    env_var, default_value = env_spec.split(':', 1)
                    env_value = os.getenv(env_var)
                    if env_value is None:
                        logger.debug(f"Environment variable {env_var} not found, using default: {default_value}")
                        # Convert string representations to proper types
                        if default_value.lower() == 'true':
                            return True
                        elif default_value.lower() == 'false':
                            return False
                        elif default_value.isdigit():
                            return int(default_value)
                        else:
                            return default_value
                    else:
                        # Convert string representations to proper types
                        if env_value.lower() == 'true':
                            return True
                        elif env_value.lower() == 'false':
                            return False
                        elif env_value.isdigit():
                            return int(env_value)
                        else:
                            return env_value
                else:
                    # No default value specified
                    env_var = env_spec
                env_value = os.getenv(env_var)
                if env_value is None:
                    logger.warning(f"Environment variable {env_var} not found")
                    # Try to get from .env file
                    env_path = Path(__file__).parent.parent.parent / ".env"
                    if env_path.exists():
                        with open(env_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    try:
                                        key, value = line.split('=', 1)
                                        if key.strip() == env_var:
                                            env_value = value.strip().strip('"').strip("'")
                                            os.environ[env_var] = env_value
                                            break
                                    except ValueError:
                                        continue
                    if env_value is None:
                        return config  # Return original if env var not found
                return env_value
            # Handle $VAR format
            elif config.startswith('$') and len(config) > 1:
                env_var = config[1:]
                env_value = os.getenv(env_var)
                if env_value is None:
                    logger.warning(f"Environment variable {env_var} not found")
                    return config  # Return original if env var not found
                return env_value
        return config
    
    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """Validate required configuration sections and their structure."""
        # Required top-level sections
        required_sections = {
            'market_data': ['validation', 'cache'],
            'exchanges': [],  # At least one exchange should be present
            'analysis': ['indicators'],  # Removed 'weights' as weights are now in confluence section
            'confluence': ['weights', 'thresholds'],  # Added confluence section with weights and thresholds
            'monitoring': ['enabled', 'interval'],
            'logging': ['version', 'handlers', 'loggers'],
            'data_processing': ['enabled', 'pipeline']
        }
        
        # Check required sections
        for section, subsections in required_sections.items():
            logger.debug(f"Checking section: {section}")
            if section not in config:
                logger.error(f"Missing required configuration section: {section}")
                raise ValueError(f"Missing required configuration section: {section}")
            
            # Check required subsections
            section_config = config[section]
            logger.debug(f"Section {section} config: {section_config}")
            for subsection in subsections:
                logger.debug(f"Checking subsection: {subsection} in {section}")
                if subsection not in section_config:
                    logger.error(f"Missing required subsection '{subsection}' in {section}")
                    raise ValueError(f"Missing required subsection '{subsection}' in {section}")
        
        # Validate exchange configurations
        exchanges = config.get('exchanges', {})
        if not exchanges:
            raise ValueError("No exchanges configured")
            
        primary_found = False
        for exchange_id, exchange_config in exchanges.items():
            if exchange_config.get('enabled', False):
                if exchange_config.get('primary', False):
                    if primary_found:
                        raise ValueError("Multiple primary exchanges configured")
                    primary_found = True
                
                # Validate exchange config
                ConfigManager._validate_exchange_config(exchange_id, exchange_config)
        
        if not primary_found:
            raise ValueError("No primary exchange configured")
        
        # New validation for root-level timeframes
        if 'timeframes' not in config:
            raise ValueError("Missing required 'timeframes' section in root config")
        
        if not isinstance(config['timeframes'], dict) or len(config['timeframes']) == 0:
            raise ValueError("Timeframes configuration must be a non-empty dictionary")
    
    @staticmethod
    def _validate_exchange_config(exchange_id: str, config: Dict[str, Any]) -> None:
        """Validate exchange configuration."""
        required_fields = {
            'api_credentials': ['api_key', 'api_secret'],
            'rate_limits': ['requests_per_second', 'requests_per_minute']
        }
        
        for section, fields in required_fields.items():
            if section not in config:
                raise ValueError(f"Missing required section '{section}' in {exchange_id} configuration")
            
            section_config = config[section]
            missing_fields = [f for f in fields if f not in section_config]
            if missing_fields:
                raise ValueError(f"Missing required fields {missing_fields} in {exchange_id}.{section}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        return self._config
    
    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        """Set the configuration."""
        self._config = value
        self._initialized = True
    
    def get_exchange_config(self, exchange_id: str) -> Dict[str, Any]:
        """Get configuration for specific exchange with validation."""
        exchanges = self.config.get('exchanges', {})
        if exchange_id not in exchanges:
            raise ValueError(f"Exchange {exchange_id} not found in configuration")
        return exchanges[exchange_id]
    
    @lru_cache(maxsize=1)
    def get_market_data_config(self) -> Dict[str, Any]:
        """Get cached market data configuration."""
        return self.config.get('market_data', {})
    
    @lru_cache(maxsize=1)
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get cached analysis configuration."""
        return self.config.get('analysis', {})
    
    @lru_cache(maxsize=1)
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get cached monitoring configuration."""
        return self.config.get('monitoring', {})
    
    def get_value(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation path."""
        try:
            value = self.config
            for key in path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_indicator_weights(self, indicator_type: str) -> Dict[str, float]:
        """
        Get the indicator weights for a specific indicator type.
        
        Args:
            indicator_type: Type of indicator (technical, orderflow, etc.)
            
        Returns:
            Dictionary of indicator weights
        """
        # Get weights from the unified weight structure
        weights = self.config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get(indicator_type, {})
        
        if not weights:
            self.logger.warning(f"No weights found for indicator type: {indicator_type}, using default weights")
            # Use default weights
            if indicator_type == 'technical':
                return {'rsi': 0.2, 'macd': 0.2, 'ao': 0.2, 'williams_r': 0.2, 'cci': 0.2}
            elif indicator_type == 'volume':
                return {'volume_delta': 0.25, 'adl': 0.25, 'cmf': 0.25, 'relative_volume': 0.25}
            elif indicator_type == 'orderflow':
                return {'cvd': 0.3, 'trade_flow': 0.3, 'imbalance': 0.2, 'open_interest': 0.2}
            elif indicator_type == 'orderbook':
                return {'imbalance': 0.3, 'depth': 0.25, 'spread': 0.2, 'liquidity': 0.25}
            elif indicator_type == 'sentiment':
                return {'funding_rate': 0.3, 'long_short_ratio': 0.3, 'liquidations': 0.2, 'social_sentiment': 0.2}
                
        return weights
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config.get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """Get data processing configuration"""
        return self.config.get('data_processing', {})
    
    def get_session_analysis_config(self) -> Dict[str, Any]:
        """Get session analysis configuration"""
        return self.config.get('session_analysis', {})
    
    def get_timeframe_config(self) -> Dict[str, str]:
        """Get timeframe configuration.
        
        Returns:
            Dictionary mapping timeframe keys to actual timeframe values
        """
        try:
            timeframes = self.config.get('timeframes', {})
            
            if not timeframes:
                # Default timeframes if not configured
                timeframes = {
                    'base': 1,
                    'ltf': 5,
                    'mtf': 30,
                    'htf': 240
                }
            
            return timeframes
            
        except Exception as e:
            logger.error(f"Error getting timeframe configuration: {str(e)}")
            return {
                'base': 1,
                'ltf': 5,
                'mtf': 30,
                'htf': 240
            } 