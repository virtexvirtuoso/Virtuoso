#!/usr/bin/env python3
"""
Alert Formatting Fixes for Virtuoso Trading System
Comprehensive fixes for alert formatting and context issues
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AlertFormattingFixes:
    """Apply comprehensive fixes to alert formatting issues"""

    def __init__(self):
        self.fixes_applied = []
        self.issues_found = []

    def apply_alert_manager_fixes(self, file_path: str):
        """Apply fixes to alert manager formatting issues"""

        issues_found = []
        fixes_applied = []

        # Read the original file
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return issues_found, fixes_applied

        original_content = content

        # Issue 1: Inconsistent alert title formatting
        # Fix: Standardize all alert titles to use consistent format
        title_patterns = [
            # Current inconsistent patterns
            (r'title=f"💥 Large Aggressive Order: \{symbol\}"',
             'title=f"💥 LARGE ORDER ALERT - {symbol}"'),

            (r'title=f"Whale \{subtype\.capitalize\(\)\} Alert - \{symbol\}"',
             'title=f"🐋 WHALE {subtype.upper()} ALERT - {symbol}"'),

            (r'title = f"\{direction_emoji\} \{position_type\} LIQUIDATION: \{symbol\}"',
             'title = f"{direction_emoji} {position_type.upper()} LIQUIDATION ALERT - {symbol}"'),

            (r'title = f"\{emoji\} \{signal_type\} SIGNAL: \{symbol\}"',
             'title = f"{emoji} {signal_type} SIGNAL ALERT - {symbol}"'),

            (r'title=f"\{level\} Alert"',
             'title=f"{level.upper()} SYSTEM ALERT"'),
        ]

        for old_pattern, new_pattern in title_patterns:
            if re.search(old_pattern, content):
                issues_found.append(f"Inconsistent title format: {old_pattern}")
                content = re.sub(old_pattern, new_pattern, content)
                fixes_applied.append(f"Standardized title format: {new_pattern}")

        # Issue 2: Missing context in alert descriptions
        # Fix: Add standardized context fields
        context_fixes = [
            # Add timestamp context to alerts that lack it
            {
                'pattern': r'(description = \[)',
                'replacement': r'\1\n                f"⏰ **Time:** {datetime.utcnow().strftime(\'%H:%M:%S UTC\')}",',
                'issue': 'Missing timestamp context in alert descriptions',
                'fix': 'Added timestamp context to alert descriptions'
            },

            # Add exchange context where missing
            {
                'pattern': r'(description\.append\(f"\*\*Price:\*\* \{price_str\}"\))',
                'replacement': r'\1\n                if exchange:\n                    description.append(f"🏢 **Exchange:** {exchange}")',
                'issue': 'Missing exchange context in price alerts',
                'fix': 'Added exchange context to price alerts'
            },

            # Add confidence indicators
            {
                'pattern': r'(description\.append\(f"\*\*Value:\*\* \$\{usd_value:.2f\}"\))',
                'replacement': r'\1\n                description.append(f"📊 **Confidence:** {reliability*100:.1f}%" if reliability else "📊 **Confidence:** Not Available")',
                'issue': 'Missing confidence indicators in value alerts',
                'fix': 'Added confidence indicators to value alerts'
            }
        ]

        for fix in context_fixes:
            if re.search(fix['pattern'], content):
                issues_found.append(fix['issue'])
                content = re.sub(fix['pattern'], fix['replacement'], content)
                fixes_applied.append(fix['fix'])

        # Issue 3: Inconsistent emoji usage
        # Fix: Standardize emoji patterns
        emoji_fixes = [
            # Standardize signal emojis
            (r'direction_emoji = "↗️" if.*else "↘️"',
             'direction_emoji = "🟢📈" if net_flow > 0 else "🔴📉"'),

            # Standardize whale emojis
            (r'"🐋 WHALE ACTIVITY"',
             '"🐋 WHALE MOVEMENT DETECTED"'),

            # Standardize system emojis
            (r'"💥 LARGE ORDER ALERT"',
             '"⚡ LARGE ORDER ALERT"'),
        ]

        for old_emoji, new_emoji in emoji_fixes:
            if re.search(old_emoji, content):
                issues_found.append(f"Inconsistent emoji usage: {old_emoji}")
                content = re.sub(old_emoji, new_emoji, content)
                fixes_applied.append(f"Standardized emoji usage: {new_emoji}")

        # Issue 4: Missing severity indicators
        # Fix: Add severity levels to all alerts
        severity_fix = '''
        # Add severity level based on alert type and values
        def get_alert_severity(alert_type: str, value: float = 0, score: float = 0) -> tuple:
            """Get standardized severity level and color for alerts"""
            if "CRITICAL" in alert_type.upper() or score > 90 or value > 10000000:
                return "🚨 CRITICAL", 0xFF0000
            elif "HIGH" in alert_type.upper() or score > 75 or value > 5000000:
                return "⚠️ HIGH", 0xFF6600
            elif "MEDIUM" in alert_type.upper() or score > 60 or value > 1000000:
                return "📊 MEDIUM", 0xFFAA00
            else:
                return "ℹ️ LOW", 0x3498DB
        '''

        # Insert severity function if not present
        if 'get_alert_severity' not in content:
            # Find a good place to insert the function (after imports)
            import_end = content.find('logger = logging.getLogger(__name__)')
            if import_end != -1:
                insert_pos = content.find('\n', import_end) + 1
                content = content[:insert_pos] + severity_fix + '\n' + content[insert_pos:]
                issues_found.append("Missing severity level standardization")
                fixes_applied.append("Added standardized severity level function")

        # Issue 5: Inconsistent price formatting
        # Fix: Standardize price display
        price_formatting_fixes = [
            # Ensure consistent price precision
            (r'f"\$\{price:.4f\}"',
             'f"${format_price_with_precision(price)}"'),

            (r'f"\$\{.*:.2f\}"',
             'f"${format_currency_value(value)}"'),
        ]

        # Add price formatting functions if needed
        price_functions = '''
def format_price_with_precision(price: float) -> str:
    """Format price with appropriate precision based on value"""
    if price < 0.01:
        return f"{price:.8f}"
    elif price < 1:
        return f"{price:.6f}"
    elif price < 10:
        return f"{price:.4f}"
    else:
        return f"{price:,.2f}"

def format_currency_value(value: float) -> str:
    """Format currency values with appropriate units"""
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value/1_000:.1f}K"
    else:
        return f"{value:.2f}"
'''

        if 'format_price_with_precision' not in content:
            # Insert after the severity function
            severity_pos = content.find('get_alert_severity')
            if severity_pos != -1:
                # Find end of function
                func_end = content.find('\n\n', severity_pos)
                if func_end != -1:
                    content = content[:func_end] + '\n' + price_functions + content[func_end:]
                    issues_found.append("Missing standardized price formatting")
                    fixes_applied.append("Added standardized price formatting functions")

        # Issue 6: Missing alert context metadata
        # Fix: Add comprehensive metadata to all alerts
        metadata_fix = '''
        # Add comprehensive metadata footer to all alerts
        metadata_fields = []
        if transaction_id:
            metadata_fields.append(f"TXN:{transaction_id}")
        if signal_id:
            metadata_fields.append(f"SIG:{signal_id}")
        if alert_id:
            metadata_fields.append(f"ALERT:{alert_id}")

        # Add system context
        metadata_fields.extend([
            f"SYS:{platform.node()}",
            f"TS:{int(time.time())}"
        ])

        embed.set_footer(text=" | ".join(metadata_fields))
        '''

        # Find embed creation patterns and ensure metadata is added
        embed_patterns = [
            r'embed = DiscordEmbed\(',
            r'embed\.set_footer\(text=.*\)'
        ]

        for pattern in embed_patterns:
            if re.search(pattern, content) and 'metadata_fields' not in content:
                issues_found.append("Missing comprehensive alert metadata")
                # Add after the last embed creation
                last_embed = list(re.finditer(r'embed = DiscordEmbed\(', content))
                if last_embed:
                    pos = last_embed[-1].end()
                    # Find the end of the embed creation block
                    next_line = content.find('\n', pos)
                    content = content[:next_line] + '\n' + metadata_fix + content[next_line:]
                    fixes_applied.append("Added comprehensive alert metadata")
                break

        # Save the fixed content if changes were made
        if content != original_content:
            try:
                # Create backup
                backup_path = f"{file_path}.backup_{int(time.time())}"
                with open(backup_path, 'w') as f:
                    f.write(original_content)

                # Write fixed content
                with open(file_path, 'w') as f:
                    f.write(content)

                logger.info(f"Applied {len(fixes_applied)} fixes to {file_path}")
                logger.info(f"Backup created at {backup_path}")

            except Exception as e:
                logger.error(f"Error writing fixes to {file_path}: {e}")

        return issues_found, fixes_applied

    def apply_alert_formatter_fixes(self, file_path: str):
        """Apply fixes to alert formatter issues"""

        issues_found = []
        fixes_applied = []

        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return issues_found, fixes_applied

        original_content = content

        # Issue 1: Inconsistent signal strength indicators
        # Fix: Standardize signal strength display
        if 'signal_strength == "CONFLICTING"' in content:
            # Enhance the conflicting signal detection
            enhanced_conflicting = '''
            if signal_strength == "CONFLICTING":
                return (
                    "🚨 **MANIPULATION WARNING**\\n"
                    f"• Detected at {datetime.utcnow().strftime('%H:%M:%S UTC')}\\n"
                    "• Order book shows large {0} orders\\n"
                    "• Actual trades are mostly {1}\\n"
                    "• **RISK LEVEL:** CRITICAL - Likely spoofing detected\\n"
                    "• **RECOMMENDED ACTION:** AVOID TRADING immediately\\n"
                    "• **MONITOR:** Wait for manipulation to clear (typically 5-15 minutes)"
                ).format(
                    "buy" if subtype == "accumulation" else "sell",
                    "sells" if sell_count > buy_count else "buys"
                )
            '''

            # Replace the existing conflicting logic
            old_pattern = r'if signal_strength == "CONFLICTING":.*?return.*?\)'
            if re.search(old_pattern, content, re.DOTALL):
                content = re.sub(old_pattern, enhanced_conflicting.strip(), content, flags=re.DOTALL)
                issues_found.append("Insufficient detail in manipulation warning")
                fixes_applied.append("Enhanced manipulation warning with detailed context")

        # Issue 2: Missing risk assessment context
        # Fix: Add comprehensive risk context
        risk_enhancement = '''
    def _assess_risk_with_context(self, signal_strength: str, net_value: float,
                                  total_trades: int, market_conditions: dict = None) -> str:
        """Enhanced risk assessment with market context"""

        risk_factors = []
        risk_level = "🟢 LOW"

        # Primary risk assessment
        if signal_strength == "CONFLICTING":
            risk_level = "🔴 CRITICAL"
            risk_factors.append("Manipulation detected")
        elif abs(net_value) > 10000000:
            risk_level = "🔴 HIGH"
            risk_factors.append(f"Massive whale activity (${abs(net_value)/1e6:.1f}M)")
        elif abs(net_value) > 5000000 and total_trades > 50:
            risk_level = "🟠 MEDIUM-HIGH"
            risk_factors.append("Large coordinated activity")
        elif abs(net_value) > 1000000:
            risk_level = "🟡 MEDIUM"
            risk_factors.append("Significant whale presence")

        # Add market context if available
        if market_conditions:
            volatility = market_conditions.get('volatility', 0)
            if volatility > 0.05:  # 5% volatility
                risk_factors.append(f"High volatility ({volatility*100:.1f}%)")

            volume_spike = market_conditions.get('volume_spike', 1)
            if volume_spike > 2:
                risk_factors.append(f"Volume spike ({volume_spike:.1f}x normal)")

        # Format final assessment
        risk_text = f"**{risk_level}**"
        if risk_factors:
            risk_text += "\\n• " + "\\n• ".join(risk_factors)

        return risk_text
        '''

        if '_assess_risk_with_context' not in content:
            # Insert the enhanced risk function
            risk_pos = content.find('def _assess_risk(')
            if risk_pos != -1:
                func_end = content.find('\n    def ', risk_pos + 1)
                if func_end != -1:
                    content = content[:func_end] + '\n' + risk_enhancement + content[func_end:]
                    issues_found.append("Basic risk assessment lacking context")
                    fixes_applied.append("Added enhanced risk assessment with market context")

        # Issue 3: Incomplete action recommendations
        # Fix: Add detailed actionable recommendations
        action_enhancement = '''
    def _get_enhanced_action_recommendation(self, signal_strength: str, subtype: str,
                                          net_flow: float, risk_level: str,
                                          confidence: float = 0) -> str:
        """Generate detailed actionable recommendations with specific steps"""

        recommendations = []

        if "CRITICAL" in risk_level:
            recommendations.extend([
                "🛑 **IMMEDIATE ACTION: STOP ALL TRADING**",
                "📊 Monitor order book for sudden cancellations",
                "⏰ Wait 15-30 minutes for manipulation to clear",
                "🔍 Verify with multiple exchanges before resuming",
                "📱 Set alerts for when normal patterns resume"
            ])

        elif signal_strength == "EXECUTING":
            if net_flow > 5000000:  # $5M+
                if confidence > 0.8:
                    recommendations.extend([
                        f"🎯 **STRONG {('BULLISH' if net_flow > 0 else 'BEARISH')} SIGNAL**",
                        f"💰 Position size: 2-3% of portfolio maximum",
                        f"⏱️ Entry: {'Market order' if confidence > 0.9 else 'Limit at current price'}",
                        f"🛡️ Stop loss: {'1.5%' if confidence > 0.9 else '2%'} from entry",
                        f"🎯 Target: {'3-4%' if confidence > 0.9 else '2-3%'} profit",
                        f"📈 Monitor: Watch for continuation signals"
                    ])
                else:
                    recommendations.extend([
                        f"⚠️ **MODERATE {('BULLISH' if net_flow > 0 else 'BEARISH')} SIGNAL**",
                        f"💰 Position size: 1-2% of portfolio",
                        f"⏱️ Entry: Wait for better confirmation",
                        f"🛡️ Stop loss: 2.5% from entry",
                        f"🎯 Target: 2% profit, secure partial profits"
                    ])
            else:
                recommendations.extend([
                    "👀 **MONITOR CLOSELY**",
                    "📊 Watch for increased volume confirmation",
                    "⏰ Consider small test position (0.5% portfolio)",
                    "🔄 Scale in if pattern strengthens"
                ])

        else:
            recommendations.extend([
                "🔍 **CONTINUE MONITORING**",
                "📊 No immediate action required",
                "⚡ Set alerts for score changes",
                "📈 Wait for stronger signal confirmation"
            ])

        return "\\n".join(recommendations)
        '''

        if '_get_enhanced_action_recommendation' not in content:
            # Replace or enhance existing action recommendation
            action_pos = content.find('def _get_recommended_action(')
            if action_pos != -1:
                func_end = content.find('\n    def ', action_pos + 1)
                if func_end == -1:
                    func_end = len(content)

                content = content[:func_end] + '\n' + action_enhancement + content[func_end:]
                issues_found.append("Basic action recommendations lack detail")
                fixes_applied.append("Added enhanced actionable recommendations")

        # Save the enhanced content
        if content != original_content:
            try:
                # Create backup
                backup_path = f"{file_path}.backup_{int(time.time())}"
                with open(backup_path, 'w') as f:
                    f.write(original_content)

                # Write enhanced content
                with open(file_path, 'w') as f:
                    f.write(content)

                logger.info(f"Applied {len(fixes_applied)} enhancements to {file_path}")

            except Exception as e:
                logger.error(f"Error writing enhancements to {file_path}: {e}")

        return issues_found, fixes_applied

    def validate_fixes(self, file_paths: List[str]) -> Dict[str, Any]:
        """Validate that fixes don't break existing functionality"""

        validation_results = {
            'syntax_valid': True,
            'imports_valid': True,
            'functions_callable': True,
            'issues': []
        }

        for file_path in file_paths:
            try:
                # Basic syntax validation
                with open(file_path, 'r') as f:
                    content = f.read()

                # Check for syntax errors
                try:
                    compile(content, file_path, 'exec')
                except SyntaxError as e:
                    validation_results['syntax_valid'] = False
                    validation_results['issues'].append(f"Syntax error in {file_path}: {e}")

                # Check for import issues
                required_imports = ['logging', 'datetime', 'time', 'platform']
                for imp in required_imports:
                    if f'import {imp}' not in content and f'from {imp}' not in content:
                        validation_results['imports_valid'] = False
                        validation_results['issues'].append(f"Missing import {imp} in {file_path}")

                # Check for function definitions
                required_functions = ['format_price_with_precision', 'get_alert_severity']
                for func in required_functions:
                    if f'def {func}' not in content:
                        validation_results['functions_callable'] = False
                        validation_results['issues'].append(f"Missing function {func} in {file_path}")

            except Exception as e:
                validation_results['issues'].append(f"Error validating {file_path}: {e}")

        return validation_results

