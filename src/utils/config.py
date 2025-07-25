"""
Configuration management for Virtuoso.

Provides a centralized configuration service that implements IConfigService
and manages application configuration from multiple sources.
"""

from typing import Dict, Any, Optional, Union
import yaml
import json
import os
import logging
from pathlib import Path
from ..core.interfaces.services import IConfigService

logger = logging.getLogger(__name__)


class ConfigManager(IConfigService):
    """
    Configuration manager that implements IConfigService interface.
    
    Supports loading configuration from:
    - YAML files
    - JSON files
    - Environment variables
    - Direct dictionary initialization
    """
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_data: Optional initial configuration data
        """
        self._config: Dict[str, Any] = config_data or {}
        self._env_prefix = "VIRTUOSO_"
        self._logger = logging.getLogger(__name__)
        
        # Load environment variables
        self._load_env_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Supports dot notation for nested keys (e.g., 'database.host').
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            if '.' in key:
                keys = key.split('.')
                value = self._config
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value
            else:
                return self._config.get(key, default)
        except Exception as e:
            self._logger.warning(f"Error getting config key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        if '.' in key:
            keys = key.split('.')
            config = self._config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        else:
            self._config[key] = value
    
    def load_file(self, file_path: Union[str, Path]) -> None:
        """
        Load configuration from file.
        
        Args:
            file_path: Path to configuration file (YAML or JSON)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            self._logger.warning(f"Config file not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    file_config = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    self._logger.error(f"Unsupported config file format: {file_path}")
                    return
            
            if file_config:
                self._merge_config(file_config)
                self._logger.info(f"Loaded configuration from {file_path}")
        
        except Exception as e:
            self._logger.error(f"Error loading config file {file_path}: {e}")
    
    def _load_env_config(self) -> None:
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                config_key = key[len(self._env_prefix):].lower()
                # Convert to nested key if contains double underscore
                config_key = config_key.replace('__', '.')
                
                # Try to parse as JSON, fallback to string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value
                
                self.set(config_key, parsed_value)
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration with existing.
        
        Args:
            new_config: Configuration to merge
        """
        def deep_merge(base: Dict, update: Dict) -> Dict:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        deep_merge(self._config, new_config)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Configuration section as dictionary
        """
        return self.get(section, {})
    
    def has(self, key: str) -> bool:
        """
        Check if configuration key exists.
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists
        """
        return self.get(key) is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get entire configuration as dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()
    
    def reload(self) -> None:
        """Reload configuration from environment."""
        self._config.clear()
        self._load_env_config()
        self._logger.info("Configuration reloaded")
    
    # Convenience methods for common config patterns
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration section."""
        return self.get_section('database')
    
    def get_exchange_config(self, exchange: str) -> Dict[str, Any]:
        """Get exchange-specific configuration."""
        return self.get_section(f'exchanges.{exchange}')
    
    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert configuration section."""
        return self.get_section('alerts')
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration section."""
        return self.get_section('monitoring')
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get('debug', False)
    
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.get('logging.level', 'INFO')
    
    # IConfigService interface methods
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (IConfigService interface)."""
        return self.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value (IConfigService interface)."""
        self.set(key, value)
    
    def reload_config(self) -> None:
        """Reload configuration from source (IConfigService interface)."""
        self.reload()
    
    def validate_config(self) -> bool:
        """Validate current configuration (IConfigService interface)."""
        try:
            # Basic validation - check if config is a dictionary
            return isinstance(self._config, dict)
        except Exception:
            return False
    
    def get_environment(self) -> str:
        """Get current environment (IConfigService interface)."""
        return self.get('environment', 'development')