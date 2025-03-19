import unittest
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from src.analysis.session_analyzer import SessionAnalyzer, MarketMetricsCalculator
from unittest.mock import Mock, patch
import asyncio
from src.data_processing.data_validator import DataValidator

class TestDataProcessor:
    """Mock DataProcessor for testing"""
    def __init__(self):
        self.data_validator = DataValidator({})  # Initialize with empty config for testing

class TestSessionAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.data_processor = TestDataProcessor()
        self.analyzer = SessionAnalyzer(self.data_processor)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create sample price data with proper structure
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        self.sample_price_data = pd.DataFrame({
            'open': np.random.uniform(45000, 46000, 100),
            'high': np.random.uniform(45500, 46500, 100),
            'low': np.random.uniform(44500, 45500, 100),
            'close': np.random.uniform(45000, 46000, 100),
            'volume': np.random.uniform(1, 100, 100),
            'turnover': np.random.uniform(1000, 10000, 100)
        }, index=dates)
        
        # Ensure timezone awareness
        self.sample_price_data.index = self.sample_price_data.index.tz_localize('UTC')

    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()

    def test_get_current_session(self):
        """Test getting current trading session."""
        # Mock datetime to return a fixed time
        with patch('src.analysis.session_analyzer.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 10, 0)  # 10:00 UTC
            mock_datetime.combine = datetime.combine
            
            session = self.analyzer.get_current_session()
            self.assertIsNotNone(session)
            self.assertEqual(session, 'london')  # Should be London session at 10:00 UTC

    def test_market_metrics_calculator(self):
        """Test MarketMetricsCalculator functionality."""
        calculator = MarketMetricsCalculator()
        result = calculator.calculate_imbalance_score(self.sample_price_data, {})
        
        self.assertIsInstance(result, dict)
        self.assertIn('score', result)
        self.assertIn('levels', result)
        self.assertIn('interpretation', result)

    def test_analyze_market_depth(self):
        """Test market depth analysis."""
        orderbook_data = {
            'bids': [(45000, 1.5), (44900, 2.0), (44800, 1.0)],
            'asks': [(45100, 1.0), (45200, 2.0), (45300, 1.5)]
        }
        
        result = self.analyzer._analyze_market_depth(orderbook_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('depth_score', result)
        self.assertIn('imbalance', result)
        self.assertIn('bid_volume', result)
        self.assertIn('ask_volume', result)

    def test_calculate_momentum_strength(self):
        """Test momentum strength calculation."""
        result = self.analyzer._calculate_momentum_strength(self.sample_price_data)
        
        self.assertIsInstance(result, float)
        self.assertTrue(0 <= result <= 100)

    async def test_generate_session_report_async(self):
        """Test the asynchronous generation of a session report.
        
        This test verifies that:
        1. The session report is generated successfully
        2. The report contains expected market data
        3. The report format is correct
        4. The report length is non-zero
        """
        # Define mock data before using it
        mock_data = {
            'price_data': self.sample_price_data,
            'orderbook': {
                'bids': [(45000, 1.5)],
                'asks': [(45100, 1.0)]
            }
        }

        class MockDataFetcher:
            async def fetch_session_data(self, symbols, session_info):
                return mock_data
        
        # Generate report
        report = await self.analyzer.generate_session_report(MockDataFetcher(), ['BTCUSDT'])
        
        # Verify report
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Market Report", report)

    def run_session_report_test(self):
        """Synchronous wrapper to run the asynchronous session report test.
        
        This method provides a synchronous interface to run the async test,
        handling the event loop and error management.
        """
        try:
            self.loop.run_until_complete(self.test_generate_session_report_async())
        except Exception as e:
            self.fail(f"Test wrapper failed with error: {str(e)}")

if __name__ == '__main__':
    unittest.main() 