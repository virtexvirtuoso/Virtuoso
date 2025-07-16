#!/usr/bin/env python3
"""
Test implementation of PrettyTable formatting for Market Reporter.

This script demonstrates how to improve the Market Reporter's table formatting
using PrettyTable instead of manual string formatting.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from prettytable import PrettyTable
except ImportError:
    print("PrettyTable not available. Please install: pip install prettytable")
    PrettyTable = None

import datetime
from typing import List, Tuple, Dict, Any

class MarketReporterPrettyTable:
    """
    Enhanced Market Reporter with PrettyTable formatting.
    
    This class demonstrates how to improve table formatting in the market reporter
    using PrettyTable for cleaner, more professional output.
    """
    
    # ANSI color codes
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    def __init__(self):
        self.use_pretty_table = bool(PrettyTable)
    
    def _format_number(self, number):
        """Format number for display with K, M, B suffix."""
        try:
            if number is None:
                return "0"
            
            number = float(number)
            abs_number = abs(number)
            
            if abs_number >= 1_000_000_000:
                return f"{number/1_000_000_000:.2f}B"
            elif abs_number >= 1_000_000:
                return f"{number/1_000_000:.2f}M"
            elif abs_number >= 1_000:
                return f"{number/1_000:.2f}K"
            else:
                return f"{number:.2f}"
        except (ValueError, TypeError):
            return "0"
    
    def _get_score_color(self, score):
        """Get color based on score value."""
        if score >= 70:
            return self.GREEN
        elif score >= 45:
            return self.YELLOW
        else:
            return self.RED
    
    def _create_gauge(self, score, width=15):
        """Create a visual gauge for the score."""
        score = max(0, min(100, score))
        filled = int((score / 100) * width)
        
        if score >= 70:
            fill_char = "█"
            color = self.GREEN
        elif score >= 45:
            fill_char = "▓"
            color = self.YELLOW
        else:
            fill_char = "░"
            color = self.RED
        
        gauge = color + fill_char * filled + "·" * (width - filled) + self.RESET
        return gauge
    
    def format_market_performance_table(self, winners: List[Tuple], losers: List[Tuple]) -> str:
        """Format market performance data using PrettyTable."""
        if not self.use_pretty_table:
            return self._format_market_performance_legacy(winners, losers)
        
        output = []
        
        # Top Performers Table
        if winners:
            winners_table = PrettyTable()
            winners_table.field_names = ["Rank", "Symbol", "Change %", "Volume", "Open Interest", "Price"]
            winners_table.align = "l"
            winners_table.align["Change %"] = "r"
            winners_table.align["Volume"] = "r"
            winners_table.align["Open Interest"] = "r"
            winners_table.align["Price"] = "r"
            winners_table.align["Rank"] = "c"
            
            for i, (change, entry, symbol, price) in enumerate(winners[:5], 1):
                # Parse entry string: "SYMBOL +X.X% | Vol: XXX | OI: XXX"
                parts = entry.split(' | ')
                change_str = f"{self.GREEN}{change:+.2f}%{self.RESET}"
                vol_str = parts[1].replace('Vol: ', '') if len(parts) > 1 else "N/A"
                oi_str = parts[2].replace('OI: ', '') if len(parts) > 2 else "N/A"
                price_str = f"${price:,.2f}" if price > 1 else f"${price:.4f}"
                
                winners_table.add_row([
                    f"#{i}",
                    f"{self.BOLD}{symbol}{self.RESET}",
                    change_str,
                    vol_str,
                    oi_str,
                    price_str
                ])
            
            output.append(f"{self.BOLD}{self.GREEN}📈 TOP PERFORMERS{self.RESET}")
            output.append(str(winners_table))
        
        # Biggest Losers Table
        if losers:
            losers_table = PrettyTable()
            losers_table.field_names = ["Rank", "Symbol", "Change %", "Volume", "Open Interest", "Price"]
            losers_table.align = "l"
            losers_table.align["Change %"] = "r"
            losers_table.align["Volume"] = "r"
            losers_table.align["Open Interest"] = "r"
            losers_table.align["Price"] = "r"
            losers_table.align["Rank"] = "c"
            
            for i, (change, entry, symbol, price) in enumerate(losers[:5], 1):
                parts = entry.split(' | ')
                change_str = f"{self.RED}{change:+.2f}%{self.RESET}"
                vol_str = parts[1].replace('Vol: ', '') if len(parts) > 1 else "N/A"
                oi_str = parts[2].replace('OI: ', '') if len(parts) > 2 else "N/A"
                price_str = f"${price:,.2f}" if price > 1 else f"${price:.4f}"
                
                losers_table.add_row([
                    f"#{i}",
                    f"{self.BOLD}{symbol}{self.RESET}",
                    change_str,
                    vol_str,
                    oi_str,
                    price_str
                ])
            
            output.append(f"\n{self.BOLD}{self.RED}📉 BIGGEST LOSERS{self.RESET}")
            output.append(str(losers_table))
        
        return "\n".join(output)
    
    def format_smart_money_table(self, smart_money_data: Dict[str, Any]) -> str:
        """Format Smart Money Index data using PrettyTable."""
        if not self.use_pretty_table:
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
        
        table.add_row([
            "Market Bias",
            smart_money_data.get('bias', 'NEUTRAL'),
            smart_money_data.get('confidence', 'MEDIUM'),
            "🎯"
        ])
        
        return f"""
{self.BOLD}{self.CYAN}🧠 SMART MONEY ANALYSIS{self.RESET}
{table}
"""
    
    def format_whale_activity_table(self, whale_data: Dict[str, Any]) -> str:
        """Format whale activity data using PrettyTable."""
        if not self.use_pretty_table:
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
                dt = datetime.datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
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
    
    def format_futures_premium_table(self, premium_data: Dict[str, Any]) -> str:
        """Format futures premium data using PrettyTable."""
        if not self.use_pretty_table:
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
    
    def format_analysis_dashboard_table(self, analysis_result: Dict[str, Any], symbol_str: str) -> str:
        """Format analysis dashboard using PrettyTable."""
        if not self.use_pretty_table:
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
    
    # Legacy formatting methods (fallbacks)
    def _format_market_performance_legacy(self, winners, losers):
        """Legacy market performance formatting."""
        output = []
        
        if winners:
            output.append("📈 TOP PERFORMERS:")
            output.append("-" * 50)
            for i, (change, entry, symbol, price) in enumerate(winners[:5], 1):
                output.append(f"{i}. {entry}")
        
        if losers:
            output.append("\n📉 BIGGEST LOSERS:")
            output.append("-" * 50)
            for i, (change, entry, symbol, price) in enumerate(losers[:5], 1):
                output.append(f"{i}. {entry}")
        
        return "\n".join(output)
    
    def _format_smart_money_legacy(self, smart_money_data):
        """Legacy smart money formatting."""
        return f"""
