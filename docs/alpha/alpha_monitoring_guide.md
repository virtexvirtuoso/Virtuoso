# 🚀 Real-Time Alpha Opportunity Monitoring Guide

## Overview

This guide shows you how to monitor real-time alpha opportunities using the enhanced multi-timeframe alpha scanner. You'll receive actionable trading alerts with different priority levels for optimal timing.

## 📊 **What You'll Monitor**

### **Performance Tiers**
- **🔥 Ultra-Fast** (1m, 5m): Immediate scalping opportunities (15-30 min duration)
- **⚡ Fast** (30m): Short-term momentum plays (1-2 hour duration)  
- **📈 Stable** (4h): Confirmed trend opportunities (4-6 hour duration)

### **Alpha Patterns**
1. **Correlation Breakdown**: Asset moving independently from Bitcoin
2. **Beta Expansion**: Asset showing amplified moves vs Bitcoin
3. **Alpha Breakout**: Asset generating consistent excess returns

---

## 🎯 **Setup Instructions**

### **1. Discord Alert Setup**

1. **Create Discord Webhook** (if not done):
   ```bash
   # In your Discord server:
   # Server Settings → Integrations → Webhooks → New Webhook
   # Copy the webhook URL
   ```

2. **Configure Environment Variables**:
   ```bash
   # Add to your .env file:
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
   SYSTEM_ALERTS_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_SYSTEM_WEBHOOK_URL
   ```

3. **Verify Alert Configuration**:
   ```yaml
   # In config/config.yaml:
   monitoring:
     alerts:
       enabled: true
       discord_webhook_url: ${DISCORD_WEBHOOK_URL}
   
   alpha_scanning:
     alerts:
       enabled: true
       cooldown_minutes: 60
       max_alerts_per_scan: 3
   ```

### **2. Start Alpha Monitoring**

#### **Option A: Production Monitoring Script**
```bash
# Start the dedicated alpha monitor
python scripts/monitor_alpha_opportunities.py
```

#### **Option B: Full System with Alpha Scanning**
```bash
# Start the complete monitoring system
python main.py
```

#### **Option C: Background Service**
```bash
# Run as background service
nohup python scripts/monitor_alpha_opportunities.py > logs/alpha_monitor.log 2>&1 &
```

---

## 📨 **Understanding Discord Alerts**

### **Alert Format**
```
🔥 ALPHA OPPORTUNITY - ULTRA_FAST PRIORITY

Symbol: ETHUSDT
Pattern: CORRELATION_BREAKDOWN
Confidence: 85%
Alpha Potential: 3.2%
Risk Level: High
Duration: 30m

💡 Insight: ETHUSDT correlation breakdown detected on ltf (strongest: ltf, priority: ultra_fast)
📋 Action: Consider ETHUSDT for independent movement - ultra_fast priority

🎯 Signals: ltf:0.12, base:0.08
⏰ Entry: Volume confirmation, Technical setup, Momentum validation
🚪 Exit: Correlation recovery, Technical breakdown, Time-based exit
```

### **Priority Interpretation**

#### **🔥 Ultra-Fast Priority** (Act within 5-15 minutes)
- **Timeframes**: 1m, 5m
- **Duration**: 15-30 minutes
- **Risk**: High (but quick)
- **Strategy**: Scalping, quick entries/exits
- **Position Size**: Smaller (higher risk)

#### **⚡ Fast Priority** (Act within 15-30 minutes) 
- **Timeframes**: 30m
- **Duration**: 1-2 hours
- **Risk**: Medium-High
- **Strategy**: Short-term momentum trading
- **Position Size**: Standard

#### **📈 Stable Priority** (Act within 30-60 minutes)
- **Timeframes**: 4h
- **Duration**: 4-6 hours
- **Risk**: Medium
- **Strategy**: Swing trading, trend following
- **Position Size**: Larger (more confirmed)

---

## 💹 **Trading Guidelines**

### **Entry Strategy by Priority**

#### **Ultra-Fast Opportunities (1m/5m)**
```
1. Receive alert → Immediately check charts
2. Confirm volume spike and momentum
3. Enter within 5-15 minutes of alert
4. Use tight stops (1-2%)
5. Take profits quickly (2-5% targets)
6. Monitor for 15-30 minutes max
```

#### **Fast Opportunities (30m)**
```
1. Receive alert → Check within 15 minutes
2. Wait for technical confirmation
3. Enter on breakout/momentum continuation
4. Use moderate stops (2-3%)
5. Target 3-7% moves
6. Hold for 1-2 hours
```

#### **Stable Opportunities (4h)**
```
1. Receive alert → Analyze within 30-60 minutes
2. Wait for proper setup and confirmation
3. Enter on pullbacks or breakouts
4. Use wider stops (3-5%)
5. Target 5-15% moves
6. Hold for 4-6+ hours
```

### **Risk Management Rules**

