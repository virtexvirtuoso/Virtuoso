# PrettyTable Expansion Opportunities

## Overview

Based on comprehensive analysis of the codebase, there are numerous opportunities to improve data presentation using PrettyTable formatting. This document outlines priority areas and implementation strategies.

## 🎯 **Priority Implementation Areas**

### **1. Market Reporter Tables (HIGH PRIORITY)**
**Files**: `src/monitoring/market_reporter.py`, `src/monitoring/enhanced_market_report.py`

#### Current Issues:
- Manual string formatting for performance data
- Inconsistent table layouts
- Hard to read market summaries

#### Current Code Example:
```python
# Current implementation in _format_analysis_results
component_table = "\nCOMPONENT SCORES:\n"
component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"
component_table += f"| {'Component':<23} | {'Score':<8} | {'Visual':<20} |\n"
component_table += f"+{'-' * 25}+{'-' * 10}+{'-' * 22}+\n"

# Add components to table
for name, value in components.items():
    color = get_color_code(comp_score)
    component_table += f"| {name:<23} | {color}{comp_score:<8.2f}{reset_code} | {create_gauge(comp_score):<20} |\n"
```

#### PrettyTable Implementation:
```python
def format_market_performance_table(self, winners, losers):
    """Format market performance data using PrettyTable."""
    if not PrettyTable:
        return self._format_market_performance_legacy(winners, losers)
    
    # Top Performers Table
    winners_table = PrettyTable()
    winners_table.field_names = ["Symbol", "Change %", "Volume", "Open Interest"]
    winners_table.align = "l"
    winners_table.align["Change %"] = "r"
    winners_table.align["Volume"] = "r"
    winners_table.align["Open Interest"] = "r"
    
    for change, entry, symbol, price in winners[:5]:
        # Extract data from entry string
        parts = entry.split(' | ')
        change_str = f"{self.GREEN}{change:+.2f}%{self.RESET}"
        vol_str = parts[1].replace('Vol: ', '') if len(parts) > 1 else "N/A"
        oi_str = parts[2].replace('OI: ', '') if len(parts) > 2 else "N/A"
        
        winners_table.add_row([symbol, change_str, vol_str, oi_str])
    
    # Losers Table
    losers_table = PrettyTable()
    losers_table.field_names = ["Symbol", "Change %", "Volume", "Open Interest"]
    losers_table.align = "l"
    losers_table.align["Change %"] = "r"
    losers_table.align["Volume"] = "r"
    losers_table.align["Open Interest"] = "r"
    
    for change, entry, symbol, price in losers[:5]:
        parts = entry.split(' | ')
        change_str = f"{self.RED}{change:+.2f}%{self.RESET}"
        vol_str = parts[1].replace('Vol: ', '') if len(parts) > 1 else "N/A"
        oi_str = parts[2].replace('OI: ', '') if len(parts) > 2 else "N/A"
        
        losers_table.add_row([symbol, change_str, vol_str, oi_str])
    
    return f"""
{self.BOLD}📈 TOP PERFORMERS{self.RESET}
{winners_table}

{self.BOLD}📉 BIGGEST LOSERS{self.RESET}
{losers_table}
"""
```

### **2. Analysis Dashboard Tables (HIGH PRIORITY)**
**Files**: `src/monitoring/monitor.py`, `src/core/formatting.py`

#### Current Issues:
- Complex manual table construction
- Inconsistent alignment and spacing
- Hard to maintain formatting code

#### PrettyTable Implementation:
```python
def format_analysis_dashboard_table(self, analysis_result, symbol_str):
    """Format analysis dashboard using PrettyTable."""
    if not PrettyTable:
        return self._format_analysis_dashboard_legacy(analysis_result, symbol_str)
    
    score = analysis_result.get('confluence_score', 0)
    reliability = analysis_result.get('reliability', 0)
    components = analysis_result.get('components', {})
    
    # Main analysis table
    table = PrettyTable()
    table.field_names = ["Component", "Score", "Status", "Gauge"]
    table.align = "l"
    table.align["Score"] = "r"
    table.align["Status"] = "c"
    
    # Add overall score
    overall_status = "BULLISH" if score >= 70 else "NEUTRAL" if score >= 45 else "BEARISH"
    overall_color = self._get_score_color(score)
    overall_gauge = self._create_gauge(score, 15)
    
    table.add_row([
        f"{self.BOLD}OVERALL CONFLUENCE{self.RESET}",
        f"{overall_color}{score:.2f}{self.RESET}",
        f"{overall_color}{overall_status}{self.RESET}",
        overall_gauge
    ])
    
    # Add separator row
    table.add_row(["-" * 20, "-" * 8, "-" * 10, "-" * 15])
    
    # Add component scores
    for name, comp_score in sorted(components.items(), key=lambda x: x[1], reverse=True):
        display_name = name.replace('_', ' ').title()
        status = "STRONG" if comp_score >= 70 else "NEUTRAL" if comp_score >= 45 else "WEAK"
        color = self._get_score_color(comp_score)
        gauge = self._create_gauge(comp_score, 15)
        
        table.add_row([
            display_name,
            f"{color}{comp_score:.2f}{self.RESET}",
            f"{color}{status}{self.RESET}",
            gauge
        ])
    
    # Header with timestamp
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f"""
{self.BOLD}{self.CYAN}ANALYSIS DASHBOARD FOR {symbol_str}{self.RESET}
{self.BOLD}Generated: {timestamp} | Reliability: {reliability:.1%}{self.RESET}
{'=' * 70}

{table}

{'=' * 70}
"""
    
    return header
```

