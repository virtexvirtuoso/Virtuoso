#!/usr/bin/env python3
"""
Alert System Health Monitor - Detects Silent Failures

This script monitors the alert system for:
1. Silent failures (exceptions being caught and ignored)
2. Alert processing errors
3. Webhook delivery failures
4. Component health status
5. Alert generation vs delivery rates
"""

import os
import sys
import json
import asyncio
import aiohttp
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# Add project root to path
import platform
if platform.system() == 'Darwin':  # macOS
    sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')
else:  # Linux/VPS
    sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

class AlertHealthMonitor:
    """Monitor alert system health and detect silent failures."""
    
    def __init__(self):
        self.issues_found = []
        self.stats = {
            'alerts_checked': 0,
            'silent_failures': 0,
            'webhook_failures': 0,
            'processing_errors': 0,
            'missing_components': 0,
            'alert_generation_rate': 0,
            'alert_delivery_rate': 0,
            'last_alert_time': None,
            'last_webhook_time': None
        }
        
    async def check_log_for_errors(self, log_path: Path) -> Dict[str, Any]:
        """Check logs for silent failures and suppressed errors."""
        errors = {
            'silent_failures': [],
            'suppressed_exceptions': [],
            'webhook_errors': [],
            'processing_errors': [],
            'warning_patterns': []
        }
        
        if not log_path.exists():
            return errors
        
        # Patterns that indicate ACTUAL silent failures (not config or debug logs)
        # Must be very specific to avoid false positives
        silent_failure_patterns = [
            r'^\s*except.*:\s*pass',  # Bare except with pass (code pattern)
            r'^\s*except:\s*$',  # Bare except without handler (code pattern)
            r'\[ERROR\].*Failed to.*alert',  # ERROR level: Alert failures
            r'\[ERROR\].*alert.*failed',  # ERROR level: Alert failed
            r'\[ERROR\].*Could not send.*alert',  # ERROR level: Send failures
            r'\[ERROR\].*webhook.*failed',  # ERROR level: Webhook failures
            r'\[ERROR\].*Discord.*error',  # ERROR level: Discord errors
            r'\[WARNING\].*Alert.*exception',  # WARNING level: Alert exceptions
            r'\[WARNING\].*Alert.*timed out',  # WARNING level: Alert timeouts
            r'Alert handler crashed',  # Critical alert handler failures
            r'Alert system unresponsive',  # System-level alert failures
        ]
        
        # Read last 10000 lines
        with open(log_path, 'r') as f:
            lines = f.readlines()[-10000:]
        
        for i, line in enumerate(lines):
            # Check for silent failure patterns
            for pattern in silent_failure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    context = ''.join(lines[max(0, i-2):min(len(lines), i+3)])
                    errors['silent_failures'].append({
                        'line': i,
                        'pattern': pattern,
                        'context': context[:500]
                    })
                    self.stats['silent_failures'] += 1
            
            # Check for suppressed exceptions
            if 'except' in line.lower() and ('pass' in line or not lines[i+1].strip() if i+1 < len(lines) else False):
                errors['suppressed_exceptions'].append({
                    'line': i,
                    'code': line.strip()
                })
        
        return errors
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check alert database for delivery failures."""
        db_health = {
            'total_alerts': 0,
            'delivered_alerts': 0,
            'failed_alerts': 0,
            'pending_alerts': 0,
            'delivery_rate': 0,
            'recent_failures': []
        }
        
        db_path = Path('data/alerts.db')
        if not db_path.exists():
            db_path = Path('/home/linuxuser/trading/Virtuoso_ccxt/data/alerts.db')
        
        if not db_path.exists():
            return db_health
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get alert statistics
            cursor.execute("SELECT COUNT(*) FROM alerts")
            db_health['total_alerts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'sent'")
            db_health['delivered_alerts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'failed'")
            db_health['failed_alerts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'pending'")
            db_health['pending_alerts'] = cursor.fetchone()[0]
            
            # Calculate delivery rate
            if db_health['total_alerts'] > 0:
                db_health['delivery_rate'] = (db_health['delivered_alerts'] / db_health['total_alerts']) * 100
            
            # Get recent failures
            cursor.execute("""
                SELECT alert_type, symbol, timestamp, error_message 
                FROM alerts 
                WHERE status = 'failed' 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                db_health['recent_failures'].append({
                    'type': row[0],
                    'symbol': row[1],
                    'time': datetime.fromtimestamp(row[2]).isoformat() if row[2] else None,
                    'error': row[3]
                })
            
            conn.close()
            
        except Exception as e:
            db_health['error'] = str(e)
        
        return db_health
    
    async def test_alert_components(self) -> Dict[str, bool]:
        """Test each alert component to ensure it's working."""
        components = {
            'alert_manager': False,
            'webhook_connectivity': False,
            'whale_detection': False,
            'liquidation_detection': False,
            'confluence_calculation': False,
            'smart_money_detection': False,
            'volume_analysis': False,
            'error_handling': False
        }
        
        # Test webhook connectivity
        webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
        if not webhook_url:
            env_file = Path('.env')
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if 'SYSTEM_ALERTS_WEBHOOK_URL=' in line:
                            webhook_url = line.split('=', 1)[1].strip()
                            break
        
        if webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    test_payload = {
                        'content': '🔍 Alert Health Check',
                        'embeds': [{
                            'title': 'System Health Monitor',
                            'description': 'Testing alert delivery pipeline',
                            'color': 0x00ff00,
                            'timestamp': datetime.now().isoformat()
                        }]
                    }
                    async with session.post(webhook_url, json=test_payload) as response:
                        components['webhook_connectivity'] = response.status == 204
            except:
                components['webhook_connectivity'] = False
        
        # Test alert manager import
        try:
            from src.monitoring.alert_manager import AlertManager
            components['alert_manager'] = True
        except Exception as e:
            components['alert_manager'] = False
            print(f"   ⚠️ Alert Manager import error: {e}")
        
        # Test detection components
        try:
            from src.monitoring.smart_money_detector import SmartMoneyDetector
            components['smart_money_detection'] = True
        except Exception as e:
            components['smart_money_detection'] = False
            print(f"   ⚠️ Smart Money Detector import error: {e}")
        
        try:
            from src.core.analysis.liquidation_detector import LiquidationDetectionEngine
            components['liquidation_detection'] = True
        except Exception as e:
            components['liquidation_detection'] = False
            print(f"   ⚠️ Liquidation Detector import error: {e}")
        
        try:
            from src.core.analysis.confluence import ConfluenceAnalyzer
            components['confluence_calculation'] = True
        except Exception as e:
            components['confluence_calculation'] = False
            print(f"   ⚠️ Confluence Analyzer import error: {e}")
        
        return components
    
    async def check_alert_generation_rate(self) -> Dict[str, Any]:
        """Check if alerts are being generated at expected rates."""
        rate_analysis = {
            'last_hour_alerts': 0,
            'last_day_alerts': 0,
            'alert_types': {},
            'time_since_last': None,
            'is_healthy': False
        }
        
        # Check logs for recent alert generation
        log_path = Path('logs/app.log')
        if not log_path.exists():
            log_path = Path('/home/linuxuser/trading/Virtuoso_ccxt/logs/app.log')
        
        if log_path.exists():
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            with open(log_path, 'r') as f:
                lines = f.readlines()[-50000:]  # Last 50k lines
            
            for line in lines:
                # Look for alert generation patterns
                if any(pattern in line.lower() for pattern in ['alert generated', 'sending alert', 'whale detected', 'signal detected']):
                    # Try to extract timestamp
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        alert_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                        
                        if alert_time > hour_ago:
                            rate_analysis['last_hour_alerts'] += 1
                        if alert_time > day_ago:
                            rate_analysis['last_day_alerts'] += 1
                        
                        if rate_analysis['time_since_last'] is None or alert_time > rate_analysis['time_since_last']:
                            rate_analysis['time_since_last'] = alert_time
                    
                    # Extract alert type
                    for alert_type in ['whale', 'liquidation', 'confluence', 'volume', 'smart_money']:
                        if alert_type in line.lower():
                            rate_analysis['alert_types'][alert_type] = rate_analysis['alert_types'].get(alert_type, 0) + 1
        
        # Calculate time since last alert
        if rate_analysis['time_since_last']:
            time_diff = datetime.now() - rate_analysis['time_since_last']
            rate_analysis['hours_since_last'] = time_diff.total_seconds() / 3600
            rate_analysis['is_healthy'] = rate_analysis['hours_since_last'] < 24  # Alert in last 24 hours
        
        return rate_analysis
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report."""
        print("🔍 ALERT SYSTEM HEALTH CHECK")
        print("=" * 60)
        
        # Check logs for errors
        print("\n1️⃣ Checking logs for silent failures...")
        log_errors = await self.check_log_for_errors(Path('logs/app.log'))
        
        # Check database health
        print("2️⃣ Checking alert database health...")
        db_health = await self.check_database_health()
        
        # Test components
        print("3️⃣ Testing alert components...")
        component_health = await self.test_alert_components()
        
        # Check generation rates
        print("4️⃣ Analyzing alert generation rates...")
        generation_rate = await self.check_alert_generation_rate()
        
        # Compile report
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'HEALTHY',
            'issues_found': [],
            'statistics': self.stats,
            'log_errors': log_errors,
            'database_health': db_health,
            'component_status': component_health,
            'generation_rate': generation_rate
        }
        
        # Determine overall health
        critical_issues = []
        warnings = []
        
        # Check for critical issues
        if len(log_errors['silent_failures']) > 10:
            critical_issues.append(f"High number of silent failures: {len(log_errors['silent_failures'])}")
        
        if db_health['delivery_rate'] < 80 and db_health['total_alerts'] > 0:
            critical_issues.append(f"Low alert delivery rate: {db_health['delivery_rate']:.1f}%")
        
        if not component_health['webhook_connectivity']:
            critical_issues.append("Discord webhook not accessible")
        
        if not component_health['alert_manager']:
            critical_issues.append("Alert manager component failed to load")
        
        if generation_rate.get('hours_since_last') and generation_rate['hours_since_last'] > 48:
            warnings.append(f"No alerts generated in {generation_rate['hours_since_last']:.1f} hours")
        
        # Set overall health status
        if critical_issues:
            report['overall_health'] = 'CRITICAL'
            report['issues_found'] = critical_issues
        elif warnings:
            report['overall_health'] = 'WARNING'
            report['issues_found'] = warnings
        else:
            report['overall_health'] = 'HEALTHY'
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted health report."""
        print("\n" + "=" * 60)
        print("📊 HEALTH REPORT SUMMARY")
        print("=" * 60)
        
        # Overall status
        health_emoji = "✅" if report['overall_health'] == 'HEALTHY' else "⚠️" if report['overall_health'] == 'WARNING' else "🔴"
        print(f"\n{health_emoji} Overall Health: {report['overall_health']}")
        
        if report['issues_found']:
            print("\n⚠️ Issues Found:")
            for issue in report['issues_found']:
                print(f"  • {issue}")
        
        # Component status
        print("\n🔧 Component Status:")
        for component, status in report['component_status'].items():
            status_emoji = "✅" if status else "❌"
            print(f"  {status_emoji} {component}: {'Working' if status else 'Failed'}")
        
        # Database health
        db = report['database_health']
        if db['total_alerts'] > 0:
            print(f"\n📊 Alert Database:")
            print(f"  Total Alerts: {db['total_alerts']}")
            print(f"  Delivered: {db['delivered_alerts']} ({db['delivery_rate']:.1f}%)")
            print(f"  Failed: {db['failed_alerts']}")
            print(f"  Pending: {db['pending_alerts']}")
        
        # Generation rate
        gen = report['generation_rate']
        print(f"\n📈 Alert Generation:")
        print(f"  Last Hour: {gen['last_hour_alerts']} alerts")
        print(f"  Last Day: {gen['last_day_alerts']} alerts")
        if gen.get('hours_since_last'):
            print(f"  Time Since Last: {gen['hours_since_last']:.1f} hours")
        
        # Silent failures
        if report['log_errors']['silent_failures']:
            print(f"\n⚠️ Silent Failures Detected: {len(report['log_errors']['silent_failures'])}")
            for failure in report['log_errors']['silent_failures'][:3]:
                print(f"  Pattern: {failure['pattern']}")
                print(f"  Context: {failure['context'][:100]}...")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if report['overall_health'] == 'CRITICAL':
            print("  🔴 IMMEDIATE ACTION REQUIRED:")
            print("  1. Check Discord webhook configuration")
            print("  2. Review error logs for exceptions")
            print("  3. Restart the trading service")
            print("  4. Verify all API keys are valid")
        elif report['overall_health'] == 'WARNING':
            print("  ⚠️ ATTENTION NEEDED:")
            print("  1. Monitor alert generation closely")
            print("  2. Check for rate limiting issues")
            print("  3. Review threshold configurations")
        else:
            print("  ✅ System is healthy")
            print("  1. Continue monitoring")
            print("  2. Check alerts are reaching Discord")
        
        print("\n" + "=" * 60)
        
        # Save report to file
        report_path = Path('alert_health_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Full report saved to: {report_path}")
    
    async def send_health_alert(self, report: Dict[str, Any]):
        """Send health status to Discord if issues found."""
        if report['overall_health'] == 'HEALTHY':
            return
        
        webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
        if not webhook_url:
            return
        
        color = 0xff0000 if report['overall_health'] == 'CRITICAL' else 0xffff00
        
        embed = {
            'title': f"{'🔴' if report['overall_health'] == 'CRITICAL' else '⚠️'} Alert System Health Warning",
            'color': color,
            'description': f"Health Status: **{report['overall_health']}**",
            'fields': []
        }
        
        if report['issues_found']:
            embed['fields'].append({
                'name': 'Issues Detected',
                'value': '\n'.join(f"• {issue}" for issue in report['issues_found'][:5]),
                'inline': False
            })
        
        # Add statistics
        db = report['database_health']
        if db['total_alerts'] > 0:
            embed['fields'].append({
                'name': 'Alert Delivery Rate',
                'value': f"{db['delivery_rate']:.1f}%",
                'inline': True
            })
        
        gen = report['generation_rate']
        embed['fields'].append({
            'name': 'Recent Activity',
            'value': f"Last hour: {gen['last_hour_alerts']} alerts",
            'inline': True
        })
        
        embed['timestamp'] = datetime.now().isoformat()
        embed['footer'] = {'text': 'Alert Health Monitor'}
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {'embeds': [embed]}
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        print("✅ Health alert sent to Discord")
        except Exception as e:
            print(f"❌ Failed to send health alert: {e}")

async def main():
    """Run alert health monitoring."""
    monitor = AlertHealthMonitor()
    
    # Generate health report
    report = await monitor.generate_health_report()
    
    # Print report
    monitor.print_report(report)
    
    # Send alert if issues found
    await monitor.send_health_alert(report)
    
    print("\n✅ Health check complete!")

if __name__ == "__main__":
    asyncio.run(main())