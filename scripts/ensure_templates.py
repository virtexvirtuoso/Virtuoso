#!/usr/bin/env python3
"""
Utility script to establish a canonical template directory structure for the application.
This script centralizes all templates in src/core/reporting/templates/ and updates references.
"""

import os
import shutil
import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("template_setup")

# Define the canonical template directory
CANONICAL_TEMPLATE_DIR = os.path.join(os.getcwd(), "src", "core", "reporting", "templates")

def optimize_template_directories():
    """Create a centralized template structure and clean up redundant directories."""
    
    logger.info(f"Establishing canonical template directory at: {CANONICAL_TEMPLATE_DIR}")
    
    # Ensure canonical directory exists
    os.makedirs(CANONICAL_TEMPLATE_DIR, exist_ok=True)
    
    # List of template files we need to ensure exist
    required_templates = [
        "pdf_signal_template.html",
        "trading_report_dark.html",
        "signal_report_template.html",
        "market_report_dark.html"
    ]
    
    # Check if templates exist in canonical location
    for template in required_templates:
        if not os.path.exists(os.path.join(CANONICAL_TEMPLATE_DIR, template)):
            logger.warning(f"Template {template} missing from canonical directory")
            
            # Look in templates/ directory
            alt_template_path = os.path.join(os.getcwd(), "templates", template)
            if os.path.exists(alt_template_path) and os.path.isfile(alt_template_path):
                if not os.path.islink(alt_template_path):
                    # If it's a real file, copy it to canonical directory
                    logger.info(f"Copying {template} from templates/ to canonical directory")
                    shutil.copy2(alt_template_path, os.path.join(CANONICAL_TEMPLATE_DIR, template))
    
    # Create a config file that points to the canonical template directory
    config = {
        "template_directory": CANONICAL_TEMPLATE_DIR
    }
    
    config_dir = os.path.join(os.getcwd(), "config")
    os.makedirs(config_dir, exist_ok=True)
    
    with open(os.path.join(config_dir, "templates_config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created templates configuration at config/templates_config.json")
    
    # Create symlink from project root to the canonical directory for backward compatibility
    templates_symlink = os.path.join(os.getcwd(), "templates")
    if os.path.exists(templates_symlink):
        if os.path.islink(templates_symlink):
            os.unlink(templates_symlink)
        else:
            # Backup existing directory if it's not a symlink
            backup_dir = f"{templates_symlink}.bak"
            logger.warning(f"templates/ exists but is not a symlink. Backing up to {backup_dir}")
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            os.rename(templates_symlink, backup_dir)
    
    # Create relative symlink for compatibility
    os.symlink("src/core/reporting/templates", templates_symlink)
    logger.info(f"Created symbolic link from {templates_symlink} -> src/core/reporting/templates")
    
    logger.info("Template organization optimization complete!")
    return True

if __name__ == "__main__":
    try:
        optimize_template_directories()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error setting up templates: {str(e)}")
        sys.exit(1) 