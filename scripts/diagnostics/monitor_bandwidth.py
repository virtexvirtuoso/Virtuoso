#!/usr/bin/env python3
"""
Bandwidth monitoring for Virtuoso Trading System
"""
import time
import json
import os
import subprocess
from datetime import datetime
from typing import Dict, Tuple

class BandwidthMonitor:
    def __init__(self, interface="enp1s0", history_file="/tmp/bandwidth_history.json"):
        self.interface = interface
        self.history_file = history_file
        self.last_stats = None
        
    def get_interface_stats(self) -> Dict[str, int]:
        """Get current interface statistics"""
        try:
            # Get stats using ip command
            cmd = f"ip -s -j link show {self.interface}"
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            if result.returncode != 0:
                # Fallback to /sys/class/net
                rx_bytes = int(open(f"/sys/class/net/{self.interface}/statistics/rx_bytes").read().strip())
                tx_bytes = int(open(f"/sys/class/net/{self.interface}/statistics/tx_bytes").read().strip())
                rx_packets = int(open(f"/sys/class/net/{self.interface}/statistics/rx_packets").read().strip())
                tx_packets = int(open(f"/sys/class/net/{self.interface}/statistics/tx_packets").read().strip())
            else:
                data = json.loads(result.stdout)[0]
                stats = data['stats64']
                rx_bytes = stats['rx']['bytes']
                tx_bytes = stats['tx']['bytes']
                rx_packets = stats['rx']['packets']
                tx_packets = stats['tx']['packets']
                
            return {
                'timestamp': time.time(),
                'rx_bytes': rx_bytes,
                'tx_bytes': tx_bytes,
                'rx_packets': rx_packets,
                'tx_packets': tx_packets
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return None
    
    def calculate_bandwidth(self, current_stats: Dict, last_stats: Dict) -> Dict:
        """Calculate bandwidth usage between two measurements"""
        if not last_stats or not current_stats:
            return None
            
        time_diff = current_stats['timestamp'] - last_stats['timestamp']
        if time_diff <= 0:
            return None
            
        rx_bytes_diff = current_stats['rx_bytes'] - last_stats['rx_bytes']
        tx_bytes_diff = current_stats['tx_bytes'] - last_stats['tx_bytes']
        
        # Calculate rates in bytes per second
        rx_rate = rx_bytes_diff / time_diff
        tx_rate = tx_bytes_diff / time_diff
        
        # Calculate human-readable values
        rx_mbps = (rx_rate * 8) / (1024 * 1024)  # Megabits per second
        tx_mbps = (tx_rate * 8) / (1024 * 1024)
        
        return {
            'timestamp': current_stats['timestamp'],
            'rx_rate_bps': rx_rate,
            'tx_rate_bps': tx_rate,
            'rx_mbps': rx_mbps,
            'tx_mbps': tx_mbps,
            'rx_total_mb': current_stats['rx_bytes'] / (1024 * 1024),
            'tx_total_mb': current_stats['tx_bytes'] / (1024 * 1024),
            'total_mb': (current_stats['rx_bytes'] + current_stats['tx_bytes']) / (1024 * 1024)
        }
    
    def load_history(self) -> Dict:
        """Load previous stats from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def save_history(self, stats: Dict):
        """Save current stats to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(stats, f)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def get_current_bandwidth(self) -> Dict:
        """Get current bandwidth usage"""
        current_stats = self.get_interface_stats()
        if not current_stats:
            return None
            
        # Load last stats
        last_stats = self.load_history()
        
        # Calculate bandwidth
        bandwidth = self.calculate_bandwidth(current_stats, last_stats) if last_stats else None
        
        # Save current stats for next time
        self.save_history(current_stats)
        
        return {
            'current': bandwidth,
            'total_rx_gb': current_stats['rx_bytes'] / (1024**3),
            'total_tx_gb': current_stats['tx_bytes'] / (1024**3),
            'total_gb': (current_stats['rx_bytes'] + current_stats['tx_bytes']) / (1024**3)
        }

def format_bandwidth_report(bandwidth_data: Dict) -> str:
    """Format bandwidth data for display"""
    if not bandwidth_data:
        return "No bandwidth data available"
        
    report = []
    report.append("📊 BANDWIDTH STATISTICS")
    report.append("=" * 50)
    
    # Total usage
    report.append(f"\n📥 Total Downloaded: {bandwidth_data['total_rx_gb']:.2f} GB")
    report.append(f"📤 Total Uploaded: {bandwidth_data['total_tx_gb']:.2f} GB")
    report.append(f"📊 Total Traffic: {bandwidth_data['total_gb']:.2f} GB")
    
    # Current rates
    if bandwidth_data.get('current'):
        current = bandwidth_data['current']
        report.append(f"\n⚡ Current Rates:")
        report.append(f"   ↓ Download: {current['rx_mbps']:.2f} Mbps ({current['rx_rate_bps']/1024:.1f} KB/s)")
        report.append(f"   ↑ Upload: {current['tx_mbps']:.2f} Mbps ({current['tx_rate_bps']/1024:.1f} KB/s)")
    
    return "\n".join(report)

if __name__ == "__main__":
    # Example usage
    monitor = BandwidthMonitor()
    bandwidth = monitor.get_current_bandwidth()
    print(format_bandwidth_report(bandwidth))
    
    # For continuous monitoring
    if "--continuous" in os.sys.argv:
        while True:
            time.sleep(5)
            bandwidth = monitor.get_current_bandwidth()
            os.system('clear')
            print(format_bandwidth_report(bandwidth))
            print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")