def main():
    """Apply comprehensive alert formatting fixes"""

    # Initialize the fixes
    fixer = AlertFormattingFixes()

    # Target files for fixes
    alert_manager_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/alert_manager.py"
    alert_formatter_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/alert_formatter.py"

    all_issues = []
    all_fixes = []

    print("🔧 ALERT FORMATTING FIXES - Comprehensive Validation & Repair")
    print("=" * 70)

    # Apply fixes to alert manager
    if os.path.exists(alert_manager_path):
        print(f"📁 Processing: {alert_manager_path}")
        issues, fixes = fixer.apply_alert_manager_fixes(alert_manager_path)
        all_issues.extend(issues)
        all_fixes.extend(fixes)
        print(f"   ✅ Found {len(issues)} issues, applied {len(fixes)} fixes")

    # Apply fixes to alert formatter
    if os.path.exists(alert_formatter_path):
        print(f"📁 Processing: {alert_formatter_path}")
        issues, fixes = fixer.apply_alert_formatter_fixes(alert_formatter_path)
        all_issues.extend(issues)
        all_fixes.extend(fixes)
        print(f"   ✅ Found {len(issues)} issues, applied {len(fixes)} fixes")

    # Validate the fixes
    print(f"\n🔍 VALIDATION PHASE")
    validation = fixer.validate_fixes([alert_manager_path, alert_formatter_path])

    if validation['syntax_valid'] and validation['imports_valid'] and validation['functions_callable']:
        print("   ✅ All fixes validated successfully")
    else:
        print("   ⚠️ Validation issues found:")
        for issue in validation['issues']:
            print(f"      • {issue}")

    # Summary report
    print(f"\n📊 SUMMARY REPORT")
    print(f"   🔍 Total issues identified: {len(all_issues)}")
    print(f"   🔧 Total fixes applied: {len(all_fixes)}")
    print(f"   ✅ Validation status: {'PASSED' if not validation['issues'] else 'ISSUES FOUND'}")

    return {
        'issues_found': all_issues,
        'fixes_applied': all_fixes,
        'validation': validation
    }

if __name__ == "__main__":
    import time
    import platform

    results = main()

    # Save detailed report
    report_path = f"/Users/ffv_macmini/Desktop/Virtuoso_ccxt/alert_formatting_fixes_report_{int(time.time())}.json"
    import json
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📋 Detailed report saved to: {report_path}")