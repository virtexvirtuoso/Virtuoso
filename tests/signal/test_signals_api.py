#!/usr/bin/env python3
"""
Simple test script for the signals API.
This script creates a minimal FastAPI app that includes only the signals router.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path
import webbrowser
import threading
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the signals router
from src.api.routes.signals import router as signals_router

# Create a minimal FastAPI app
app = FastAPI(
    title="Signals API Test",
    description="Test API for accessing signal data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the signals router
# Note: we're mounting it at / instead of /api/signals to simplify testing
app.include_router(signals_router, tags=["signals"])

# Make sure the reports directory exists
reports_json_dir = Path("reports/json")
if not reports_json_dir.exists():
    logger.warning(f"Reports directory {reports_json_dir} doesn't exist! Creating it...")
    reports_json_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample signal file for testing
    sample_signal = {
        "symbol": "BTCUSDT",
        "signal": "BULLISH",
        "score": 75.0,
        "reliability": 0.9,
        "price": 55000.0,
        "components": {
            "price_action": {
                "score": 80,
                "impact": 4.0,
                "interpretation": "Strong bullish price action"
            },
            "momentum": {
                "score": 70,
                "impact": 3.0,
                "interpretation": "Positive momentum indicators"
            }
        }
    }
    
    import json
    import datetime
    
    # Create sample signal file
    signal_filename = f"BTCUSDT_BULLISH_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    signal_path = reports_json_dir / signal_filename
    
    with open(signal_path, "w") as f:
        json.dump(sample_signal, f, indent=2)
        
    logger.info(f"Created sample signal file: {signal_path}")

def open_browser():
    """Open the browser to the Swagger UI after a short delay"""
    time.sleep(2)  # Give the server time to start
    webbrowser.open("http://localhost:8000/docs")
    logger.info("Opening browser to API docs page...")

if __name__ == "__main__":
    logger.info("Starting test signals API...")
    
    # Print helpful information about the available endpoints
    logger.info("Available endpoints:")
    logger.info("  - http://localhost:8000/signals           (List all signals with pagination)")
    logger.info("  - http://localhost:8000/signals/latest    (Get latest signals)")
    logger.info("  - http://localhost:8000/signals/symbol/BTCUSDT (Get signals for specific symbol)")
    logger.info("  - http://localhost:8000/docs              (API documentation)")
    
    # Start a thread to open the browser
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000) 