### **3. Smart Money Index Tables (MEDIUM PRIORITY)**
**Files**: `src/monitoring/market_reporter.py`

#### PrettyTable Implementation:
```python
def format_smart_money_table(self, smart_money_data):
    """Format Smart Money Index data using PrettyTable."""
    if not PrettyTable:
        return self._format_smart_money_legacy(smart_money_data)
    
    table = PrettyTable()
    table.field_names = ["Metric", "Value", "Status", "Trend"]
    table.align = "l"
    table.align["Value"] = "r"
    table.align["Status"] = "c"
    table.align["Trend"] = "c"
    
    smi_value = smart_money_data.get('index', 50.0)
    sentiment = smart_money_data.get('sentiment', 'NEUTRAL')
    flow = smart_money_data.get('institutional_flow', '0.0%')
    
    # Determine colors and indicators
    smi_color = self.GREEN if smi_value >= 60 else self.YELLOW if smi_value >= 40 else self.RED
    sentiment_color = self.GREEN if sentiment == 'BULLISH' else self.RED if sentiment == 'BEARISH' else self.YELLOW
    trend_indicator = "↑" if smi_value >= 55 else "↓" if smi_value <= 45 else "→"
    
    table.add_row([
        "Smart Money Index",
        f"{smi_color}{smi_value:.1f}/100{self.RESET}",
        f"{sentiment_color}{sentiment}{self.RESET}",
        f"{smi_color}{trend_indicator}{self.RESET}"
    ])
    
    table.add_row([
        "Institutional Flow",
        f"{flow}",
        "Active" if abs(float(flow.replace('%', ''))) > 1 else "Quiet",
        "📊"
    ])
    
    return f"""
{self.BOLD}{self.CYAN}🧠 SMART MONEY ANALYSIS{self.RESET}
{table}
"""
```

### **4. Whale Activity Tables (MEDIUM PRIORITY)**
**Files**: `src/monitoring/market_reporter.py`, `src/monitoring/alert_manager.py`

#### PrettyTable Implementation:
```python
def format_whale_activity_table(self, whale_data):
    """Format whale activity data using PrettyTable."""
    if not PrettyTable:
        return self._format_whale_activity_legacy(whale_data)
    
    transactions = whale_data.get('transactions', [])
    if not transactions:
        return f"{self.BOLD}🐋 WHALE ACTIVITY{self.RESET}\nNo significant whale activity detected"
    
    table = PrettyTable()
    table.field_names = ["Symbol", "Side", "Amount", "USD Value", "Time"]
    table.align = "l"
    table.align["Amount"] = "r"
    table.align["USD Value"] = "r"
    table.align["Side"] = "c"
    
    for tx in transactions[:10]:  # Show top 10
        symbol = tx.get('symbol', 'Unknown')
        side = tx.get('side', 'unknown').upper()
        amount = self._format_number(tx.get('amount', 0))
        usd_value = self._format_number(tx.get('usd_value', 0))
        timestamp = tx.get('timestamp', 0)
        
        # Format time
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
            time_str = dt.strftime('%H:%M:%S')
        else:
            time_str = "Unknown"
        
        # Color coding for side
        side_colored = f"{self.GREEN}BUY{self.RESET}" if side == 'BUY' else f"{self.RED}SELL{self.RESET}" if side == 'SELL' else side
        
        table.add_row([
            symbol,
            side_colored,
            amount,
            f"${usd_value}",
            time_str
        ])
    
    # Summary statistics
    total_volume = sum(tx.get('usd_value', 0) for tx in transactions)
    buy_volume = sum(tx.get('usd_value', 0) for tx in transactions if tx.get('side') == 'buy')
    sell_volume = sum(tx.get('usd_value', 0) for tx in transactions if tx.get('side') == 'sell')
    net_flow = buy_volume - sell_volume
    
    summary = f"""
{self.BOLD}📊 WHALE ACTIVITY SUMMARY{self.RESET}
Total Volume: ${self._format_number(total_volume)}
Net Flow: {self.GREEN if net_flow > 0 else self.RED}${self._format_number(abs(net_flow))} {'BUYING' if net_flow > 0 else 'SELLING'}{self.RESET}
Transactions: {len(transactions)}
"""
    
    return f"""
{self.BOLD}🐋 WHALE ACTIVITY{self.RESET}
{table}
{summary}
"""
```

