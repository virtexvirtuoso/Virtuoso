"""
Confluence Prism Integration
===========================

Integrates the 3D Signal Prism visualization with the existing confluence analyzer
to create real-time, interactive trading signal visualizations.

This script provides:
- Real-time signal prism updates
- Integration with existing confluence analysis
- Automated visualization generation
- Dashboard integration capabilities
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.core.analysis.confluence import ConfluenceAnalyzer
from scripts.visualization.signal_prism_3d import SignalPrism3D
from src.core.logger import Logger


class ConfluencePrismIntegration:
    """Integrates confluence analysis with 3D prism visualization."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the integration system."""
        self.logger = Logger(__name__)
        self.config = config or {}
        
        # Initialize components
        self.confluence_analyzer = ConfluenceAnalyzer(config)
        self.prism_visualizer = SignalPrism3D(config)
        
        # Output settings
        self.output_dir = self.config.get('output_dir', 'examples/demo/3d_viz_output')
        self.auto_save = self.config.get('auto_save', True)
        self.auto_rotate = self.config.get('auto_rotate', True)
        
        self.logger.info("Confluence Prism Integration initialized")
    
    async def analyze_and_visualize(self, market_data: Dict[str, Any], 
                                  symbol: str = "SYMBOL") -> Dict[str, Any]:
        """Perform confluence analysis and create 3D prism visualization."""
        
        try:
            self.logger.info(f"Starting analysis and visualization for {symbol}")
            
            # Perform confluence analysis
            self.logger.info("Running confluence analysis...")
            analysis_result = await self.confluence_analyzer.analyze(market_data)
            
            if not analysis_result or 'error' in analysis_result:
                self.logger.error(f"Confluence analysis failed: {analysis_result}")
                return {'error': 'Analysis failed', 'details': analysis_result}
            
            # Extract component scores
            component_scores = self._extract_component_scores(analysis_result)
            overall_score = analysis_result.get('confluence_score', 50.0)
            confidence = analysis_result.get('reliability', 0.5)
            
            self.logger.info(f"Analysis complete - Overall Score: {overall_score:.1f}, Confidence: {confidence:.2f}")
            self.logger.info(f"Component Scores: {component_scores}")
            
            # Create 3D prism visualization
            self.logger.info("Creating 3D prism visualization...")
            prism_fig = self.prism_visualizer.create_interactive_visualization(
                component_scores=component_scores,
                overall_score=overall_score,
                confidence=confidence,
                symbol=symbol,
                timestamp=datetime.now()
            )
            
            # Add animation controls if enabled
            if self.auto_rotate:
                prism_fig = self.prism_visualizer.add_animation_controls(prism_fig)
            
            # Create dashboard view
            dashboard_fig = self.prism_visualizer.create_dashboard_view(
                component_scores=component_scores,
                overall_score=overall_score,
                confidence=confidence,
                symbol=symbol
            )
            
            # Save visualizations if auto-save is enabled
            saved_files = {}
            if self.auto_save:
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Save main prism visualization
                prism_path = self.prism_visualizer.save_visualization(
                    prism_fig, 
                    f"signal_prism_{symbol}_{timestamp_str}",
                    self.output_dir
                )
                saved_files['prism'] = prism_path
                
                # Save dashboard
                dashboard_path = self.prism_visualizer.save_visualization(
                    dashboard_fig,
                    f"signal_dashboard_{symbol}_{timestamp_str}",
                    self.output_dir
                )
                saved_files['dashboard'] = dashboard_path
                
                # Save analysis data
                analysis_path = self._save_analysis_data(analysis_result, symbol, timestamp_str)
                saved_files['analysis'] = analysis_path
                
                self.logger.info(f"Visualizations saved: {saved_files}")
            
            # Return comprehensive result
            return {
                'success': True,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis_result,
                'component_scores': component_scores,
                'overall_score': overall_score,
                'confidence': confidence,
                'visualizations': {
                    'prism_figure': prism_fig,
                    'dashboard_figure': dashboard_fig
                },
                'saved_files': saved_files,
                'trading_recommendation': self._generate_trading_recommendation(
                    overall_score, confidence, component_scores
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error in analyze_and_visualize: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'error': str(e), 'success': False}
    
    def _extract_component_scores(self, analysis_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract component scores from confluence analysis result."""
        
        component_scores = {}
        
        # Map analysis result keys to prism component keys
        component_mapping = {
            'technical': 'technical',
            'volume': 'volume', 
            'orderflow': 'orderflow',
            'sentiment': 'sentiment',
            'orderbook': 'orderbook',
            'price_structure': 'price_structure'
        }
        
        # Extract scores from analysis result
        for prism_key, analysis_key in component_mapping.items():
            if analysis_key in analysis_result:
                # Handle different result structures
                component_data = analysis_result[analysis_key]
                if isinstance(component_data, dict):
                    score = component_data.get('score', 50.0)
                else:
                    score = float(component_data) if component_data is not None else 50.0
            else:
                score = 50.0  # Default neutral score
                
            component_scores[prism_key] = score
        
        return component_scores
    
    def _generate_trading_recommendation(self, overall_score: float, 
                                       confidence: float, 
                                       component_scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate actionable trading recommendations based on signal analysis."""
        
        # Determine primary signal direction
        if overall_score >= 65:
            primary_signal = "BULLISH"
            signal_strength = "STRONG" if overall_score >= 75 else "MODERATE"
        elif overall_score <= 35:
            primary_signal = "BEARISH" 
            signal_strength = "STRONG" if overall_score <= 25 else "MODERATE"
        else:
            primary_signal = "NEUTRAL"
            signal_strength = "WEAK"
        
        # Assess confidence level
        if confidence >= 0.8:
            confidence_level = "HIGH"
        elif confidence >= 0.6:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"
        
        # Identify strongest and weakest components
        strongest_component = max(component_scores.items(), key=lambda x: x[1])
        weakest_component = min(component_scores.items(), key=lambda x: x[1])
        
        # Generate specific recommendations
        recommendations = []
        
        if confidence_level == "HIGH" and signal_strength in ["STRONG", "MODERATE"]:
            if primary_signal == "BULLISH":
                recommendations.append("Consider LONG position")
                recommendations.append("Look for pullback entries")
            elif primary_signal == "BEARISH":
                recommendations.append("Consider SHORT position")
                recommendations.append("Look for bounce entries")
        else:
            recommendations.append("WAIT for clearer signals")
            recommendations.append("Monitor for confirmation")
        
        # Add component-specific insights
        if strongest_component[1] >= 70:
            recommendations.append(f"Strong {strongest_component[0]} signal supports direction")
        
        if weakest_component[1] <= 30:
            recommendations.append(f"Weak {weakest_component[0]} signal - monitor closely")
        
        return {
            'primary_signal': primary_signal,
            'signal_strength': signal_strength,
            'confidence_level': confidence_level,
            'overall_score': overall_score,
            'confidence': confidence,
            'strongest_component': strongest_component,
            'weakest_component': weakest_component,
            'recommendations': recommendations,
            'risk_level': self._assess_risk_level(overall_score, confidence, component_scores)
        }
    
    def _assess_risk_level(self, overall_score: float, confidence: float, 
                          component_scores: Dict[str, float]) -> str:
        """Assess risk level based on signal characteristics."""
        
        # Calculate score variance (higher variance = higher risk)
        scores = list(component_scores.values())
        score_variance = np.var(scores) if len(scores) > 1 else 0
        
        # Risk factors
        risk_factors = []
        
        if confidence < 0.5:
            risk_factors.append("Low confidence")
        
        if score_variance > 400:  # High variance in component scores
            risk_factors.append("Conflicting signals")
        
        if 40 <= overall_score <= 60:  # Neutral zone
            risk_factors.append("Neutral territory")
        
        # Determine risk level
        if len(risk_factors) >= 2:
            return "HIGH"
        elif len(risk_factors) == 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _save_analysis_data(self, analysis_result: Dict[str, Any], 
                           symbol: str, timestamp_str: str) -> str:
        """Save analysis data to JSON file."""
        
        try:
            # Prepare data for JSON serialization
            save_data = {
                'symbol': symbol,
                'timestamp': timestamp_str,
                'analysis_result': analysis_result
            }
            
            # Create filename
            filename = f"analysis_data_{symbol}_{timestamp_str}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Ensure directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving analysis data: {str(e)}")
            return ""
    
    async def create_live_dashboard(self, market_data_stream, symbol: str = "LIVE"):
        """Create a live updating dashboard with real-time signal prisms."""
        
        self.logger.info(f"Starting live dashboard for {symbol}")
        
        try:
            async for market_data in market_data_stream:
                # Analyze and visualize
                result = await self.analyze_and_visualize(market_data, symbol)
                
                if result.get('success'):
                    self.logger.info(f"Live update - Score: {result['overall_score']:.1f}, "
                                   f"Confidence: {result['confidence']:.2f}")
                    
                    # Yield result for external processing
                    yield result
                else:
                    self.logger.warning(f"Live update failed: {result.get('error')}")
                    
        except Exception as e:
            self.logger.error(f"Error in live dashboard: {str(e)}")


async def demo_integration():
    """Demonstration of the confluence prism integration."""
    
    # Sample market data (replace with real data in production)
    sample_market_data = {
        'ohlcv': {
            '1m': pd.DataFrame({
                'open': [0.01055] * 100,
                'high': [0.01056] * 100,
                'low': [0.01054] * 100,
                'close': [0.01055] * 100,
                'volume': [1000000] * 100
            }),
            '5m': pd.DataFrame({
                'open': [0.01055] * 100,
                'high': [0.01056] * 100,
                'low': [0.01054] * 100,
                'close': [0.01055] * 100,
                'volume': [5000000] * 100
            })
        },
        'orderbook': {
            'bids': [[0.01054, 1000000], [0.01053, 2000000]],
            'asks': [[0.01056, 1000000], [0.01057, 2000000]]
        },
        'trades': [
            {'price': 0.01055, 'size': 1000, 'side': 'buy', 'timestamp': 1640995200000},
            {'price': 0.01055, 'size': 2000, 'side': 'sell', 'timestamp': 1640995201000}
        ] * 100
    }
    
    # Initialize integration
    integration = ConfluencePrismIntegration()
    
    # Run analysis and visualization
    result = await integration.analyze_and_visualize(sample_market_data, "XRPUSDT")
    
    if result.get('success'):
        print("\n" + "="*60)
        print("🎯 SIGNAL PRISM ANALYSIS COMPLETE")
        print("="*60)
        print(f"Symbol: {result['symbol']}")
        print(f"Overall Score: {result['overall_score']:.1f}/100")
        print(f"Confidence: {result['confidence']*100:.0f}%")
        print(f"Timestamp: {result['timestamp']}")
        
        print("\n📊 Component Breakdown:")
        for component, score in result['component_scores'].items():
            print(f"  {component.title()}: {score:.1f}")
        
        print(f"\n🎯 Trading Recommendation:")
        rec = result['trading_recommendation']
        print(f"  Signal: {rec['primary_signal']} ({rec['signal_strength']})")
        print(f"  Confidence: {rec['confidence_level']}")
        print(f"  Risk Level: {rec['risk_level']}")
        print(f"  Recommendations:")
        for r in rec['recommendations']:
            print(f"    • {r}")
        
        if result.get('saved_files'):
            print(f"\n💾 Files Saved:")
            for file_type, path in result['saved_files'].items():
                print(f"  {file_type.title()}: {path}")
        
        print("\n" + "="*60)
        
    else:
        print(f"❌ Analysis failed: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Run the demo
    result = asyncio.run(demo_integration()) 