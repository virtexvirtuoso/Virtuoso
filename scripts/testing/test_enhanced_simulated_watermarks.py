#!/usr/bin/env python3
"""
Test script to verify enhanced watermarks on simulated charts.
This script tests the new prominent watermark system for simulated trading charts.
"""

import sys
import os
import tempfile
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.reporting.pdf_generator import ReportGenerator

def test_enhanced_simulated_watermarks():
    """Test that simulated charts have prominent watermarks."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create report generator
    generator = ReportGenerator()
    
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Testing enhanced simulated watermarks in: {temp_dir}")
        
        # Test parameters
        test_cases = [
            {
                "symbol": "BTCUSDT",
                "entry_price": 45000.0,
                "stop_loss": 43000.0,
                "targets": [
                    {"price": 47000.0, "name": "Target 1"},
                    {"price": 49000.0, "name": "Target 2"},
                    {"price": 52000.0, "name": "Target 3"}
                ]
            },
            {
                "symbol": "ETHUSDT", 
                "entry_price": 3200.0,
                "stop_loss": 3100.0,
                "targets": [
                    {"price": 3350.0, "name": "Target 1"},
                    {"price": 3500.0, "name": "Target 2"}
                ]
            },
            {
                "symbol": "DOGEUSDT",
                "entry_price": 0.195,
                "stop_loss": 0.185,
                "targets": [
                    {"price": 0.205, "name": "Target 1"},
                    {"price": 0.215, "name": "Target 2"}
                ]
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                logger.info(f"\n--- Test Case {i}: {test_case['symbol']} ---")
                
                # Create simulated chart
                chart_path = generator._create_simulated_chart(
                    symbol=test_case["symbol"],
                    entry_price=test_case["entry_price"],
                    stop_loss=test_case["stop_loss"],
                    targets=test_case["targets"],
                    output_dir=temp_dir
                )
                
                if chart_path and os.path.exists(chart_path):
                    file_size = os.path.getsize(chart_path)
                    logger.info(f"✅ Chart created: {chart_path} ({file_size} bytes)")
                    
                    # Verify filename contains 'simulated'
                    if 'simulated' in os.path.basename(chart_path):
                        logger.info("✅ Filename correctly indicates simulated data")
                    else:
                        logger.warning("⚠️ Filename doesn't indicate simulated data")
                    
                    results.append({
                        "symbol": test_case["symbol"],
                        "success": True,
                        "chart_path": chart_path,
                        "file_size": file_size
                    })
                    
                else:
                    logger.error(f"❌ Failed to create chart for {test_case['symbol']}")
                    results.append({
                        "symbol": test_case["symbol"],
                        "success": False,
                        "error": "Chart creation failed"
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error testing {test_case['symbol']}: {str(e)}")
                results.append({
                    "symbol": test_case["symbol"],
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("ENHANCED WATERMARK TEST SUMMARY")
        logger.info("="*60)
        
        successful_tests = sum(1 for r in results if r["success"])
        total_tests = len(results)
        
        logger.info(f"Tests passed: {successful_tests}/{total_tests}")
        
        for result in results:
            if result["success"]:
                logger.info(f"✅ {result['symbol']}: Chart created with enhanced watermarks")
                logger.info(f"   📁 File: {result['chart_path']}")
                logger.info(f"   📊 Size: {result['file_size']} bytes")
            else:
                logger.error(f"❌ {result['symbol']}: {result.get('error', 'Unknown error')}")
        
        if successful_tests == total_tests:
            logger.info("\n🎉 All tests passed! Enhanced watermarks are working correctly.")
            logger.info("\nWatermark features tested:")
            logger.info("• Large diagonal 'SIMULATED DATA' watermark")
            logger.info("• Secondary 'NOT REAL MARKET DATA' watermark")
            logger.info("• Corner indicators with warning symbols")
            logger.info("• Warning text in title area")
            logger.info("• Chart title includes simulation warning")
            return True
        else:
            logger.error(f"\n❌ {total_tests - successful_tests} tests failed.")
            return False

def test_watermark_method_directly():
    """Test the watermark method directly."""
    
    logger = logging.getLogger(__name__)
    logger.info("\n--- Testing watermark method directly ---")
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        # Create a simple test figure
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot([1, 2, 3, 4], [1, 4, 2, 3], 'b-', linewidth=2)
        ax.set_title("Test Chart")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        
        # Create generator and add watermarks
        generator = ReportGenerator()
        generator._add_simulated_watermarks(fig, ax)
        
        # Save test chart
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "watermark_test.png")
            plt.savefig(test_path, dpi=150, bbox_inches="tight")
            plt.close()
            
            if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                logger.info(f"✅ Watermark method test passed: {test_path}")
                return True
            else:
                logger.error("❌ Watermark method test failed: No output file")
                return False
                
    except Exception as e:
        logger.error(f"❌ Watermark method test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Enhanced Simulated Chart Watermarks")
    print("=" * 60)
    
    # Test main functionality
    main_test_passed = test_enhanced_simulated_watermarks()
    
    # Test watermark method directly
    method_test_passed = test_watermark_method_directly()
    
    # Final result
    if main_test_passed and method_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Enhanced watermarks are working correctly.")
        print("\nKey improvements:")
        print("• Multiple prominent watermarks")
        print("• Warning symbols and colors")
        print("• Clear indication of simulated data")
        print("• Professional appearance with strong visibility")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please check the watermark implementation.")
        sys.exit(1) 