#!/usr/bin/env python3
"""Minimal API server to test symbols endpoint."""

from fastapi import FastAPI
from datetime import datetime, timezone
import uvicorn
import random

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "OK", "message": "Test symbols API"}

@app.get("/api/dashboard/symbols")
async def get_dashboard_symbols():
    """Return mock symbols data for testing."""
    
    symbols = [
        {"name": "BTCUSDT", "price": 105234.56, "change": 2.45},
        {"name": "ETHUSDT", "price": 3456.78, "change": -1.23},
        {"name": "SOLUSDT", "price": 234.56, "change": 5.67},
        {"name": "XRPUSDT", "price": 2.34, "change": -0.89},
        {"name": "AVAXUSDT", "price": 45.67, "change": 3.21},
        {"name": "DOGEUSDT", "price": 0.345, "change": 1.98},
        {"name": "ADAUSDT", "price": 0.89, "change": -2.34},
        {"name": "MATICUSDT", "price": 1.23, "change": 0.56},
        {"name": "DOTUSDT", "price": 12.34, "change": 4.12},
        {"name": "LINKUSDT", "price": 23.45, "change": -1.78}
    ]
    
    symbols_data = []
    for s in symbols:
        symbols_data.append({
            "symbol": s["name"],
            "price": s["price"],
            "confluence_score": random.randint(40, 80),
            "change_24h": s["change"],
            "volume_24h": random.uniform(1000000, 100000000),
            "high_24h": s["price"] * 1.02,
            "low_24h": s["price"] * 0.98
        })
    
    return {
        "symbols": symbols_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)