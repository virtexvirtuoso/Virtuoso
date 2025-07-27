"""Alert storage module for persisting alerts to database.

This module handles storing and retrieving alerts that are sent to Discord,
allowing the mobile dashboard to show historical alerts.
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class AlertStorage:
    """Handles persistence of alerts to SQLite database."""
    
    def __init__(self, db_path: str = None):
        """Initialize alert storage.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default from config.
        """
        if db_path is None:
            # Default path from config
            db_path = os.getenv('DATABASE_URL', 'sqlite:///./data/virtuoso.db')
            if db_path.startswith('sqlite:///'):
                db_path = db_path.replace('sqlite:///', '')
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        self.db_path = db_path
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT UNIQUE,
                        alert_type TEXT NOT NULL,
                        symbol TEXT,
                        severity TEXT,
                        title TEXT,
                        message TEXT,
                        description TEXT,
                        confluence_score REAL,
                        price REAL,
                        volume REAL,
                        change_24h REAL,
                        timestamp INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        sent_to_discord BOOLEAN DEFAULT 0,
                        webhook_response TEXT,
                        metadata TEXT,
                        details TEXT
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                    ON alerts(timestamp DESC)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_symbol 
                    ON alerts(symbol)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_type 
                    ON alerts(alert_type)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_alerts_severity 
                    ON alerts(severity)
                ''')
                
                conn.commit()
                self.logger.info(f"Alert database initialized at {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"Error initializing alert database: {e}")
            raise
    
    def store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store an alert in the database.
        
        Args:
            alert_data: Dictionary containing alert information
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Extract fields from alert_data
                alert_id = alert_data.get('alert_id', f"alert_{int(time.time() * 1000)}")
                alert_type = alert_data.get('alert_type', alert_data.get('type', 'system'))
                symbol = alert_data.get('symbol')
                severity = alert_data.get('severity', 'INFO')
                title = alert_data.get('title', '')
                message = alert_data.get('message', '')
                description = alert_data.get('description', '')
                confluence_score = alert_data.get('confluence_score', alert_data.get('score'))
                price = alert_data.get('price', alert_data.get('current_price'))
                volume = alert_data.get('volume', alert_data.get('volume_24h'))
                change_24h = alert_data.get('change_24h', alert_data.get('price_change_percent'))
                timestamp = alert_data.get('timestamp', int(time.time() * 1000))
                sent_to_discord = alert_data.get('sent_to_discord', False)
                webhook_response = alert_data.get('webhook_response', '')
                
                # Store additional details as JSON
                details = alert_data.get('details', {})
                if isinstance(details, dict):
                    details_json = json.dumps(details)
                else:
                    details_json = str(details)
                
                # Store full metadata as JSON for flexibility
                metadata = json.dumps({
                    k: v for k, v in alert_data.items() 
                    if k not in ['alert_id', 'alert_type', 'symbol', 'severity', 
                                 'title', 'message', 'description', 'confluence_score',
                                 'price', 'volume', 'change_24h', 'timestamp',
                                 'sent_to_discord', 'webhook_response', 'details']
                })
                
                # Insert alert
                cursor.execute('''
                    INSERT OR REPLACE INTO alerts (
                        alert_id, alert_type, symbol, severity, title, message,
                        description, confluence_score, price, volume, change_24h,
                        timestamp, sent_to_discord, webhook_response, metadata, details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert_id, alert_type, symbol, severity, title, message,
                    description, confluence_score, price, volume, change_24h,
                    timestamp, sent_to_discord, webhook_response, metadata, details_json
                ))
                
                conn.commit()
                self.logger.debug(f"Stored alert {alert_id} for {symbol}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing alert: {e}")
            return False
    
    def get_alerts(self, limit: int = 50, start_time: Optional[float] = None,
                   symbol: Optional[str] = None, alert_type: Optional[str] = None,
                   severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve alerts from database with optional filters.
        
        Args:
            limit: Maximum number of alerts to return
            start_time: Only return alerts after this timestamp (Unix timestamp in seconds)
            symbol: Filter by symbol
            alert_type: Filter by alert type
            severity: Filter by severity
            
        Returns:
            List of alert dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build query with filters
                query = "SELECT * FROM alerts WHERE 1=1"
                params = []
                
                if start_time:
                    # Convert seconds to milliseconds for comparison
                    query += " AND timestamp >= ?"
                    params.append(int(start_time * 1000))
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if alert_type:
                    query += " AND alert_type = ?"
                    params.append(alert_type)
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity)
                
                # Order by timestamp descending and apply limit
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                alerts = []
                for row in rows:
                    alert = dict(row)
                    
                    # Parse JSON fields
                    if alert.get('metadata'):
                        try:
                            metadata = json.loads(alert['metadata'])
                            alert.update(metadata)
                        except:
                            pass
                    
                    if alert.get('details'):
                        try:
                            alert['details'] = json.loads(alert['details'])
                        except:
                            pass
                    
                    alerts.append(alert)
                
                return alerts
                
        except Exception as e:
            self.logger.error(f"Error retrieving alerts: {e}")
            return []
    
    def cleanup_old_alerts(self, days: int = 7) -> int:
        """Remove alerts older than specified days.
        
        Args:
            days: Number of days to keep alerts
            
        Returns:
            Number of alerts deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate cutoff timestamp (in milliseconds)
                cutoff_time = int((time.time() - (days * 24 * 3600)) * 1000)
                
                cursor.execute(
                    "DELETE FROM alerts WHERE timestamp < ?",
                    (cutoff_time,)
                )
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} alerts older than {days} days")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old alerts: {e}")
            return 0
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with alert statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate start time
                start_time = int((time.time() - (hours * 3600)) * 1000)
                
                # Total alerts
                cursor.execute(
                    "SELECT COUNT(*) FROM alerts WHERE timestamp >= ?",
                    (start_time,)
                )
                total_alerts = cursor.fetchone()[0]
                
                # Alerts by type
                cursor.execute(
                    "SELECT alert_type, COUNT(*) FROM alerts WHERE timestamp >= ? GROUP BY alert_type",
                    (start_time,)
                )
                alerts_by_type = dict(cursor.fetchall())
                
                # Alerts by severity
                cursor.execute(
                    "SELECT severity, COUNT(*) FROM alerts WHERE timestamp >= ? GROUP BY severity",
                    (start_time,)
                )
                alerts_by_severity = dict(cursor.fetchall())
                
                # Most alerted symbols
                cursor.execute(
                    "SELECT symbol, COUNT(*) as count FROM alerts WHERE timestamp >= ? AND symbol IS NOT NULL GROUP BY symbol ORDER BY count DESC LIMIT 10",
                    (start_time,)
                )
                top_symbols = cursor.fetchall()
                
                return {
                    'total_alerts': total_alerts,
                    'alerts_by_type': alerts_by_type,
                    'alerts_by_severity': alerts_by_severity,
                    'top_symbols': [{'symbol': s[0], 'count': s[1]} for s in top_symbols],
                    'time_period_hours': hours
                }
                
        except Exception as e:
            self.logger.error(f"Error getting alert stats: {e}")
            return {
                'total_alerts': 0,
                'alerts_by_type': {},
                'alerts_by_severity': {},
                'top_symbols': [],
                'time_period_hours': hours
            }