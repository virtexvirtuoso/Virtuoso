#!/usr/bin/env python3
"""Simple test script for the Awesome Oscillator calculation."""

import logging
import pandas as pd
import numpy as np
import talib
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_ao(df, fast_period=5, slow_period=34):
    """Calculate Awesome Oscillator."""
    if 'high' not in df or 'low' not in df:
        logger.error("DataFrame must contain 'high' and 'low' columns")
        return None
        
    # Calculate median price
    df['median_price'] = (df['high'] + df['low']) / 2
    
    # Calculate AO using SMA
    fast_sma = talib.SMA(df['median_price'], timeperiod=fast_period)
    slow_sma = talib.SMA(df['median_price'], timeperiod=slow_period)
    ao = fast_sma - slow_sma
    
    return ao

def calculate_ao_score(df, ao_fast=5, ao_slow=34):
    """Calculate Awesome Oscillator score with improved scaling for real-world data."""
    try:
        # Validate input
        if 'high' not in df or 'low' not in df:
            logger.error("Missing required columns for AO calculation")
            return 50.0
            
        # Calculate median price
        median_price = (df['high'] + df['low']) / 2
        
        # Calculate AO
        fast_sma = talib.SMA(median_price, timeperiod=ao_fast)
        slow_sma = talib.SMA(median_price, timeperiod=ao_slow)
        ao = fast_sma - slow_sma
        
        # Drop NaN values and ensure we have enough data
        ao_valid = ao.dropna()
        if len(ao_valid) < 2:
            logger.warning("Insufficient data points for AO calculation")
            return 50.0
        
        # Get latest values and historical context
        current_ao = ao_valid.iloc[-1]
        prev_ao = ao_valid.iloc[-2]
        
        # Calculate dynamic scaling factor based on historical AO volatility
        ao_history = ao_valid.tail(20)
        if len(ao_history) < 5:
            ao_std = 1.0  # Default if not enough history
        else:
            ao_std = max(ao_history.std(), 0.0001)  # Prevent division by zero
        
        # Normalize the scaling factor based on price
        price_scale = df['close'].iloc[-1] * 0.0001  # 0.01% of price
        scaling_factor = max(100 / ao_std, 1000) if ao_std > 0 else 1000
        
        # Apply reasonable limits to the scaling factor
        scaling_factor = min(max(scaling_factor, 100), 10000)
        
        logger.info(f"AO calculation: current_ao={current_ao:.6f}, prev_ao={prev_ao:.6f}, scaling_factor={scaling_factor:.2f}")
        
        # Calculate score with adaptive scaling
        base_score = 50 + (current_ao * scaling_factor * 0.01)
        
        # Direction change has more impact than absolute value
        momentum_factor = 30 if abs(current_ao) > 0.0001 else 10
        momentum_score = 50 + ((current_ao - prev_ao) * scaling_factor * 0.02 * momentum_factor)
        
        # Log intermediate scores
        logger.info(f"AO base_score={base_score:.2f}, momentum_score={momentum_score:.2f}")
        
        # Zero-crossing is significant - add bonus for crossing zero line
        zero_cross_bonus = 0
        if (prev_ao < 0 and current_ao > 0):  # Crossing from negative to positive
            zero_cross_bonus = 15  # Bullish bonus
            logger.info("AO crossed zero line from below (bullish)")
        elif (prev_ao > 0 and current_ao < 0):  # Crossing from positive to negative
            zero_cross_bonus = -15  # Bearish penalty
            logger.info("AO crossed zero line from above (bearish)")
        
        # Combine scores with zero-crossing bonus
        score = (base_score * 0.6 + momentum_score * 0.4) + zero_cross_bonus
        final_score = float(np.clip(score, 0, 100))
        
        logger.info(f"AO final_score={final_score:.2f} (with zero_cross_bonus={zero_cross_bonus})")
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating AO score: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 50.0

