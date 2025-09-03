import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
import time
import logging
import yaml

from ..models.signals import Signal, SignalList, SymbolSignals, LatestSignals

router = APIRouter()

# Path to the signals JSON directory
SIGNALS_DIR = Path("reports/json")

# Load configuration to check if signal tracking is enabled
def is_signal_tracking_enabled() -> bool:
    """Check if signal tracking is enabled in configuration."""
    logger = logging.getLogger(__name__)
    try:
        # Try multiple possible config paths
        possible_paths = [
            Path("config/config.yaml"),
            Path("../config/config.yaml"),
            Path("../../config/config.yaml"),
            Path("/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml")
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path:
            logger.debug(f"Found config at: {config_path.absolute()}")
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                signal_tracking_config = config.get('signal_tracking', {})
                enabled = signal_tracking_config.get('enabled', True)
                logger.info(f"Signal tracking config: enabled={enabled}")
                return enabled
        else:
            logger.warning(f"Config file not found in any of these paths: {[str(p) for p in possible_paths]}")
    except Exception as e:
        logger.error(f"Error reading signal tracking config: {e}")
    
    logger.warning("Defaulting to signal tracking enabled due to config read failure")
    return True  # Default to enabled if config can't be read

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
    logger = logging.getLogger(__name__)
    
    try:
        if not SIGNALS_DIR.exists():
            logger.warning(f"Signals directory not found: {SIGNALS_DIR}")
            return LatestSignals(count=0, signals=[])
        
        # Get all JSON files with a reasonable limit to prevent timeout
        all_files = []
        file_count = 0
        max_files_to_check = 1000  # Limit file scanning to prevent timeouts
        
        for file_path in SIGNALS_DIR.glob("*.json"):
            if file_path.is_file():
                all_files.append(file_path)
                file_count += 1
                if file_count >= max_files_to_check:
                    break
        
        logger.info(f"Found {len(all_files)} signal files to process")
        
        if not all_files:
            logger.info("No signal files found")
            return LatestSignals(count=0, signals=[])
        
        # Sort files by modification time (newest first) - limit to prevent timeout
        try:
            all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting files by modification time: {e}")
            # Fall back to filename sorting
            all_files.sort(key=lambda x: x.name, reverse=True)
        
        latest_signals = []
        processed_count = 0
        max_process = min(limit * 3, 50)  # Process at most 3x limit or 50 files
        
        # Take the top N files
        for file_path in all_files[:max_process]:
            try:
                with open(file_path, 'r') as f:
                    signal_data = json.load(f)
                
                signal_data['filename'] = file_path.name
                signal_data['file_path'] = str(file_path)
                
                # Quick validation - don't use pydantic model validation for speed
                if isinstance(signal_data, dict) and signal_data.get('symbol'):
                    latest_signals.append(signal_data)
                    
                processed_count += 1
                
                # Stop once we have enough signals
                if len(latest_signals) >= limit:
                    break
                    
            except Exception as e:
                logger.debug(f"Error processing file {file_path}: {e}")
                continue
        
        logger.info(f"Successfully processed {processed_count} files, returning {len(latest_signals)} signals")
        
        return LatestSignals(
            count=len(latest_signals),
            signals=latest_signals[:limit]
        )
        
    except Exception as e:
        logger.error(f"Error in get_latest_signals: {e}")
        # Return empty result instead of raising exception
        return LatestSignals(count=0, signals=[])

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

@router.get("/active")
async def get_active_signals(
    limit: int = Query(default=10, ge=1, le=50),
    db_client = Depends(get_database_client)
) -> Dict[str, Any]:
    """
    Get currently active trading signals.
    
    This unified endpoint:
    - Returns live tracking signals when signal_tracking.enabled = true
    - Returns recent historical signals when signal_tracking.enabled = false
    """
    try:
        logger = logging.getLogger(__name__)
        
        # Check if signal tracking is enabled
        if is_signal_tracking_enabled():
            # Signal tracking is enabled - return live tracking data
            logger.debug("Signal tracking enabled - attempting to fetch from tracking API")
            
            try:
                # Try to get live signals from signal_tracking module
                from .signal_tracking import active_signals, cleanup_expired_signals, format_duration
                
                # Clean up expired signals
                cleanup_expired_signals()
                
                # Convert to list and add current P&L calculations
                signals_list = []
                for signal_id, signal_data in active_signals.items():
                    signal_copy = signal_data.copy()
                    signal_copy['id'] = signal_id
                    
                    # Add duration
                    current_time = time.time()
                    duration_seconds = current_time - signal_data.get('created_at', current_time)
                    signal_copy['duration_seconds'] = int(duration_seconds)
                    signal_copy['duration_formatted'] = format_duration(duration_seconds)
                    
                    signals_list.append(signal_copy)
                
                logger.info(f"Returning {len(signals_list)} live tracking signals")
                return {
                    "signals": signals_list,
                    "count": len(signals_list),
                    "timestamp": int(time.time() * 1000),
                    "source": "live_tracking"
                }
                
            except ImportError as e:
                logger.warning(f"Could not import signal tracking module: {e}")
                # Fall back to historical signals
                pass
        else:
            # Signal tracking is explicitly disabled
            logger.debug("Signal tracking disabled - returning empty signals list")
            return {
                "signals": [],
                "count": 0,
                "timestamp": int(time.time() * 1000),
                "source": "disabled",
                "message": "Signal tracking disabled"
            }
        
        # This section should only be reached if signal tracking is enabled but import failed
        # Signal tracking enabled but unavailable - return historical signals as fallback
        logger.debug("Signal tracking enabled but unavailable - returning historical signals as fallback")
        
        if not SIGNALS_DIR.exists():
            return {
                "signals": [], 
                "count": 0, 
                "timestamp": int(time.time() * 1000),
                "source": "historical",
                "message": "No signals directory found"
            }
        
        # Get recent signal files (last 24 hours worth)
        all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]
        
        # Sort by modification time (most recent first)
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        active_signals_list = []
        
        for file_path in all_files[:limit]:
            try:
                with open(file_path, 'r') as f:
                    signal_data = json.load(f)
                
                # Skip signals without valid symbols
                symbol = signal_data.get("symbol")
                if not symbol or symbol.upper() in ['UNKNOWN', 'NULL', 'UNDEFINED', 'NONE', '', 'INVALID', 'ERROR']:
                    logger.debug(f"Skipping signal file {file_path} - invalid or missing symbol: '{symbol}'")
                    continue
                
                # Simulate active signal properties for historical data
                active_signal = {
                    "id": signal_data.get("filename", file_path.stem),
                    "symbol": symbol,
                    "action": signal_data.get("signal", "HOLD").upper(),
                    "signal_type": signal_data.get("signal", "HOLD").upper(),
                    "entry_price": signal_data.get("current_price", 0.0),
                    "price": signal_data.get("current_price", 0.0),
                    "confidence": signal_data.get("score", 50.0),
                    "score": signal_data.get("score", 50.0),
                    "quantity": 1.0,  # Default quantity
                    "timestamp": signal_data.get("timestamp", int(time.time() * 1000)),
                    "created_at": signal_data.get("timestamp", int(time.time() * 1000)),
                    "status": "historical"
                }
                
                active_signals_list.append(active_signal)
                
            except Exception as e:
                logger.debug(f"Error processing signal file {file_path}: {e}")
                continue
        
        logger.info(f"Returning {len(active_signals_list)} historical signals")
        return {
            "signals": active_signals_list,
            "count": len(active_signals_list),
            "timestamp": int(time.time() * 1000),
            "source": "historical"
        }
        
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting active signals: {str(e)}") 