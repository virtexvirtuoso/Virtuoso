#!/usr/bin/env python3
"""Test script to verify chart generation and PDF stop loss fixes."""

import sys
import os
import asyncio
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.reporting.pdf_generator import PDFReportGenerator
from src.core.reporting.report_manager import ReportManager
from src.monitoring.alert_manager import AlertManager
from src.core.container import Container


async def test_pdf_and_chart_generation():
    """Test PDF generation with stop loss and chart extraction."""
    
    print("=" * 60)
    print("TESTING PDF AND CHART GENERATION")
    print("=" * 60)
    
    # Initialize components
    container = Container()
    config = container.config()
    
    pdf_generator = PDFReportGenerator()
    
    # Create test signal data similar to ENAUSDT example
    signal_data = {
        "symbol": "ENAUSDT",
        "timestamp": datetime.now().isoformat(),
        "signal_type": "BUY",
        "confluence_score": 69.2,
        "reliability": 0.85,
        "price": 0.0600,
        "trade_params": {
            "entry_price": 0.059520,
            "stop_loss": 0.0577,  # Stop loss from the chart
            "targets": [
                {"name": "Target 1", "price": 0.0620, "size": 50},
                {"name": "Target 2", "price": 0.0640, "size": 30},
                {"name": "Target 3", "price": 0.0660, "size": 20}
            ]
        },
        "insights": [
            "Technical indicators show slight bullish bias within overall neutrality",
            "MACD shows neutral trend conditions",
            "Volume patterns show strong participation without clear directional bias"
        ],
        "components": {
            "orderbook": {"score": 80.6, "reliability": 0.9},
            "orderflow": {"score": 76.6, "reliability": 0.85},
            "volume": {"score": 63.2, "reliability": 0.8},
            "sentiment": {"score": 63.0, "reliability": 0.75},
            "technical": {"score": 60.8, "reliability": 0.9},
            "structure": {"score": 54.0, "reliability": 0.85}
        }
    }
    
    # Create simulated OHLCV data
    periods = 100
    base_price = 0.0595
    timestamps = pd.date_range(end=datetime.now(), periods=periods, freq='5min')
    
    # Generate realistic price movement
    price_changes = np.random.normal(0, 0.0002, periods)
    prices = base_price + np.cumsum(price_changes)
    
    ohlcv_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices + np.random.uniform(-0.0001, 0.0001, periods),
        'high': prices + np.random.uniform(0, 0.0003, periods),
        'low': prices - np.random.uniform(0, 0.0003, periods),
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, periods)
    })
    ohlcv_data.set_index('timestamp', inplace=True)
    
    # Test 1: Generate PDF and verify stop loss is displayed correctly
    print("\n1. Testing PDF generation with stop loss from trade_params...")
    
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        result = pdf_generator.generate_trading_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_dir=output_dir
        )
        
        if result and len(result) >= 3:
            pdf_path, json_path, chart_path = result
            
            print(f"✅ PDF generated: {pdf_path}")
            print(f"✅ JSON exported: {json_path}")
            print(f"✅ Chart path: {chart_path}")
            
            # Verify stop loss in JSON data
            if json_path and os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    saved_data = json.load(f)
                    saved_stop_loss = saved_data.get('stop_loss')
                    print(f"\n   Stop loss in JSON: ${saved_stop_loss}")
                    if saved_stop_loss == signal_data['trade_params']['stop_loss']:
                        print("   ✅ Stop loss correctly saved!")
                    else:
                        print("   ❌ Stop loss mismatch!")
            
            # Check if chart exists
            if chart_path and os.path.exists(chart_path):
                file_size = os.path.getsize(chart_path) / 1024
                print(f"\n   Chart file size: {file_size:.1f} KB")
                print("   ✅ Chart generated successfully!")
            else:
                print("   ❌ Chart not generated or missing!")
                
        else:
            print("❌ PDF generation failed!")
            
    except Exception as e:
        print(f"❌ Error during PDF generation: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_alert_manager_chart_sending():
    """Test the alert manager's ability to send charts."""
    
    print("\n" + "=" * 60)
    print("TESTING ALERT MANAGER CHART FUNCTIONALITY")
    print("=" * 60)
    
    # Initialize container
    container = Container()
    
    # Initialize alert manager
    alert_manager = AlertManager(container.config())
    
    # Add PDF generator to alert manager
    alert_manager.pdf_generator = PDFReportGenerator()
    
    # Create test signal data
    signal_data = {
        "symbol": "BTCUSDT",
        "signal_type": "BUY",
        "confluence_score": 75.5,
        "price": 45000,
        "trade_params": {
            "entry_price": 45000,
            "stop_loss": 43500,
            "targets": [
                {"name": "TP1", "price": 46500, "size": 40},
                {"name": "TP2", "price": 48000, "size": 30},
                {"name": "TP3", "price": 50000, "size": 30}
            ]
        },
        "transaction_id": "test123",
        "signal_id": "sig456"
    }
    
    print("\n2. Testing chart generation from signal data...")
    
    try:
        # Test the chart generation method
        chart_path = await alert_manager._generate_chart_from_signal_data(
            signal_data, 
            signal_data['transaction_id'], 
            signal_data['signal_id']
        )
        
        if chart_path and os.path.exists(chart_path):
            print(f"✅ Chart generated: {chart_path}")
            file_size = os.path.getsize(chart_path) / 1024
            print(f"   File size: {file_size:.1f} KB")
        else:
            print("❌ Chart generation failed!")
            
    except Exception as e:
        print(f"❌ Error during chart generation: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing Discord message formatting...")
    
    # Extract trade parameters for the message
    trade_params = signal_data.get('trade_params', {})
    entry_price = trade_params.get('entry_price')
    stop_loss = trade_params.get('stop_loss')
    targets = trade_params.get('targets', [])
    
    # Format stop loss and targets information
    sl_info = f"**Stop Loss:** ${stop_loss:.4f}" if stop_loss else "**Stop Loss:** Not set"
    
    tp_info = []
    if targets:
        for i, target in enumerate(targets):
            if isinstance(target, dict):
                target_price = target.get('price', 0)
                target_size = target.get('size', 0)
                if target_price > 0:
                    tp_info.append(f"**TP{i+1}:** ${target_price:.4f} ({target_size}%)")
    
    tp_text = "\n".join(tp_info) if tp_info else "**Targets:** Not set"
    
    # Create message for chart
    chart_message = f"📊 **{signal_data['symbol']} Price Action Chart**\n\n**Entry:** ${entry_price:.4f}\n{sl_info}\n\n{tp_text}"
    
    print("\nFormatted Discord message:")
    print("-" * 40)
    print(chart_message)
    print("-" * 40)
    
    return chart_path


async def test_integrated_workflow():
    """Test the complete workflow with report manager."""
    
    print("\n" + "=" * 60)
    print("TESTING INTEGRATED WORKFLOW")
    print("=" * 60)
    
    # Initialize components
    container = Container()
    report_manager = ReportManager(container.config())
    
    # Create comprehensive test data
    signal_data = {
        "symbol": "SOLUSDT",
        "signal_type": "BUY",
        "confluence_score": 72.3,
        "reliability": 0.88,
        "price": 120.50,
        "entry_price": 120.50,
        "trade_params": {
            "entry_price": 120.50,
            "stop_loss": 115.25,
            "targets": [
                {"name": "Target 1", "price": 125.00, "size": 40},
                {"name": "Target 2", "price": 130.00, "size": 35},
                {"name": "Target 3", "price": 135.00, "size": 25}
            ]
        },
        "components": {
            "technical": {"score": 78, "reliability": 0.9},
            "volume": {"score": 72, "reliability": 0.85},
            "sentiment": {"score": 68, "reliability": 0.8}
        }
    }
    
    print("\n4. Testing report generation through report manager...")
    
    try:
        # Generate report
        success, pdf_path, json_path = await report_manager.generate_and_attach_report(
            signal_data=signal_data,
            signal_type="buy",
            output_path="test_output/integrated_test.pdf"
        )
        
        if success:
            print(f"✅ Report generated successfully!")
            print(f"   PDF: {pdf_path}")
            print(f"   JSON: {json_path}")
            
            # Check if chart path was stored
            if 'chart_path' in signal_data:
                print(f"   Chart: {signal_data['chart_path']}")
                print("   ✅ Chart path properly stored in signal_data!")
            else:
                print("   ❌ Chart path not found in signal_data!")
        else:
            print("❌ Report generation failed!")
            
    except Exception as e:
        print(f"❌ Error during integrated test: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    
    print("\n🧪 STARTING LOCAL TESTS FOR CHART AND PDF UPDATES\n")
    
    # Test 1: PDF and chart generation
    await test_pdf_and_chart_generation()
    
    # Test 2: Alert manager chart functionality
    chart_path = await test_alert_manager_chart_sending()
    
    # Test 3: Integrated workflow
    await test_integrated_workflow()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print("\n✅ Tests completed! Check the following:")
    print("1. test_output/ directory for generated PDFs and charts")
    print("2. JSON files to verify stop loss values are correct")
    print("3. Chart images to ensure they are high quality")
    print("4. Console output for any errors or warnings")
    
    print("\n📌 Next steps:")
    print("1. Open a generated PDF and verify stop loss shows correctly")
    print("2. Check that chart images have TP/SL markers")
    print("3. If all looks good, restart the VPS application")


if __name__ == "__main__":
    asyncio.run(main())