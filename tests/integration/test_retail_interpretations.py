#!/usr/bin/env python3

"""
Test script to validate retail sentiment interpretations in InterpretationGenerator.
Ensures comprehensive RPI analysis follows the same pattern as other orderbook components.
"""

import sys
import os
sys.path.append('/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.core.analysis.interpretation_generator import InterpretationGenerator

def test_retail_interpretations():
    """Test retail sentiment interpretations across different score ranges."""

    print("🧪 Testing Retail Sentiment Interpretations\n")
    print("=" * 80)

    interpreter = InterpretationGenerator()

    # Test different retail sentiment scenarios
    test_scenarios = [
        {
            "name": "EXTREME Retail Buying (Score: 85)",
            "data": {
                "score": 65,
                "components": {
                    "retail": 85,
                    "imbalance": 55,
                    "liquidity": 60
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.35,
                        "retail_imbalance": 0.7
                    }
                }
            }
        },
        {
            "name": "Strong Retail Buying (Score: 72)",
            "data": {
                "score": 58,
                "components": {
                    "retail": 72,
                    "imbalance": 52,
                    "liquidity": 55
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.28,
                        "retail_imbalance": 0.6
                    }
                }
            }
        },
        {
            "name": "Retail-Institutional CONFLUENCE (Both Bullish)",
            "data": {
                "score": 68,  # Institutional bullish
                "components": {
                    "retail": 75,  # Retail bullish
                    "imbalance": 65,
                    "liquidity": 62
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.32,
                        "retail_imbalance": 0.65
                    }
                }
            }
        },
        {
            "name": "Retail-Institutional DIVERGENCE (Retail Bull, Inst Bear)",
            "data": {
                "score": 35,  # Institutional bearish
                "components": {
                    "retail": 78,  # Retail bullish
                    "imbalance": 42,
                    "liquidity": 38
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.42,  # High participation
                        "retail_imbalance": 0.7
                    }
                }
            }
        },
        {
            "name": "EXTREME Retail Selling (Score: 15)",
            "data": {
                "score": 38,
                "components": {
                    "retail": 15,
                    "imbalance": 45,
                    "liquidity": 42
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.38,
                        "retail_imbalance": -0.6
                    }
                }
            }
        },
        {
            "name": "Retail Neutral (Score: 50)",
            "data": {
                "score": 52,
                "components": {
                    "retail": 50,
                    "imbalance": 48,
                    "liquidity": 53
                },
                "metadata": {
                    "raw_values": {
                        "retail_participation_rate": 0.15,
                        "retail_imbalance": 0.05
                    }
                }
            }
        }
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📊 Test {i}: {scenario['name']}")
        print("-" * 60)

        try:
            interpretation = interpreter.get_component_interpretation("orderbook", scenario["data"])

            # Extract retail-specific parts
            retail_parts = [part.strip() for part in interpretation.split('.') if 'retail' in part.lower()]

            print("💡 Full Interpretation:")
            print(f"   {interpretation}")

            if retail_parts:
                print(f"\n🎯 Retail-Specific Analysis:")
                for part in retail_parts:
                    if part:  # Skip empty parts
                        print(f"   • {part}")
            else:
                print("⚠️  NO RETAIL-SPECIFIC INTERPRETATION FOUND!")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print("✅ Retail Interpretation Testing Complete!")
    print("🔍 Verify interpretations include:")
    print("   • Detailed retail score analysis (0-100 scale)")
    print("   • CONFLUENCE/DIVERGENCE alerts with institutional flow")
    print("   • Retail participation rate insights")
    print("   • Institutional trading recommendations")
    print("   • Historical pattern context")

if __name__ == "__main__":
    test_retail_interpretations()