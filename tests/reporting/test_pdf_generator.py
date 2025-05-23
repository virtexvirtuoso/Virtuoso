import unittest
import os
import pandas as pd
import numpy as np
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from src.core.reporting.pdf_generator import ReportGenerator

class TestPDFChartGeneration(unittest.TestCase):
    """Test class for chart generation in PDF reports"""
    
    def setUp(self):
        """Set up test environment"""
        self.generator = ReportGenerator(log_level=logging.DEBUG)
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample data
        self.symbol = "BTCUSDT"
        self.entry_price = 50000
        self.stop_loss = 48000
        self.targets = [
            {"name": "Target 1", "price": 52000, "size": 50},
            {"name": "Target 2", "price": 54000, "size": 30},
            {"name": "Target 3", "price": 56000, "size": 20},
        ]
        
        # Create sample OHLCV data
        self.create_sample_ohlcv_data()
        
    def create_sample_ohlcv_data(self):
        """Create sample OHLCV data with different sizes"""
        # Create base data
        start_date = datetime.now() - timedelta(days=10)
        
        # Normal size dataset
        dates_normal = pd.date_range(start=start_date, periods=100, freq='1H')
        self.ohlcv_normal = self.generate_ohlcv_data(dates_normal, self.entry_price)
        
        # Large dataset that might cause tick overflow
        dates_large = pd.date_range(start=start_date, periods=5500, freq='5min')
        self.ohlcv_large = self.generate_ohlcv_data(dates_large, self.entry_price)
    
    def generate_ohlcv_data(self, dates, base_price):
        """Generate synthetic OHLCV data"""
        np.random.seed(42)  # For reproducibility
        num_points = len(dates)
        
        # Create price data with random walk
        close_prices = [base_price]
        for _ in range(num_points - 1):
            # Random price change with mean reverting tendency
            change = np.random.normal(0, base_price * 0.005)
            mean_reversion = (base_price - close_prices[-1]) * 0.1
            new_price = close_prices[-1] + change + mean_reversion
            close_prices.append(new_price)
        
        df = pd.DataFrame()
        df['timestamp'] = dates
        df['close'] = close_prices
        
        # Calculate open, high, low from close
        volatility = base_price * 0.005  # 0.5% volatility
        df['open'] = df['close'].shift(1)
        df.loc[0, 'open'] = df['close'].iloc[0] * (1 - np.random.normal(0, 0.002))
        
        df['high'] = df[['open', 'close']].max(axis=1) + np.random.normal(0, volatility, num_points)
        df['low'] = df[['open', 'close']].min(axis=1) - np.random.normal(0, volatility, num_points)
        
        # Ensure high and low are sensible
        df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
        df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
        
        # Generate volume data
        df['volume'] = np.random.gamma(shape=2.0, scale=1000, size=num_points)
        
        # Set index
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def test_simulated_chart_creation(self):
        """Test creation of simulated chart"""
        chart_path = self.generator._create_simulated_chart(
            symbol=self.symbol,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            targets=self.targets,
            output_dir=self.temp_dir
        )
        
        # Assert chart was created
        self.assertIsNotNone(chart_path)
        self.assertTrue(os.path.exists(chart_path))
        
    def test_candlestick_chart_normal_data(self):
        """Test creation of candlestick chart with normal sized data"""
        chart_path = self.generator._create_candlestick_chart(
            symbol=self.symbol,
            ohlcv_data=self.ohlcv_normal,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            targets=self.targets,
            output_dir=self.temp_dir
        )
        
        # Assert chart was created
        self.assertIsNotNone(chart_path)
        self.assertTrue(os.path.exists(chart_path))
    
    def test_candlestick_chart_large_data(self):
        """Test creation of candlestick chart with large dataset that would cause tick overflow"""
        chart_path = self.generator._create_candlestick_chart(
            symbol=self.symbol,
            ohlcv_data=self.ohlcv_large,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            targets=self.targets,
            output_dir=self.temp_dir
        )
        
        # Assert chart was created
        self.assertIsNotNone(chart_path)
        self.assertTrue(os.path.exists(chart_path))
    
    def test_downsample_ohlcv_data(self):
        """Test the downsampling function"""
        # Test with normal data (should not be downsampled)
        normal_downsampled = self.generator._downsample_ohlcv_data(self.ohlcv_normal)
        self.assertEqual(len(normal_downsampled), len(self.ohlcv_normal))
        
        # Test with large data (should be downsampled)
        large_downsampled = self.generator._downsample_ohlcv_data(self.ohlcv_large, max_samples=500)
        self.assertEqual(len(large_downsampled), 500)
        
        # Ensure OHLCV columns are preserved
        for col in ['open', 'high', 'low', 'close', 'volume']:
            self.assertIn(col, large_downsampled.columns)
    
    def test_safe_plot_result_unpack(self):
        """Test the safe plot result unpacking function"""
        # Create a simple figure
        fig, ax = plt.subplots()
        
        # Test tuple form
        result = self.generator._safe_plot_result_unpack((fig, [ax]))
        self.assertEqual(len(result), 2)
        self.assertTrue(isinstance(result[0], plt.Figure))
        
        # Test figure form
        result = self.generator._safe_plot_result_unpack(fig)
        self.assertEqual(len(result), 2)
        self.assertTrue(isinstance(result[0], plt.Figure))
        
        # Close the figure
        plt.close(fig)
    
    def test_configure_axis_ticks(self):
        """Test the axis tick configuration function"""
        # Create a figure with a lot of ticks
        fig, ax = plt.subplots()
        ax.plot(range(1000))
        
        # Get initial tick count
        initial_ticks = len(ax.get_xticks())
        
        # Apply tick limiting
        self.generator._configure_axis_ticks(ax, max_ticks=10)
        
        # Check the number of ticks is reduced or equal to the max_ticks
        final_ticks = len(ax.get_xticks())
        self.assertLessEqual(final_ticks, 10)
        
        # If initial ticks were > max_ticks, the function should have reduced them
        if initial_ticks > 10:
            self.assertLess(final_ticks, initial_ticks)
        
        # Close the figure
        plt.close(fig)
    
    def test_component_chart_creation(self):
        """Test creation of component chart"""
        components = {
            "RSI": {
                "score": 82,
                "impact": 3.2,
            },
            "MACD": {
                "score": 71,
                "impact": 2.5,
            },
            "Bollinger Bands": {
                "score": 68,
                "impact": 1.8,
            },
            "Volume": {
                "score": 65,
                "impact": 1.5,
            },
        }
        
        chart_path = self.generator._create_component_chart(
            components=components,
            output_dir=self.temp_dir
        )
        
        # Assert chart was created
        self.assertIsNotNone(chart_path)
        self.assertTrue(os.path.exists(chart_path))
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove temp directory and its contents
        for file in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, file))
            except:
                pass
        try:
            os.rmdir(self.temp_dir)
        except:
            pass


if __name__ == '__main__':
    unittest.main() 