def create_test_data():
    """Create test data for AO calculation."""
    # Create longer data series to ensure enough data for AO calculation
    n_samples = 200  # More samples for better visualization
    
    # Create up-trending data
    uptrend = pd.DataFrame({
        'open': np.linspace(100, 120, n_samples),
        'high': np.linspace(101, 122, n_samples) + np.random.normal(0, 0.5, n_samples),
        'low': np.linspace(99, 118, n_samples) - np.random.normal(0, 0.5, n_samples),
        'close': np.linspace(100, 120, n_samples) + np.random.normal(0, 0.3, n_samples),
        'volume': np.random.randn(n_samples) * 1000 + 5000
    })
    
    # Create down-trending data
    downtrend = pd.DataFrame({
        'open': np.linspace(120, 100, n_samples),
        'high': np.linspace(122, 101, n_samples) + np.random.normal(0, 0.5, n_samples),
        'low': np.linspace(118, 99, n_samples) - np.random.normal(0, 0.5, n_samples),
        'close': np.linspace(120, 100, n_samples) + np.random.normal(0, 0.3, n_samples),
        'volume': np.random.randn(n_samples) * 1000 + 5000
    })
    
    # Create sideways data with slight noise
    base = 100
    sideways = pd.DataFrame({
        'open': np.random.normal(base, 0.5, n_samples),
        'high': [max(base + np.random.normal(1, 0.3), o) for o in np.random.normal(base, 0.5, n_samples)],
        'low': [min(base - np.random.normal(1, 0.3), o) for o in np.random.normal(base, 0.5, n_samples)],
        'close': np.random.normal(base, 0.5, n_samples),
        'volume': np.random.randn(n_samples) * 1000 + 5000
    })
    
    # Create data with a zero-crossing
    zero_cross = pd.DataFrame({
        'open': np.concatenate([np.linspace(110, 100, n_samples//2), np.linspace(100, 110, n_samples//2)]),
        'high': np.concatenate([np.linspace(112, 101, n_samples//2), np.linspace(101, 112, n_samples//2)]) + np.random.normal(0, 0.5, n_samples),
        'low': np.concatenate([np.linspace(108, 99, n_samples//2), np.linspace(99, 108, n_samples//2)]) - np.random.normal(0, 0.5, n_samples),
        'close': np.concatenate([np.linspace(110, 100, n_samples//2), np.linspace(100, 110, n_samples//2)]) + np.random.normal(0, 0.3, n_samples),
        'volume': np.random.randn(n_samples) * 1000 + 5000
    })
    
    return {
        'uptrend': uptrend, 
        'downtrend': downtrend, 
        'sideways': sideways, 
        'zero_cross': zero_cross
    }

def plot_ao_vs_price(df, ao, data_type):
    """Plot AO alongside price data."""
    plt.figure(figsize=(14, 10))
    
    # Top subplot for price
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df['close'].values, label='Close Price')
    ax1.set_title(f'Price Chart - {data_type.capitalize()}')
    ax1.legend()
    ax1.grid(True)
    
    # Bottom subplot for AO
    ax2 = plt.subplot(2, 1, 2)
    
    # Create color list based on sequential changes
    colors = []
    for i in range(len(ao)):
        if i == 0:
            colors.append('green')  # Default first bar as green
        else:
            colors.append('green' if ao.iloc[i] > ao.iloc[i-1] else 'red')
    
    # Plot using the color list
    ax2.bar(range(len(ao)), ao.values, color=colors)
    ax2.axhline(y=0, color='black', linestyle='-')
    ax2.set_title('Awesome Oscillator')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(f'ao_test_{data_type}.png')
    logger.info(f"Chart saved as ao_test_{data_type}.png")

def main():
    """Main test function."""
    logger.info("Testing Awesome Oscillator calculation")
    
    # Create test data
    test_data = create_test_data()
    
    # Test each dataset
    for data_type, df in test_data.items():
        logger.info(f"\n===== Testing {data_type} data =====")
        
        # Calculate AO
        ao = calculate_ao(df)
        if ao is None:
            continue
            
        # Ensure we have enough data (no NaNs at the beginning)
        valid_ao = ao.dropna()
        if len(valid_ao) < 2:
            logger.warning(f"Not enough valid AO data points for {data_type}")
            continue
            
        # Print some statistics
        logger.info(f"AO Statistics: Min={valid_ao.min():.4f}, Max={valid_ao.max():.4f}, Mean={valid_ao.mean():.4f}, Std={valid_ao.std():.4f}")
        logger.info(f"AO Last 5 Values: {valid_ao.tail(5).values}")
            
        # Calculate AO score with our improved function
        ao_score = calculate_ao_score(df)
        logger.info(f"AO Score: {ao_score:.2f}")
        
        # Plot results
        plot_ao_vs_price(df, valid_ao, data_type)

    # Create a summary table of normal vs extreme AO values
    logger.info("\n===== AO Score Response Testing =====")
    
    # Create a test dataframe with adequate history
    test_df = test_data['uptrend'].copy()  # Use the uptrend data as base
    
    # Test cases with different AO values (manual override for testing)
    test_cases = [
        {"name": "Strong Positive", "current": 5.0, "prev": 4.0},
        {"name": "Weak Positive", "current": 0.5, "prev": 0.3},
        {"name": "Very Weak Positive", "current": 0.05, "prev": 0.03},
        {"name": "Ultra Weak Positive", "current": 0.005, "prev": 0.003},
        {"name": "Zero", "current": 0.0, "prev": 0.0},
        {"name": "Ultra Weak Negative", "current": -0.005, "prev": -0.003},
        {"name": "Very Weak Negative", "current": -0.05, "prev": -0.03},
        {"name": "Weak Negative", "current": -0.5, "prev": -0.3},
        {"name": "Strong Negative", "current": -5.0, "prev": -4.0},
        {"name": "Bullish Zero Cross", "current": 0.1, "prev": -0.1},
        {"name": "Bearish Zero Cross", "current": -0.1, "prev": 0.1},
        {"name": "Positive Accelerating", "current": 2.0, "prev": 1.0},
        {"name": "Positive Decelerating", "current": 2.0, "prev": 3.0},
        {"name": "Negative Accelerating", "current": -2.0, "prev": -1.0},
        {"name": "Negative Decelerating", "current": -2.0, "prev": -3.0},
    ]
    
    # Run and display test cases
    print("\nAO Score Response Table:")
    print("-" * 80)
    print(f"{'Test Case':<25} | {'Current AO':>10} | {'Previous AO':>10} | {'AO Score':>10}")
    print("-" * 80)
    
    for case in test_cases:
        # Create a copy of the AO series with the test values manually inserted
        ao_series = calculate_ao(test_df).dropna()
        
        # Mock the calculation by replacing the last values
        # This approach maintains the historical data needed for scaling
        ao_series.iloc[-1] = case["current"]
        ao_series.iloc[-2] = case["prev"]
        
        # Manually patch the dataframe to calculate scores
        test_copy = test_df.copy()
        
        # Simulate the AO calculation for our scoring function
        # (A bit hacky, but allows us to test the scoring with controlled inputs)
        def mock_sma(series, timeperiod):
            result = pd.Series(index=series.index)
            slow_val = 50  # Arbitrary base value
            # Set values to generate our desired AO
            for i in range(len(series)):
                if i == len(series) - 1:  # Last value
                    fast_val = slow_val + case["current"]
                    result.iloc[i] = fast_val if timeperiod == 5 else slow_val
                elif i == len(series) - 2:  # Second-to-last value
                    fast_val = slow_val + case["prev"]
                    result.iloc[i] = fast_val if timeperiod == 5 else slow_val
                else:
                    # Keep other historical values consistent
                    fast_val = slow_val + ao_series.iloc[i] if i < len(ao_series) else slow_val
                    result.iloc[i] = fast_val if timeperiod == 5 else slow_val
            return result
        
        # Calculate score with our test case data
        try:
            # Replace talib.SMA with our mock function temporarily
            original_sma = talib.SMA
            talib.SMA = mock_sma
            
            # Calculate the score
            score = calculate_ao_score(test_copy)
            
            # Restore the original function
            talib.SMA = original_sma
            
            print(f"{case['name']:<25} | {case['current']:>10.4f} | {case['prev']:>10.4f} | {score:>10.2f}")
            
        except Exception as e:
            logger.error(f"Error testing case {case['name']}: {str(e)}")
            print(f"{case['name']:<25} | {case['current']:>10.4f} | {case['prev']:>10.4f} | {'ERROR':>10}")
    
    print("-" * 80)
    logger.info("AO testing complete")

if __name__ == "__main__":
    main() 