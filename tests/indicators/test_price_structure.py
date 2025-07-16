#!/usr/bin/env python3

import yaml
import logging
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

def main():
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test_price_structure')
    
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
    
    # Test _compute_weighted_score with sample data
    test_scores = {
        'order_blocks': 75.0,
        'support_resistance': 60.0,
        'trend_position': 40.0,
        'volume_profile': 80.0,
        'swing_structure': 50.0
    }
    
    print("\nTest Scores:")
    for component, score in test_scores.items():
        print(f"  {component}: {score:.2f}")
    
    # Calculate weighted score
    weighted_score = indicator._compute_weighted_score(test_scores)
    print(f"\nWeighted Score: {weighted_score:.2f}")
    
    # Test with mapped component names
    mapped_test_scores = {
        'order_block': 75.0,
        'support_resistance': 60.0,
        'vwap': 40.0,
        'volume_profile': 80.0,
        'swing_structure': 50.0
    }
    
    print("\nMapped Test Scores:")
    for component, score in mapped_test_scores.items():
        print(f"  {component}: {score:.2f}")
    
    # Calculate weighted score with mapped names
    mapped_weighted_score = indicator._compute_weighted_score(mapped_test_scores)
    print(f"\nMapped Weighted Score: {mapped_weighted_score:.2f}")

if __name__ == "__main__":
    main() 