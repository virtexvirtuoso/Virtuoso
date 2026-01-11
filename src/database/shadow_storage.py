"""
Shadow Mode Storage Module

Persists shadow mode predictions to virtuoso.db for later analysis and validation.
This allows reviewing predictions without needing to keep them in memory.

Tables:
- shadow_btc_predictions: Bitcoin lead/lag predictions
- shadow_dual_regime: Dual-regime adjustments
- shadow_crypto_regime: Crypto-specific regime detections
- shadow_cas_signals: Cascade Absorption Signal (CAS) predictions
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Get the path to virtuoso.db."""
    return os.path.join(os.getcwd(), 'data', 'virtuoso.db')


def init_shadow_tables():
    """
    Initialize shadow mode tables in the database.
    Creates tables if they don't exist.
    """
    try:
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # BTC Predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_btc_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                original_score REAL NOT NULL,
                would_boost REAL NOT NULL,
                btc_direction TEXT,
                confidence REAL,
                stability_score REAL,
                beta REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create index for efficient querying
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_btc_pred_timestamp
            ON shadow_btc_predictions(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_btc_pred_symbol
            ON shadow_btc_predictions(symbol)
        ''')

        # Dual-Regime Adjustments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_dual_regime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                score_before REAL NOT NULL,
                score_after REAL NOT NULL,
                adjustment REAL NOT NULL,
                market_regime TEXT,
                symbol_regime TEXT,
                fear_greed REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                entry_price REAL,
                return_15m REAL,
                return_1h REAL,
                return_4h REAL,
                return_24h REAL,
                return_calculated_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dual_regime_timestamp
            ON shadow_dual_regime(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dual_regime_symbol
            ON shadow_dual_regime(symbol)
        ''')

        # Crypto Regime Detections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_crypto_regime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                base_regime TEXT NOT NULL,
                crypto_regime TEXT NOT NULL,
                funding_rate REAL,
                oi_change_pct REAL,
                volatility_percentile REAL,
                atr_expansion REAL,
                detection_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                entry_price REAL,
                return_15m REAL,
                return_1h REAL,
                return_4h REAL,
                return_24h REAL,
                return_calculated_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_crypto_regime_timestamp
            ON shadow_crypto_regime(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_crypto_regime_symbol
            ON shadow_crypto_regime(symbol)
        ''')

        # CAS (Cascade Absorption Signal) table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shadow_cas_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                cas_score REAL NOT NULL,
                signal_direction TEXT NOT NULL,
                signal_strength TEXT NOT NULL,
                proximity REAL,
                magnitude REAL,
                whale_signal REAL,
                retail_extreme REAL,
                alignment REAL,
                trend_damping REAL,
                cascade_side TEXT,
                cascade_price REAL,
                current_price REAL,
                atr REAL,
                confidence REAL,
                is_valid INTEGER,
                reason TEXT,
                return_1h REAL,
                return_4h REAL,
                return_24h REAL,
                return_calculated_at INTEGER,
                components_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cas_timestamp
            ON shadow_cas_signals(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cas_symbol
            ON shadow_cas_signals(symbol)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cas_is_valid
            ON shadow_cas_signals(is_valid)
        ''')

        conn.commit()
        conn.close()
        logger.info("Shadow mode database tables initialized")
        return True

    except Exception as e:
        logger.error(f"Error initializing shadow tables: {e}")
        return False


# ============================================================================
# BTC PREDICTION STORAGE
# ============================================================================

