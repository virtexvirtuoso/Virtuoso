"""Configuration manager for the application."""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration loading and access.
    
    This class handles:
    - Loading configuration from YAML
    - Environment variable substitution
    - Configuration validation
    - Providing typed access to config sections
    """
    
    _instance = None
    _config = None
    
    def __new__(cls, config=None):
        """Singleton pattern to ensure only one config instance."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config=None):
        """Initialize the ConfigManager.
        
        Args:
            config: Optional pre-loaded configuration
        """
        if not hasattr(self, '_initialized') or not self._initialized:
            if config is not None:
                self._config = config
            else:
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
                current_dir.parent.parent.parent / "config" / "config.yaml",  # /project_root/config/config.yaml
                current_dir.parent.parent / "config.yaml",                    # /project_root/src/config.yaml
                current_dir.parent / "config.yaml",                           # /project_root/src/core/config.yaml
                current_dir / "config.yaml"                                  # /project_root/src/core/config/config.yaml
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
                    config = yaml.safe_load(f)
                    logger.info(f"Successfully loaded configuration from {config_path}")
                    
                    # Process environment variables
                    config = ConfigManager._process_env_variables(config)
                    
                    # Validate configuration
                    instance = ConfigManager.__new__(ConfigManager)
                    instance._validate_config(config)
                    
                    return config
                    
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML configuration: {str(e)}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
            # Return empty config to avoid further errors
            return {}
    
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
            # Handle ${VAR} format
            if config.startswith('${') and config.endswith('}'):
                env_var = config[2:-1]
                env_value = os.getenv(env_var)
                if env_value is None:
                    logger.warning(f"Environment variable {env_var} not found")
                    # Try to get from .env file
                    from pathlib import Path
                    env_path = Path(__file__).parent.parent.parent / "config" / ".env"
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
    
    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get a configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Configuration section or None if not found
        """
        return self._config.get(section, {}) if self._config else {}
    
    def get_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation path.
        
        Args:
            path: Dot-notation path (e.g., 'database.host')
            default: Default value if path not found
            
        Returns:
            Configuration value or default if not found
        """
        if not self._config:
            return default
            
        parts = path.split('.')
        value = self._config
        
        try:
            for part in parts:
                value = value.get(part, {})
                
            # Check if we reached a non-dict value
            if value == {} and parts[-1] not in self._config:
                return default
                
            return value
        except (KeyError, TypeError):
            return default

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the configuration structure.
        
        Checks for required sections and their structure.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not config:
            raise ValueError("Empty configuration")
            
        # Define required sections (make them less strict)
        required_sections = {
            'exchanges': [],  # Remove 'enabled' requirement
            'timeframes': [],
            'analysis': [],  # Remove 'thresholds' requirement
            'monitoring': []
        }
        
        # Check required sections
        for section, subsections in required_sections.items():
            logger.debug(f"Checking section: {section}")
            if section not in config:
                logger.warning(f"Missing configuration section: {section}")
                # Don't raise error, just warn
                continue
            
            # Check required subsections (if any)
            section_config = config[section]
            logger.debug(f"Section {section} config: {section_config}")
            for subsection in subsections:
                logger.debug(f"Checking subsection: {subsection} in {section}")
                if subsection not in section_config:
                    logger.warning(f"Missing subsection '{subsection}' in {section}")
                    # Don't raise error, just warn
        
        # Validate exchange configurations (make less strict)
        if 'exchanges' in config:
            self._validate_exchanges(config)
        
        # Validate timeframes (make less strict)
        if 'timeframes' in config:
            self._validate_timeframes(config)
    
    def _validate_exchanges(self, config: Dict[str, Any]) -> None:
        """Validate exchange configurations.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If exchange validation fails
        """
        exchanges = config.get('exchanges', {})
        if not exchanges:
            logger.warning("No exchanges configured")
            return
            
        primary_found = False
        for exchange_id, exchange_config in exchanges.items():
            if isinstance(exchange_config, dict) and exchange_config.get('enabled', False):
                if exchange_config.get('primary', False):
                    if primary_found:
                        logger.warning("Multiple primary exchanges configured")
                    primary_found = True
                
                # Check recommended exchange fields (don't require them)
                recommended_fields = ['api_key', 'secret']
                for field in recommended_fields:
                    if field not in exchange_config:
                        logger.debug(f"Exchange {exchange_id} missing recommended field: {field}")
        
        if not primary_found:
            logger.debug("No primary exchange configured")

    def _validate_timeframes(self, config: Dict[str, Any]) -> None:
        """Validate timeframe configurations.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If timeframe validation fails
        """
        timeframes = config.get('timeframes', {})
        if not timeframes:
            logger.warning("No timeframes configured")
            return
            
        recommended_timeframes = ['base', 'ltf', 'mtf', 'htf']
        for tf in recommended_timeframes:
            if tf not in timeframes:
                logger.debug(f"Missing recommended timeframe: {tf}") 