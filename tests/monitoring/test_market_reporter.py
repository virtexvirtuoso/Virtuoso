import asyncio
import logging
import sys
import os

# Add parent directory to Python path to handle imports properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Now import can work
from src.monitoring.market_reporter import MarketReporter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_market_reporter():
    """Test the fixes for market_reporter.py to ensure all sections are included."""
    print("Initializing MarketReporter...")
    market_reporter = MarketReporter()
    
    # Test 1: Generate report with empty data (should trigger auto-generation of missing sections)
    print("\nTest 1: Testing with empty report data...")
    try:
        empty_report_success = await market_reporter.generate_market_report({})
        print(f"Generate report with empty data result: {empty_report_success}")
    except Exception as e:
        print(f"Error in Test 1: {str(e)}")
    
    # Test 2: Generate report with partial data
    print("\nTest 2: Testing with partial report data...")
    try:
        partial_data = {
            'timestamp': 1714952210000,  # Unix timestamp
            'market_overview': {
                'regime': 'NEUTRAL',
                'trend_strength': '25.0%',
                'volatility': 1.5
            }
            # Intentionally missing other sections to test fallback
        }
        partial_report_success = await market_reporter.generate_market_report(partial_data)
        print(f"Generate report with partial data result: {partial_report_success}")
    except Exception as e:
        print(f"Error in Test 2: {str(e)}")
    
    # Test 3: Generate market summary directly (bypassing the report generation)
    print("\nTest 3: Directly generating market summary...")
    try:
        market_summary = await market_reporter.generate_market_summary()
        if market_summary:
            print(f"Market summary generated successfully.")
            print(f"Sections included: {list(market_summary.keys())}")
            
            # Check if all required analytical sections exist
            required_sections = [
                'market_overview', 
                'futures_premium', 
                'smart_money_index',
                'whale_activity',
                'performance_metrics'
            ]
            missing_sections = [section for section in required_sections if section not in market_summary]
            if missing_sections:
                print(f"WARNING: Missing sections: {missing_sections}")
            else:
                print("All required analytical sections are present!")
        else:
            print("Failed to generate market summary.")
    except Exception as e:
        print(f"Error in Test 3: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_market_reporter()) 