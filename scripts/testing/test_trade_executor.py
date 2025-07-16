#!/usr/bin/env python3
"""
Test script to verify TradeExecutor's core functionality
"""

import os
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv
from src.trade_execution.trade_executor import TradeExecutor

# Load environment variables from .env file
load_dotenv("config/env/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('trade_executor_test')

def test_position_size_calculation():
    """Test the position size calculation functionality of TradeExecutor"""
    try:
        logger.info("Setting up minimal configuration for position size calculation test")
        
        # Get API credentials from environment variables
        api_key = os.getenv("BYBIT_API_KEY", "test-key")
        api_secret = os.getenv("BYBIT_API_SECRET", "test-secret")
        
        # Create minimal configuration required for testing position size calculations
        config = {
            'exchanges': {
                'bybit': {
                    'api_credentials': {
                        'api_key': api_key,
                        'api_secret': api_secret
                    }
                }
            },
            'position_manager': {
                'base_position_pct': 0.03,
                'scale_factor': 0.01,
                'max_position_pct': 0.10
            },
            'confluence': {
                'thresholds': {
                    'buy': 68,
                    'sell': 35
                }
            }
        }
        
        # Initialize TradeExecutor without calling initialize() which makes API calls
        executor = TradeExecutor(config)
        logger.info("TradeExecutor instance created with minimal config")
        
        # Test position size calculation for different scenarios
        test_cases = [
            # Buy signals
            {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'balance': 10000.0,
                'score': 50.0,
                'expected': 'no trade'  # Below buy threshold (68) - should not trade
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'balance': 10000.0,
                'score': 67.0,
                'expected': 'no trade'  # Below buy threshold (68) - should not trade
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'balance': 10000.0,
                'score': 68.0,
                'expected': 'base position'  # At buy threshold (68) - use base position
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'balance': 10000.0,
                'score': 75.0,
                'expected': 'scaled up'  # Above buy threshold (68) - scale up
            },
            # Sell signals
            {
                'symbol': 'BTC/USDT',
                'side': 'sell',
                'balance': 10000.0,
                'score': 25.0,
                'expected': 'scaled up'  # Below sell threshold (35) - scale up
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'sell',
                'balance': 10000.0,
                'score': 35.0,
                'expected': 'base position'  # At sell threshold (35) - use base position
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'sell',
                'balance': 10000.0,
                'score': 36.0,
                'expected': 'no trade'  # Above sell threshold (35) - should not trade
            },
            {
                'symbol': 'BTC/USDT',
                'side': 'sell',
                'balance': 10000.0,
                'score': 40.0,
                'expected': 'no trade'  # Above sell threshold (35) - should not trade
            }
        ]
        
        for idx, case in enumerate(test_cases):
            position_size = executor.calculate_position_size(
                symbol=case['symbol'],
                side=case['side'],
                available_balance=case['balance'],
                confluence_score=case['score']
            )
            
            base_position = case['balance'] * executor.base_position_pct
            max_position = case['balance'] * executor.max_position_pct
            
            logger.info(f"Test case {idx+1}:")
            logger.info(f"  Symbol: {case['symbol']}, Side: {case['side']}, Score: {case['score']}")
            logger.info(f"  Available balance: ${case['balance']}")
            logger.info(f"  Calculated position size: ${position_size}")
            
            # Skip showing base/max for no trade cases
            if position_size > 0:
                logger.info(f"  Base position: ${base_position}")
                logger.info(f"  Max position: ${max_position}")
            
            # Verify expectations
            if case['expected'] == 'no trade':
                assert position_size == 0.0, "Should not trade (position size should be 0)"
                logger.info("  Result: ✅ No trade as expected")
            elif case['expected'] == 'base position':
                assert abs(position_size - base_position) < 0.01, "Should use base position"
                logger.info("  Result: ✅ Using base position as expected")
            elif case['expected'] == 'scaled up':
                assert position_size > base_position, "Should scale up position"
                assert position_size <= max_position, "Should not exceed max position"
                logger.info("  Result: ✅ Scaled up position as expected")
            
            logger.info("")
        
        logger.info("All position size calculation tests passed!")
        return True
        
    except AssertionError as ae:
        logger.error(f"Test failed: {str(ae)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_api_functionality():
    """Test the API functionality of TradeExecutor when valid credentials are available"""
    try:
        logger.info("Checking for valid API credentials")
        
        # Get API credentials from environment variables
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_API_SECRET")
        
        # Skip API tests if credentials are not available
        if not api_key or not api_secret or api_key == "test-key":
            logger.warning("No valid API credentials found in environment. Skipping API tests.")
            return True
            
        logger.info("Valid API credentials found. Running API functionality tests.")
        
        # Create configuration for API testing
        config = {
            'exchanges': {
                'bybit': {
                    'api_credentials': {
                        'api_key': api_key,
                        'api_secret': api_secret
                    },
                    'rest_endpoint': 'https://api-demo.bybit.com'
                }
            },
            'position_manager': {
                'base_position_pct': 0.03,
                'scale_factor': 0.01,
                'max_position_pct': 0.10
            },
            'confluence': {
                'thresholds': {
                    'buy': 68,
                    'sell': 35
                }
            }
        }
        
        # Initialize TradeExecutor
        executor = TradeExecutor(config)
        await executor.initialize()
        logger.info("TradeExecutor initialized successfully with API connection")
        
        # Test wallet balance
        logger.info("Testing wallet balance retrieval...")
        balance = await executor._get_wallet_balance()
        if not balance:
            logger.warning("Wallet balance retrieval returned empty result")
        else:
            logger.info(f"Successfully retrieved wallet balance")
        
        # Test simulated trade
        logger.info("Testing simulated trade execution...")
        trade_result = await executor.simulate_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.001,
            confluence_score=75.0
        )
        
        if trade_result and trade_result.get('success'):
            logger.info(f"Successfully simulated trade at price: ${trade_result.get('price', 'N/A')}")
        else:
            logger.warning(f"Simulated trade returned: {trade_result}")
        
        # Clean up
        await executor.close()
        logger.info("API functionality tests completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"API test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_scaled_stop_loss_calculation():
    """Test the scaled stop loss calculation functionality"""
    try:
        logger.info("Testing scaled stop loss calculations")
        
        # Create configuration with max_position_pct = 0.20
        config = {
            'exchanges': {
                'bybit': {
                    'api_credentials': {
                        'api_key': 'test-key',
                        'api_secret': 'test-secret'
                    }
                }
            },
            'position_manager': {
                'base_position_pct': 0.03,
                'trailing_stop_pct': 0.02,  # Note: Our trade_executor will read this from config
                'scale_factor': 0.01,
                'max_position_pct': 0.20
            },
            'confluence': {
                'thresholds': {
                    'buy': 68,
                    'sell': 35
                }
            }
        }
        
        # Initialize TradeExecutor
        executor = TradeExecutor(config)
        
        # Test cases
        balance = 10000.0
        test_cases = [
            # Position size, expected stop loss pct
            {'position': 0.03 * balance, 'expected': 0.0200},  # Base position - default stop
            {'position': 0.05 * balance, 'expected': 0.0192},  # 12% between base and max - slightly tighter
            {'position': 0.10 * balance, 'expected': 0.0173},  # 41% between base and max - tighter
            {'position': 0.15 * balance, 'expected': 0.0153},  # 71% between base and max - much tighter
            {'position': 0.20 * balance, 'expected': 0.0133},  # Max position - tightest stop
        ]
        
        for idx, case in enumerate(test_cases):
            position = case['position']
            expected = case['expected']
            
            stop_pct = executor.calculate_scaled_stop_loss(position, balance)
            position_pct = position / balance * 100
            
            logger.info(f"Test case {idx+1}:")
            logger.info(f"  Position: ${position:.2f} ({position_pct:.2f}% of balance)")
            logger.info(f"  Calculated stop loss: {stop_pct*100:.2f}%")
            logger.info(f"  Expected stop loss: {expected*100:.2f}%")
            
            # Check if within tolerance
            assert abs(stop_pct - expected) < 0.001, f"Stop loss {stop_pct} should be close to {expected}"
            logger.info(f"  Result: ✅ Correct stop loss calculated")
            logger.info("")
        
        logger.info("All scaled stop loss tests passed!")
        return True
        
    except AssertionError as ae:
        logger.error(f"Test failed: {str(ae)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def run_all_tests():
    """Run all tests"""
    # Always run position size calculation test
    pos_size_success = test_position_size_calculation()
    
    # Run API tests if position size tests pass
    api_success = True
    if pos_size_success:
        logger.info("Position size calculation tests passed, proceeding to API tests")
        api_success = await test_api_functionality()
    
    # Run scaled stop loss test if position size tests pass
    scaled_stop_loss_success = True
    if pos_size_success:
        logger.info("Position size calculation tests passed, proceeding to scaled stop loss test")
        scaled_stop_loss_success = test_scaled_stop_loss_calculation()
    
    # Return overall success
    return pos_size_success and api_success and scaled_stop_loss_success

if __name__ == "__main__":
    logger.info("Starting TradeExecutor tests")
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1) 