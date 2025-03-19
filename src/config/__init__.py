import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Returns:
    -------
    Dict[str, Any]
        Configuration dictionary
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}")
            return {}
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            logger.error("Invalid config format - expected dictionary")
            return {}
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {} 