### **5. Futures Premium Tables (MEDIUM PRIORITY)**
**Files**: `src/monitoring/market_reporter.py`

#### PrettyTable Implementation:
```python
def format_futures_premium_table(self, premium_data):
    """Format futures premium data using PrettyTable."""
    if not PrettyTable:
        return self._format_futures_premium_legacy(premium_data)
    
    premiums = premium_data.get('premiums', {})
    if not premiums:
        return f"{self.BOLD}⚡ FUTURES PREMIUM{self.RESET}\nNo premium data available"
    
    table = PrettyTable()
    table.field_names = ["Symbol", "Spot Price", "Futures Price", "Premium %", "Status"]
    table.align = "l"
    table.align["Spot Price"] = "r"
    table.align["Futures Price"] = "r"
    table.align["Premium %"] = "r"
    table.align["Status"] = "c"
    
    for symbol, data in list(premiums.items())[:10]:  # Top 10
        spot_price = data.get('spot_price', 0)
        futures_price = data.get('futures_price', 0)
        premium_pct = data.get('premium_percentage', 0)
        
        # Determine status and color
        if premium_pct > 5:
            status = f"{self.RED}HIGH{self.RESET}"
        elif premium_pct > 2:
            status = f"{self.YELLOW}ELEVATED{self.RESET}"
        elif premium_pct > -2:
            status = f"{self.GREEN}NORMAL{self.RESET}"
        else:
            status = f"{self.RED}BACKWARDATION{self.RESET}"
        
        premium_colored = f"{self.GREEN if premium_pct > 0 else self.RED}{premium_pct:+.2f}%{self.RESET}"
        
        table.add_row([
            symbol,
            f"${spot_price:.2f}",
            f"${futures_price:.2f}",
            premium_colored,
            status
        ])
    
    # Calculate average premium
    avg_premium = sum(data.get('premium_percentage', 0) for data in premiums.values()) / len(premiums)
    
    summary = f"""
{self.BOLD}📊 PREMIUM SUMMARY{self.RESET}
Average Premium: {self.GREEN if avg_premium > 0 else self.RED}{avg_premium:+.2f}%{self.RESET}
Symbols Tracked: {len(premiums)}
"""
    
    return f"""
{self.BOLD}⚡ FUTURES PREMIUM ANALYSIS{self.RESET}
{table}
{summary}
"""
```

### **6. Component Breakdown Tables (LOW PRIORITY)**
**Files**: `src/core/formatting/formatter.py`

#### Current Issues:
- Nested component data is hard to read
- Inconsistent sub-component formatting

#### PrettyTable Implementation:
```python
def format_component_breakdown_table(self, components, results):
    """Format detailed component breakdown using PrettyTable."""
    if not PrettyTable:
        return self._format_component_breakdown_legacy(components, results)
    
    output = []
    
    for component_name, component_data in results.items():
        if not isinstance(component_data, dict) or 'components' not in component_data:
            continue
        
        display_name = component_name.replace('_', ' ').title()
        sub_components = component_data['components']
        
        # Create table for this component
        table = PrettyTable()
        table.field_names = ["Indicator", "Score", "Status", "Gauge"]
        table.align = "l"
        table.align["Score"] = "r"
        table.align["Status"] = "c"
        
        for sub_name, sub_score in sorted(sub_components.items(), key=lambda x: x[1], reverse=True):
            if not isinstance(sub_score, (int, float)):
                continue
            
            indicator_name = sub_name.replace('_', ' ').title()
            status = "STRONG" if sub_score >= 70 else "NEUTRAL" if sub_score >= 45 else "WEAK"
            color = self._get_score_color(sub_score)
            gauge = self._create_gauge(sub_score, 10)
            
            table.add_row([
                indicator_name,
                f"{color}{sub_score:.2f}{self.RESET}",
                f"{color}{status}{self.RESET}",
                gauge
            ])
        
        output.append(f"""
{self.BOLD}{self.CYAN}{display_name} Breakdown{self.RESET}
{table}
""")
    
    return "\n".join(output)
```

## 🔧 **Implementation Strategy**

### **Phase 1: High Priority Tables**
1. **Market Reporter Performance Tables**
   - Update `_get_performance_data()` method
   - Create `format_market_performance_table()`
   - Add fallback to legacy formatting

