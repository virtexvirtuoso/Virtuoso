"""
Test the Discord alert system's ability to properly interpret and display 
the strongest components that make up the confluence score.

This test validates that mock data contamination has been removed and 
that the system handles empty component dictionaries gracefully.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the classes we need to test
from src.signal_generation.signal_generator import SignalGenerator
from src.monitoring.alert_manager import AlertManager


class TestStrongestComponentsAlert:
    """Test suite for validating strongest components in Discord alerts without mock data contamination."""
    
    def setup_method(self):
        """Set up test environment."""
        # Mock configuration
        self.config = {
            'confluence': {
                'weights': {
                    'components': {
                        'technical': 0.25,
                        'volume': 0.20,
                        'orderflow': 0.20,
                        'orderbook': 0.15,
                        'sentiment': 0.10,
                        'price_structure': 0.10
                    }
                },
                'thresholds': {
                    'buy': 60.0,
                    'sell': 40.0,
                    'neutral_buffer': 5.0
                }
            },
            'timeframes': {
                'base': {
                    'weight': 1.0,
                    'interval': 60,
                    'validation': {'min_candles': 20}
                },
                'ltf': {
                    'weight': 1.0,
                    'interval': 60,
                    'validation': {'min_candles': 20}
                },
                'mtf': {
                    'weight': 0.8,
                    'interval': 240,
                    'validation': {'min_candles': 20}
                }, 
                'htf': {
                    'weight': 0.6,
                    'interval': 1440,
                    'validation': {'min_candles': 20}
                }
            }
        }
        
        # Create signal generator
        self.signal_generator = SignalGenerator(self.config)
        
        # Create mock alert manager
        self.alert_manager = Mock()
        self.alert_manager.send_confluence_alert = AsyncMock()
        
    def test_component_extraction_with_actual_data(self):
        """Test that component extraction prioritizes actual analysis data over fallbacks."""
        # Create test data with nested component structure (actual analysis format)
        test_indicators = {
            'technical': {
                'score': 75.0,
                'components': {
                    'rsi': 80.0,
                    'macd': 70.0,
                    'ao': 75.0,
                    'williams_r': 65.0,
                    'atr': 85.0,
                    'cci': 60.0
                }
            },
            'volume': {
                'score': 60.0,
                'components': {
                    'volume_delta': 65.0,
                    'cmf': 55.0,
                    'adl': 60.0,
                    'obv': 70.0,
                    'vwap': 50.0
                }
            },
            'orderflow': {
                'score': 55.0,
                'components': {
                    'trade_flow_score': 60.0,
                    'imbalance_score': 50.0,
                    'cvd': 55.0,
                    'delta': 58.0
                }
            }
        }
        
        # Test technical components extraction
        technical_components = self.signal_generator._extract_technical_components(test_indicators)
        assert 'rsi' in technical_components
        assert technical_components['rsi'] == 80.0
        assert technical_components['macd'] == 70.0
        assert len(technical_components) == 6  # Should have all 6 technical indicators
        
        # Test volume components extraction
        volume_components = self.signal_generator._extract_volume_components(test_indicators)
        assert 'volume_delta' in volume_components
        assert volume_components['volume_delta'] == 65.0
        assert volume_components['cmf'] == 55.0
        assert len(volume_components) == 5  # Should have all 5 volume indicators
        
        # Test orderflow components extraction
        orderflow_components = self.signal_generator._extract_orderflow_components(test_indicators)
        assert 'trade_flow_score' in orderflow_components
        assert orderflow_components['trade_flow_score'] == 60.0
        assert orderflow_components['imbalance_score'] == 50.0
        assert len(orderflow_components) == 4  # Should have all 4 orderflow indicators
        
        logger.info("✅ Component extraction with actual data works correctly")
    
    def test_component_extraction_no_mock_data_contamination(self):
        """Test that component extraction returns empty dictionaries when no actual data is available."""
        # Create test data without nested component structure - should return empty dicts
        test_indicators = {
            'technical_score': 75.0,
            'volume_score': 60.0,
            'orderflow_score': 55.0,
            # No nested components - should NOT return hardcoded fallbacks
        }
        
        # Test technical components extraction - should return empty dict
        technical_components = self.signal_generator._extract_technical_components(test_indicators)
        assert technical_components == {}, f"Expected empty dict, got: {technical_components}"
        
        # Test volume components extraction - should return empty dict
        volume_components = self.signal_generator._extract_volume_components(test_indicators)
        assert volume_components == {}, f"Expected empty dict, got: {volume_components}"
        
        # Test orderflow components extraction - should return empty dict
        orderflow_components = self.signal_generator._extract_orderflow_components(test_indicators)
        assert orderflow_components == {}, f"Expected empty dict, got: {orderflow_components}"
        
        # Test orderbook components extraction - should return empty dict
        orderbook_components = self.signal_generator._extract_orderbook_components(test_indicators)
        assert orderbook_components == {}, f"Expected empty dict, got: {orderbook_components}"
        
        # Test sentiment components extraction - should return empty dict
        sentiment_components = self.signal_generator._extract_sentiment_components(test_indicators)
        assert sentiment_components == {}, f"Expected empty dict, got: {sentiment_components}"
        
        # Test price structure components extraction - should return empty dict
        price_structure_components = self.signal_generator._extract_price_structure_components(test_indicators)
        assert price_structure_components == {}, f"Expected empty dict, got: {price_structure_components}"
        
        # Test futures premium components extraction - should return empty dict
        futures_premium_components = self.signal_generator._extract_futures_premium_components(test_indicators)
        assert futures_premium_components == {}, f"Expected empty dict, got: {futures_premium_components}"
        
        logger.info("✅ No mock data contamination - all extraction methods return empty dicts when no actual data")
    
    def test_component_extraction_with_direct_indicators(self):
        """Test that component extraction works with direct indicator values."""
        # Create test data with direct indicator values (not nested)
        test_indicators = {
            'rsi': 75.0,
            'macd': 80.0,
            'volume_delta': 65.0,
            'cmf': 55.0,
            'cvd': 60.0,
            'trade_flow_score': 70.0,
            'support_resistance': 50.0,
            'liquidity': 45.0,
            'risk_score': 40.0,
            'funding_rate': 35.0
        }
        
        # Test technical components extraction
        technical_components = self.signal_generator._extract_technical_components(test_indicators)
        logger.debug(f"Technical components found: {technical_components}")
        assert technical_components['rsi'] == 75.0
        assert technical_components['macd'] == 80.0
        assert len(technical_components) == 2  # Should have 2 technical indicators
        
        # Test volume components extraction
        volume_components = self.signal_generator._extract_volume_components(test_indicators)
        logger.debug(f"Volume components found: {volume_components}")
        assert volume_components['delta'] == 65.0  # volume_delta becomes delta
        assert volume_components['cmf'] == 55.0
        assert len(volume_components) == 2  # Should have 2 volume indicators
        
        # Test orderflow components extraction
        orderflow_components = self.signal_generator._extract_orderflow_components(test_indicators)
        logger.debug(f"Orderflow components found: {orderflow_components}")
        assert orderflow_components['cvd'] == 60.0
        assert orderflow_components['trade_flow_score'] == 70.0
        assert len(orderflow_components) == 2  # Should have 2 orderflow indicators
        
        # Test orderbook components extraction
        orderbook_components = self.signal_generator._extract_orderbook_components(test_indicators)
        logger.debug(f"Orderbook components found: {orderbook_components}")
        assert orderbook_components['support_resistance'] == 50.0
        assert orderbook_components['liquidity'] == 45.0
        assert len(orderbook_components) == 2  # Should have 2 orderbook indicators
        
        # Test sentiment components extraction
        sentiment_components = self.signal_generator._extract_sentiment_components(test_indicators)
        logger.debug(f"Sentiment components found: {sentiment_components}")
        assert sentiment_components['risk_score'] == 40.0
        assert sentiment_components['funding_rate'] == 35.0
        assert len(sentiment_components) == 2  # Should have 2 sentiment indicators
        
        logger.info("✅ Component extraction with direct indicators works correctly")
    
    def test_weighted_impact_calculation_with_empty_components(self):
        """Test that weighted impact calculation handles empty component dictionaries gracefully."""
        # Create test data with some components having actual data and others empty
        symbol = "BTC/USDT"
        confluence_score = 70.0
        components = {
            'technical': 80.0,
            'volume': 60.0,
            'orderflow': 55.0,
            'orderbook': 50.0,
            'sentiment': 45.0,
            'price_structure': 40.0
        }
        
        # Mock results where some components have actual data and others don't
        results = {
            'technical': {
                'score': 80.0,
                'components': {
                    'rsi': 85.0,
                    'macd': 75.0,
                    'ao': 80.0
                }
            },
            'volume': {
                'score': 60.0,
                'components': {
                    'volume_delta': 65.0,
                    'cmf': 55.0
                }
            },
            # Other components will have empty component dictionaries
            'orderflow': {'score': 55.0, 'components': {}},
            'orderbook': {'score': 50.0, 'components': {}},
            'sentiment': {'score': 45.0, 'components': {}},
            'price_structure': {'score': 40.0, 'components': {}}
        }
        
        # Generate enhanced formatted data
        enhanced_data = self.signal_generator._generate_enhanced_formatted_data(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            reliability=0.8,
            buy_threshold=60.0,
            sell_threshold=40.0
        )
        
        # Verify enhanced data structure
        assert 'top_weighted_subcomponents' in enhanced_data
        top_components = enhanced_data['top_weighted_subcomponents']
        assert isinstance(top_components, list)
        
        # Should only have components with actual data (technical and volume)
        component_names = [comp['parent_display_name'] for comp in top_components]
        assert 'Technical' in component_names
        assert 'Volume' in component_names
        
        # Should NOT have components with empty dictionaries
        assert all(comp['parent_display_name'] in ['Technical', 'Volume'] for comp in top_components)
        
        # Verify weighted impact calculation for actual components
        for comp in top_components:
            assert 'weighted_impact' in comp
            assert comp['weighted_impact'] > 0  # Should have positive impact
            assert comp['weighted_impact'] > 0.5  # Should meet threshold
        
        logger.info("✅ Weighted impact calculation handles empty components gracefully")
        logger.info(f"Components with actual data: {len(top_components)}")
    
    def test_enhanced_data_generation_structure(self):
        """Test that enhanced data generation maintains proper structure with mixed data availability."""
        # Create test data with mixed component availability
        symbol = "BTC/USDT"
        confluence_score = 65.0
        components = {
            'technical': 75.0,
            'volume': 50.0,  # No actual components
            'orderflow': 60.0,
            'orderbook': 50.0,  # No actual components
            'sentiment': 50.0,  # No actual components
            'price_structure': 50.0  # No actual components
        }
        
        # Results with mixed component availability
        results = {
            'technical': {
                'score': 75.0,
                'components': {
                    'rsi': 80.0,
                    'macd': 70.0
                }
            },
            'volume': {'score': 50.0, 'components': {}},  # Empty
            'orderflow': {
                'score': 60.0,
                'components': {
                    'cvd': 65.0,
                    'delta': 55.0
                }
            },
            'orderbook': {'score': 50.0, 'components': {}},  # Empty
            'sentiment': {'score': 50.0, 'components': {}},  # Empty
            'price_structure': {'score': 50.0, 'components': {}}  # Empty
        }
        
        # Generate enhanced data
        enhanced_data = self.signal_generator._generate_enhanced_formatted_data(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            reliability=0.75,
            buy_threshold=60.0,
            sell_threshold=40.0
        )
        
        # Verify structure
        assert 'market_interpretations' in enhanced_data
        assert 'actionable_insights' in enhanced_data
        assert 'influential_components' in enhanced_data
        assert 'top_weighted_subcomponents' in enhanced_data
        
        # Verify only components with actual data are included
        top_components = enhanced_data['top_weighted_subcomponents']
        parent_components = set(comp['parent_display_name'] for comp in top_components)
        
        # Should only include Technical and Orderflow (components with actual data)
        expected_components = {'Technical', 'Orderflow'}
        assert parent_components.issubset(expected_components), f"Unexpected components: {parent_components - expected_components}"
        
        # Should NOT include components with empty dictionaries
        unexpected_components = {'Volume', 'Orderbook', 'Sentiment', 'Price Structure'}
        assert not parent_components.intersection(unexpected_components), f"Found components with empty data: {parent_components.intersection(unexpected_components)}"
        
        logger.info("✅ Enhanced data generation maintains proper structure with mixed data availability")
        logger.info(f"Components with actual subcomponents: {parent_components}")
    
    async def test_discord_alert_integration_no_mock_data(self):
        """Test integration with Discord alert system using only actual data."""
        if not os.getenv("DISCORD_WEBHOOK_URL"):
            logger.warning("⚠️ DISCORD_WEBHOOK_URL not set, skipping integration test")
            return
            
        # Create alert manager with proper config structure
        alert_config = {
            'monitoring': {
                'alerts': {
                    'thresholds': {
                        'buy': 60.0,
                        'sell': 40.0
                    },
                    'discord_webhook_url': os.getenv("DISCORD_WEBHOOK_URL")
                }
            }
        }
        
        alert_manager = AlertManager(config=alert_config)
        
        # Test data with only actual component data (no fallbacks)
        symbol = "BTC/USDT"
        confluence_score = 75.0
        components = {
            'technical': 85.0,
            'volume': 70.0,
            'orderflow': 65.0,
            'orderbook': 60.0,
            'sentiment': 55.0,
            'price_structure': 50.0
        }
        
        # Results with actual nested component data
        results = {
            'technical': {
                'score': 85.0,
                'components': {
                    'rsi': 90.0,
                    'macd': 80.0,
                    'ao': 85.0
                }
            },
            'volume': {
                'score': 70.0,
                'components': {
                    'volume_delta': 75.0,
                    'obv': 80.0
                }
            },
            'orderflow': {
                'score': 65.0,
                'components': {
                    'cvd': 70.0,
                    'delta': 60.0
                }
            },
            # Other components have empty component dictionaries (realistic scenario)
            'orderbook': {'score': 60.0, 'components': {}},
            'sentiment': {'score': 55.0, 'components': {}},
            'price_structure': {'score': 50.0, 'components': {}}
        }
        
        # Generate enhanced data
        enhanced_data = self.signal_generator._generate_enhanced_formatted_data(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            reliability=0.85,
            buy_threshold=60.0,
            sell_threshold=40.0
        )
        
        # Verify no mock data contamination
        top_components = enhanced_data.get('top_weighted_subcomponents', [])
        for comp in top_components:
            # Verify all components have meaningful impact and are not default values
            assert comp['weighted_impact'] > 0.5
            assert comp['score'] != 50.0 or comp['display_name'] in ['Ao', 'Delta']  # Allow some legitimate 50.0 values
            
        # Send alert with enhanced data
        try:
            await alert_manager.send_confluence_alert(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                reliability=0.85,
                price=67234.56,
                top_weighted_subcomponents=enhanced_data.get('top_weighted_subcomponents'),
                market_interpretations=enhanced_data.get('market_interpretations'),
                actionable_insights=enhanced_data.get('actionable_insights')
            )
            
            logger.info("✅ Discord alert sent successfully with no mock data contamination")
            
        except Exception as e:
            logger.error(f"❌ Error sending Discord alert: {str(e)}")
            raise


async def run_tests():
    """Run all tests."""
    logger.info("🧪 Starting Discord alert strongest components tests (No Mock Data Contamination)...")
    
    test_suite = TestStrongestComponentsAlert()
    test_suite.setup_method()
    
    try:
        # Run synchronous tests
        test_suite.test_component_extraction_with_actual_data()
        test_suite.test_component_extraction_no_mock_data_contamination()
        test_suite.test_component_extraction_with_direct_indicators()
        test_suite.test_weighted_impact_calculation_with_empty_components()
        test_suite.test_enhanced_data_generation_structure()
        
        # Run async tests
        await test_suite.test_discord_alert_integration_no_mock_data()
        
        logger.info("✅ All tests passed successfully! No mock data contamination detected.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests()) 