def store_btc_prediction(prediction: Dict[str, Any]) -> Optional[int]:
    """
    Store a BTC prediction to the database.

    Args:
        prediction: Dictionary with keys:
            - timestamp: Unix timestamp (ms)
            - symbol: Trading symbol
            - signal_type: LONG/SHORT
            - original_score: Score before boost
            - would_boost: Points that would be added
            - btc_direction: BTC predicted direction
            - confidence: Prediction confidence
            - stability_score: Stability score
            - beta: Symbol's beta to BTC

    Returns:
        Inserted row ID or None on failure
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO shadow_btc_predictions (
                timestamp, symbol, signal_type, original_score, would_boost,
                btc_direction, confidence, stability_score, beta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            prediction.get('timestamp', int(datetime.now(timezone.utc).timestamp() * 1000)),
            prediction.get('symbol', ''),
            prediction.get('signal_type', ''),
            prediction.get('original_score', 0),
            prediction.get('would_boost', 0),
            prediction.get('btc_direction'),
            prediction.get('confidence'),
            prediction.get('stability_score'),
            prediction.get('beta')
        ))

        conn.commit()
        row_id = cursor.lastrowid
        conn.close()

        logger.debug(f"Stored BTC prediction for {prediction.get('symbol')} (id={row_id})")
        return row_id

    except Exception as e:
        logger.error(f"Error storing BTC prediction: {e}")
        return None


def get_btc_predictions(
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    symbol: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Retrieve BTC predictions from the database.

    Args:
        start_timestamp: Filter predictions after this timestamp (ms)
        end_timestamp: Filter predictions before this timestamp (ms)
        symbol: Filter by symbol
        limit: Maximum rows to return

    Returns:
        List of prediction dictionaries
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM shadow_btc_predictions WHERE 1=1'
        params = []

        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)

        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper())

        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error retrieving BTC predictions: {e}")
        return []


# ============================================================================
# DUAL-REGIME STORAGE
# ============================================================================

def store_dual_regime_adjustment(adjustment: Dict[str, Any]) -> Optional[int]:
    """
    Store a dual-regime adjustment to the database.

    Args:
        adjustment: Dictionary with keys:
            - timestamp: Unix timestamp (ms)
            - symbol: Trading symbol
            - signal_type: LONG/SHORT
            - score_before: Score before adjustment
            - score_after: Score after adjustment
            - adjustment: Points adjusted
            - market_regime: Market regime detected
            - symbol_regime: Symbol-specific regime
            - fear_greed: Fear & Greed index value
            - entry_price: Current price at signal time (for forward return calc)

    Returns:
        Inserted row ID or None on failure
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO shadow_dual_regime (
                timestamp, symbol, signal_type, score_before, score_after,
                adjustment, market_regime, symbol_regime, fear_greed, entry_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            adjustment.get('timestamp', int(datetime.now(timezone.utc).timestamp() * 1000)),
            adjustment.get('symbol', ''),
            adjustment.get('signal_type', ''),
            adjustment.get('score_before', 0),
            adjustment.get('score_after', 0),
            adjustment.get('adjustment', 0),
            adjustment.get('market_regime'),
            adjustment.get('symbol_regime'),
            adjustment.get('fear_greed'),
            adjustment.get('entry_price')
        ))

        conn.commit()
        row_id = cursor.lastrowid
        conn.close()

        logger.debug(f"Stored dual-regime adjustment for {adjustment.get('symbol')} (id={row_id})")
        return row_id

    except Exception as e:
        logger.error(f"Error storing dual-regime adjustment: {e}")
        return None


def get_dual_regime_adjustments(
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    symbol: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Retrieve dual-regime adjustments from the database.
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM shadow_dual_regime WHERE 1=1'
        params = []

        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)

        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper())

        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error retrieving dual-regime adjustments: {e}")
        return []


