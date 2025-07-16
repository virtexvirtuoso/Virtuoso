#!/usr/bin/env python3
"""
Alpha Alert Quality Monitor and Optimizer

This script monitors alpha alert performance and provides recommendations
for threshold optimization to reduce noise while maintaining signal quality.

Performance alerts are sent to SYSTEM_ALERTS_WEBHOOK_URL for operational monitoring.
"""

import asyncio
import logging
import json
import sys
import os
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config.config_manager import ConfigManager
from src.monitoring.alpha_integration import AlphaMonitorIntegration


class AlphaAlertOptimizer:
    """Monitor and optimize alpha alert quality."""
    
    def __init__(self, config_path: str = None):
        """Initialize the optimizer."""
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        config_manager = ConfigManager(config_path)
        self.config = config_manager.get_config()
        
        # Get system alerts webhook URL
        self.system_webhook_url = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts_webhook_url')
        if not self.system_webhook_url:
            self.system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
        
        # Alert quality tracking
        self.alert_history = []
        self.quality_metrics = {}
        
        # Optimization recommendations
        self.recommendations = []
        
        # Performance alert settings
        self.performance_alert_enabled = True
        self.last_performance_alert = {}
        self.performance_alert_cooldown = 3600  # 1 hour between performance alerts
        
    async def send_system_alert(self, title: str, message: str, alert_type: str = "info", color: int = None):
        """Send performance/optimization alert to system webhook."""
        if not self.system_webhook_url or not self.performance_alert_enabled:
            self.logger.debug("System webhook not configured or performance alerts disabled")
            return
            
        # Check cooldown for this alert type
        current_time = datetime.now().timestamp()
        last_alert_time = self.last_performance_alert.get(alert_type, 0)
        
        if current_time - last_alert_time < self.performance_alert_cooldown:
            self.logger.debug(f"Performance alert throttled for {alert_type}")
            return
            
        # Color coding for different alert types
        colors = {
            "critical": 0xFF0000,  # Red
            "warning": 0xFFA500,   # Orange
            "info": 0x0099FF,      # Blue
            "success": 0x00FF00    # Green
        }
        
        embed_color = color or colors.get(alert_type, colors["info"])
        
        # Create Discord embed
        embed = {
            "title": f"🎯 Alpha System Performance: {title}",
            "description": message,
            "color": embed_color,
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "Virtuoso Alpha Optimizer",
                "icon_url": "https://i.imgur.com/alpha_bot.png"
            },
            "fields": [
                {
                    "name": "📊 Alert Type",
                    "value": alert_type.upper(),
                    "inline": True
                },
                {
                    "name": "🕐 Timestamp",
                    "value": f"<t:{int(current_time)}:F>",
                    "inline": True
                }
            ]
        }
        
        payload = {
            "username": "Virtuoso Alpha Monitor",
            "avatar_url": "https://i.imgur.com/alpha_bot.png",
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.system_webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info(f"System performance alert sent: {title}")
                        self.last_performance_alert[alert_type] = current_time
                    else:
                        self.logger.warning(f"Failed to send system alert: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending system alert: {str(e)}")

    async def analyze_alert_quality(self, alpha_integration: AlphaMonitorIntegration) -> Dict[str, Any]:
        """Analyze current alert quality and performance."""
        stats = alpha_integration.get_enhanced_stats()
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'current_stats': stats,
            'quality_assessment': self._assess_quality(stats),
            'optimization_recommendations': self._generate_recommendations(stats),
            'threshold_suggestions': self._suggest_threshold_adjustments(stats)
        }
        
        # Send system alerts for critical issues
        await self._check_and_send_performance_alerts(analysis)
        
        return analysis
    
    async def _check_and_send_performance_alerts(self, analysis: Dict[str, Any]):
        """Check for performance issues and send system alerts."""
        quality = analysis['quality_assessment']
        recommendations = analysis['optimization_recommendations']
        stats = analysis['current_stats']
        
        # Critical performance issues
        if quality['overall_grade'] == 'D':
            await self.send_system_alert(
                "Critical Performance Issues Detected",
                f"**Alpha alert system performance is poor (Grade: {quality['overall_grade']})**\n\n"
                f"📊 **Current Stats:**\n"
                f"• Filter Efficiency: {quality['filter_efficiency']:.1f}%\n"
                f"• Alert Frequency: {quality['alert_frequency']}\n"
                f"• Total Opportunities: {quality['total_opportunities']}\n"
                f"• Alerts Sent: {quality['sent_alerts']}\n\n"
                f"⚠️ **Issues:**\n" + "\n".join([f"• {issue}" for issue in quality['issues']]) + "\n\n"
                f"🔧 **Immediate Actions Needed:**\n" + "\n".join([f"• {rec}" for rec in recommendations[:3]]),
                "critical"
            )
        
        # High alert frequency warning
        hourly_count = stats.get('hourly_alert_count', 0)
        if hourly_count > 10:
            await self.send_system_alert(
                "High Alert Frequency Detected",
                f"**Alpha alerts are being generated too frequently**\n\n"
                f"📈 **Current Rate:** {hourly_count} alerts in the last hour\n"
                f"🎯 **Target Rate:** ≤5 alerts per hour\n\n"
                f"**Recommended Actions:**\n"
                f"• Increase confidence threshold to 90%+\n"
                f"• Increase check interval to 30+ minutes\n"
                f"• Enable stricter volume confirmation\n\n"
                f"This may indicate market volatility or overly sensitive thresholds.",
                "warning"
            )
        
        # Low filter efficiency warning
        if quality['filter_efficiency'] < 30 and quality['total_opportunities'] > 10:
            await self.send_system_alert(
                "Low Filter Efficiency Warning",
                f"**Alpha alert filters are not working effectively**\n\n"
                f"📊 **Filter Efficiency:** {quality['filter_efficiency']:.1f}%\n"
                f"🎯 **Target Efficiency:** ≥70%\n\n"
                f"**Impact:**\n"
                f"• Too many low-quality alerts passing through\n"
                f"• Potential alert fatigue for traders\n"
                f"• Reduced signal-to-noise ratio\n\n"
                f"**Recommended Actions:**\n"
                f"• Increase confidence threshold\n"
                f"• Enable volume confirmation\n"
                f"• Add market regime filtering",
                "warning"
            )
        
        # System health check - good performance
        if quality['overall_grade'] in ['A', 'B'] and quality['total_opportunities'] > 5:
            # Only send success alert once per day
            today = datetime.now().date()
            last_success = self.last_performance_alert.get('daily_success', datetime.min.date())
            
            if last_success < today:
                await self.send_system_alert(
                    "Alpha System Performing Well",
                    f"**Alpha alert system is operating optimally**\n\n"
                    f"📊 **Performance Grade:** {quality['overall_grade']}\n"
                    f"• Filter Efficiency: {quality['filter_efficiency']:.1f}%\n"
                    f"• Alert Frequency: {quality['alert_frequency']}\n"
                    f"• Opportunities Processed: {quality['total_opportunities']}\n"
                    f"• Quality Alerts Sent: {quality['sent_alerts']}\n\n"
                    f"✅ System is properly filtering noise while maintaining signal quality.",
                    "success"
                )
                self.last_performance_alert['daily_success'] = today
        
        # Configuration optimization suggestions
        threshold_suggestions = analysis['threshold_suggestions']
        if threshold_suggestions['suggested']:
            suggestion_text = "**Optimization Opportunities Detected**\n\n"
            suggestion_text += "🔧 **Suggested Threshold Adjustments:**\n"
            
            for param, value in threshold_suggestions['suggested'].items():
                current = threshold_suggestions['current'].get(param, 'Unknown')
                reasoning = threshold_suggestions['reasoning'].get(param, 'No reasoning provided')
                suggestion_text += f"• **{param}:** {current} → {value}\n"
                suggestion_text += f"  *{reasoning}*\n\n"
            
            suggestion_text += "💡 **To apply these changes:**\n"
            suggestion_text += "Update `config/alpha_integration.yaml` with the suggested values above."
            
            await self.send_system_alert(
                "Configuration Optimization Available",
                suggestion_text,
                "info"
            )

    def _assess_quality(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall alert quality."""
        sent = stats.get('alpha_opportunities_sent', 0)
        filtered = stats.get('alpha_opportunities_filtered', 0)
        total = sent + filtered
        
        if total == 0:
            return {
                'overall_grade': 'N/A',
                'filter_efficiency': 0,
                'alert_frequency': 'None',
                'issues': ['No alerts generated yet']
            }
        
        filter_efficiency = (filtered / total) * 100
        hourly_count = stats.get('hourly_alert_count', 0)
        
        # Grade the system
        issues = []
        if filter_efficiency < 50:
            issues.append('Low filter efficiency - too many alerts passing through')
        if hourly_count > 8:
            issues.append('High alert frequency - may be too noisy')
        if sent == 0:
            issues.append('No alerts sent - thresholds may be too strict')
        
        # Overall grade
        if len(issues) == 0:
            grade = 'A'
        elif len(issues) == 1:
            grade = 'B'
        elif len(issues) == 2:
            grade = 'C'
        else:
            grade = 'D'
        
        return {
            'overall_grade': grade,
            'filter_efficiency': filter_efficiency,
            'alert_frequency': self._categorize_frequency(hourly_count),
            'issues': issues,
            'total_opportunities': total,
            'sent_alerts': sent,
            'filtered_alerts': filtered
        }
    
    def _categorize_frequency(self, hourly_count: int) -> str:
        """Categorize alert frequency."""
        if hourly_count == 0:
            return 'None'
        elif hourly_count <= 2:
            return 'Low (Optimal)'
        elif hourly_count <= 5:
            return 'Medium'
        elif hourly_count <= 8:
            return 'High'
        else:
            return 'Very High (Noisy)'
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        sent = stats.get('alpha_opportunities_sent', 0)
        filtered = stats.get('alpha_opportunities_filtered', 0)
        total = sent + filtered
        hourly_count = stats.get('hourly_alert_count', 0)
        
        if total == 0:
            recommendations.append("System is not generating any opportunities. Consider lowering thresholds.")
            return recommendations
        
        filter_efficiency = (filtered / total) * 100
        
        # Filter efficiency recommendations
        if filter_efficiency < 30:
            recommendations.append("🔴 URGENT: Very low filter efficiency. Increase confidence threshold to 90%+")
        elif filter_efficiency < 50:
            recommendations.append("🟡 Moderate filter efficiency. Consider increasing alpha threshold to 5%+")
        elif filter_efficiency > 90:
            recommendations.append("🟡 Very high filter efficiency. May be missing good opportunities - consider lowering thresholds slightly")
        
        # Alert frequency recommendations
        if hourly_count > 10:
            recommendations.append("🔴 URGENT: Too many alerts per hour. Increase check interval to 30+ minutes")
        elif hourly_count > 5:
            recommendations.append("🟡 High alert frequency. Consider increasing throttling limits")
        elif hourly_count == 0 and total > 0:
            recommendations.append("🟡 Alerts being generated but not sent. Check throttling configuration")
        
        # Threshold-specific recommendations
        thresholds = stats.get('thresholds', {})
        confidence_threshold = thresholds.get('confidence', 0.85)
        alpha_threshold = thresholds.get('alpha', 0.04)
        
        if confidence_threshold < 0.8:
            recommendations.append("🔴 Confidence threshold too low. Increase to 85%+ for production")
        if alpha_threshold < 0.03:
            recommendations.append("🟡 Alpha threshold may be too sensitive. Consider 4%+ for significant moves")
        
        # Volume confirmation
        if not stats.get('volume_confirmation_enabled', True):
            recommendations.append("🔴 Enable volume confirmation to reduce false signals")
        
        return recommendations
    
    def _suggest_threshold_adjustments(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest specific threshold adjustments."""
        current_thresholds = stats.get('thresholds', {})
        sent = stats.get('alpha_opportunities_sent', 0)
        filtered = stats.get('alpha_opportunities_filtered', 0)
        hourly_count = stats.get('hourly_alert_count', 0)
        
        suggestions = {
            'current': current_thresholds,
            'suggested': {},
            'reasoning': {}
        }
        
        # Confidence threshold suggestions
        current_confidence = current_thresholds.get('confidence', 0.85)
        if hourly_count > 8:  # Too many alerts
            suggested_confidence = min(0.95, current_confidence + 0.05)
            suggestions['suggested']['confidence'] = suggested_confidence
            suggestions['reasoning']['confidence'] = f"Increase from {current_confidence:.0%} to {suggested_confidence:.0%} to reduce noise"
        elif sent == 0 and filtered > 10:  # Too restrictive
            suggested_confidence = max(0.75, current_confidence - 0.05)
            suggestions['suggested']['confidence'] = suggested_confidence
            suggestions['reasoning']['confidence'] = f"Decrease from {current_confidence:.0%} to {suggested_confidence:.0%} to allow more signals"
        
        # Alpha threshold suggestions
        current_alpha = current_thresholds.get('alpha', 0.04)
        if hourly_count > 5:  # Too sensitive
            suggested_alpha = min(0.08, current_alpha + 0.01)
            suggestions['suggested']['alpha'] = suggested_alpha
            suggestions['reasoning']['alpha'] = f"Increase from {current_alpha:.1%} to {suggested_alpha:.1%} for more significant moves"
        elif sent == 0:  # Too restrictive
            suggested_alpha = max(0.02, current_alpha - 0.01)
            suggestions['suggested']['alpha'] = suggested_alpha
            suggestions['reasoning']['alpha'] = f"Decrease from {current_alpha:.1%} to {suggested_alpha:.1%} to catch smaller opportunities"
        
        # Check interval suggestions
        current_interval = stats.get('check_interval', 900)
        if hourly_count > 8:
            suggested_interval = min(1800, current_interval + 300)  # Add 5 minutes
            suggestions['suggested']['check_interval'] = suggested_interval
            suggestions['reasoning']['check_interval'] = f"Increase from {current_interval}s to {suggested_interval}s to reduce frequency"
        
        return suggestions
    
    def generate_optimization_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a human-readable optimization report."""
        quality = analysis['quality_assessment']
        recommendations = analysis['optimization_recommendations']
        threshold_suggestions = analysis['threshold_suggestions']
        
        report = f"""
🎯 ALPHA ALERT QUALITY REPORT
Generated: {analysis['timestamp']}

📊 CURRENT PERFORMANCE
Overall Grade: {quality['overall_grade']}
Filter Efficiency: {quality['filter_efficiency']:.1f}%
Alert Frequency: {quality['alert_frequency']}
Total Opportunities: {quality['total_opportunities']}
Alerts Sent: {quality['sent_alerts']}
Alerts Filtered: {quality['filtered_alerts']}

"""
        
        if quality['issues']:
            report += "⚠️  IDENTIFIED ISSUES:\n"
            for issue in quality['issues']:
                report += f"   • {issue}\n"
            report += "\n"
        
        if recommendations:
            report += "🔧 OPTIMIZATION RECOMMENDATIONS:\n"
            for rec in recommendations:
                report += f"   {rec}\n"
            report += "\n"
        
        if threshold_suggestions['suggested']:
            report += "⚙️  SUGGESTED THRESHOLD ADJUSTMENTS:\n"
            for param, value in threshold_suggestions['suggested'].items():
                current = threshold_suggestions['current'].get(param, 'Unknown')
                reasoning = threshold_suggestions['reasoning'].get(param, 'No reasoning provided')
                report += f"   • {param}: {current} → {value}\n"
                report += f"     Reason: {reasoning}\n"
            report += "\n"
        
        report += """
📋 QUICK CONFIGURATION UPDATES:

To apply these recommendations, update your config/alpha_integration.yaml:

```yaml
alpha_detection:
  alert_threshold: {confidence}
  check_interval: {check_interval}
  detection_params:
    min_alpha_threshold: {alpha}
    volume_confirmation_required: true
    market_regime_filtering: true
```

🔄 MONITORING COMMANDS:

# Check current stats
python scripts/monitoring/alpha_alert_optimizer.py --stats

# Generate optimization report  
python scripts/monitoring/alpha_alert_optimizer.py --optimize

# Apply suggested thresholds
python scripts/monitoring/alpha_alert_optimizer.py --apply-suggestions

📡 SYSTEM ALERTS:
Performance alerts are automatically sent to SYSTEM_ALERTS_WEBHOOK_URL
Regular alpha trading alerts continue to use the main webhook
""".format(
            confidence=threshold_suggestions['suggested'].get('confidence', 0.85),
            check_interval=threshold_suggestions['suggested'].get('check_interval', 900),
            alpha=threshold_suggestions['suggested'].get('alpha', 0.04)
        )
        
        return report
    
    async def save_analysis(self, analysis: Dict[str, Any], output_dir: str = "reports/alpha_optimization"):
        """Save analysis to file."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON analysis
        json_file = f"{output_dir}/alpha_analysis_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        # Save human-readable report
        report = self.generate_optimization_report(analysis)
        report_file = f"{output_dir}/alpha_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Analysis saved to {json_file} and {report_file}")
        return json_file, report_file


