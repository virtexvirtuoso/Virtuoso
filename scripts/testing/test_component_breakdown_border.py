#!/usr/bin/env python3
"""
Test script to verify that the Component Breakdown section can have
a top border added for consistent visual formatting.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.formatting.formatter import PrettyTableFormatter

def test_component_breakdown_border():
    """Test adding a top border to the Component Breakdown section."""
    
    print("Testing Component Breakdown Border Enhancement...")
    print("=" * 80)
    
    # Create test data
    test_results = {
        'technical': {'score': 41.04, 'components': {}},
        'volume': {'score': 52.71, 'components': {}},
        'orderbook': {'score': 76.50, 'components': {}},
        'orderflow': {'score': 49.20, 'components': {}},
        'sentiment': {'score': 62.00, 'components': {}},
        'price_structure': {'score': 50.75, 'components': {}}
    }
    
    # Test the current formatting
    current_output = PrettyTableFormatter.format_enhanced_confluence_score_table(
        symbol="TESTUSDT",
        confluence_score=54.64,
        components={'technical': 41.04, 'volume': 52.71, 'orderbook': 76.50, 'orderflow': 49.20, 'sentiment': 62.00, 'price_structure': 50.75},
        results=test_results,
        weights={'orderflow': 0.25, 'orderbook': 0.25, 'volume': 0.16, 'price_structure': 0.16, 'technical': 0.11, 'sentiment': 0.07},
        reliability=1.0
    )
    
    print("CURRENT OUTPUT:")
    print("-" * 80)
    print(current_output)
    print("-" * 80)
    
    # Check for Component Breakdown section
    lines = current_output.split('\n')
    
    component_breakdown_found = False
    has_border = False
    
    for i, line in enumerate(lines):
        if 'Component Breakdown' in line:
            component_breakdown_found = True
            # Check if there's a border above it
            if i > 0 and '╔' in lines[i-1]:
                has_border = True
                print("✅ Component Breakdown section found with top border!")
                print(f"   Header line: {line}")
                print(f"   Border line: {lines[i-1]}")
            else:
                print("❌ Component Breakdown section found but no top border")
                print(f"   Header line: {line}")
                if i > 0:
                    print(f"   Line above: {lines[i-1]}")
            break
    
    if not component_breakdown_found:
        print("❌ Component Breakdown section not found")
    
    # Show what the bordered version should look like
    print("\n" + "=" * 80)
    print("EXPECTED BORDERED VERSION:")
    print("-" * 80)
    
    # Simulate what it should look like with borders
    bordered_example = """
╔══════════════════════════════════════════════════════════════════════════════╗
║ Component Breakdown                                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║          ╔═════════════════╦═══════╦════════╦════════════════════════════════╗ ║
║          ║ Component       ║ Score ║ Impact ║ Gauge                          ║ ║
║          ╠═════════════════╬═══════╬════════╬════════════════════════════════╣ ║
║          ║ Orderbook       ║ 76.50 ║   19.1 ║ ██████████████████████········ ║ ║
║          ║ Orderflow       ║ 49.20 ║   12.3 ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓················ ║ ║
║          ║ Volume          ║ 52.71 ║    8.4 ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓··············· ║ ║
║          ║ Price Structure ║ 50.75 ║    8.1 ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓··············· ║ ║
║          ║ Technical       ║ 41.04 ║    4.5 ║ ░░░░░░░░░░░░·················· ║ ║
║          ║ Sentiment       ║ 62.00 ║    4.3 ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓············ ║ ║
║          ╚═════════════════╩═══════╩════════╩════════════════════════════════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(bordered_example)
    
    print("Component Breakdown Border Test Complete!")

if __name__ == "__main__":
    test_component_breakdown_border() 