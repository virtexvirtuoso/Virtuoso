"""Logging configuration utility."""

import os
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any

def configure_logging(config: Dict[str, Any]) -> None:
    """Configure logging based on configuration dictionary.
    
    Args:
        config: Logging configuration dictionary
    """
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    try:
        logging.config.dictConfig(config)
        logger = logging.getLogger(__name__)
        logger.info("Logging configured successfully")
        
    except Exception as e:
        # Set up basic logging if configuration fails
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] - %(name)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Error configuring logging: {str(e)}")
        logger.info("Using basic logging configuration") 