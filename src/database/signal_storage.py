"""
Signal Storage Module

Stores trading signals to the virtuoso.db database for persistence and analysis.
This module provides functions to save signal data from JSON reports to the database.
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Get the path to virtuoso.db."""
    return os.path.join(os.getcwd(), 'data', 'virtuoso.db')


def store_trading_signal(
    signal_data: Dict[str, Any],
    json_path: Optional[str] = None,
    pdf_path: Optional[str] = None,
    sent_to_discord: bool = True
) -> Optional[int]:
    """
    Store a trading signal to the trading_signals table in virtuoso.db.

    Args:
        signal_data: Dictionary containing signal data with keys:
            - symbol: Trading pair (e.g., 'BTCUSDT')
            - signal_type: 'LONG' or 'SHORT'
            - score: Confluence score (0-100)
            - price: Current price
            - reliability: Signal reliability score
            - components: Dict of component scores
            - targets: List of take profit targets
            - trade_params: Dict with entry_price, stop_loss, targets
            - market_interpretations: List of interpretation dicts
            - actionable_insights: List of insight strings
            - influential_components: List of influential component dicts
        json_path: Path to the JSON file (optional)
        pdf_path: Path to the PDF file (optional)
        sent_to_discord: Whether the signal was sent to Discord

    Returns:
        The ID of the inserted row, or None if insertion failed
    """
    try:
        db_path = get_db_path()

        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Extract data from signal_data
        symbol = signal_data.get('symbol', '').upper().replace('/', '')
        signal_type = signal_data.get('signal_type', 'UNKNOWN')
        score = signal_data.get('score', 0)
        reliability = signal_data.get('reliability')
        price = signal_data.get('price')

        # Trade params
        trade_params = signal_data.get('trade_params', {})
        entry_price = trade_params.get('entry_price', price)
        stop_loss = trade_params.get('stop_loss')

        # Generate signal_id from symbol, type, score, and timestamp
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        score_str = f"{score:.1f}".replace('.', 'p')
        signal_id = f"{symbol.lower()}_{signal_type}_{score_str}_{timestamp_str}"

        # Check for duplicate
        cursor.execute('SELECT id FROM trading_signals WHERE signal_id = ?', (signal_id,))
        if cursor.fetchone():
            logger.debug(f"Signal {signal_id} already exists, skipping")
            conn.close()
            return None

        # Current timestamp in milliseconds
        timestamp_ms = int(datetime.now().timestamp() * 1000)

        # Components
        components = signal_data.get('components', {})
        components_json = json.dumps(components) if components else None

        # Targets
        targets = signal_data.get('targets', trade_params.get('targets', []))
        targets_json = json.dumps(targets) if targets else None

        # Interpretations - condense to essential data
        interpretations = signal_data.get('market_interpretations', [])
        if interpretations:
            condensed = []
            for i in interpretations:
                if isinstance(i, dict):
                    condensed.append({
                        'component': i.get('component'),
                        'interpretation': i.get('interpretation', '')[:500]
                    })
            interpretations_json = json.dumps(condensed)
        else:
            interpretations_json = None

        # Insights
        insights = signal_data.get('actionable_insights', [])
        insights_json = json.dumps(insights) if insights else None

        # Influential components
        influential = signal_data.get('influential_components', [])
        influential_json = json.dumps(influential) if influential else None

        # Trade params JSON
        trade_params_json = json.dumps(trade_params) if trade_params else None

        # Insert into database
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, confluence_score, reliability,
                entry_price, stop_loss, current_price, timestamp,
                targets, components, interpretations, insights, influential_components,
                sent_to_discord, json_path, pdf_path, trade_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_id, symbol, signal_type, score, reliability,
            entry_price, stop_loss, price, timestamp_ms,
            targets_json, components_json, interpretations_json, insights_json, influential_json,
            1 if sent_to_discord else 0,
            json_path,
            pdf_path,
            trade_params_json
        ))

        conn.commit()
        inserted_id = cursor.lastrowid
        conn.close()

        logger.info(f"Stored trading signal {signal_id} to database (id={inserted_id})")
        return inserted_id

    except Exception as e:
        logger.error(f"Error storing trading signal to database: {str(e)}")
        return None


def get_recent_signals(
    limit: int = 50,
    symbol: Optional[str] = None,
    signal_type: Optional[str] = None
) -> list:
    """
    Retrieve recent trading signals from the database.

    Args:
        limit: Maximum number of signals to return
        symbol: Filter by symbol (optional)
        signal_type: Filter by signal type (optional)

    Returns:
        List of signal dictionaries
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM trading_signals WHERE 1=1'
        params = []

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol.upper().replace('/', ''))

        if signal_type:
            query += ' AND signal_type = ?'
            params.append(signal_type.upper())

        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        signals = []
        for row in rows:
            signal = dict(row)
            # Parse JSON fields
            for json_field in ['targets', 'components', 'interpretations', 'insights', 'influential_components', 'trade_params']:
                if signal.get(json_field):
                    try:
                        signal[json_field] = json.loads(signal[json_field])
                    except:
                        pass
            signals.append(signal)

        conn.close()
        return signals

    except Exception as e:
        logger.error(f"Error retrieving trading signals: {str(e)}")
        return []


def get_signal_by_id(signal_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific trading signal by its signal_id.

    Args:
        signal_id: The unique signal identifier

    Returns:
        Signal dictionary or None if not found
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM trading_signals WHERE signal_id = ?', (signal_id,))
        row = cursor.fetchone()

        if row:
            signal = dict(row)
            # Parse JSON fields
            for json_field in ['targets', 'components', 'interpretations', 'insights', 'influential_components', 'trade_params']:
                if signal.get(json_field):
                    try:
                        signal[json_field] = json.loads(signal[json_field])
                    except:
                        pass
            conn.close()
            return signal

        conn.close()
        return None

    except Exception as e:
        logger.error(f"Error retrieving trading signal {signal_id}: {str(e)}")
        return None
