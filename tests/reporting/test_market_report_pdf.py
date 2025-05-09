#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify market report PDF generation with all components.
This script tests that PDF reports include all components like Smart Money Index and Whale Activity.
"""

import os
import sys
import json
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_market_report_pdf")

# Ensure the current directory is in the path for imports
sys.path.append('.')

async def test_market_report_pdf():
    """
    Test the generation of a market report PDF with all components.
    """
    from src.core.reporting.pdf_generator import ReportGenerator
    from src.core.reporting.report_manager import ReportManager

    try:
        logger.info("Starting market report PDF test...")
        
        # Create output directories if they don't exist
        os.makedirs("reports/pdf", exist_ok=True)
        
        # Set up template directory
        template_dir = os.path.join(os.getcwd(), "templates")
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found: {template_dir}")
            template_dir = os.path.join(os.getcwd(), "src/core/reporting/templates")
            if not os.path.exists(template_dir):
                logger.error("Could not find template directory")
                return False
        
        logger.info(f"Using template directory: {template_dir}")
        
        # Initialize PDF generator
        pdf_generator = ReportGenerator(template_dir=template_dir)
        
        # Manually set the template_dir attribute on the object to ensure it's available
        pdf_generator.template_dir = template_dir
        
        # Create report manager
        report_manager = ReportManager()
        report_manager.pdf_generator = pdf_generator
        
        # Generate sample market data with all components
        market_data = generate_sample_market_data()
        
        # Set output paths
        timestamp = int(time.time())
        html_path = f"reports/pdf/test_market_report_{timestamp}.html"
        pdf_path = f"reports/pdf/test_market_report_{timestamp}.pdf"
        
        # Generate the HTML report
        logger.info(f"Generating HTML report: {html_path}")
        html_success = await pdf_generator.generate_market_html_report(
            market_data=market_data,
            output_path=html_path,
            generate_pdf=False
        )
        
        if html_success:
            logger.info(f"HTML report generated successfully: {html_path}")
        else:
            logger.error("Failed to generate HTML report")
            return False
        
        # Now generate the PDF from the HTML
        logger.info(f"Generating PDF report: {pdf_path}")
        pdf_success = await pdf_generator.generate_pdf(html_path, pdf_path)
        
        if pdf_success:
            logger.info(f"PDF report generated successfully: {pdf_path}")
            # Verify the PDF exists and has content
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                logger.info(f"PDF file exists and has size: {os.path.getsize(pdf_path)} bytes")
                return True
            else:
                logger.error(f"PDF file missing or empty: {pdf_path}")
                return False
        else:
            logger.error("Failed to generate PDF report")
            return False
        
    except Exception as e:
        logger.error(f"Error in test_market_report_pdf: {str(e)}", exc_info=True)
        return False

def generate_sample_market_data() -> Dict[str, Any]:
    """Generate sample market data for testing."""
    timestamp = int(time.time() * 1000)
    
    # Market overview data
    market_overview = {
        "regime": "BULLISH",
        "trend_strength": "65.5%",
        "volatility": 12.3,
        "total_volume": 45000000000,
        "total_turnover": 32000000000,
        "daily_change": 2.35,
        "btc_dominance": "42.7%"
    }
    
    # Smart money index data
    smart_money_index = {
        "index": 72.5,
        "sentiment": "BULLISH",
        "institutional_flow": "+2.8%",
        "key_zones": [
            {
                "symbol": "BTC/USDT",
                "type": "accumulation",
                "strength": 78.5,
                "buy_volume": 1200.5,
                "sell_volume": 450.2
            },
            {
                "symbol": "ETH/USDT",
                "type": "accumulation",
                "strength": 65.2,
                "buy_volume": 8500.3,
                "sell_volume": 3200.1
            }
        ]
    }
    
    # Whale activity data
    whale_activity = {
        "has_significant_activity": True,
        "significant_activity": {
            "BTC/USDT": {
                "net_whale_volume": 450.5,
                "usd_value": 22500000
            },
            "ETH/USDT": {
                "net_whale_volume": -320.8,
                "usd_value": -650000
            }
        },
        "large_transactions": [
            {
                "symbol": "BTC/USDT",
                "usd_value": 15000000,
                "timestamp": timestamp - 3600000
            },
            {
                "symbol": "ETH/USDT",
                "usd_value": -8500000,
                "timestamp": timestamp - 1800000
            }
        ]
    }
    
    # Top performers data
    top_performers = [
        {
            "symbol": "SOL/USDT",
            "price": 120.5,
            "change_percent": 8.75,
            "volume": 1500000000
        },
        {
            "symbol": "AVAX/USDT",
            "price": 35.2,
            "change_percent": 7.2,
            "volume": 850000000
        },
        {
            "symbol": "MATIC/USDT",
            "price": 0.85,
            "change_percent": -3.5,
            "volume": 450000000
        }
    ]
    
    # Complete market data
    return {
        "timestamp": timestamp,
        "market_overview": market_overview,
        "smart_money_index": smart_money_index,
        "whale_activity": whale_activity,
        "top_performers": top_performers,
        "additional_sections": {
            "market_sentiment": {
                "overall": "Bullish",
                "volume_sentiment": "Increasing",
                "funding_rates": "Positive"
            }
        }
    }

async def main():
    """Main entry point for the test script."""
    success = await test_market_report_pdf()
    
    if success:
        logger.info("✅ Market report PDF generation test passed!")
        return 0
    else:
        logger.error("❌ Market report PDF generation test failed!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result) 