async def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alpha Alert Quality Monitor and Optimizer")
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--stats', action='store_true', help='Show current statistics')
    parser.add_argument('--optimize', action='store_true', help='Generate optimization report')
    parser.add_argument('--apply-suggestions', action='store_true', help='Apply suggested threshold adjustments')
    parser.add_argument('--output-dir', default='reports/alpha_optimization', help='Output directory for reports')
    parser.add_argument('--test-system-alert', action='store_true', help='Send test system alert')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    optimizer = AlphaAlertOptimizer(args.config)
    
    print("🎯 Alpha Alert Quality Optimizer")
    print("=" * 50)
    
    if args.test_system_alert:
        print("📡 Testing System Alert...")
        await optimizer.send_system_alert(
            "Test System Alert",
            "This is a test alert to verify system webhook connectivity.\n\n"
            "✅ If you see this message, the system alerts are working correctly.\n"
            "🔧 Performance alerts will be sent to this webhook automatically.",
            "info"
        )
        print("✅ Test alert sent to system webhook")
        return
    
    if args.stats:
        print("📊 Current Statistics:")
        print("   This would show real-time stats from your alpha integration")
        print("   Connect to your running monitor instance to get live data")
    
    if args.optimize:
        print("🔧 Generating Optimization Report:")
        print("   This would analyze your current alert performance")
        print("   and provide specific recommendations for improvement")
        print("   📡 Performance alerts will be sent to SYSTEM_ALERTS_WEBHOOK_URL")
    
    if args.apply_suggestions:
        print("⚙️  Applying Suggested Threshold Adjustments:")
        print("   This would automatically update your configuration")
        print("   with optimized thresholds based on performance data")
    
    print("\n💡 To use this tool with your live system:")
    print("   1. Ensure your monitor is running with alpha integration")
    print("   2. Connect this script to your AlphaMonitorIntegration instance")
    print("   3. Run periodic optimization analysis")
    print("   4. Apply recommended threshold adjustments")
    print("\n📡 System Alert Configuration:")
    print(f"   SYSTEM_ALERTS_WEBHOOK_URL: {'✅ Configured' if optimizer.system_webhook_url else '❌ Not configured'}")
    print("   Performance alerts will be sent to system webhook")
    print("   Regular alpha alerts continue to main webhook")


if __name__ == "__main__":
    asyncio.run(main()) 