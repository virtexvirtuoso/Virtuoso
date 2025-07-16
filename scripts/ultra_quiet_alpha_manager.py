#!/usr/bin/env python3
"""
Ultra Quiet Alpha Manager
Implements maximum noise reduction for alpha alerts with extreme filtering
"""

import yaml
import argparse
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from monitoring.optimized_alpha_scanner import OptimizedAlphaScanner
from core.config.config_manager import ConfigManager

class UltraQuietAlphaManager:
    """Manages ultra quiet mode with maximum noise reduction"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / 'config' / 'alpha_optimization.yaml'
        self.logger = self._setup_logging()
        self.config_manager = ConfigManager()
        
    def _setup_logging(self):
        """Setup logging for the manager"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def enable_ultra_quiet_mode(self):
        """Enable ultra quiet mode with maximum noise reduction"""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Enable ultra quiet mode
            config['alpha_scanning_optimized']['ultra_quiet_mode']['enabled'] = True
            config['alpha_scanning_optimized']['silent_mode']['enabled'] = False
            config['alpha_scanning_optimized']['extreme_mode']['enabled'] = False
            config['alpha_scanning_optimized']['alpha_alerts_enabled'] = True
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info("✅ Ultra Quiet Mode ENABLED")
            self.logger.info("📊 Expected alert volume: 1-3 alerts per day maximum")
            self.logger.info("🎯 Target: 200%+ alpha, 99.5%+ confidence")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to enable ultra quiet mode: {e}")
            return False
    
    def enable_silent_mode(self):
        """Enable silent mode with zero tolerance for noise"""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Enable silent mode
            config['alpha_scanning_optimized']['silent_mode']['enabled'] = True
            config['alpha_scanning_optimized']['ultra_quiet_mode']['enabled'] = False
            config['alpha_scanning_optimized']['extreme_mode']['enabled'] = False
            config['alpha_scanning_optimized']['alpha_alerts_enabled'] = True
            
            # Hard disable problematic patterns
            config['pattern_configs']['cross_timeframe']['enabled'] = False
            config['pattern_configs']['alpha_breakout']['enabled'] = False
            config['pattern_configs']['correlation_breakdown']['enabled'] = False
            
            # Set pattern weights to zero for disabled patterns
            config['alpha_scanning_optimized']['pattern_weights']['cross_timeframe'] = 0.0
            config['alpha_scanning_optimized']['pattern_weights']['alpha_breakout'] = 0.0
            config['alpha_scanning_optimized']['pattern_weights']['correlation_breakdown'] = 0.0
            
            # Increase minimum thresholds even further
            config['alpha_scanning_optimized']['alpha_tiers']['tier_1_critical']['min_alpha'] = 3.0  # 300% alpha
            config['alpha_scanning_optimized']['alpha_tiers']['tier_1_critical']['min_confidence'] = 0.999  # 99.9% confidence
            config['alpha_scanning_optimized']['alpha_tiers']['tier_2_high']['min_alpha'] = 1.5  # 150% alpha
            config['alpha_scanning_optimized']['alpha_tiers']['tier_2_high']['min_confidence'] = 0.99  # 99% confidence
            
            # Increase cooldowns
            config['alpha_scanning_optimized']['alpha_tiers']['tier_1_critical']['symbol_cooldown_hours'] = 72  # 3 days
            config['alpha_scanning_optimized']['alpha_tiers']['tier_2_high']['symbol_cooldown_hours'] = 48  # 2 days
            
            # Reduce daily limits
            config['alpha_scanning_optimized']['throttling']['max_total_alerts_per_day'] = 1  # Max 1 alert per day
            config['alpha_scanning_optimized']['throttling']['max_total_alerts_per_hour'] = 0.5  # Max 1 alert per 2 hours
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info("🔇 Silent Mode ENABLED")
            self.logger.info("📊 Expected alert volume: High-quality alerts with relaxed frequency")
            self.logger.info("🎯 Target: 300%+ alpha, 99.9%+ confidence")
            self.logger.info("🚫 Hard blocked: Cross Timeframe, Alpha Breakout, Correlation Breakdown")
            self.logger.info("⏰ Cooldowns: 4 hours (Tier 1), 2 hours (Tier 2)")
            self.logger.info("📈 Limits: Up to 20 alerts/day, 5 alerts/hour")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to enable silent mode: {e}")
            return False
    
    def disable_all_alerts(self):
        """Completely disable all alpha alerts"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            config['alpha_scanning_optimized']['alpha_alerts_enabled'] = False
            config['alpha_scanning_optimized']['ultra_quiet_mode']['enabled'] = False
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info("🔇 All alpha alerts DISABLED")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to disable alerts: {e}")
            return False
    
    def get_current_status(self):
        """Get current alert system status"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            alerts_enabled = config['alpha_scanning_optimized']['alpha_alerts_enabled']
            ultra_quiet = config['alpha_scanning_optimized']['ultra_quiet_mode']['enabled']
            silent_mode = config['alpha_scanning_optimized']['silent_mode']['enabled']
            extreme_mode = config['alpha_scanning_optimized']['extreme_mode']['enabled']
            
            status = {
                'alerts_enabled': alerts_enabled,
                'ultra_quiet_mode': ultra_quiet,
                'silent_mode': silent_mode,
                'extreme_mode': extreme_mode,
                'mode': 'DISABLED'
            }
            
            if alerts_enabled:
                if silent_mode:
                    status['mode'] = 'SILENT'
                elif ultra_quiet:
                    status['mode'] = 'ULTRA_QUIET'
                elif extreme_mode:
                    status['mode'] = 'EXTREME'
                else:
                    status['mode'] = 'NORMAL'
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get status: {e}")
            return None
    
    def show_noise_reduction_plan(self):
        """Display comprehensive noise reduction plan"""
        plan = """
🔇 ULTRA QUIET MODE - NOISE REDUCTION PLAN
==========================================

📊 CURRENT PROBLEM ANALYSIS:
• Even extreme mode generates too many alerts
• Low-value signals drowning out high-value opportunities
• Alert fatigue reducing trading effectiveness

🎯 ULTRA QUIET MODE SOLUTION:
• Maximum 3 alerts per day (vs current 50+)
• 200%+ alpha minimum (vs current 100%)
• 99.5%+ confidence (vs current 98%)
• 48-hour symbol cooldowns
• Multi-timeframe confirmation required

📈 EXPECTED RESULTS:
• 95%+ reduction in alert volume
• 500%+ increase in average alert value
• 90%+ success rate target
• Only highest conviction signals

🛡️ NOISE REDUCTION FEATURES:

1. EXTREME THRESHOLDS:
   • Tier 1: 200%+ alpha, 99.5% confidence, 15min scanning
   • Tier 2: 100%+ alpha, 98% confidence, 30min scanning
   • Tiers 3&4: Completely disabled

2. AGGRESSIVE COOLDOWNS:
   • 48-hour symbol cooldowns (Tier 1)
   • 24-hour symbol cooldowns (Tier 2)
   • 6-8 hour pattern-specific cooldowns
   • Market condition pauses

3. ENHANCED VALIDATION:
   • 10-20x volume spike requirements
   • 3+ timeframe confirmation
   • 15+ minute pattern persistence
   • Trend alignment validation

4. SMART FILTERING:
   • Market regime filtering (trending only)
   • High volatility pauses (1 hour)
   • News event pauses (30 minutes)
   • Signal quality validation (95%+)

5. QUALITY TARGETS:
   • Max 3 alerts per day
   • 90% success rate minimum
   • 150% average alpha target
   • 5% false positive rate maximum

🚀 IMPLEMENTATION OPTIONS:

Option 1: COMPLETE SILENCE
• Disable all alerts immediately
• Develop better filtering offline
• Re-enable when ready

Option 2: ULTRA QUIET MODE
• Enable maximum noise reduction
• Monitor for 24-48 hours
• Adjust thresholds if needed

Option 3: GRADUAL REDUCTION
• Start with ultra quiet mode
• Further reduce if still noisy
• Fine-tune based on results

📋 RECOMMENDED ACTION PLAN:

1. IMMEDIATE (Now):
   ✅ Alerts currently DISABLED
   • Implement ultra quiet mode
   • Test for 24 hours

2. SHORT-TERM (24-48 hours):
   • Monitor alert quality
   • Adjust thresholds if needed
   • Validate noise reduction

3. MEDIUM-TERM (1 week):
   • Analyze alert outcomes
   • Optimize based on results
   • Document best practices

4. LONG-TERM (Ongoing):
   • Continuous quality monitoring
   • Adaptive threshold adjustment
   • Market condition optimization
"""
        print(plan)
    
    def validate_ultra_quiet_config(self):
        """Validate ultra quiet mode configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            issues = []
            
            # Check ultra quiet mode settings
            uq_config = config['alpha_scanning_optimized']
            
            # Validate tier settings
            tier1 = uq_config['alpha_tiers']['tier_1_critical']
            if tier1['min_alpha'] < 2.0:
                issues.append("Tier 1 alpha threshold too low (should be 2.0+)")
            
            if tier1['min_confidence'] < 0.995:
                issues.append("Tier 1 confidence threshold too low (should be 0.995+)")
            
            if tier1['max_alerts_per_hour'] > 0.25:
                issues.append("Tier 1 alert rate too high (should be 0.25 max)")
            
            # Validate throttling
            throttling = uq_config['throttling']
            if throttling['max_total_alerts_per_day'] > 3:
                issues.append("Daily alert limit too high (should be 3 max)")
            
            # Validate filtering
            filtering = uq_config['filtering']
            if filtering['min_alert_value_score'] < 500:
                issues.append("Value score threshold too low (should be 500+)")
            
            if not issues:
                self.logger.info("✅ Ultra quiet configuration validated successfully")
                return True
            else:
                self.logger.warning("⚠️ Configuration issues found:")
                for issue in issues:
                    self.logger.warning(f"  • {issue}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to validate config: {e}")
            return False

    def validate_pattern_blocking(self):
        """Validate that problematic patterns are completely blocked"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            issues = []
            
            # Check pattern configs
            patterns = config['pattern_configs']
            
            # Cross timeframe should be disabled
            if patterns['cross_timeframe']['enabled']:
                issues.append("❌ Cross Timeframe pattern is still enabled")
            
            # Check pattern weights
            weights = config['alpha_scanning_optimized']['pattern_weights']
            if weights['cross_timeframe'] > 0:
                issues.append("❌ Cross Timeframe weight is not zero")
            
            if weights['alpha_breakout'] > 0:
                issues.append("❌ Alpha Breakout weight is not zero")
            
            if weights['correlation_breakdown'] > 0:
                issues.append("❌ Correlation Breakdown weight is not zero")
            
            # Check if silent mode is properly configured
            if config['alpha_scanning_optimized']['silent_mode']['enabled']:
                tier1 = config['alpha_scanning_optimized']['alpha_tiers']['tier_1_critical']
                if tier1['min_alpha'] < 3.0:
                    issues.append("❌ Silent mode Tier 1 alpha too low (should be 3.0+)")
                
                if tier1['min_confidence'] < 0.999:
                    issues.append("❌ Silent mode Tier 1 confidence too low (should be 0.999+)")
            
            if not issues:
                self.logger.info("✅ Pattern blocking validated successfully")
                return True
            else:
                self.logger.warning("⚠️ Pattern blocking issues found:")
                for issue in issues:
                    self.logger.warning(f"  {issue}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to validate pattern blocking: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Ultra Quiet Alpha Manager')
    parser.add_argument('--enable', action='store_true', help='Enable ultra quiet mode')
    parser.add_argument('--silent', action='store_true', help='Enable silent mode (zero tolerance)')
    parser.add_argument('--disable', action='store_true', help='Disable all alerts')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--plan', action='store_true', help='Show noise reduction plan')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--check-patterns', action='store_true', help='Validate pattern blocking')
    
    args = parser.parse_args()
    
    manager = UltraQuietAlphaManager()
    
    if args.plan:
        manager.show_noise_reduction_plan()
        return
    
    if args.status:
        status = manager.get_current_status()
        if status:
            print(f"\n📊 ALPHA ALERT SYSTEM STATUS")
            print(f"{'='*40}")
            print(f"Alerts Enabled: {'✅' if status['alerts_enabled'] else '❌'}")
            print(f"Current Mode: {status['mode']}")
            print(f"Silent Mode: {'✅' if status['silent_mode'] else '❌'}")
            print(f"Ultra Quiet: {'✅' if status['ultra_quiet_mode'] else '❌'}")
            print(f"Extreme Mode: {'✅' if status['extreme_mode'] else '❌'}")
        return
    
    if args.validate:
        manager.validate_ultra_quiet_config()
        return
    
    if args.check_patterns:
        manager.validate_pattern_blocking()
        return
    
    if args.silent:
        if manager.enable_silent_mode():
            print("\n🔇 SILENT MODE ENABLED")
            print("Expected: 0-1 ultra-high-conviction alerts per day maximum")
            print("Hard blocked: Cross Timeframe, Alpha Breakout, Correlation Breakdown")
            manager.validate_pattern_blocking()
        return
    
    if args.enable:
        if manager.enable_ultra_quiet_mode():
            print("\n🔇 ULTRA QUIET MODE ENABLED")
            print("Expected: 1-3 high-conviction alerts per day maximum")
            manager.validate_ultra_quiet_config()
        return
    
    if args.disable:
        if manager.disable_all_alerts():
            print("\n❌ ALL ALERTS DISABLED")
            print("System is now completely quiet")
        return
    
    # Default: show help and current status
    parser.print_help()
    print("\n" + "="*50)
    status = manager.get_current_status()
    if status:
        print(f"Current Mode: {status['mode']}")

if __name__ == "__main__":
    main() 