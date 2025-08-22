#!/usr/bin/env python3
"""
Sync Discord alerts from SQLite database to cache for dashboard display
This ensures alerts sent to Discord appear in the Signals tab
"""

import sqlite3
import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import memcache client
try:
    from pymemcache.client.base import Client
    from pymemcache import serde
except ImportError:
    logger.error("pymemcache not installed. Run: pip install pymemcache")
    exit(1)

class AlertSignalSync:
    """Syncs alerts from SQLite to cache for dashboard display"""
    
    def __init__(self, db_path: str = "data/alerts.db", cache_host: str = "localhost", cache_port: int = 11211):
        self.db_path = db_path
        self.cache = Client((cache_host, cache_port), serde=serde.pickle_serde)
        self.logger = logging.getLogger(__name__)
        
    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Fetch recent alerts from SQLite database"""
        alerts = []
        
        if not Path(self.db_path).exists():
            self.logger.warning(f"Database not found at {self.db_path}")
            return alerts
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Calculate timestamp cutoff
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Query recent alerts (focusing on trading signals)
            query = """
                SELECT alert_id, alert_type, symbol, timestamp, title, message, 
                       data, status, webhook_sent, priority, tags
                FROM alerts
                WHERE timestamp > ? 
                  AND alert_type IN ('confluence', 'signal', 'whale', 'volume_spike')
                  AND symbol IS NOT NULL
                  AND webhook_sent = 1
                ORDER BY timestamp DESC
                LIMIT ?
            """
            
            cursor.execute(query, (cutoff_timestamp, limit))
            rows = cursor.fetchall()
            
            for row in rows:
                alert = dict(row)
                
                # Parse JSON data field
                if alert['data']:
                    try:
                        alert['data'] = json.loads(alert['data'])
                    except:
                        alert['data'] = {}
                
                # Parse tags
                if alert['tags']:
                    try:
                        alert['tags'] = json.loads(alert['tags'])
                    except:
                        alert['tags'] = []
                        
                alerts.append(alert)
                
            conn.close()
            self.logger.info(f"Retrieved {len(alerts)} recent alerts from database")
            
        except Exception as e:
            self.logger.error(f"Error reading alerts from database: {e}")
            
        return alerts
    
    def convert_alert_to_signal(self, alert: Dict) -> Dict:
        """Convert an alert to dashboard signal format"""
        
        # Extract data from alert
        data = alert.get('data', {})
        symbol = alert.get('symbol', 'UNKNOWN')
        alert_type = alert.get('alert_type', 'signal')
        
        # Determine signal direction and strength
        direction = 'neutral'
        strength = 'medium'
        score = 50
        
        # Parse from message or data
        message = alert.get('message', '').lower()
        title = alert.get('title', '').lower()
        
        if 'buy' in message or 'buy' in title or 'bullish' in message:
            direction = 'buy'
            score = data.get('confluence_score', 70)
        elif 'sell' in message or 'sell' in title or 'bearish' in message:
            direction = 'sell'
            score = data.get('confluence_score', 30)
        elif 'whale' in alert_type:
            # Whale activity signals
            if 'accumulation' in message:
                direction = 'buy'
                score = 65
            elif 'distribution' in message:
                direction = 'sell'
                score = 35
        
        # Determine strength based on score
        if score > 70 or score < 30:
            strength = 'strong'
        elif score > 60 or score < 40:
            strength = 'medium'
        else:
            strength = 'weak'
            
        # Build signal object
        signal = {
            'symbol': symbol,
            'type': alert_type,
            'direction': direction,
            'strength': strength,
            'score': score,
            'timestamp': alert.get('timestamp', time.time()),
            'message': alert.get('title', alert.get('message', '')),
            'alert_id': alert.get('alert_id'),
            'components': {
                'source': 'discord_alert',
                'priority': alert.get('priority', 'normal'),
                'tags': alert.get('tags', [])
            }
        }
        
        # Add additional data if available
        if data:
            if 'price' in data:
                signal['price'] = data['price']
            if 'volume' in data:
                signal['volume'] = data['volume']
            if 'momentum_score' in data:
                signal['components']['momentum'] = data['momentum_score']
            if 'volume_score' in data:
                signal['components']['volume'] = data['volume_score']
                
        return signal
    
    def sync_to_cache(self, signals: List[Dict]) -> bool:
        """Store signals in cache for dashboard"""
        try:
            # Prepare cache data
            cache_data = {
                'signals': signals,
                'count': len(signals),
                'timestamp': int(time.time()),
                'source': 'alert_sync'
            }
            
            # Store in cache with 5 minute TTL
            self.cache.set('analysis:signals', cache_data, expire=300)
            
            # Also store individual signal keys for quick lookup
            for signal in signals[:20]:  # Store top 20 signals
                key = f"signal:{signal['symbol']}"
                self.cache.set(key, signal, expire=300)
            
            self.logger.info(f"Synced {len(signals)} signals to cache")
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing to cache: {e}")
            return False
    
    def run_sync(self, continuous: bool = False, interval: int = 60):
        """Run the sync process"""
        
        while True:
            try:
                # Get recent alerts
                alerts = self.get_recent_alerts(hours=24, limit=50)
                
                if alerts:
                    # Convert to signals
                    signals = []
                    for alert in alerts:
                        signal = self.convert_alert_to_signal(alert)
                        signals.append(signal)
                    
                    # Sort by timestamp (most recent first)
                    signals.sort(key=lambda x: x['timestamp'], reverse=True)
                    
                    # Sync to cache
                    if self.sync_to_cache(signals):
                        self.logger.info(f"Successfully synced {len(signals)} signals at {datetime.now()}")
                    else:
                        self.logger.error("Failed to sync signals to cache")
                else:
                    # No alerts, store empty signals
                    self.sync_to_cache([])
                    self.logger.info("No recent alerts found - stored empty signals")
                
                if not continuous:
                    break
                    
                # Wait before next sync
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Sync process interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
                if not continuous:
                    break
                time.sleep(30)  # Wait before retry

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync Discord alerts to dashboard signals')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Run continuously (daemon mode)')
    parser.add_argument('--interval', '-i', type=int, default=60,
                       help='Sync interval in seconds (default: 60)')
    parser.add_argument('--db', default='data/alerts.db',
                       help='Path to alerts database')
    parser.add_argument('--cache-host', default='localhost',
                       help='Memcached host')
    parser.add_argument('--cache-port', type=int, default=11211,
                       help='Memcached port')
    
    args = parser.parse_args()
    
    # Create syncer
    syncer = AlertSignalSync(
        db_path=args.db,
        cache_host=args.cache_host,
        cache_port=args.cache_port
    )
    
    # Run sync
    logger.info(f"Starting alert-to-signal sync (continuous={args.continuous})")
    syncer.run_sync(continuous=args.continuous, interval=args.interval)

if __name__ == "__main__":
    main()