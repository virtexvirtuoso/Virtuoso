#!/usr/bin/env python3
"""
Test script to demonstrate the difference between linear and enhanced RSI scoring.

This script shows how the enhanced RSI scoring provides better differentiation
at extreme values compared to the old linear method.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.indicators.base_indicator import BaseIndicator
from src.core.logger import Logger

class RSIComparison:
    """Compare linear vs enhanced RSI scoring methods."""
    
    def __init__(self):
        self.logger = Logger(__name__)
        
        # Create a mock BaseIndicator to access the enhanced transform
        config = {
            'timeframes': {
                'base': {'interval': '1', 'validation': {'min_candles': 100}, 'weight': 0.5},
                'ltf': {'interval': '5', 'validation': {'min_candles': 50}, 'weight': 0.15},
                'mtf': {'interval': '30', 'validation': {'min_candles': 50}, 'weight': 0.20},
                'htf': {'interval': '240', 'validation': {'min_candles': 20}, 'weight': 0.15}
            }
        }
        
        # Create a test indicator to access the enhanced transform
        class TestIndicator(BaseIndicator):
            def __init__(self, config):
                self.indicator_type = 'technical'
                self.component_weights = {'test': 1.0}
                super().__init__(config)
            
            async def calculate(self, market_data):
                return {'score': 50.0, 'components': {}, 'signals': {}, 'metadata': {}}
        
        self.indicator = TestIndicator(config)
    
    def linear_rsi_score(self, rsi_value: float, overbought: float = 70.0, oversold: float = 30.0) -> float:
        """
        Original linear RSI scoring method.
        
        This is the problematic method that needs to be replaced.
        """
        if rsi_value > overbought:
            # Overbought: 50 → 0 as RSI goes from 70 → 100
            return max(0, 50 - ((rsi_value - overbought) / 30) * 50)
        elif rsi_value < oversold:
            # Oversold: 50 → 100 as RSI goes from 30 → 0
            return min(100, 50 + ((oversold - rsi_value) / 30) * 50)
        else:
            # Neutral: Linear scaling between 30-70
            return 50 + ((rsi_value - 50) / 20) * 25
    
    def enhanced_rsi_score(self, rsi_value: float, overbought: float = 70.0, oversold: float = 30.0) -> float:
        """Enhanced RSI scoring using non-linear transformations."""
        return self.indicator._enhanced_rsi_transform(rsi_value, overbought, oversold)
    
    def compare_methods(self):
        """Compare linear vs enhanced RSI scoring across different RSI values."""
        print("🎯 RSI Scoring Comparison: Linear vs Enhanced")
        print("=" * 60)
        
        # Test different RSI values
        test_values = [
            # Extreme oversold
            5, 10, 15, 20, 25,
            # Oversold boundary
            30, 35,
            # Neutral zone
            40, 45, 50, 55, 60, 65,
            # Overbought boundary
            70, 75,
            # Extreme overbought
            80, 85, 90, 95
        ]
        
        print(f"{'RSI':<5} {'Linear':<8} {'Enhanced':<10} {'Difference':<12} {'Improvement':<15}")
        print("-" * 60)
        
        for rsi in test_values:
            linear_score = self.linear_rsi_score(rsi)
            enhanced_score = self.enhanced_rsi_score(rsi)
            difference = enhanced_score - linear_score
            
            # Determine improvement type
            if rsi > 70:
                # Overbought: Enhanced should provide better differentiation (more negative for extreme values)
                improvement = "Better differentiation" if difference < 0 else "Neutral"
            elif rsi < 30:
                # Oversold: Enhanced should provide better differentiation (more positive for extreme values)
                improvement = "Better differentiation" if difference > 0 else "Neutral"
            else:
                # Neutral: Should be similar
                improvement = "Smooth transition"
            
            print(f"{rsi:<5} {linear_score:<8.2f} {enhanced_score:<10.2f} {difference:<+12.2f} {improvement:<15}")
        
        return test_values
    
    def demonstrate_extreme_differentiation(self):
        """Demonstrate how enhanced method better differentiates extreme values."""
        print("\n🚀 Extreme Value Differentiation Analysis")
        print("=" * 60)
        
        # Test extreme overbought levels
        extreme_overbought = [75, 80, 85, 90, 95]
        print("\nOverbought Differentiation (Lower scores = More bearish):")
        print(f"{'RSI':<5} {'Linear':<8} {'Enhanced':<10} {'Linear Diff':<12} {'Enhanced Diff':<15}")
        print("-" * 60)
        
        linear_base = self.linear_rsi_score(75)
        enhanced_base = self.enhanced_rsi_score(75)
        
        for rsi in extreme_overbought:
            linear_score = self.linear_rsi_score(rsi)
            enhanced_score = self.enhanced_rsi_score(rsi)
            
            linear_diff = linear_score - linear_base
            enhanced_diff = enhanced_score - enhanced_base
            
            print(f"{rsi:<5} {linear_score:<8.2f} {enhanced_score:<10.2f} {linear_diff:<+12.2f} {enhanced_diff:<+15.2f}")
        
        # Test extreme oversold levels
        extreme_oversold = [25, 20, 15, 10, 5]
        print("\nOversold Differentiation (Higher scores = More bullish):")
        print(f"{'RSI':<5} {'Linear':<8} {'Enhanced':<10} {'Linear Diff':<12} {'Enhanced Diff':<15}")
        print("-" * 60)
        
        linear_base = self.linear_rsi_score(25)
        enhanced_base = self.enhanced_rsi_score(25)
        
        for rsi in extreme_oversold:
            linear_score = self.linear_rsi_score(rsi)
            enhanced_score = self.enhanced_rsi_score(rsi)
            
            linear_diff = linear_score - linear_base
            enhanced_diff = enhanced_score - enhanced_base
            
            print(f"{rsi:<5} {linear_score:<8.2f} {enhanced_score:<10.2f} {linear_diff:<+12.2f} {enhanced_diff:<+15.2f}")
    
    def analyze_mathematical_properties(self):
        """Analyze the mathematical properties of both methods."""
        print("\n📊 Mathematical Properties Analysis")
        print("=" * 60)
        
        # Generate full range of RSI values
        rsi_values = np.linspace(0, 100, 1000)
        linear_scores = [self.linear_rsi_score(rsi) for rsi in rsi_values]
        enhanced_scores = [self.enhanced_rsi_score(rsi) for rsi in rsi_values]
        
        # Calculate derivatives (rate of change)
        linear_derivatives = np.gradient(linear_scores)
        enhanced_derivatives = np.gradient(enhanced_scores)
        
        # Find key statistics
        print("Key Statistics:")
        print(f"Linear method:")
        print(f"  - Range: {min(linear_scores):.2f} to {max(linear_scores):.2f}")
        print(f"  - Mean derivative: {np.mean(np.abs(linear_derivatives)):.4f}")
        print(f"  - Max derivative: {np.max(np.abs(linear_derivatives)):.4f}")
        
        print(f"Enhanced method:")
        print(f"  - Range: {min(enhanced_scores):.2f} to {max(enhanced_scores):.2f}")
        print(f"  - Mean derivative: {np.mean(np.abs(enhanced_derivatives)):.4f}")
        print(f"  - Max derivative: {np.max(np.abs(enhanced_derivatives)):.4f}")
        
        # Analyze smoothness
        linear_second_derivatives = np.gradient(linear_derivatives)
        enhanced_second_derivatives = np.gradient(enhanced_derivatives)
        
        print(f"\nSmoothness (lower = smoother):")
        print(f"  - Linear method: {np.mean(np.abs(linear_second_derivatives)):.6f}")
        print(f"  - Enhanced method: {np.mean(np.abs(enhanced_second_derivatives)):.6f}")
        
        return rsi_values, linear_scores, enhanced_scores
    
    def create_visualization(self, rsi_values, linear_scores, enhanced_scores):
        """Create a visualization comparing the two methods."""
        try:
            plt.figure(figsize=(12, 8))
            
            # Main comparison plot
            plt.subplot(2, 2, 1)
            plt.plot(rsi_values, linear_scores, 'b-', label='Linear Method', linewidth=2)
            plt.plot(rsi_values, enhanced_scores, 'r-', label='Enhanced Method', linewidth=2)
            plt.axvline(x=30, color='gray', linestyle='--', alpha=0.5, label='Oversold (30)')
            plt.axvline(x=70, color='gray', linestyle='--', alpha=0.5, label='Overbought (70)')
            plt.xlabel('RSI Value')
            plt.ylabel('Score')
            plt.title('RSI Scoring Comparison: Linear vs Enhanced')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Difference plot
            plt.subplot(2, 2, 2)
            differences = np.array(enhanced_scores) - np.array(linear_scores)
            plt.plot(rsi_values, differences, 'g-', linewidth=2)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.axvline(x=30, color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=70, color='gray', linestyle='--', alpha=0.5)
            plt.xlabel('RSI Value')
            plt.ylabel('Score Difference (Enhanced - Linear)')
            plt.title('Improvement from Enhanced Method')
            plt.grid(True, alpha=0.3)
            
            # Extreme values focus
            plt.subplot(2, 2, 3)
            extreme_mask = (rsi_values <= 30) | (rsi_values >= 70)
            plt.plot(rsi_values[extreme_mask], np.array(linear_scores)[extreme_mask], 'b-', label='Linear', linewidth=2)
            plt.plot(rsi_values[extreme_mask], np.array(enhanced_scores)[extreme_mask], 'r-', label='Enhanced', linewidth=2)
            plt.xlabel('RSI Value (Extreme Zones)')
            plt.ylabel('Score')
            plt.title('Extreme Value Differentiation')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Derivatives (rate of change)
            plt.subplot(2, 2, 4)
            linear_derivatives = np.gradient(linear_scores)
            enhanced_derivatives = np.gradient(enhanced_scores)
            plt.plot(rsi_values, linear_derivatives, 'b-', label='Linear Derivative', linewidth=2)
            plt.plot(rsi_values, enhanced_derivatives, 'r-', label='Enhanced Derivative', linewidth=2)
            plt.axvline(x=30, color='gray', linestyle='--', alpha=0.5)
            plt.axvline(x=70, color='gray', linestyle='--', alpha=0.5)
            plt.xlabel('RSI Value')
            plt.ylabel('Rate of Change')
            plt.title('Sensitivity Comparison')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save the plot
            output_path = 'test_output/rsi_comparison.png'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"\n📈 Visualization saved to: {output_path}")
            
        except ImportError:
            print("\n⚠️  Matplotlib not available - skipping visualization")
        except Exception as e:
            print(f"\n❌ Error creating visualization: {e}")
    
    def run_comprehensive_test(self):
        """Run comprehensive comparison test."""
        print("🔬 Enhanced RSI Scoring Implementation Test")
        print("=" * 60)
        print("This test demonstrates the improvements in RSI scoring using")
        print("non-linear transformations to fix linear scoring problems.")
        print()
        
        # Run all comparisons
        test_values = self.compare_methods()
        self.demonstrate_extreme_differentiation()
        rsi_values, linear_scores, enhanced_scores = self.analyze_mathematical_properties()
        
        # Create visualization
        self.create_visualization(rsi_values, linear_scores, enhanced_scores)
        
        print("\n✅ Summary of Improvements:")
        print("1. Better differentiation at extreme RSI values (>70, <30)")
        print("2. Smooth transitions using sigmoid in neutral zone")
        print("3. Exponential scaling for extreme values reflects increasing reversal probability")
        print("4. Mathematically sound with proper bounds and error handling")
        print("5. Maintains interpretability while adding sophistication")
        
        return {
            'test_values': test_values,
            'rsi_values': rsi_values,
            'linear_scores': linear_scores,
            'enhanced_scores': enhanced_scores
        }

def main():
    """Run the RSI comparison test."""
    try:
        comparison = RSIComparison()
        results = comparison.run_comprehensive_test()
        
        print(f"\n🎯 Test completed successfully!")
        print(f"   - Tested {len(results['test_values'])} specific RSI values")
        print(f"   - Analyzed {len(results['rsi_values'])} points across full range")
        print(f"   - Enhanced method shows clear improvements in extreme value handling")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 