def update_dual_regime_forward_returns(
    record_id: int,
    return_15m: Optional[float] = None,
    return_1h: Optional[float] = None,
    return_4h: Optional[float] = None,
    return_24h: Optional[float] = None,
    entry_price: Optional[float] = None
) -> bool:
    """
    Update forward returns for a dual-regime adjustment (for validation).

    Args:
        record_id: Database ID of the adjustment record
        return_15m: 15-minute forward return (%)
        return_1h: 1-hour forward return (%)
        return_4h: 4-hour forward return (%)
        return_24h: 24-hour forward return (%)
        entry_price: Price at time of signal

    Returns:
        True if updated successfully
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if return_15m is not None:
            updates.append('return_15m = ?')
            params.append(return_15m)

        if return_1h is not None:
            updates.append('return_1h = ?')
            params.append(return_1h)

        if return_4h is not None:
            updates.append('return_4h = ?')
            params.append(return_4h)

        if return_24h is not None:
            updates.append('return_24h = ?')
            params.append(return_24h)

        if entry_price is not None:
            updates.append('entry_price = ?')
            params.append(entry_price)

        if updates:
            updates.append('return_calculated_at = ?')
            params.append(datetime.now(timezone.utc).isoformat())

            query = f"UPDATE shadow_dual_regime SET {', '.join(updates)} WHERE id = ?"
            params.append(record_id)

            cursor.execute(query, params)
            conn.commit()

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error updating dual-regime forward returns: {e}")
        return False


def get_dual_regime_pending_returns(
    hours_back: int = 24,
    return_type: str = '15m'
) -> List[Dict[str, Any]]:
    """
    Get dual-regime adjustments that need forward returns calculated.

    Args:
        hours_back: How many hours back to look for records
        return_type: Which return to check ('15m', '1h', '4h', '24h')

    Returns:
        List of records missing the specified return
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate cutoff timestamp
        cutoff_ms = int((datetime.now(timezone.utc).timestamp() - (hours_back * 3600)) * 1000)

        # Map return type to column
        return_col = f'return_{return_type}'
        if return_col not in ['return_15m', 'return_1h', 'return_4h', 'return_24h']:
            return_col = 'return_15m'

        cursor.execute(f'''
            SELECT * FROM shadow_dual_regime
            WHERE timestamp >= ?
            AND {return_col} IS NULL
            ORDER BY timestamp ASC
        ''', (cutoff_ms,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error getting dual-regime records pending returns: {e}")
        return []


# ============================================================================
# CRYPTO REGIME STORAGE
# ============================================================================

def store_crypto_regime_detection(detection: Dict[str, Any]) -> Optional[int]:
    """
    Store a crypto regime detection to the database.

    Args:
        detection: Dictionary with keys:
            - timestamp: Unix timestamp (ms)
            - symbol: Trading symbol
            - signal_type: LONG/SHORT
            - base_regime: Base market regime
            - crypto_regime: Crypto-specific regime
            - funding_rate: Current funding rate
            - oi_change_pct: Open interest change %
            - volatility_percentile: Volatility percentile
            - atr_expansion: ATR expansion value
            - detection_data: Additional detection data (dict)
            - entry_price: Current price at detection time (for forward return calc)

    Returns:
        Inserted row ID or None on failure
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        detection_data = detection.get('detection_data', {})
        detection_json = json.dumps(detection_data) if detection_data else None

        cursor.execute('''
            INSERT INTO shadow_crypto_regime (
                timestamp, symbol, signal_type, base_regime, crypto_regime,
                funding_rate, oi_change_pct, volatility_percentile, atr_expansion,
                detection_data, entry_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            detection.get('timestamp', int(datetime.now(timezone.utc).timestamp() * 1000)),
            detection.get('symbol', ''),
            detection.get('signal_type', ''),
            detection.get('base_regime', ''),
            detection.get('crypto_regime', ''),
            detection.get('funding_rate'),
            detection.get('oi_change_pct'),
            detection.get('volatility_percentile'),
            detection.get('atr_expansion'),
            detection_json,
            detection.get('entry_price')
        ))

        conn.commit()
        row_id = cursor.lastrowid
        conn.close()

        logger.debug(f"Stored crypto regime detection for {detection.get('symbol')} (id={row_id})")
        return row_id

    except Exception as e:
        logger.error(f"Error storing crypto regime detection: {e}")
        return None


def update_crypto_regime_forward_returns(
    record_id: int,
    return_15m: Optional[float] = None,
    return_1h: Optional[float] = None,
    return_4h: Optional[float] = None,
    return_24h: Optional[float] = None,
    entry_price: Optional[float] = None
) -> bool:
    """
    Update forward returns for a crypto regime detection (for validation).

    Args:
        record_id: Database ID of the detection record
        return_15m: 15-minute forward return (%)
        return_1h: 1-hour forward return (%)
        return_4h: 4-hour forward return (%)
        return_24h: 24-hour forward return (%)
        entry_price: Price at time of detection

    Returns:
        True if updated successfully
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if return_15m is not None:
            updates.append('return_15m = ?')
            params.append(return_15m)

        if return_1h is not None:
            updates.append('return_1h = ?')
            params.append(return_1h)

        if return_4h is not None:
            updates.append('return_4h = ?')
            params.append(return_4h)

        if return_24h is not None:
            updates.append('return_24h = ?')
            params.append(return_24h)

        if entry_price is not None:
            updates.append('entry_price = ?')
            params.append(entry_price)

        if updates:
            updates.append('return_calculated_at = ?')
            params.append(datetime.now(timezone.utc).isoformat())

            query = f"UPDATE shadow_crypto_regime SET {', '.join(updates)} WHERE id = ?"
            params.append(record_id)

            cursor.execute(query, params)
            conn.commit()

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error updating crypto regime forward returns: {e}")
        return False


def get_crypto_regime_pending_returns(
    hours_back: int = 24,
    return_type: str = '15m'
) -> List[Dict[str, Any]]:
    """
    Get crypto regime detections that need forward returns calculated.

    Args:
        hours_back: How many hours back to look for records
        return_type: Which return to check ('15m', '1h', '4h', '24h')

    Returns:
        List of records missing the specified return
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate cutoff timestamp
        cutoff_ms = int((datetime.now(timezone.utc).timestamp() - (hours_back * 3600)) * 1000)

        # Map return type to column
        return_col = f'return_{return_type}'
        if return_col not in ['return_15m', 'return_1h', 'return_4h', 'return_24h']:
            return_col = 'return_15m'

        cursor.execute(f'''
            SELECT * FROM shadow_crypto_regime
            WHERE timestamp >= ?
            AND {return_col} IS NULL
            AND entry_price IS NOT NULL
            ORDER BY timestamp ASC
        ''', (cutoff_ms,))

        rows = cursor.fetchall()
        conn.close()

        # Parse JSON fields
        results = []
        for row in rows:
            record = dict(row)
            if record.get('detection_data'):
                try:
                    record['detection_data'] = json.loads(record['detection_data'])
                except:
                    pass
            results.append(record)

        return results

    except Exception as e:
        logger.error(f"Error getting crypto regime records pending returns: {e}")
        return []


def get_crypto_regime_detections(
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    symbol: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Retrieve crypto regime detections from the database.
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM shadow_crypto_regime WHERE 1=1'
        params = []

        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)

        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper())

        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Parse JSON fields
        results = []
        for row in rows:
            record = dict(row)
            if record.get('detection_data'):
                try:
                    record['detection_data'] = json.loads(record['detection_data'])
                except:
                    pass
            results.append(record)

        return results

    except Exception as e:
        logger.error(f"Error retrieving crypto regime detections: {e}")
        return []


def update_crypto_regime_forward_returns(
    record_id: int,
    return_15m: Optional[float] = None,
    return_1h: Optional[float] = None,
    return_4h: Optional[float] = None,
    return_24h: Optional[float] = None,
    entry_price: Optional[float] = None
) -> bool:
    """
    Update forward returns for a crypto regime detection (for validation).

    Args:
        record_id: Database ID of the detection record
        return_15m: 15-minute forward return (%)
        return_1h: 1-hour forward return (%)
        return_4h: 4-hour forward return (%)
        return_24h: 24-hour forward return (%)
        entry_price: Price at time of detection (if not set during insert)

    Returns:
        True if updated successfully
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if return_15m is not None:
            updates.append('return_15m = ?')
            params.append(return_15m)

        if return_1h is not None:
            updates.append('return_1h = ?')
            params.append(return_1h)

        if return_4h is not None:
            updates.append('return_4h = ?')
            params.append(return_4h)

        if return_24h is not None:
            updates.append('return_24h = ?')
            params.append(return_24h)

        if entry_price is not None:
            updates.append('entry_price = ?')
            params.append(entry_price)

        if updates:
            updates.append('return_calculated_at = ?')
            params.append(datetime.now(timezone.utc).isoformat())

            query = f"UPDATE shadow_crypto_regime SET {', '.join(updates)} WHERE id = ?"
            params.append(record_id)

            cursor.execute(query, params)
            conn.commit()

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error updating crypto regime forward returns: {e}")
        return False


# ============================================================================
# CAS SIGNAL STORAGE
# ============================================================================

def store_cas_signal(signal: Dict[str, Any]) -> Optional[int]:
    """
    Store a CAS (Cascade Absorption Signal) to the database.

    Args:
        signal: Dictionary with keys:
            - timestamp: Unix timestamp (ms)
            - symbol: Trading symbol
            - cas_score: Signal score (-100 to 100)
            - signal_direction: BULLISH/BEARISH/NEUTRAL
            - signal_strength: STRONG/MODERATE/WEAK/NONE
            - proximity, magnitude, whale_signal, retail_extreme: Components
            - alignment, trend_damping: Additional components
            - cascade_side, cascade_price, current_price, atr: Context
            - confidence: Signal confidence (0-1)
            - is_valid: Boolean
            - reason: Explanation string
            - components: Dict of component scores (stored as JSON)

    Returns:
        Inserted row ID or None on failure
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Extract components for JSON storage
        components = signal.get('components', {})
        if not components:
            components = {
                'proximity': signal.get('proximity', 0),
                'magnitude': signal.get('magnitude', 0),
                'whale_signal': signal.get('whale_signal', 0),
                'retail_extreme': signal.get('retail_extreme', 0),
                'alignment': signal.get('alignment', 0),
                'trend_damping': signal.get('trend_damping', 1)
            }
        components_json = json.dumps(components)

        cursor.execute('''
            INSERT INTO shadow_cas_signals (
                timestamp, symbol, cas_score, signal_direction, signal_strength,
                proximity, magnitude, whale_signal, retail_extreme,
                alignment, trend_damping, cascade_side, cascade_price,
                current_price, atr, confidence, is_valid, reason,
                components_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.get('timestamp', int(datetime.now(timezone.utc).timestamp() * 1000)),
            signal.get('symbol', ''),
            signal.get('cas_score', 0),
            signal.get('signal_direction', 'NEUTRAL'),
            signal.get('signal_strength', 'NONE'),
            # Extract from nested 'components' dict (to_dict() nests these)
            components.get('proximity', signal.get('proximity', 0)),
            components.get('magnitude', signal.get('magnitude', 0)),
            components.get('whale_signal', signal.get('whale_signal', 0)),
            components.get('retail_extreme', signal.get('retail_extreme', 0)),
            components.get('alignment', signal.get('alignment', 0)),
            components.get('trend_damping', signal.get('trend_damping', 1)),
            signal.get('cascade_side', ''),
            signal.get('cascade_price', 0),
            signal.get('current_price', 0),
            signal.get('atr', 0),
            signal.get('confidence', 0),
            1 if signal.get('is_valid', False) else 0,
            signal.get('reason', ''),
            components_json
        ))

        conn.commit()
        row_id = cursor.lastrowid
        conn.close()

        logger.debug(f"Stored CAS signal for {signal.get('symbol')} (id={row_id}, score={signal.get('cas_score', 0):.1f})")
        return row_id

    except Exception as e:
        logger.error(f"Error storing CAS signal: {e}")
        return None


def get_cas_signals(
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    symbol: Optional[str] = None,
    is_valid_only: bool = False,
    min_score: Optional[float] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Retrieve CAS signals from the database.

    Args:
        start_timestamp: Filter signals after this timestamp (ms)
        end_timestamp: Filter signals before this timestamp (ms)
        symbol: Filter by symbol
        is_valid_only: Only return valid signals
        min_score: Minimum absolute score to return
        limit: Maximum rows to return

    Returns:
        List of signal dictionaries
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM shadow_cas_signals WHERE 1=1'
        params = []

        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)

        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper())

        if is_valid_only:
            query += ' AND is_valid = 1'

        if min_score is not None:
            query += ' AND ABS(cas_score) >= ?'
            params.append(min_score)

        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Parse JSON fields
        results = []
        for row in rows:
            record = dict(row)
            record['is_valid'] = bool(record.get('is_valid', 0))
            if record.get('components_json'):
                try:
                    record['components'] = json.loads(record['components_json'])
                except:
                    record['components'] = {}
            results.append(record)

        return results

    except Exception as e:
        logger.error(f"Error retrieving CAS signals: {e}")
        return []


def update_cas_forward_returns(
    signal_id: int,
    return_1h: Optional[float] = None,
    return_4h: Optional[float] = None,
    return_24h: Optional[float] = None
) -> bool:
    """
    Update forward returns for a CAS signal (for validation).

    Args:
        signal_id: Database ID of the signal
        return_1h: 1-hour forward return (%)
        return_4h: 4-hour forward return (%)
        return_24h: 24-hour forward return (%)

    Returns:
        True if updated successfully
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if return_1h is not None:
            updates.append('return_1h = ?')
            params.append(return_1h)

        if return_4h is not None:
            updates.append('return_4h = ?')
            params.append(return_4h)

        if return_24h is not None:
            updates.append('return_24h = ?')
            params.append(return_24h)

        if updates:
            updates.append('return_calculated_at = ?')
            params.append(int(datetime.now(timezone.utc).timestamp() * 1000))

            query = f"UPDATE shadow_cas_signals SET {', '.join(updates)} WHERE id = ?"
            params.append(signal_id)

            cursor.execute(query, params)
            conn.commit()

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error updating CAS forward returns: {e}")
        return False


def get_cas_signals_pending_returns(
    hours_back: int = 24,
    return_type: str = '1h'
) -> List[Dict[str, Any]]:
    """
    Get CAS signals that need forward returns calculated.

    Args:
        hours_back: How many hours back to look for signals
        return_type: Which return to check ('1h', '4h', '24h')

    Returns:
        List of signals missing the specified return
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate cutoff timestamp
        cutoff_ms = int((datetime.now(timezone.utc).timestamp() - (hours_back * 3600)) * 1000)

        # Map return type to column
        return_col = f'return_{return_type}'
        if return_col not in ['return_1h', 'return_4h', 'return_24h']:
            return_col = 'return_1h'

        cursor.execute(f'''
            SELECT * FROM shadow_cas_signals
            WHERE timestamp >= ?
            AND is_valid = 1
            AND {return_col} IS NULL
            ORDER BY timestamp ASC
        ''', (cutoff_ms,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error getting CAS signals pending returns: {e}")
        return []


# ============================================================================
# STATISTICS & REPORTING
# ============================================================================

def get_shadow_statistics(days: int = 7) -> Dict[str, Any]:
    """
    Get aggregate statistics for shadow mode data.

    Args:
        days: Number of days to look back

    Returns:
        Dictionary with statistics for each shadow mode type
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Calculate timestamp cutoff
        cutoff_ms = int((datetime.now(timezone.utc).timestamp() - (days * 86400)) * 1000)

        stats = {}

        # BTC Predictions stats
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                AVG(would_boost) as avg_boost,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM shadow_btc_predictions
            WHERE timestamp >= ?
        ''', (cutoff_ms,))
        row = cursor.fetchone()
        stats['btc_predictions'] = {
            'total': row[0] or 0,
            'avg_boost': round(row[1] or 0, 2),
            'avg_confidence': round(row[2] or 0, 2),
            'unique_symbols': row[3] or 0
        }

        # Dual-Regime stats
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                AVG(adjustment) as avg_adjustment,
                AVG(ABS(adjustment)) as avg_abs_adjustment,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM shadow_dual_regime
            WHERE timestamp >= ?
        ''', (cutoff_ms,))
        row = cursor.fetchone()
        stats['dual_regime'] = {
            'total': row[0] or 0,
            'avg_adjustment': round(row[1] or 0, 2),
            'avg_abs_adjustment': round(row[2] or 0, 2),
            'unique_symbols': row[3] or 0
        }

        # Crypto Regime stats
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT crypto_regime) as unique_regimes,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM shadow_crypto_regime
            WHERE timestamp >= ?
        ''', (cutoff_ms,))
        row = cursor.fetchone()
        stats['crypto_regime'] = {
            'total': row[0] or 0,
            'unique_regimes': row[1] or 0,
            'unique_symbols': row[2] or 0
        }

        # Regime distribution
        cursor.execute('''
            SELECT crypto_regime, COUNT(*) as count
            FROM shadow_crypto_regime
            WHERE timestamp >= ?
            GROUP BY crypto_regime
            ORDER BY count DESC
        ''', (cutoff_ms,))
        stats['crypto_regime']['distribution'] = {
            row[0]: row[1] for row in cursor.fetchall()
        }

        # CAS Signal stats
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN is_valid = 1 THEN 1 END) as valid_signals,
                AVG(CASE WHEN is_valid = 1 THEN cas_score END) as avg_score,
                AVG(CASE WHEN is_valid = 1 THEN confidence END) as avg_confidence,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(CASE WHEN return_1h IS NOT NULL THEN 1 END) as with_returns
            FROM shadow_cas_signals
            WHERE timestamp >= ?
        ''', (cutoff_ms,))
        row = cursor.fetchone()
        stats['cas_signals'] = {
            'total': row[0] or 0,
            'valid_signals': row[1] or 0,
            'avg_score': round(row[2] or 0, 2),
            'avg_confidence': round(row[3] or 0, 2),
            'unique_symbols': row[4] or 0,
            'with_returns': row[5] or 0
        }

        # CAS direction distribution
        cursor.execute('''
            SELECT signal_direction, COUNT(*) as count
            FROM shadow_cas_signals
            WHERE timestamp >= ? AND is_valid = 1
            GROUP BY signal_direction
            ORDER BY count DESC
        ''', (cutoff_ms,))
        stats['cas_signals']['direction_distribution'] = {
            row[0]: row[1] for row in cursor.fetchall()
        }

        # CAS win rate (if returns are available)
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN (signal_direction = 'BULLISH' AND return_1h > 0)
                           OR (signal_direction = 'BEARISH' AND return_1h < 0) THEN 1 END) as wins
            FROM shadow_cas_signals
            WHERE timestamp >= ? AND is_valid = 1 AND return_1h IS NOT NULL
        ''', (cutoff_ms,))
        row = cursor.fetchone()
        total_with_returns = row[0] or 0
        wins = row[1] or 0
        stats['cas_signals']['win_rate_1h'] = round(wins / total_with_returns * 100, 1) if total_with_returns > 0 else None

        conn.close()
        return stats

    except Exception as e:
        logger.error(f"Error getting shadow statistics: {e}")
        return {}


def cleanup_old_shadow_data(days_to_keep: int = 30) -> int:
    """
    Remove shadow data older than specified days.

    Args:
        days_to_keep: Number of days of data to retain

    Returns:
        Total number of rows deleted
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff_ms = int((datetime.now(timezone.utc).timestamp() - (days_to_keep * 86400)) * 1000)
        total_deleted = 0

        for table in ['shadow_btc_predictions', 'shadow_dual_regime', 'shadow_crypto_regime', 'shadow_cas_signals']:
            cursor.execute(f'DELETE FROM {table} WHERE timestamp < ?', (cutoff_ms,))
            total_deleted += cursor.rowcount

        conn.commit()
        conn.close()

        if total_deleted > 0:
            logger.info(f"Cleaned up {total_deleted} old shadow records (older than {days_to_keep} days)")

        return total_deleted

    except Exception as e:
        logger.error(f"Error cleaning up shadow data: {e}")
        return 0