2. **Analysis Dashboard Tables**
   - Update `_format_analysis_results()` method
   - Create `format_analysis_dashboard_table()`
   - Maintain backward compatibility

### **Phase 2: Medium Priority Tables**
3. **Smart Money Index Tables**
4. **Whale Activity Tables**  
5. **Futures Premium Tables**

### **Phase 3: Low Priority Tables**
6. **Component Breakdown Tables**
7. **Report Summary Tables**

## 📝 **Implementation Template**

For each new PrettyTable formatter, follow this pattern:

```python
def format_[data_type]_table(self, data, use_pretty_table=True):
    """Format [data_type] using PrettyTable.
    
    Args:
        data: The data to format
        use_pretty_table: Whether to use PrettyTable (default: True)
        
    Returns:
        str: Formatted table
    """
    # Fallback check
    if not use_pretty_table or not PrettyTable:
        return self._format_[data_type]_legacy(data)
    
    # Validate data
    if not data:
        return f"{self.BOLD}[DATA_TYPE] TABLE{self.RESET}\nNo data available"
    
    # Create table
    table = PrettyTable()
    table.field_names = ["Column1", "Column2", "Column3"]
    table.align = "l"  # Set default alignment
    table.align["Column2"] = "r"  # Adjust specific columns
    
    # Populate table
    for item in data:
        # Format data with colors
        col1 = item.get('field1', 'N/A')
        col2_color = self._get_score_color(item.get('field2', 0))
        col2 = f"{col2_color}{item.get('field2', 0):.2f}{self.RESET}"
        col3 = self._create_gauge(item.get('field3', 0))
        
        table.add_row([col1, col2, col3])
    
    # Add header and summary
    header = f"{self.BOLD}{self.CYAN}[DATA_TYPE] ANALYSIS{self.RESET}"
    summary = f"Total items: {len(data)}"
    
    return f"""
{header}
{table}
{summary}
"""
```

## 🧪 **Testing Strategy**

### **Unit Tests**
Create tests for each new formatter:

```python
def test_format_market_performance_table():
    """Test market performance table formatting."""
    formatter = MarketReporter()
    
    # Test data
    winners = [(5.2, "BTCUSDT +5.2% | Vol: 1.2B | OI: 850M", "BTCUSDT", 45000)]
    losers = [(-3.1, "ETHUSDT -3.1% | Vol: 800M | OI: 600M", "ETHUSDT", 3200)]
    
    # Test PrettyTable formatting
    result = formatter.format_market_performance_table(winners, losers)
    
    assert "TOP PERFORMERS" in result
    assert "BIGGEST LOSERS" in result
    assert "BTCUSDT" in result
    assert "ETHUSDT" in result
    
    # Test fallback
    result_fallback = formatter.format_market_performance_table(winners, losers, use_pretty_table=False)
    assert result != result_fallback  # Should be different formatting
```

### **Integration Tests**
Test with real data from the monitoring system:

```python
async def test_market_reporter_integration():
    """Test market reporter with PrettyTable integration."""
    reporter = MarketReporter()
    
    # Generate real market data
    report_data = await reporter.generate_market_summary()
    
    # Test each new formatter
    performance_table = reporter.format_market_performance_table(
        report_data.get('winners', []),
        report_data.get('losers', [])
    )
    
    assert performance_table is not None
    assert len(performance_table) > 100  # Should be substantial output
```

## 📊 **Expected Benefits**

### **Code Quality**
- **Reduced Complexity**: Eliminate manual table formatting logic
- **Better Maintainability**: Easier to modify table structure
- **Consistent Styling**: All tables follow same formatting standards

### **User Experience**
- **Improved Readability**: Clean, professional table appearance
- **Better Data Scanning**: Consistent alignment and spacing
- **Enhanced Visual Hierarchy**: Clear headers and data separation

### **Development Efficiency**
- **Faster Implementation**: New tables easier to create
- **Fewer Bugs**: Automatic alignment reduces formatting errors
- **Better Testing**: Standardized table structure easier to test

## 🚀 **Getting Started**

1. **Install PrettyTable** (already done):
   ```bash
   pip install prettytable>=3.7.0
   ```

2. **Start with Market Reporter**:
   - Update `src/monitoring/market_reporter.py`
   - Implement `format_market_performance_table()`
   - Test with real market data

3. **Gradually Migrate**:
   - One table type at a time
   - Maintain backward compatibility
   - Test thoroughly before deploying

4. **Monitor Performance**:
   - Ensure PrettyTable doesn't impact performance
   - Compare output quality with stakeholders
   - Gather feedback for improvements

This comprehensive approach will significantly improve the readability and maintainability of all data tables throughout the Virtuoso trading system. 