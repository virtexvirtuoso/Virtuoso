#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')

try:
    from indicators.orderbook_indicators import OrderbookIndicators

    config = {
        "timeframes": {
            "base": {"interval": 1, "weight": 0.4, "validation": {"min_candles": 50}},
            "ltf": {"interval": 5, "weight": 0.3, "validation": {"min_candles": 30}},
            "mtf": {"interval": 15, "weight": 0.2, "validation": {"min_candles": 20}},
            "htf": {"interval": 60, "weight": 0.1, "validation": {"min_candles": 10}}
        }
    }

    indicators = OrderbookIndicators(config_data=config)

    retail_weight = indicators.component_weights.get('retail', 0)
    component_count = len(indicators.component_weights)

    print(f"SUCCESS: Retail weight: {retail_weight}")
    print(f"SUCCESS: Total components: {component_count}")
    print(f"SUCCESS: All components: {list(indicators.component_weights.keys())}")

    if retail_weight == 0.04 and component_count == 9:
        print("SUCCESS: VPS RPI integration fully validated")
    else:
        print(f"FAILURE: Expected retail=0.04 and 9 components, got {retail_weight} and {component_count}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()