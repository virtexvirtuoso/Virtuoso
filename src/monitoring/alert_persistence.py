"""
Alert Persistence System for Virtuoso Trading Platform
Stores all alerts in SQLite database for historical tracking and analysis
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import asyncio
try:
    import aiofiles
except ImportError:
    aiofiles = None
from contextlib import asynccontextmanager
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

class AlertType(Enum):
    """Types of alerts in the system"""
    WHALE = "whale"
    CONFLUENCE = "confluence"
    LIQUIDATION = "liquidation"
    VOLUME_SPIKE = "volume_spike"
    PRICE_ALERT = "price_alert"
    SYSTEM = "system"
    ERROR = "error"
    INFO = "info"
    MARKET_CONDITION = "market_condition"
    SIGNAL = "signal"

class AlertStatus(Enum):
    """Status of alerts"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: str
    symbol: Optional[str]
    timestamp: float
    title: str
    message: str
    data: Dict[str, Any]
    status: str
    webhook_sent: bool = False
    webhook_response: Optional[str] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    priority: str = "normal"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).timestamp()

class AlertPersistence:
    """Manages alert persistence in SQLite database"""
    
    def __init__(self, db_path: str = "data/alerts.db", logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self._init_db()
        
    def _init_db(self):
        """Initialize database with tables"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Main alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    symbol TEXT,
                    timestamp REAL NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    status TEXT NOT NULL,
                    webhook_sent BOOLEAN DEFAULT 0,
                    webhook_response TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL,
                    acknowledged_at REAL,
                    resolved_at REAL,
                    acknowledged_by TEXT,
                    resolved_by TEXT,
                    priority TEXT DEFAULT 'normal',
                    tags TEXT
                )
            """)
            
            # Create indexes separately
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON alerts (symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_type ON alerts (alert_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON alerts (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON alerts (created_at)")
            
            # Whale alerts specific table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_alerts (
                    alert_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    net_usd_value REAL,
                    whale_trades_count INTEGER,
                    whale_buy_volume REAL,
                    whale_sell_volume REAL,
                    signal_strength TEXT,
                    current_price REAL,
                    volume_multiple TEXT,
                    interpretation TEXT,
                    
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                )
            """)
            
            # Create indexes for whale_alerts
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wa_symbol ON whale_alerts (symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wa_timestamp ON whale_alerts (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wa_value ON whale_alerts (net_usd_value)")
            
            # Confluence alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS confluence_alerts (
                    alert_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    confluence_score REAL,
                    timeframe TEXT,
                    signal_direction TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit_1 REAL,
                    take_profit_2 REAL,
                    take_profit_3 REAL,
                    risk_reward_ratio REAL,
                    
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                )
            """)
            
            # Create indexes for confluence_alerts
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ca_symbol ON confluence_alerts (symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ca_timestamp ON confluence_alerts (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ca_score ON confluence_alerts (confluence_score)")
            
            # Alert history table (for tracking changes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    user TEXT,
                    details TEXT,
                    
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                )
            """)
            
            # Create indexes for alert_history
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ah_alert_id ON alert_history (alert_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ah_timestamp ON alert_history (timestamp)")
            
            conn.commit()
    
    async def save_alert(self, alert: Alert) -> bool:
        """Save an alert to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert tags list to JSON string
                tags_json = json.dumps(alert.tags) if alert.tags else "[]"
                data_json = json.dumps(alert.data) if alert.data else "{}"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO alerts (
                        alert_id, alert_type, symbol, timestamp, title, message,
                        data, status, webhook_sent, webhook_response,
                        created_at, updated_at, acknowledged_at, resolved_at,
                        acknowledged_by, resolved_by, priority, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id, alert.alert_type, alert.symbol,
                    alert.timestamp, alert.title, alert.message,
                    data_json, alert.status, alert.webhook_sent,
                    alert.webhook_response, alert.created_at, alert.updated_at,
                    alert.acknowledged_at, alert.resolved_at,
                    alert.acknowledged_by, alert.resolved_by,
                    alert.priority, tags_json
                ))
                
                # Save type-specific data
                if alert.alert_type == AlertType.WHALE.value:
                    await self._save_whale_alert_details(cursor, alert)
                elif alert.alert_type == AlertType.CONFLUENCE.value:
                    await self._save_confluence_alert_details(cursor, alert)
                
                # Add to history
                cursor.execute("""
                    INSERT INTO alert_history (alert_id, action, timestamp, details)
                    VALUES (?, ?, ?, ?)
                """, (
                    alert.alert_id, "created", alert.created_at,
                    json.dumps({"initial_status": alert.status})
                ))
                
                conn.commit()
                self.logger.info(f"Alert {alert.alert_id} saved successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save alert {alert.alert_id}: {e}")
            return False
    
    async def _save_whale_alert_details(self, cursor, alert: Alert):
        """Save whale-specific alert details"""
        data = alert.data
        cursor.execute("""
            INSERT OR REPLACE INTO whale_alerts (
                alert_id, symbol, timestamp, net_usd_value,
                whale_trades_count, whale_buy_volume, whale_sell_volume,
                signal_strength, current_price, volume_multiple, interpretation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id, alert.symbol, alert.timestamp,
            data.get('net_usd_value'), data.get('whale_trades_count'),
            data.get('whale_buy_volume'), data.get('whale_sell_volume'),
            data.get('signal_strength'), data.get('current_price'),
            data.get('volume_multiple'), data.get('interpretation')
        ))
    
    async def _save_confluence_alert_details(self, cursor, alert: Alert):
        """Save confluence-specific alert details"""
        data = alert.data
        cursor.execute("""
            INSERT OR REPLACE INTO confluence_alerts (
                alert_id, symbol, timestamp, confluence_score,
                timeframe, signal_direction, entry_price,
                stop_loss, take_profit_1, take_profit_2, take_profit_3,
                risk_reward_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.alert_id, alert.symbol, alert.timestamp,
            data.get('confluence_score'), data.get('timeframe'),
            data.get('signal_direction'), data.get('entry_price'),
            data.get('stop_loss'), data.get('take_profit_1'),
            data.get('take_profit_2'), data.get('take_profit_3'),
            data.get('risk_reward_ratio')
        ))
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Retrieve a specific alert by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM alerts WHERE alert_id = ?
                """, (alert_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_alert(row)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get alert {alert_id}: {e}")
            return None
    
    async def get_alerts(
        self,
        symbol: Optional[str] = None,
        alert_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """Query alerts with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM alerts WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                if alert_type:
                    query += " AND alert_type = ?"
                    params.append(alert_type)
                if status:
                    query += " AND status = ?"
                    params.append(status)
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_alert(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to query alerts: {e}")
            return []
    
    async def update_alert_status(
        self,
        alert_id: str,
        status: str,
        user: Optional[str] = None
    ) -> bool:
        """Update alert status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now(timezone.utc).timestamp()
                
                updates = ["status = ?", "updated_at = ?"]
                params = [status, now]
                
                if status == AlertStatus.ACKNOWLEDGED.value:
                    updates.append("acknowledged_at = ?")
                    params.append(now)
                    if user:
                        updates.append("acknowledged_by = ?")
                        params.append(user)
                
                elif status == AlertStatus.RESOLVED.value:
                    updates.append("resolved_at = ?")
                    params.append(now)
                    if user:
                        updates.append("resolved_by = ?")
                        params.append(user)
                
                params.append(alert_id)
                
                cursor.execute(f"""
                    UPDATE alerts SET {', '.join(updates)}
                    WHERE alert_id = ?
                """, params)
                
                # Add to history
                cursor.execute("""
                    INSERT INTO alert_history (alert_id, action, timestamp, user, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    alert_id, f"status_changed_to_{status}", now, user,
                    json.dumps({"new_status": status})
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update alert status: {e}")
            return False
    
    async def get_alert_statistics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                time_clause = ""
                params = []
                
                if start_time and end_time:
                    time_clause = "WHERE timestamp BETWEEN ? AND ?"
                    params = [start_time, end_time]
                elif start_time:
                    time_clause = "WHERE timestamp >= ?"
                    params = [start_time]
                elif end_time:
                    time_clause = "WHERE timestamp <= ?"
                    params = [end_time]
                
                # Total alerts
                cursor.execute(f"SELECT COUNT(*) FROM alerts {time_clause}", params)
                total = cursor.fetchone()[0]
                
                # By type
                cursor.execute(f"""
                    SELECT alert_type, COUNT(*) as count
                    FROM alerts {time_clause}
                    GROUP BY alert_type
                """, params)
                by_type = dict(cursor.fetchall())
                
                # By status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM alerts {time_clause}
                    GROUP BY status
                """, params)
                by_status = dict(cursor.fetchall())
                
                # By symbol (top 10)
                cursor.execute(f"""
                    SELECT symbol, COUNT(*) as count
                    FROM alerts {time_clause}
                    {"AND" if time_clause else "WHERE"} symbol IS NOT NULL
                    GROUP BY symbol
                    ORDER BY count DESC
                    LIMIT 10
                """, params)
                top_symbols = dict(cursor.fetchall())
                
                # Whale statistics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        SUM(ABS(net_usd_value)) as total_value,
                        AVG(ABS(net_usd_value)) as avg_value,
                        MAX(ABS(net_usd_value)) as max_value
                    FROM whale_alerts
                    {"WHERE timestamp BETWEEN ? AND ?" if start_time and end_time else ""}
                """, params if start_time and end_time else [])
                whale_stats = cursor.fetchone()
                
                return {
                    "total_alerts": total,
                    "by_type": by_type,
                    "by_status": by_status,
                    "top_symbols": top_symbols,
                    "whale_statistics": {
                        "total": whale_stats[0] if whale_stats else 0,
                        "total_value": whale_stats[1] if whale_stats else 0,
                        "avg_value": whale_stats[2] if whale_stats else 0,
                        "max_value": whale_stats[3] if whale_stats else 0
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """Convert database row to Alert object"""
        return Alert(
            alert_id=row['alert_id'],
            alert_type=row['alert_type'],
            symbol=row['symbol'],
            timestamp=row['timestamp'],
            title=row['title'],
            message=row['message'],
            data=json.loads(row['data']) if row['data'] else {},
            status=row['status'],
            webhook_sent=bool(row['webhook_sent']),
            webhook_response=row['webhook_response'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            acknowledged_at=row['acknowledged_at'],
            resolved_at=row['resolved_at'],
            acknowledged_by=row['acknowledged_by'],
            resolved_by=row['resolved_by'],
            priority=row['priority'],
            tags=json.loads(row['tags']) if row['tags'] else []
        )
    
    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """Remove alerts older than specified days"""
        try:
            cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get count first
                cursor.execute("SELECT COUNT(*) FROM alerts WHERE timestamp < ?", (cutoff,))
                count = cursor.fetchone()[0]
                
                # Delete old alerts
                cursor.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff,))
                cursor.execute("DELETE FROM whale_alerts WHERE timestamp < ?", (cutoff,))
                cursor.execute("DELETE FROM confluence_alerts WHERE timestamp < ?", (cutoff,))
                cursor.execute("DELETE FROM alert_history WHERE timestamp < ?", (cutoff,))
                
                conn.commit()
                self.logger.info(f"Cleaned up {count} alerts older than {days} days")
                return count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old alerts: {e}")
            return 0