import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..models.signals import Signal, SignalList, SymbolSignals, LatestSignals

router = APIRouter()

# Path to the signals JSON directory
SIGNALS_DIR = Path("reports/json")

def get_database_client(request: Request):
    """Dependency to get database client from app state"""
    if hasattr(request.app.state, "database_client"):
        return request.app.state.database_client
    return None

@router.get("/signals/latest", response_model=LatestSignals)
async def get_latest_signals(
    limit: int = Query(5, ge=1, le=20, description="Number of latest signals to return"),
    db_client = Depends(get_database_client)
) -> LatestSignals:
    """
    Get the latest signals across all symbols.
    """
    if not SIGNALS_DIR.exists():
        raise HTTPException(status_code=404, detail="Signals directory not found")
    
    # Get all JSON files
    all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]
    
    # Sort files by modification time (newest first)
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    latest_signals = []
    
    # Take the top N files
    for file_path in all_files[:limit]:
        try:
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            signal_data['filename'] = file_path.name
            signal_data['file_path'] = str(file_path)
            
            # Validate the data
            signal_obj = Signal(**signal_data)
            latest_signals.append(signal_data)
        except:
            # Skip files with errors
            continue
    
    return LatestSignals(
        count=len(latest_signals),
        signals=latest_signals
    )

@router.get("/signals/symbol/{symbol}", response_model=SymbolSignals)
async def get_signals_by_symbol(
    symbol: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of signals to return"),
    db_client = Depends(get_database_client)
) -> SymbolSignals:
    """
    Get signals for a specific symbol sorted by date (newest first).
    """
    if not SIGNALS_DIR.exists():
        raise HTTPException(status_code=404, detail="Signals directory not found")
    
    symbol = symbol.upper()
    
    # Get all JSON files for the symbol
    all_files = [f for f in SIGNALS_DIR.glob(f"{symbol}_*.json") if f.is_file()]
    
    # If no files match the pattern, try a less strict pattern
    if not all_files:
        all_files = [f for f in SIGNALS_DIR.glob(f"*{symbol}*.json") if f.is_file()]
    
    signals = []
    
    for file_path in all_files:
        try:
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            # Verify the symbol matches
            if signal_data.get('symbol', '').upper() == symbol:
                signal_data['filename'] = file_path.name
                signal_data['file_path'] = str(file_path)
                
                # Validate the data
                signal_obj = Signal(**signal_data)
                signals.append(signal_data)
        except:
            # Skip files with errors
            continue
    
    # Sort by timestamp (descending) or filename
    signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)
    
    # Limit the number of results
    signals = signals[:limit]
    
    return SymbolSignals(
        symbol=symbol,
        count=len(signals),
        signals=signals
    )

@router.get("/signals", response_model=SignalList)
async def get_all_signals(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (BULLISH, BEARISH, etc.)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum score"),
    db_client = Depends(get_database_client)
) -> SignalList:
    """
    Get signal data with filtering and pagination.
    Retrieves signals from JSON files stored in the reports/json directory.
    """
    if not SIGNALS_DIR.exists():
        raise HTTPException(status_code=404, detail="Signals directory not found")
    
    # Get all JSON files in the directory
    all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]
    
    # Process files and apply filters
    filtered_signals = []
    
    for file_path in all_files:
        try:
            # Parse filename for quick filtering
            filename = file_path.stem  # Gets filename without extension
            
            # Quick filter by symbol and signal_type if present in filename
            if symbol and symbol.upper() not in filename.upper():
                continue
                
            if signal_type and signal_type.upper() not in filename.upper():
                continue
            
            # Load the JSON file
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            # Add filename and file_path to the data
            signal_data['filename'] = file_path.name
            signal_data['file_path'] = str(file_path)
            
            # Apply additional filters
            if symbol and signal_data.get('symbol', '').upper() != symbol.upper():
                continue
                
            if signal_type and signal_data.get('signal', '').upper() != signal_type.upper():
                continue
                
            if min_score is not None and signal_data.get('score', 0) < min_score:
                continue
                
            # Parse dates from filename if available (assuming format SYMBOL_TYPE_YYYYMMDD_HHMMSS)
            try:
                date_part = None
                parts = filename.split('_')
                if len(parts) >= 3:
                    date_part = parts[-2]  # Try to get date from second-to-last part
                
                if date_part and len(date_part) == 8:  # YYYYMMDD format
                    # Filter by date if provided
                    if start_date and date_part < start_date:
                        continue
                    if end_date and date_part > end_date:
                        continue
            except:
                # If date parsing fails, don't filter by date
                pass
            
            # Convert the data to a Signal object to validate it
            try:
                signal_obj = Signal(**signal_data)
                filtered_signals.append(signal_data)
            except Exception as e:
                # Skip invalid signal data
                continue
            
        except Exception as e:
            # Skip files with errors
            continue
    
    # Sort signals by timestamp (descending) if available or by filename
    filtered_signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)
    
    # Calculate pagination
    total = len(filtered_signals)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paged_signals = filtered_signals[start_idx:end_idx]
    
    return SignalList(
        signals=paged_signals,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if size > 0 else 0
    )

@router.get("/signals/{filename}", response_model=Signal)
async def get_signal_by_filename(
    filename: str,
    db_client = Depends(get_database_client)
) -> Signal:
    """
    Get a specific signal by its filename.
    """
    file_path = SIGNALS_DIR / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Signal file {filename} not found")
    
    try:
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        # Add filename and file_path to the data
        signal_data['filename'] = filename
        signal_data['file_path'] = str(file_path)
        
        # Validate the data by creating a Signal object
        return Signal(**signal_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading signal file: {str(e)}") 