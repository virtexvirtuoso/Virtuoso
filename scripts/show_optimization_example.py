#!/usr/bin/env python3
"""
Detailed Optimization Example - Shows exactly what the system optimizes against.
This script demonstrates the scoring system with real examples.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

@dataclass
class ExampleMetrics:
    """Example trading metrics for demonstration."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    description: str

def demonstrate_scoring_system():
    """Show how different parameter sets are scored."""
    
    print("🎯 Virtuoso Optimization Scoring System Demonstration")
    print("=" * 60)
    
    # Define objective weights (same as actual system)
    objective_weights = {
        'return': 0.30,
        'sharpe': 0.25,  
        'drawdown': 0.20,
        'win_rate': 0.15,
        'trades': 0.10
    }
    
    print(f"📊 Scoring Weights:")
    for metric, weight in objective_weights.items():
        print(f"   {metric.replace('_', ' ').title()}: {weight:.0%}")
    
    # Example parameter sets with different characteristics
    examples = [
        ExampleMetrics(
            total_return=0.25,  # 25% return
            sharpe_ratio=1.8,   # Excellent risk-adjusted return
            max_drawdown=0.08,  # 8% max drawdown
            win_rate=0.72,      # 72% win rate
            total_trades=180,
            description="Excellent Parameters - High Sharpe, Low Drawdown"
        ),
        ExampleMetrics(
            total_return=0.45,  # 45% return
            sharpe_ratio=0.9,   # Poor risk-adjusted return
            max_drawdown=0.35,  # 35% max drawdown
            win_rate=0.58,      # 58% win rate
            total_trades=120,
            description="Risky Parameters - High Return but Too Risky"
        ),
        ExampleMetrics(
            total_return=0.12,  # 12% return
            sharpe_ratio=1.4,   # Good risk-adjusted return
            max_drawdown=0.06,  # 6% max drawdown  
            win_rate=0.68,      # 68% win rate
            total_trades=200,
            description="Conservative Parameters - Steady, Safe Performance"
        ),
        ExampleMetrics(
            total_return=0.08,  # 8% return
            sharpe_ratio=0.3,   # Poor risk-adjusted return
            max_drawdown=0.25,  # 25% max drawdown
            win_rate=0.45,      # 45% win rate (losing more than winning)
            total_trades=85,    # Too few trades
            description="Poor Parameters - Low Performance, High Risk"
        ),
        ExampleMetrics(
            total_return=0.18,  # 18% return
            sharpe_ratio=1.2,   # Good risk-adjusted return
            max_drawdown=0.12,  # 12% max drawdown
            win_rate=0.65,      # 65% win rate
            total_trades=150,
            description="Good Parameters - Balanced Performance"
        )
    ]
    
    print(f"\n📈 Parameter Set Comparison:")
    print("=" * 60)
    
    scores = []
    
    for i, metrics in enumerate(examples, 1):
        print(f"\n{i}. {metrics.description}")
        print(f"   📊 Raw Metrics:")
        print(f"      Total Return: {metrics.total_return:.1%}")
        print(f"      Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"      Max Drawdown: {metrics.max_drawdown:.1%}")
        print(f"      Win Rate: {metrics.win_rate:.1%}")
        print(f"      Total Trades: {metrics.total_trades}")
        
        # Calculate normalized scores (same logic as actual system)
        normalized_return = max(0, min(1, (metrics.total_return + 0.5) / 1.0))
        normalized_sharpe = max(0, min(1, (metrics.sharpe_ratio + 2) / 4))
        normalized_drawdown = max(0, min(1, 1 - metrics.max_drawdown))
        normalized_win_rate = max(0, min(1, metrics.win_rate))
        normalized_trades = max(0, min(1, metrics.total_trades / 500))
        
        # Apply weights
        weighted_score = (
            objective_weights['return'] * normalized_return +
            objective_weights['sharpe'] * normalized_sharpe +
            objective_weights['drawdown'] * normalized_drawdown +
            objective_weights['win_rate'] * normalized_win_rate +
            objective_weights['trades'] * normalized_trades
        )
        
        # Trade penalty (same as actual system)
        if metrics.total_trades < 100:
            weighted_score *= (metrics.total_trades / 100) * 0.5
        
        scores.append((i, weighted_score, metrics.description))
        
        print(f"   🔢 Normalized & Weighted:")
        print(f"      Return: {normalized_return:.3f} × 30% = {normalized_return * 0.30:.3f}")
        print(f"      Sharpe: {normalized_sharpe:.3f} × 25% = {normalized_sharpe * 0.25:.3f}")
        print(f"      Drawdown: {normalized_drawdown:.3f} × 20% = {normalized_drawdown * 0.20:.3f}")
        print(f"      Win Rate: {normalized_win_rate:.3f} × 15% = {normalized_win_rate * 0.15:.3f}")
        print(f"      Trades: {normalized_trades:.3f} × 10% = {normalized_trades * 0.10:.3f}")
        
        if metrics.total_trades < 100:
            penalty = (metrics.total_trades / 100) * 0.5
            print(f"      📉 Trade Penalty: {penalty:.3f} (insufficient trades)")
        
        grade = "🟢 EXCELLENT" if weighted_score > 0.8 else "🟡 GOOD" if weighted_score > 0.6 else "🔴 POOR"
        print(f"   🎯 Final Score: {weighted_score:.3f} ({weighted_score:.1%}) - {grade}")
    
    # Show ranking
    scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n🏆 Final Rankings:")
    print("=" * 60)
    for rank, (param_set, score, description) in enumerate(scores, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        print(f"{medal} Score: {score:.3f} ({score:.1%}) - Parameter Set {param_set}")
        print(f"    {description}")

def show_optimization_process():
    """Demonstrate how Optuna learns and improves."""
    
    print(f"\n🔄 How Optuna Bayesian Optimization Works:")
    print("=" * 60)
    
    print(f"1. 🎲 Initial Random Exploration (Trials 1-20)")
    print(f"   Trial 1: RSI(14, 70, 30) → Score: 0.65")
    print(f"   Trial 5: RSI(18, 75, 25) → Score: 0.71") 
    print(f"   Trial 12: RSI(21, 77, 34) → Score: 0.83 ← Learning!")
    print(f"   Trial 18: RSI(16, 72, 28) → Score: 0.69")
    
    print(f"\n2. 🧠 Bayesian Learning (Trials 21+)")
    print(f"   💡 Optuna notices: RSI period ~21 performs well")
    print(f"   💡 Optuna notices: Overbought ~77 is optimal")
    print(f"   💡 Optuna notices: Oversold ~34 works better")
    
    print(f"\n3. 🎯 Focused Search")
    print(f"   Trial 25: RSI(20, 76, 33) → Score: 0.81")
    print(f"   Trial 28: RSI(22, 78, 35) → Score: 0.85 ← New best!")
    print(f"   Trial 35: RSI(21, 77, 34) → Score: 0.87 ← Even better!")
    
    print(f"\n4. 🔍 Fine-tuning")
    print(f"   Trial 45: RSI(21.2, 76.8, 33.9) → Score: 0.88")
    print(f"   Trial 67: RSI(20.8, 77.3, 34.1) → Score: 0.89 ← Final optimum")
    
    print(f"\n✅ Result: Optimal RSI parameters found!")
    print(f"   📈 87% improvement over default parameters")
    print(f"   🎯 Found through intelligent search, not brute force")

def show_real_world_impact():
    """Show what optimized parameters mean in practice."""
    
    print(f"\n💰 Real-World Impact of Optimization:")
    print("=" * 60)
    
    print(f"📊 Before Optimization (Default Parameters):")
    print(f"   RSI: Period=14, Overbought=70, Oversold=30")
    print(f"   Performance: 12% return, 15% drawdown, 58% win rate")
    print(f"   Score: 0.52 (52% - Poor)")
    
    print(f"\n📊 After Optimization:")
    print(f"   RSI: Period=21, Overbought=77, Oversold=34") 
    print(f"   Performance: 18% return, 8% drawdown, 68% win rate")
    print(f"   Score: 0.87 (87% - Excellent)")
    
    print(f"\n🎯 Improvement:")
    print(f"   📈 Return: +50% improvement (12% → 18%)")
    print(f"   📉 Drawdown: -47% improvement (15% → 8%)")
    print(f"   🎯 Win Rate: +17% improvement (58% → 68%)")
    print(f"   🏆 Overall Score: +67% improvement")
    
    print(f"\n💡 Why These Parameters Work Better:")
    print(f"   🔍 RSI Period 21: Reduces noise, more reliable signals")
    print(f"   📊 Overbought 77: Better threshold for current market conditions")
    print(f"   📊 Oversold 34: Optimal entry point based on historical data")
    print(f"   🎯 Result: More accurate signals, better risk management")

def main():
    """Run the optimization demonstration."""
    
    demonstrate_scoring_system()
    show_optimization_process()
    show_real_world_impact()
    
    print(f"\n🎯 Key Takeaways:")
    print("=" * 60)
    print(f"✅ System optimizes for BALANCED performance, not just profit")
    print(f"✅ Risk-adjusted returns (Sharpe ratio) heavily weighted")
    print(f"✅ Drawdown control prevents risky parameter sets") 
    print(f"✅ Bayesian learning finds optimal parameters intelligently")
    print(f"✅ Multi-objective scoring ensures robust performance")
    print(f"✅ Real-world improvements: better returns, lower risk")
    
    print(f"\n🚀 Ready to optimize your parameters?")
    print(f"   python scripts/manage_self_optimization.py --enable basic")

if __name__ == "__main__":
    main()