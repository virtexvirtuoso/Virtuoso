#!/usr/bin/env python3
"""Test Phase 1 API endpoints"""
import asyncio
import sys
import os
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')
os.chdir('/home/linuxuser/trading/Virtuoso_ccxt')

from fastapi import FastAPI
from src.core.market_data_direct import DirectMarketData
import uvicorn

app = FastAPI()

@app.get("/test/market")
async def test_market():
    """Simple test endpoint for Phase 1"""
    tickers = await DirectMarketData.fetch_tickers(3)
    return {
        "status": "success",
        "count": len(tickers),
        "tickers": tickers
    }

@app.get("/test/dashboard")
async def test_dashboard():
    """Test dashboard data endpoint"""
    data = await DirectMarketData.get_dashboard_data()
    return data

if __name__ == "__main__":
    print("Starting Phase 1 API test server on port 8003...")
    uvicorn.run(app, host="0.0.0.0", port=8003)