1. **Position Sizing**:
   - Ultra-Fast: 0.5-1% of portfolio
   - Fast: 1-2% of portfolio  
   - Stable: 2-5% of portfolio

2. **Stop Losses**:
   - Always use stops based on priority level
   - Ultra-Fast: 1-2% stops
   - Fast: 2-3% stops
   - Stable: 3-5% stops

3. **Profit Taking**:
   - Scale out at resistance levels
   - Take partial profits at 50% of target
   - Trail stops on winning positions

---

## 📈 **Monitoring Dashboard**

### **Real-Time Monitoring Output**
```
🔍 Alpha Scan #45 - 14:32:15 UTC
🎯 Found 2 actionable alpha opportunities:

   🔥 #1: ETHUSDT - CORRELATION_BREAKDOWN
      Confidence: 85% | Alpha: 3.2% | Risk: High
      Duration: 30m | Priority: ULTRA_FAST
      💡 ETHUSDT correlation breakdown detected on ltf, base
      📋 Action: Consider ETHUSDT for independent movement - ultra_fast priority
      🎯 Signals: ltf:0.12, base:0.08

   ⚡ #2: SOLUSDT - BETA_EXPANSION  
      Confidence: 78% | Alpha: 4.1% | Risk: Medium
      Duration: 1h 30m | Priority: FAST
      💡 SOLUSDT beta expansion on mtf (β=2.3)
      📋 Action: Consider SOLUSDT for momentum play - fast priority
      🎯 Signals: mtf:2.31

   Scan completed in 1.2s
```

### **Statistics Tracking**
```
📊 ALPHA MONITORING STATISTICS
============================================================
Total Scans: 45
Total Opportunities: 23
Alerts Sent: 18
Average per Scan: 0.5

📈 Priority Distribution:
   Ultra_fast: 8 (34.8%)
   Fast: 10 (43.5%)
   Stable: 5 (21.7%)

⚙️ Scanner Settings:
   Interval: 15 minutes
   Timeframes: ['htf', 'mtf', 'ltf', 'base']
   Patterns: ['correlation_breakdown', 'beta_expansion', 'alpha_breakout']
```

---

## ⚡ **Quick Start Commands**

### **Start Monitoring**
```bash
# Create logs directory
mkdir -p logs

# Start alpha monitoring
python scripts/monitor_alpha_opportunities.py
```

### **Check Configuration**
```bash
# Verify alpha scanning is enabled
python -c "
import yaml
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)
alpha_config = config.get('alpha_scanning', {})
print(f'Alpha scanning enabled: {alpha_config.get(\"enabled\", False)}')
print(f'Scan interval: {alpha_config.get(\"interval_minutes\", 15)} minutes')
print(f'Timeframes: {alpha_config.get(\"timeframes\", [])}')
"
```

### **Test Discord Alerts**
```bash
# Test Discord webhook connectivity
python -c "
import asyncio
import yaml
from src.monitoring.alert_manager import AlertManager
import logging

async def test_alert():
    with open('config/config.yaml') as f:
        config = yaml.safe_load(f)
    
    alert_manager = AlertManager(config, logging.getLogger())
    
    test_data = {
        'symbol': 'TESTUSDT',
        'type': 'correlation_breakdown', 
        'confidence': 0.85,
        'alpha_potential': 0.032,
        'risk_level': 'High',
        'expected_duration': '30m',
        'trading_insight': 'Test alpha opportunity detected',
        'recommended_action': 'Test alert - ultra_fast priority',
        'timeframe_signals': {'ltf': 0.12},
        'entry_conditions': ['Test entry'],
        'exit_conditions': ['Test exit']
    }
    
    await alert_manager.send_alpha_opportunity_alert(test_data)
    print('✅ Test alert sent successfully')

asyncio.run(test_alert())
"
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

1. **No Alerts Received**:
   ```bash
   # Check webhook URL is correct
   echo $DISCORD_WEBHOOK_URL
   
   # Verify alpha scanning is enabled
   grep -A 5 "alpha_scanning:" config/config.yaml
   ```

2. **Too Many/Few Alerts**:
   ```yaml
   # Adjust thresholds in config/config.yaml
   alpha_scanning:
     thresholds:
       min_confidence: 0.75  # Increase to reduce alerts
     alerts:
       max_alerts_per_scan: 3  # Limit per scan
       cooldown_minutes: 60    # Increase to reduce frequency
   ```

3. **Missing Dependencies**:
   ```bash
   # Install required packages
   pip install -r requirements.txt
   
   # Check imports
   python -c "from src.monitoring.alpha_scanner import AlphaOpportunityScanner"
   ```

### **Log Files**
- **Alpha Monitor**: `logs/alpha_monitor.log`
- **Main System**: `logs/app.log`
- **Indicators**: `logs/indicators.log`

---

## 📞 **Support**

For issues or questions:
1. Check log files for error messages
2. Verify configuration settings
3. Test Discord webhook connectivity
4. Ensure all dependencies are installed

**Happy Alpha Hunting! 🎯** 