🧠 SMART MONEY ANALYSIS
Smart Money Index: {smart_money_data.get('index', 50.0):.1f}/100
Sentiment: {smart_money_data.get('sentiment', 'NEUTRAL')}
Institutional Flow: {smart_money_data.get('institutional_flow', '0.0%')}
"""
    
    def _format_whale_activity_legacy(self, whale_data):
        """Legacy whale activity formatting."""
        transactions = whale_data.get('transactions', [])
        if not transactions:
            return "🐋 WHALE ACTIVITY\nNo significant whale activity detected"
        
        output = ["🐋 WHALE ACTIVITY"]
        for tx in transactions[:5]:
            symbol = tx.get('symbol', 'Unknown')
            side = tx.get('side', 'unknown').upper()
            usd_value = self._format_number(tx.get('usd_value', 0))
            output.append(f"{symbol} {side} ${usd_value}")
        
        return "\n".join(output)
    
    def _format_futures_premium_legacy(self, premium_data):
        """Legacy futures premium formatting."""
        premiums = premium_data.get('premiums', {})
        if not premiums:
            return "⚡ FUTURES PREMIUM\nNo premium data available"
        
        output = ["⚡ FUTURES PREMIUM"]
        for symbol, data in list(premiums.items())[:5]:
            premium_pct = data.get('premium_percentage', 0)
            output.append(f"{symbol}: {premium_pct:+.2f}%")
        
        return "\n".join(output)
    
    def _format_analysis_dashboard_legacy(self, analysis_result, symbol_str):
        """Legacy analysis dashboard formatting."""
        score = analysis_result.get('confluence_score', 0)
        components = analysis_result.get('components', {})
        
        output = [f"ANALYSIS DASHBOARD FOR {symbol_str}"]
        output.append(f"Overall Score: {score:.2f}")
        output.append("-" * 40)
        
        for name, comp_score in components.items():
            display_name = name.replace('_', ' ').title()
            output.append(f"{display_name}: {comp_score:.2f}")
        
        return "\n".join(output)


def create_sample_data():
    """Create sample data for testing."""
    
    # Market performance data
    winners = [
        (8.5, "BTCUSDT +8.5% | Vol: 2.1B | OI: 1.2B", "BTCUSDT", 45000),
        (6.2, "ETHUSDT +6.2% | Vol: 1.8B | OI: 900M", "ETHUSDT", 3200),
        (5.8, "ADAUSDT +5.8% | Vol: 450M | OI: 300M", "ADAUSDT", 0.52),
        (4.3, "SOLUSDT +4.3% | Vol: 680M | OI: 400M", "SOLUSDT", 98.5),
        (3.9, "DOTUSDT +3.9% | Vol: 320M | OI: 200M", "DOTUSDT", 6.8)
    ]
    
    losers = [
        (-5.2, "LINKUSDT -5.2% | Vol: 380M | OI: 250M", "LINKUSDT", 14.2),
        (-4.8, "AVAXUSDT -4.8% | Vol: 290M | OI: 180M", "AVAXUSDT", 28.5),
        (-3.6, "MATICUSDT -3.6% | Vol: 220M | OI: 150M", "MATICUSDT", 0.89),
        (-2.9, "LTCUSDT -2.9% | Vol: 180M | OI: 120M", "LTCUSDT", 95.2),
        (-2.1, "BCHUSDT -2.1% | Vol: 160M | OI: 100M", "BCHUSDT", 245.8)
    ]
    
    # Smart money data
    smart_money_data = {
        'index': 72.5,
        'sentiment': 'BULLISH',
        'institutional_flow': '+3.2%',
        'bias': 'LONG',
        'confidence': 'HIGH'
    }
    
    # Whale activity data
    whale_data = {
        'transactions': [
            {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'amount': 125.5,
                'usd_value': 5647500,
                'timestamp': 1640995200000
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'sell',
                'amount': 850.2,
                'usd_value': 2720640,
                'timestamp': 1640995100000
            },
            {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'amount': 89.3,
                'usd_value': 4018500,
                'timestamp': 1640995000000
            }
        ]
    }
    
    # Futures premium data
    premium_data = {
        'premiums': {
            'BTCUSDT': {
                'spot_price': 45000,
                'futures_price': 45450,
                'premium_percentage': 1.0
            },
            'ETHUSDT': {
                'spot_price': 3200,
                'futures_price': 3248,
                'premium_percentage': 1.5
            },
            'SOLUSDT': {
                'spot_price': 98.5,
                'futures_price': 102.1,
                'premium_percentage': 3.7
            }
        }
    }
    
    # Analysis data
    analysis_result = {
        'confluence_score': 68.5,
        'reliability': 0.85,
        'components': {
            'technical': 75.2,
            'volume': 68.8,
            'orderflow': 72.1,
            'sentiment': 65.3,
            'orderbook': 58.9,
            'price_structure': 63.7
        }
    }
    
    return winners, losers, smart_money_data, whale_data, premium_data, analysis_result


def test_prettytable_formatting():
    """Test all PrettyTable formatting methods."""
    
    print("=" * 100)
    print("MARKET REPORTER PRETTYTABLE FORMATTING TEST")
    print("=" * 100)
    
    # Create formatter
    formatter = MarketReporterPrettyTable()
    
    # Get sample data
    winners, losers, smart_money_data, whale_data, premium_data, analysis_result = create_sample_data()
    
    print(f"\nPrettyTable Available: {formatter.use_pretty_table}")
    print("=" * 50)
    
    # Test Market Performance Table
    print("\n1. MARKET PERFORMANCE TABLE")
    print("-" * 50)
    performance_table = formatter.format_market_performance_table(winners, losers)
    print(performance_table)
    
    # Test Smart Money Table
    print("\n\n2. SMART MONEY TABLE")
    print("-" * 50)
    smart_money_table = formatter.format_smart_money_table(smart_money_data)
    print(smart_money_table)
    
    # Test Whale Activity Table
    print("\n\n3. WHALE ACTIVITY TABLE")
    print("-" * 50)
    whale_table = formatter.format_whale_activity_table(whale_data)
    print(whale_table)
    
    # Test Futures Premium Table
    print("\n\n4. FUTURES PREMIUM TABLE")
    print("-" * 50)
    premium_table = formatter.format_futures_premium_table(premium_data)
    print(premium_table)
    
    # Test Analysis Dashboard Table
    print("\n\n5. ANALYSIS DASHBOARD TABLE")
    print("-" * 50)
    dashboard_table = formatter.format_analysis_dashboard_table(analysis_result, "BTCUSDT")
    print(dashboard_table)
    
    print("\n" + "=" * 100)
    print("ALL TESTS COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    test_prettytable_formatting() 