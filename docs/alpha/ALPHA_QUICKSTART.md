# ⚡ Alpha Opportunity Monitoring - Quick Start

## 🚀 **Ready to Monitor!**

Your enhanced multi-timeframe alpha scanner is configured and ready. Here's how to start monitoring real-time alpha opportunities immediately.

---

## 📊 **What's Configured**

✅ **Alpha scanning enabled**: Every 15 minutes  
✅ **All timeframes active**: 1m, 5m, 30m, 4h  
✅ **Performance tiers**: Ultra-fast, Fast, Stable  
✅ **Timeframe-specific thresholds**: Optimized for each timeframe  
✅ **Discord alerts**: Ready for real-time notifications  

---

## 🎯 **Start Monitoring Now**

### **Option 1: Quick Test (Recommended First)**
```bash
# Test the enhanced alpha scanner
python tests/test_enhanced_alpha_scanner.py
```

### **Option 2: Production Alpha Monitor**
```bash
# Create logs directory
mkdir -p logs

# Start dedicated alpha monitoring
python scripts/monitor_alpha_opportunities.py
```

### **Option 3: Full System with Alpha Integration**
```bash
# Start complete monitoring system (includes alpha scanning)
python main.py
```

---

## 📱 **Discord Alert Examples**

You'll receive alerts like these:

### **🔥 Ultra-Fast Alert (1m/5m timeframes)**
```
🔥 ALPHA OPPORTUNITY - ULTRA_FAST PRIORITY

Symbol: ETHUSDT
Pattern: CORRELATION_BREAKDOWN  
Confidence: 85% | Alpha: 3.2%
Duration: 30m | Risk: High

💡 ETHUSDT correlation breakdown on ltf, base
📋 Action: Consider ETHUSDT for independent movement
⏰ Entry: Volume confirmation, Technical setup
```

### **⚡ Fast Alert (30m timeframe)**
```
⚡ ALPHA OPPORTUNITY - FAST PRIORITY

Symbol: SOLUSDT  
Pattern: BETA_EXPANSION
Confidence: 78% | Alpha: 4.1%
Duration: 1h 30m | Risk: Medium

💡 SOLUSDT beta expansion on mtf (β=2.3)
📋 Action: Consider SOLUSDT for momentum play
⏰ Entry: Momentum confirmation, Volume spike
```

### **📈 Stable Alert (4h timeframe)**
```
📈 ALPHA OPPORTUNITY - STABLE PRIORITY

Symbol: ADAUSDT
Pattern: ALPHA_BREAKOUT
Confidence: 72% | Alpha: 5.8%  
Duration: 6h 0m | Risk: Medium

💡 ADAUSDT alpha breakout 5.8% on htf
📋 Action: Consider ADAUSDT for alpha generation
⏰ Entry: Alpha trend confirmation, Technical setup
```

---

## ⚡ **Trading Response Times**

- **🔥 Ultra-Fast**: Act within **5-15 minutes** (scalping opportunities)
- **⚡ Fast**: Act within **15-30 minutes** (momentum plays)  
- **📈 Stable**: Act within **30-60 minutes** (swing trades)

---

## 🔧 **Quick Commands**

### **Check Status**
```bash
# Verify configuration
python -c "import yaml; config=yaml.safe_load(open('config/config.yaml')); print('Alpha enabled:', config['alpha_scanning']['enabled'])"

# Test imports
python -c "from src.monitoring.alpha_scanner import AlphaOpportunityScanner; print('✅ Ready')"
```

### **Test Discord Webhook**
```bash
# Ensure your .env has DISCORD_WEBHOOK_URL set
echo $DISCORD_WEBHOOK_URL

# Test alert (replace with your actual webhook)
python -c "
import asyncio, yaml, logging
from src.monitoring.alert_manager import AlertManager

async def test():
    config = yaml.safe_load(open('config/config.yaml'))
    alert = AlertManager(config, logging.getLogger())
    await alert.send_alpha_opportunity_alert({
        'symbol': 'TEST', 'type': 'test', 'confidence': 0.85,
        'alpha_potential': 0.03, 'risk_level': 'Test', 
        'expected_duration': '30m', 'trading_insight': 'Test alert',
        'recommended_action': 'Test - ultra_fast priority',
        'timeframe_signals': {'ltf': 0.12}
    })
    print('✅ Test alert sent')

asyncio.run(test())
"
```

---

## 📈 **What You'll See**

### **Console Output Example**
```
🚀 Starting Alpha Opportunity Monitor
============================================================
✅ Alpha scanning configuration loaded:
   Scan interval: 15 minutes
   Timeframes: ['htf', 'mtf', 'ltf', 'base']
   Performance tiers: {'ultra_fast': ['base', 'ltf'], 'fast': ['mtf'], 'stable': ['htf']}

🔍 Starting real-time alpha opportunity monitoring...
⏰ Scanning every 15 minutes
📊 Monitoring for:
   🔥 Ultra-fast opportunities (1m, 5m timeframes)
   ⚡ Fast opportunities (30m timeframe)
   📈 Stable opportunities (4h timeframe)
------------------------------------------------------------

🔍 Alpha Scan #1 - 14:32:15 UTC
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

---

## 🎯 **Ready to Trade Alpha Opportunities!**

Your system is now configured to:

1. **Scan every 15 minutes** for alpha opportunities
2. **Detect across all timeframes** (1m, 5m, 30m, 4h)  
3. **Prioritize by urgency** (ultra_fast, fast, stable)
4. **Send Discord alerts** with actionable insights
5. **Provide trading parameters** for each opportunity

### **Start monitoring now:**
```bash
python scripts/monitor_alpha_opportunities.py
```

**Happy alpha hunting! 🎯** 