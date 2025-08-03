"""
Bandwidth monitoring integration for Virtuoso Trading System
"""
import asyncio
import json
import subprocess
from typing import Dict, Optional, List
from datetime import datetime
from collections import deque

class BandwidthMonitor:
    """Monitor network bandwidth usage with historical tracking"""
    
    def __init__(self, interface: str = "enp1s0", history_size: int = 360):
        self.interface = interface
        self._last_stats = None
        self._last_update = None
        # Keep 360 samples (6 hours at 1 minute intervals)
        self.history = deque(maxlen=history_size)
        self._history_lock = asyncio.Lock()
        
    async def get_bandwidth_stats(self) -> Dict:
        """Get current bandwidth statistics"""
        try:
            # Get interface stats
            rx_bytes = await self._read_stat("rx_bytes")
            tx_bytes = await self._read_stat("tx_bytes")
            rx_packets = await self._read_stat("rx_packets")
            tx_packets = await self._read_stat("tx_packets")
            
            current_time = datetime.now()
            current_stats = {
                'rx_bytes': rx_bytes,
                'tx_bytes': tx_bytes,
                'rx_packets': rx_packets,
                'tx_packets': tx_packets,
                'timestamp': current_time
            }
            
            # Calculate rates if we have previous stats
            rates = None
            if self._last_stats and self._last_update:
                time_diff = (current_time - self._last_update).total_seconds()
                if time_diff > 0:
                    rx_rate = (rx_bytes - self._last_stats['rx_bytes']) / time_diff
                    tx_rate = (tx_bytes - self._last_stats['tx_bytes']) / time_diff
                    
                    rates = {
                        'rx_rate_bps': rx_rate,
                        'tx_rate_bps': tx_rate,
                        'rx_rate_mbps': (rx_rate * 8) / (1024 * 1024),
                        'tx_rate_mbps': (tx_rate * 8) / (1024 * 1024),
                        'rx_rate_kbps': rx_rate / 1024,
                        'tx_rate_kbps': tx_rate / 1024
                    }
            
            # Update last stats
            self._last_stats = current_stats
            self._last_update = current_time
            
            # Store in history
            if rates:
                async with self._history_lock:
                    self.history.append({
                        'timestamp': current_time.isoformat(),
                        'rx_mbps': rates['rx_rate_mbps'],
                        'tx_mbps': rates['tx_rate_mbps']
                    })
            
            # Return formatted stats
            return {
                'interface': self.interface,
                'timestamp': current_time.isoformat(),
                'total': {
                    'rx_bytes': rx_bytes,
                    'tx_bytes': tx_bytes,
                    'rx_gb': rx_bytes / (1024**3),
                    'tx_gb': tx_bytes / (1024**3),
                    'total_gb': (rx_bytes + tx_bytes) / (1024**3),
                    'rx_packets': rx_packets,
                    'tx_packets': tx_packets
                },
                'rates': rates or {
                    'rx_rate_bps': 0,
                    'tx_rate_bps': 0,
                    'rx_rate_mbps': 0,
                    'tx_rate_mbps': 0,
                    'rx_rate_kbps': 0,
                    'tx_rate_kbps': 0
                }
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'interface': self.interface,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _read_stat(self, stat_name: str) -> int:
        """Read a network interface statistic"""
        try:
            stat_file = f"/sys/class/net/{self.interface}/statistics/{stat_name}"
            proc = await asyncio.create_subprocess_exec(
                'cat', stat_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return int(stdout.decode().strip())
        except:
            return 0
    
    def get_formatted_stats(self, stats: Dict) -> Dict:
        """Format stats for API response"""
        if 'error' in stats:
            return stats
            
        return {
            'bandwidth': {
                'incoming': {
                    'total_gb': f"{stats['total']['rx_gb']:.2f}",
                    'rate_mbps': f"{stats['rates']['rx_rate_mbps']:.2f}",
                    'rate_kbps': f"{stats['rates']['rx_rate_kbps']:.1f}"
                },
                'outgoing': {
                    'total_gb': f"{stats['total']['tx_gb']:.2f}",
                    'rate_mbps': f"{stats['rates']['tx_rate_mbps']:.2f}",
                    'rate_kbps': f"{stats['rates']['tx_rate_kbps']:.1f}"
                },
                'total': {
                    'gb': f"{stats['total']['total_gb']:.2f}",
                    'packets_rx': stats['total']['rx_packets'],
                    'packets_tx': stats['total']['tx_packets']
                }
            },
            'timestamp': stats['timestamp']
        }
    
    async def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get historical bandwidth data"""
        async with self._history_lock:
            history_list = list(self.history)
            
        if limit and limit > 0:
            return history_list[-limit:]
        return history_list
    
    def get_history_summary(self) -> Dict:
        """Get summary statistics from history"""
        if not self.history:
            return {
                'samples': 0,
                'avg_rx_mbps': 0,
                'avg_tx_mbps': 0,
                'max_rx_mbps': 0,
                'max_tx_mbps': 0,
                'total_rx_gb': 0,
                'total_tx_gb': 0
            }
        
        history_list = list(self.history)
        rx_rates = [h['rx_mbps'] for h in history_list]
        tx_rates = [h['tx_mbps'] for h in history_list]
        
        # Calculate totals (assuming 1 minute intervals)
        total_rx_gb = sum(rx_rates) * 60 / (8 * 1024)  # Convert from Mbps*minutes to GB
        total_tx_gb = sum(tx_rates) * 60 / (8 * 1024)
        
        return {
            'samples': len(history_list),
            'avg_rx_mbps': sum(rx_rates) / len(rx_rates),
            'avg_tx_mbps': sum(tx_rates) / len(tx_rates),
            'max_rx_mbps': max(rx_rates) if rx_rates else 0,
            'max_tx_mbps': max(tx_rates) if tx_rates else 0,
            'total_rx_gb': total_rx_gb,
            'total_tx_gb': total_tx_gb,
            'time_span_minutes': len(history_list)
        }

# Global instance
bandwidth_monitor = BandwidthMonitor()