"""
Bandwidth monitoring integration for Virtuoso Trading System
"""
import asyncio
import json
import subprocess
from typing import Dict, Optional
from datetime import datetime

class BandwidthMonitor:
    """Monitor network bandwidth usage"""
    
    def __init__(self, interface: str = "enp1s0"):
        self.interface = interface
        self._last_stats = None
        self._last_update = None
        
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

# Global instance
bandwidth_monitor = BandwidthMonitor()