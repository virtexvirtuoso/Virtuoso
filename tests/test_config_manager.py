#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the ConfigManager class.
"""

import unittest
import os
import sys
import tempfile
import yaml
import logging

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    """Test the ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.yaml")
        
        # Create a valid test configuration
        self.valid_config = {
            "exchanges": {
                "binance": {
                    "enabled": True,
                    "primary": True,
                    "api_key": "test_key",
                    "secret": "test_secret",
                    "testnet": True
                }
            },
            "timeframes": {
                "base": "1m",
                "ltf": "5m",
                "mtf": "1h",
                "htf": "1d"
            },
            "analysis": {
                "thresholds": {
                    "buy": 60,
                    "sell": 40
                }
            },
            "monitoring": {
                "enabled": True,
                "log_level": "INFO"
            }
        }
        
        # Write the valid config to a file
        with open(self.config_path, 'w') as f:
            yaml.dump(self.valid_config, f)
        
        # Save original method to restore later
        self.original_find_config = ConfigManager._find_config_file
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up the temporary directory
        self.temp_dir.cleanup()
        
        # Restore original method
        ConfigManager._find_config_file = self.original_find_config
        
        # Reset singleton instance
        ConfigManager._instance = None
    
    def test_find_config_file(self):
        """Test the _find_config_file method."""
        # Override the _find_config_file method to return our test file
        ConfigManager._find_config_file = lambda cls: self.config_path
        
        # Create an instance
        config_manager = ConfigManager()
        
        # Verify the config was loaded
        self.assertIsNotNone(config_manager._config)
        self.assertIn("exchanges", config_manager._config)
    
    def test_get_section(self):
        """Test the get_section method."""
        # Override the _find_config_file method to return our test file
        ConfigManager._find_config_file = lambda cls: self.config_path
        
        # Create an instance
        config_manager = ConfigManager()
        
        # Get a section
        exchanges = config_manager.get_section("exchanges")
        
        # Verify the section was returned
        self.assertIsNotNone(exchanges)
        self.assertIn("binance", exchanges)
        
        # Test non-existent section
        nonexistent = config_manager.get_section("nonexistent")
        self.assertEqual(nonexistent, {})
    
    def test_get_value(self):
        """Test the get_value method."""
        # Override the _find_config_file method to return our test file
        ConfigManager._find_config_file = lambda cls: self.config_path
        
        # Create an instance
        config_manager = ConfigManager()
        
        # Get a nested value
        api_key = config_manager.get_value("exchanges.binance.api_key")
        
        # Verify the value was returned
        self.assertEqual(api_key, "test_key")
        
        # Test non-existent value
        nonexistent = config_manager.get_value("nonexistent.path")
        self.assertIsNone(nonexistent)
        
        # Test default value
        default_value = config_manager.get_value("nonexistent.path", "default")
        self.assertEqual(default_value, "default")
    
    def test_validation_valid_config(self):
        """Test validation with a valid configuration."""
        # Override the _find_config_file method to return our test file
        ConfigManager._find_config_file = lambda cls: self.config_path
        
        # Create an instance - this should not raise exceptions
        try:
            config_manager = ConfigManager()
            # Explicitly validate
            config_manager._validate_config(config_manager._config)
        except Exception as e:
            self.fail(f"Validation raised exception for valid config: {str(e)}")
    
    def test_validation_missing_section(self):
        """Test validation with a missing required section."""
        # Create an invalid config missing the exchanges section
        invalid_config = {
            "timeframes": self.valid_config["timeframes"],
            "analysis": self.valid_config["analysis"],
            "monitoring": self.valid_config["monitoring"]
        }
        
        # Write to a different file
        invalid_path = os.path.join(self.temp_dir.name, "invalid_config.yaml")
        with open(invalid_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Override the _find_config_file method to return our invalid file
        ConfigManager._find_config_file = lambda cls: invalid_path
        
        # Create an instance - this should raise an exception
        with self.assertRaises(ValueError) as context:
            config_manager = ConfigManager()
        
        self.assertIn("Missing required configuration section", str(context.exception))
    
    def test_validation_missing_subsection(self):
        """Test validation with a missing required subsection."""
        # Create an invalid config missing a required subsection
        invalid_config = dict(self.valid_config)
        invalid_config["analysis"] = {}  # Missing thresholds
        
        # Write to a different file
        invalid_path = os.path.join(self.temp_dir.name, "invalid_subsection.yaml")
        with open(invalid_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Override the _find_config_file method to return our invalid file
        ConfigManager._find_config_file = lambda cls: invalid_path
        
        # Create an instance - this should raise an exception
        with self.assertRaises(ValueError) as context:
            config_manager = ConfigManager()
        
        self.assertIn("Missing required subsection", str(context.exception))
    
    def test_validation_exchange_config(self):
        """Test validation of exchange configurations."""
        # Create an invalid config with multiple primary exchanges
        invalid_config = dict(self.valid_config)
        invalid_config["exchanges"]["bybit"] = {
            "enabled": True,
            "primary": True,  # This creates a second primary exchange
            "api_key": "bybit_key",
            "secret": "bybit_secret"
        }
        
        # Write to a different file
        invalid_path = os.path.join(self.temp_dir.name, "invalid_exchange.yaml")
        with open(invalid_path, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Test manually to avoid initialize
        config_manager = ConfigManager.__new__(ConfigManager)
        
        # This should raise an exception
        with self.assertRaises(ValueError) as context:
            config_manager._validate_exchanges(invalid_config)
        
        self.assertIn("Multiple primary exchanges configured", str(context.exception))
    
    def test_singleton_pattern(self):
        """Test that ConfigManager follows the singleton pattern."""
        # Override the _find_config_file method to return our test file
        ConfigManager._find_config_file = lambda cls: self.config_path
        
        # Create two instances
        config_manager1 = ConfigManager()
        config_manager2 = ConfigManager()
        
        # They should be the same instance
        self.assertIs(config_manager1, config_manager2)
        
        # Modify the first instance
        config_manager1._test_attribute = "test"
        
        # The second instance should have the same attribute
        self.assertEqual(config_manager2._test_attribute, "test")

if __name__ == '__main__':
    unittest.main() 