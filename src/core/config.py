"""Configuration management for the application."""

import os
import yaml
from typing import Dict, Any, Optional

class Config:
    """Manages application configuration with reasonable defaults."""
    
    # Default configuration values
    DEFAULTS = {
        'data_processing': {
            'max_items': 1000,
            'cleanup_interval': 300,  # 5 minutes
            'data_retention_hours': 1,
            'batch_size': 100
        },
        'logging': {
            'level': 'INFO',
            'max_size': 10 * 1024 * 1024,  # 10MB
            'backup_count': 5
        },
        'error_handling': {
            'discord_webhook_url': None,
            'log_stack_traces': True
        },
        'validation': {
            'strict_mode': False,
            'type_checking': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = dict(self.DEFAULTS)
        
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
            
    def _load_config(self, config_path: str) -> None:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                
            # Update defaults with file configuration
            for section, values in file_config.items():
                if section in self.config:
                    self.config[section].update(values)
                else:
                    self.config[section] = values
                    
        except Exception as e:
            print(f"Error loading config from {config_path}: {str(e)}")
            print("Using default configuration")
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(section, {}).get(key, default)
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.
        
        Args:
            section: Configuration section
            
        Returns:
            Section configuration dict
        """
        return dict(self.config.get(section, {}))
        
    @property
    def data_processing(self) -> Dict[str, Any]:
        """Get data processing configuration."""
        return self.get_section('data_processing')
        
    @property
    def logging(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get_section('logging')
        
    @property
    def error_handling(self) -> Dict[str, Any]:
        """Get error handling configuration."""
        return self.get_section('error_handling')
        
    @property
    def validation(self) -> Dict[str, Any]:
        """Get validation configuration."""
        return self.get_section('validation') 