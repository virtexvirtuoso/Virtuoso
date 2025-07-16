#!/usr/bin/env python3

import yaml
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create logger
logger = Logger('test_mapping')

# Create PriceStructureIndicators instance
indicator = PriceStructureIndicators(config, logger)

# Print component weights
print("\nComponent Weights:")
for component, weight in indicator.component_weights.items():
    print(f"  {component}: {weight:.2f}")

# Print component mapping
print("\nComponent Mapping:")
for config_name, internal_name in indicator.component_mapping.items():
    print(f"  {config_name} -> {internal_name}")

# Test with swing_structure component
print("\nSwing Structure Mapping:")
print(f"  swing_structure maps to: {indicator.component_mapping.get('swing_structure')}")
print(f"  Weight for {indicator.component_mapping.get('swing_structure')}: {indicator.component_weights.get(indicator.component_mapping.get('swing_structure'), 0.0):.2f}") 