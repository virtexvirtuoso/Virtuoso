#!/usr/bin/env python3

import yaml
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.logger import Logger

def main():
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create logger
    logger = Logger('test')
    
    # Test OrderbookIndicators
    print("\nTesting OrderbookIndicators:")
    indicator = OrderbookIndicators(config, logger)
    print("Component weights:", indicator.component_weights)
    
    # Test VolumeIndicators
    print("\nTesting VolumeIndicators:")
    indicator = VolumeIndicators(config, logger)
    print("Component weights:", indicator.component_weights)
    
    # Test SentimentIndicators
    print("\nTesting SentimentIndicators:")
    indicator = SentimentIndicators(config, logger)
    print("Component weights:", indicator.component_weights)
    
    # Test PriceStructureIndicators
    print("\nTesting PriceStructureIndicators:")
    indicator = PriceStructureIndicators(config, logger)
    print("Component weights:", indicator.component_weights)
    
    # Test TechnicalIndicators
    print("\nTesting TechnicalIndicators:")
    indicator = TechnicalIndicators(config, logger)
    print("Component weights:", indicator.component_weights)
    
    # Test OrderflowIndicators
    print("\nTesting OrderflowIndicators:")
    indicator = OrderflowIndicators(config, logger)
    print("Component weights:", indicator.component_weights)

if __name__ == "__main__":
    main() 