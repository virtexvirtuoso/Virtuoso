#!/usr/bin/env python3
"""
Optimized Bitcoin Beta 7-Day Report Generator Script

This script demonstrates the enhanced Bitcoin beta report with:
- Configurable parameters
- Performance optimizations
- Enhanced analytics
- Multiple output formats
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from reports.bitcoin_beta_7day_report import BitcoinBeta7DayReport, BitcoinBeta7DayReportConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bitcoin_beta_7day_optimized.log')
    ]
)

logger = logging.getLogger(__name__)


class MockExchangeManager:
    """Mock exchange manager for testing purposes."""
    
    async def get_primary_exchange(self):
        return MockExchange()


class MockExchange:
    """Mock exchange for testing purposes."""
    
    async def fetch_ohlcv(self, symbol, timeframe, limit):
        """Mock OHLCV data generation."""
        import numpy as np
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Generate realistic mock data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=8)  # Extra day for safety
        
        # Calculate time delta based on timeframe
        timeframe_deltas = {
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4)
        }
        
        delta = timeframe_deltas.get(timeframe, timedelta(hours=1))
        
        # Generate timestamps
        timestamps = []
        current_time = start_time
        while current_time <= end_time and len(timestamps) < limit:
            timestamps.append(int(current_time.timestamp() * 1000))
            current_time += delta
        
        # Generate realistic price data
        base_price = 50000 if 'BTC' in symbol else np.random.uniform(1, 1000)
        
        ohlcv_data = []
        price = base_price
        
        for i, timestamp in enumerate(timestamps):
            # Add some volatility
            change = np.random.normal(0, 0.02)  # 2% volatility
            price *= (1 + change)
            
            # Generate OHLCV
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price
            volume = np.random.uniform(1000, 10000)
            
            ohlcv_data.append([timestamp, open_price, high, low, close_price, volume])
        
        return ohlcv_data


async def run_optimized_report():
    """Run the optimized Bitcoin beta 7-day report."""
    try:
        logger.info("🚀 Starting Optimized Bitcoin Beta 7-Day Report Generation")
        
        # Create custom configuration
        config = BitcoinBeta7DayReportConfig(
            # Enhanced symbol list
            symbols=[
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT',
                'SOL/USDT', 'DOGE/USDT', 'DOT/USDT', 'AVAX/USDT', 'MATIC/USDT',
                'LINK/USDT', 'UNI/USDT'
            ],
            
            # Performance optimizations
            enable_caching=True,
            cache_duration_hours=1,
            parallel_processing=True,
            max_concurrent_requests=5,
            
            # Enhanced analytics
            enable_enhanced_analytics=True,
            volatility_analysis=True,
            momentum_indicators=True,
            market_regime_detection=True,
            risk_metrics=True,
            performance_attribution=True,
            
            # Chart customization
            chart_style='dark_background',
            figure_size=(24, 16),  # Larger figures
            dpi=1200,  # High resolution
            color_palette='viridis',
            
            # Watermark settings
            watermark_enabled=True,
            watermark_opacity=0.12,
            watermark_size=0.25,
            watermark_position='auto',
            
            # Output formats
            output_formats=['pdf', 'html', 'png'],
            png_high_res=True,
            include_raw_data=False,
            
            # Risk management
            var_confidence_levels=[0.95, 0.99],
            volatility_window=20,
            correlation_window=30,
            
            # Report customization
            report_title='Bitcoin Beta Analysis - Enhanced 7-Day Report',
            include_executive_summary=True,
            include_methodology=True,
            include_disclaimers=True
        )
        
        # Save configuration for future use
        config_path = Path('config/bitcoin_beta_7day_optimized.json')
        config_path.parent.mkdir(exist_ok=True)
        config.save_to_file(str(config_path))
        logger.info(f"💾 Configuration saved to: {config_path}")
        
        # Create mock exchange manager
        exchange_manager = MockExchangeManager()
        
        # Initialize report generator with configuration
        report_generator = BitcoinBeta7DayReport(exchange_manager, config)
        
        # Generate the report
        logger.info("📊 Generating enhanced Bitcoin beta report...")
        report_path = await report_generator.generate_report()
        
        if report_path:
            logger.info(f"✅ Enhanced report generated successfully!")
            logger.info(f"📄 PDF Report: {report_path}")
            
            # Log enhanced analytics summary
            if report_generator.enhanced_analytics:
                analytics = report_generator.enhanced_analytics
                logger.info("📈 Enhanced Analytics Summary:")
                
                # Volatility analysis
                if 'volatility_analysis' in analytics:
                    vol_data = analytics['volatility_analysis']
                    logger.info(f"   • Volatility Analysis: {len(vol_data)} timeframes analyzed")
                
                # Market regime
                if 'market_regime' in analytics:
                    regime_data = analytics['market_regime']
                    logger.info(f"   • Market Regime Detection: {len(regime_data)} regimes identified")
                
                # Risk metrics
                if 'risk_metrics' in analytics:
                    risk_data = analytics['risk_metrics']
                    logger.info(f"   • Risk Metrics: Portfolio analysis completed")
                
                # Performance attribution
                if 'performance_attribution' in analytics:
                    perf_data = analytics['performance_attribution']
                    logger.info(f"   • Performance Attribution: {len(perf_data)} assets analyzed")
            
            # Check for PNG exports
            png_dir = Path('exports/bitcoin_beta_7day_reports/png_exports')
            if png_dir.exists():
                png_files = list(png_dir.glob('*.png'))
                if png_files:
                    total_size = sum(f.stat().st_size for f in png_files) / (1024 * 1024)
                    logger.info(f"🖼️  High-resolution PNG exports: {len(png_files)} files ({total_size:.1f} MB)")
            
            return report_path
        else:
            logger.error("❌ Failed to generate report")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error in optimized report generation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def run_performance_comparison():
    """Run performance comparison between standard and optimized configurations."""
    try:
        import time
        
        logger.info("⚡ Running Performance Comparison")
        
        # Standard configuration
        standard_config = BitcoinBeta7DayReportConfig(
            enable_caching=False,
            parallel_processing=False,
            enable_enhanced_analytics=False,
            png_high_res=False
        )
        
        # Optimized configuration
        optimized_config = BitcoinBeta7DayReportConfig(
            enable_caching=True,
            parallel_processing=True,
            enable_enhanced_analytics=True,
            png_high_res=True,
            max_concurrent_requests=5
        )
        
        exchange_manager = MockExchangeManager()
        
        # Test standard configuration
        logger.info("📊 Testing standard configuration...")
        start_time = time.time()
        standard_generator = BitcoinBeta7DayReport(exchange_manager, standard_config)
        standard_report = await standard_generator.generate_report()
        standard_time = time.time() - start_time
        
        # Test optimized configuration
        logger.info("🚀 Testing optimized configuration...")
        start_time = time.time()
        optimized_generator = BitcoinBeta7DayReport(exchange_manager, optimized_config)
        optimized_report = await optimized_generator.generate_report()
        optimized_time = time.time() - start_time
        
        # Performance summary
        logger.info("📈 Performance Comparison Results:")
        logger.info(f"   • Standard Configuration: {standard_time:.2f} seconds")
        logger.info(f"   • Optimized Configuration: {optimized_time:.2f} seconds")
        
        if standard_time > 0:
            improvement = ((standard_time - optimized_time) / standard_time) * 100
            logger.info(f"   • Performance Improvement: {improvement:.1f}%")
        
        return {
            'standard_time': standard_time,
            'optimized_time': optimized_time,
            'standard_report': standard_report,
            'optimized_report': optimized_report
        }
        
    except Exception as e:
        logger.error(f"❌ Error in performance comparison: {str(e)}")
        return None


async def main():
    """Main execution function."""
    try:
        logger.info("🎯 Bitcoin Beta 7-Day Report - Optimization Demo")
        logger.info("=" * 60)
        
        # Create logs directory
        Path('logs').mkdir(exist_ok=True)
        
        # Run optimized report
        report_path = await run_optimized_report()
        
        if report_path:
            logger.info("=" * 60)
            logger.info("✅ Optimization Demo Completed Successfully!")
            logger.info(f"📄 Enhanced Report: {report_path}")
            
            # Optional: Run performance comparison
            logger.info("\n🔄 Running performance comparison...")
            comparison = await run_performance_comparison()
            
            if comparison:
                logger.info("📊 Performance comparison completed!")
        else:
            logger.error("❌ Optimization demo failed")
            
    except KeyboardInterrupt:
        logger.info("⏹️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main()) 