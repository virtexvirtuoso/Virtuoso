"""
Formatting utilities for displaying analysis results with improved visual presentation.

This module provides functions for formatting market analysis data with:
- ASCII/Unicode box-style dashboards 
- Color-coded output
- Visual gauges and indicators
- Consistent styling across different analysis components
- Trend indicators showing direction of change
- Detailed component breakdown tables
"""

import datetime
from typing import Dict, Any, List, Tuple, Optional, Union

class AnalysisFormatter:
    """
    Provides methods for formatting analysis results with enhanced visualization.
    
    Features:
    - Unicode box-drawing dashboard style
    - Color-coded indicators based on values
    - Visual gauges to represent numeric scores
    - Consistent formatting across different types of analysis
    - Trend indicators showing direction of movement
    - Detailed component breakdown tables
    """
    
    # ANSI terminal color codes
    GREEN = "\033[92m"    # Bullish/positive
    YELLOW = "\033[93m"   # Neutral
    RED = "\033[91m"      # Bearish/negative
    CYAN = "\033[96m"     # Headers/titles
    BLUE = "\033[94m"     # Supplementary information
    MAGENTA = "\033[95m"  # Highlights
    BOLD = "\033[1m"      # Bold formatting
    RESET = "\033[0m"     # Reset all formatting
    
    # Trend indicators
    TREND_UP = "↑"        # Bullish trend
    TREND_NEUTRAL = "→"   # Neutral/sideways trend
    TREND_DOWN = "↓"      # Bearish trend
    
    @classmethod
    def get_color_for_value(cls, value: float) -> str:
        """
        Returns the appropriate color code based on a numeric value.
        
        Args:
            value: Numeric value (typically 0-100 scale)
            
        Returns:
            str: ANSI color code
        """
        if value >= 70:
            return cls.GREEN
        elif value >= 45:
            return cls.YELLOW
        else:
            return cls.RED
    
    @classmethod
    def get_trend_indicator(cls, current: float, previous: Optional[float] = None, threshold: float = 2.0) -> str:
        """
        Returns a trend indicator symbol based on the comparison between current and previous values.
        
        Args:
            current: Current value
            previous: Previous value to compare against (if None, returns neutral)
            threshold: Minimum difference to show a trend (default: 2.0)
            
        Returns:
            str: Trend indicator symbol (↑, →, or ↓)
        """
        if previous is None:
            return cls.TREND_NEUTRAL
            
        difference = current - previous
        
        if abs(difference) < threshold:
            return cls.TREND_NEUTRAL
        elif difference >= threshold:
            return cls.TREND_UP
        else:
            return cls.TREND_DOWN
    
    @classmethod
    def create_gauge(cls, value: float, width: int = 20) -> str:
        """
        Creates a visual gauge representation of a numeric value.
        
        Args:
            value: Numeric value (0-100)
            width: Width of the gauge in characters
            
        Returns:
            str: Formatted gauge with appropriate coloring
        """
        # Ensure value is within bounds
        value = max(0, min(100, value))
        
        # Calculate filled portion
        gauge_width = width
        filled = int((value / 100) * gauge_width)
        
        # Select color based on value
        if value >= 70:
            color = cls.GREEN
            fill_char = "█"  # Solid block for bullish
        elif value >= 45:
            color = cls.YELLOW
            fill_char = "▓"  # Medium-density dotted for neutral
        else:
            color = cls.RED
            fill_char = "░"  # Low-density dotted for bearish
        
        # Create the gauge with consistent formatting
        gauge = "["
        gauge += color + fill_char * filled + cls.RESET
        gauge += " " * (gauge_width - filled)
        gauge += "]"
        
        return gauge
    
    @classmethod
    def format_analysis_dashboard(cls, 
                               symbol: str,
                               overall_score: float,
                               components: Dict[str, float],
                               reliability: float = 1.0,
                               interpretation: Optional[str] = None,
                               previous_scores: Optional[Dict[str, float]] = None,
                               detailed_components: Optional[Dict[str, Dict[str, float]]] = None) -> str:
        """
        Creates a formatted dashboard display of analysis results.
        
        Args:
            symbol: The trading symbol (e.g., 'BTCUSDT')
            overall_score: The overall/confluence score
            components: Dictionary of component scores
            reliability: Reliability score (0-1)
            interpretation: Optional interpretation text
            previous_scores: Previous component scores for trend indicators
            detailed_components: Detailed breakdown of components and their sub-indicators
            
        Returns:
            str: Formatted dashboard as a string
        """
        # Component display names mapping
        component_names = {
            'technical': 'Technical Analysis',
            'volume': 'Volume Analysis',
            'orderbook': 'Order Book',
            'orderflow': 'Order Flow',
            'sentiment': 'Market Sentiment',
            'price_structure': 'Price Structure'
        }
        
        # Preferred component display order
        component_order = [
            'technical', 
            'volume', 
            'orderbook', 
            'orderflow', 
            'sentiment', 
            'price_structure'
        ]
        
        # Format timestamp
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create header
        dashboard = f"\n{cls.BOLD}╔{'═' * 62}╗{cls.RESET}\n"
        dashboard += f"{cls.BOLD}║ {cls.CYAN}{symbol} MARKET ANALYSIS{cls.RESET}{cls.BOLD} - {timestamp} ║{cls.RESET}\n"
        dashboard += f"{cls.BOLD}╠{'═' * 25}╦{'═' * 10}╦{'═' * 21}╦{'═' * 4}╣{cls.RESET}\n"
        dashboard += f"{cls.BOLD}║ {'COMPONENT':<23} ║ {'SCORE':<8} ║ {'GAUGE':<19} ║ {'TREND'} ║{cls.RESET}\n"
        dashboard += f"{cls.BOLD}╠{'═' * 25}╬{'═' * 10}╬{'═' * 21}╬{'═' * 4}╣{cls.RESET}\n"
        
        # Get previous overall score if available
        previous_overall = None
        if previous_scores and 'overall' in previous_scores:
            previous_overall = previous_scores['overall']
            
        # Add overall score with trend
        score_color = cls.get_color_for_value(overall_score)
        trend_indicator = cls.get_trend_indicator(overall_score, previous_overall)
        dashboard += f"{cls.BOLD}║ {'OVERALL CONFLUENCE':<23} ║ {score_color}{overall_score:<8.2f}{cls.RESET}{cls.BOLD} ║ {cls.create_gauge(overall_score)} ║ {trend_indicator}  ║{cls.RESET}\n"
        dashboard += f"{cls.BOLD}╠{'═' * 25}╬{'═' * 10}╬{'═' * 21}╬{'═' * 4}╣{cls.RESET}\n"
        
        # Add component scores in specified order with trends
        for comp_key in component_order:
            if comp_key in components:
                comp_name = component_names.get(comp_key, comp_key.replace('_', ' ').title())
                comp_score = components[comp_key]
                color = cls.get_color_for_value(comp_score)
                
                # Get previous score for trend if available
                previous = None
                if previous_scores and comp_key in previous_scores:
                    previous = previous_scores[comp_key]
                
                trend = cls.get_trend_indicator(comp_score, previous)
                dashboard += f"{cls.BOLD}║ {comp_name:<23} ║ {color}{comp_score:<8.2f}{cls.RESET}{cls.BOLD} ║ {cls.create_gauge(comp_score)} ║ {trend}  ║{cls.RESET}\n"
        
        dashboard += f"{cls.BOLD}╠{'═' * 25}╩{'═' * 10}╩{'═' * 21}╩{'═' * 4}╣{cls.RESET}\n"
        
        # Add reliability info
        dashboard += f"{cls.BOLD}║ Reliability: {reliability:.2f}{' ' * 46}║{cls.RESET}\n"
        
        # Add detailed component breakdowns if provided
        if detailed_components:
            dashboard += cls._format_detailed_components(detailed_components, component_names)
        
        # Add interpretation if provided
        if interpretation:
            dashboard += f"{cls.BOLD}╠{'═' * 62}╣{cls.RESET}\n"
            dashboard += f"{cls.BOLD}║ INTERPRETATION:{' ' * 48}║{cls.RESET}\n"
            
            # Handle multi-line interpretations
            if len(interpretation) > 60:
                words = interpretation.split()
                current_line = []
                current_len = 0
                lines = []
                
                for word in words:
                    if current_len + len(word) + 1 <= 60:  # +1 for space
                        current_line.append(word)
                        current_len += len(word) + 1
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                        current_len = len(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                for i, line in enumerate(lines):
                    prefix = "║ " if i == 0 else "║   "
                    padding = 62 - len(prefix) - len(line)
                    dashboard += f"{cls.BOLD}{prefix}{line}{' ' * padding}║{cls.RESET}\n"
            else:
                dashboard += f"{cls.BOLD}║ {interpretation}{' ' * (60 - len(interpretation))}║{cls.RESET}\n"
        
        # Add footer
        dashboard += f"{cls.BOLD}╚{'═' * 62}╝{cls.RESET}\n"
        
        return dashboard
    
    @classmethod
    def _format_detailed_components(cls, detailed_components: Dict[str, Dict[str, float]], component_names: Dict[str, str]) -> str:
        """
        Format detailed component breakdowns into tables.
        
        Args:
            detailed_components: Dictionary of component details
            component_names: Dictionary mapping component keys to display names
            
        Returns:
            str: Formatted string with component breakdown tables
        """
        result = f"{cls.BOLD}╠{'═' * 62}╣{cls.RESET}\n"
        result += f"{cls.BOLD}║ DETAILED COMPONENT BREAKDOWN:{' ' * 32}║{cls.RESET}\n"
        
        for comp_key, details in detailed_components.items():
            if not details:
                continue
                
            comp_name = component_names.get(comp_key, comp_key.replace('_', ' ').title())
            
            # Add component header
            result += f"{cls.BOLD}║ {cls.BLUE}{comp_name}:{cls.RESET}{cls.BOLD}{' ' * (60 - len(comp_name) - 1)}║{cls.RESET}\n"
            result += f"{cls.BOLD}║ ┌{'─' * 22}┬{'─' * 9}┬{'─' * 22}┐ ║{cls.RESET}\n"
            result += f"{cls.BOLD}║ │ {'Indicator':<20} │ {'Score':<7} │ {'Gauge':<20} │ ║{cls.RESET}\n"
            result += f"{cls.BOLD}║ ├{'─' * 22}┼{'─' * 9}┼{'─' * 22}┤ ║{cls.RESET}\n"
            
            # Sort components by value (descending)
            sorted_details = sorted(details.items(), key=lambda x: x[1], reverse=True)
            
            # Add component rows
            for indicator, value in sorted_details:
                # Format indicator name
                indicator_name = indicator.replace('_', ' ').title()
                if len(indicator_name) > 20:
                    indicator_name = indicator_name[:17] + "..."
                    
                # Get color for value
                color = cls.get_color_for_value(value)
                
                # Create gauge (smaller than main one)
                gauge = cls.create_gauge(value, width=15)
                
                result += f"{cls.BOLD}║ │ {indicator_name:<20} │ {color}{value:<7.2f}{cls.RESET}{cls.BOLD} │ {gauge:<20} │ ║{cls.RESET}\n"
            
            result += f"{cls.BOLD}║ └{'─' * 22}┴{'─' * 9}┴{'─' * 22}┘ ║{cls.RESET}\n"
        
        return result
    
    @classmethod
    def format_analysis_result(cls, 
                           analysis_result: Dict[str, Any], 
                           symbol_str: str, 
                           previous_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Format complete analysis results dictionary with enhanced visualization.
        
        Args:
            analysis_result: The analysis result dictionary
            symbol_str: The symbol being analyzed
            previous_result: Previous analysis result for trend indicators
            
        Returns:
            str: Formatted analysis dashboard
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        # Extract key information from the analysis result
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        interpretation = analysis_result.get('overall_interpretation', '')
        
        # Extract previous scores if available
        previous_scores = None
        if previous_result:
            previous_scores = {
                'overall': previous_result.get('score', previous_result.get('confluence_score', 0))
            }
            
            # Add component scores
            prev_components = previous_result.get('components', {})
            for comp in components:
                if comp in prev_components:
                    previous_scores[comp] = prev_components[comp]
        
        # Extract detailed components if available
        detailed_components = {}
        results = analysis_result.get('results', {})
        
        for comp_key, comp_details in results.items():
            if isinstance(comp_details, dict) and 'components' in comp_details:
                detailed_components[comp_key] = comp_details['components']
        
        # Use the dashboard formatter
        return cls.format_analysis_dashboard(
            symbol=symbol_str,
            overall_score=score,
            components=components,
            reliability=reliability,
            interpretation=interpretation,
            previous_scores=previous_scores,
            detailed_components=detailed_components
        )

    def format_component_breakdown(self, components, additional_data=None):
        """
        Format component breakdown in a visually appealing way with clear structure.
        
        Args:
            components (dict): Dictionary of component scores
            additional_data (dict, optional): Additional data like signals or interpretations
            
        Returns:
            str: Formatted component breakdown with visual enhancements
        """
        if not components:
            return "No component data available"
        
        # Define some styling elements
        horizontal_line = "┄" * 50
        header = f"┌{'─' * 48}┐\n"
        header += f"│{'COMPONENT BREAKDOWN':^48}│\n"
        header += f"├{'─' * 24}┬{'─' * 23}┤\n"
        header += f"│ {'COMPONENT':^22} │ {'SCORE':^21} │\n"
        header += f"├{'─' * 24}┼{'─' * 23}┤\n"
        
        # Sort components by score for better readability (descending)
        sorted_components = sorted(
            components.items(), 
            key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
            reverse=True
        )
        
        # Build the formatted components table
        formatted_components = []
        for name, score in sorted_components:
            # Format the score
            if isinstance(score, (int, float)):
                # Format name nicely
                display_name = name.replace('_', ' ').title()
                
                # Create visual bar
                score_value = float(score)
                bar_width = 15
                filled = int((score_value / 100) * bar_width)
                
                # Choose character and color based on score
                if score_value >= 70:
                    bar_char = "█"  # Solid block for strong
                    indicator = "↑"  # Up arrow
                elif score_value >= 45:
                    bar_char = "▓"  # Medium block for neutral
                    indicator = "→"  # Right arrow
                else:
                    bar_char = "░"  # Light block for weak
                    indicator = "↓"  # Down arrow
                    
                bar = bar_char * filled + " " * (bar_width - filled)
                
                # Format the line
                formatted_score = f"{score_value:.2f} [{bar}] {indicator}"
                formatted_components.append(f"│ {display_name:22} │ {formatted_score:21} │")
        
        # Add a footer
        footer = f"└{'─' * 24}┴{'─' * 23}┘\n"
        
        # Combine all elements
        result = header + "\n".join(formatted_components) + "\n" + footer
        
        # Add interpretation if available
        if additional_data and 'interpretation' in additional_data:
            interp = additional_data['interpretation']
            result += "\nInterpretation:\n"
            if isinstance(interp, dict):
                if 'bias' in interp:
                    result += f"• Bias: {interp['bias']}\n"
                if 'signal' in interp:
                    result += f"• Signal: {interp['signal']}\n"
                if 'strength' in interp:
                    result += f"• Strength: {interp['strength']}\n"
                if 'summary' in interp:
                    result += f"• Summary: {interp['summary']}\n"
            else:
                result += f"{interp}\n"
        
        return result

    def format_analysis_result(self, analysis_result, symbol_str):
        """Format analysis results with enhanced visualization.
        
        Args:
            analysis_result (dict): Analysis result data
            symbol_str (str): Symbol being analyzed
            
        Returns:
            str: Formatted analysis output
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        results = analysis_result.get('results', {})
        
        # Create a nice bordered dashboard layout
        output = "╔══════════════════════════════════════════════════════════════╗\n"
        output += f"║ {symbol_str} MARKET ANALYSIS - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ║\n"
        output += "╠═════════════════════════╦══════════╦═════════════════════╦════╣\n"
        output += "║ COMPONENT               ║ SCORE    ║ GAUGE               ║ TREND ║\n"
        output += "╠═════════════════════════╬══════════╬═════════════════════╬════╣\n"
        
        # Overall confluence score
        gauge = self._create_fancy_gauge(score)
        trend = self._get_trend_indicator(score)
        output += f"║ OVERALL CONFLUENCE      ║ {score:.2f}    ║ {gauge} ║ {trend}  ║\n"
        output += "╠═════════════════════════╬══════════╬═════════════════════╬════╣\n"
        
        # Component scores
        for name, component_score in sorted(components.items(), key=lambda x: x[1], reverse=True):
            # Format display name
            display_name = name.replace('_', ' ').title()
            display_name = f"{display_name:<20}"
            
            # Create gauge and trend indicator
            gauge = self._create_fancy_gauge(component_score)
            trend = self._get_trend_indicator(component_score)
            
            output += f"║ {display_name}      ║ {component_score:.2f}    ║ {gauge} ║ {trend}  ║\n"
        
        # Footer with reliability
        output += "╠═════════════════════════╩══════════╩═════════════════════╩════╣\n"
        output += f"║ Reliability: {reliability:.2f}                                              ║\n"
        
        # Add detailed component breakdown if available
        has_detailed_components = False
        for component_name, component_data in results.items():
            if 'components' in component_data and component_data['components']:
                has_detailed_components = True
                break
        
        if has_detailed_components:
            output += "╠══════════════════════════════════════════════════════════════╣\n"
            output += "║ DETAILED COMPONENT BREAKDOWN:                                ║\n"
            
            # Add details for each component that has sub-components
            for component_name, component_data in results.items():
                if 'components' in component_data and component_data['components']:
                    # Format display name
                    display_name = component_name.replace('_', ' ').title()
                    output += f"║ {display_name} Analysis:                                         ║\n"
                    
                    # Create mini-table for component details
                    output += "║ ┌──────────────────────┬─────────┬──────────────────────┐ ║\n"
                    output += "║ │ Indicator            │ Score   │ Gauge                │ ║\n"
                    output += "║ ├──────────────────────┼─────────┼──────────────────────┤ ║\n"
                    
                    # Sort sub-components by score
                    sorted_subcomponents = sorted(
                        component_data['components'].items(),
                        key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                        reverse=True
                    )
                    
                    for sub_name, sub_score in sorted_subcomponents:
                        if isinstance(sub_score, (int, float)):
                            # Format sub-component name
                            sub_display_name = sub_name.replace('_', ' ').title()
                            sub_display_name = f"{sub_display_name:<20}"
                            
                            # Create mini-gauge for sub-component
                            mini_gauge = self._create_mini_gauge(sub_score)
                            
                            output += f"║ │ {sub_display_name} │ {sub_score:.2f}   │ {mini_gauge} │ ║\n"
                    
                    output += "║ └──────────────────────┴─────────┴──────────────────────┘ ║\n"
        
        # Add potential interpretations
        has_interpretations = False
        for component_name, component_data in results.items():
            if 'interpretation' in component_data:
                has_interpretations = True
                break
        
        if has_interpretations:
            output += "╠══════════════════════════════════════════════════════════════╣\n"
            output += "║ MARKET INTERPRETATION:                                      ║\n"
            
            for component_name, component_data in results.items():
                if 'interpretation' in component_data:
                    interp = component_data['interpretation']
                    display_name = component_name.replace('_', ' ').title()
                    
                    if isinstance(interp, dict):
                        if 'summary' in interp:
                            output += f"║ • {display_name}: {interp['summary'][:45]}... ║\n"
                    else:
                        output += f"║ • {display_name}: {str(interp)[:45]}... ║\n"
        
        # Close the box
        output += "╚══════════════════════════════════════════════════════════════╝\n"
        
        # Add signal notice if above threshold
        if score >= 70:
            signal_type = "BULLISH" if score > 50 else "BEARISH"
            output += f"\nSIGNAL GENERATED: {signal_type} with {score:.2f} score\n"
        else:
            output += f"\nNo signal generated (threshold: 70.00)\n"
        
        return output

    def _create_fancy_gauge(self, value):
        """Create a fancy gauge bar for the dashboard.
        
        Args:
            value (float): Value to represent (0-100)
            
        Returns:
            str: Formatted gauge bar
        """
        gauge_width = 20
        filled = int((value / 100) * gauge_width)
        
        # Choose the character based on the value
        if value >= 70:
            char = "█"  # Solid block for strong bullish
        elif value >= 45:
            char = "█"  # Still solid but conceptually neutral
        else:
            char = "█"  # Still solid but conceptually bearish
        
        gauge = char * filled + "▒" * (gauge_width - filled)
        return gauge

    def _create_mini_gauge(self, value):
        """Create a smaller gauge bar for component details.
        
        Args:
            value (float): Value to represent (0-100)
            
        Returns:
            str: Formatted mini gauge bar
        """
        gauge_width = 15
        filled = int((value / 100) * gauge_width)
        
        # Simplified character for mini gauge
        gauge = "█" * filled + "▒" * (gauge_width - filled)
        return gauge

    def _get_trend_indicator(self, value):
        """Get a trend indicator based on the value.
        
        Args:
            value (float): Value to evaluate
            
        Returns:
            str: Trend indicator
        """
        if value >= 70:
            return "↑"  # Up arrow for bullish
        elif value >= 45:
            return "→"  # Right arrow for neutral
        else:
            return "↓"  # Down arrow for bearish

# For backwards compatibility and convenience
def format_analysis_result(analysis_result: Dict[str, Any], symbol_str: str, previous_result: Optional[Dict[str, Any]] = None) -> str:
    """
    Format analysis results with enhanced visualization.
    
    Args:
        analysis_result: The analysis result dictionary
        symbol_str: The symbol being analyzed
        previous_result: Previous analysis result for trend indicators
        
    Returns:
        str: Formatted analysis dashboard
    """
    return AnalysisFormatter.format_analysis_result(analysis_result, symbol_str, previous_result)

class LogFormatter:
    """
    Provides methods for formatting log messages with enhanced readability.
    """
    
    @staticmethod
    def format_score_contribution(component_name, score, weight, contribution):
        """Format component score contribution with visual elements."""
        # Color coding based on score
        if score >= 70:
            color = AnalysisFormatter.GREEN
        elif score >= 45:
            color = AnalysisFormatter.YELLOW
        else:
            color = AnalysisFormatter.RED
        
        # Create mini gauge (width 10)
        gauge_width = 10
        filled = int((score / 100) * gauge_width)
        gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
        gauge = gauge_char * filled + "·" * (gauge_width - filled)
        
        return f"{component_name:<15}: {color}{score:<6.2f}{AnalysisFormatter.RESET} × {weight:<4.2f} = {contribution:<6.2f} {color}{gauge}{AnalysisFormatter.RESET}"
    
    @staticmethod
    def format_component_analysis(component_name, score, status):
        """Format component analysis log with visual elements."""
        if "strong bullish" in status.lower():
            color = AnalysisFormatter.GREEN
            indicator = "↑↑"
        elif "bullish" in status.lower():
            color = AnalysisFormatter.GREEN
            indicator = "↑"
        elif "strong bearish" in status.lower():
            color = AnalysisFormatter.RED
            indicator = "↓↓"
        elif "bearish" in status.lower():
            color = AnalysisFormatter.RED
            indicator = "↓"
        else:
            color = AnalysisFormatter.YELLOW
            indicator = "→"
        
        # Create mini gauge (width 10)
        gauge_width = 10
        filled = int((score / 100) * gauge_width)
        gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
        gauge = gauge_char * filled + "·" * (gauge_width - filled)
            
        return f"{component_name:<15}: {color}{status:<15}{AnalysisFormatter.RESET} ({score:<6.2f}) {indicator} {color}{gauge}{AnalysisFormatter.RESET}"
    
    @staticmethod
    def format_section_header(title):
        """Format a section header for logs."""
        border = "═" * (len(title) + 8)
        return f"\n╔{border}╗\n║  {AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}  ║\n╚{border}╝"
    
    @staticmethod
    def format_calculation_detail(name, value, extra_info=""):
        """Format calculation detail log."""
        # Add color coding based on value
        if value >= 70:
            color = AnalysisFormatter.GREEN
            indicator = "↑"
        elif value >= 45:
            color = AnalysisFormatter.YELLOW
            indicator = "→"
        else:
            color = AnalysisFormatter.RED
            indicator = "↓"
            
        return f"{name}: Value={color}{value:.2f}{AnalysisFormatter.RESET} {indicator}{', ' + extra_info if extra_info else ''}"
    
    @staticmethod
    def format_final_score(name, score, symbol=""):
        """Format final score log with visual elements."""
        if score >= 70:
            color = AnalysisFormatter.GREEN
            status = "BULLISH"
        elif score >= 45:
            color = AnalysisFormatter.YELLOW
            status = "NEUTRAL"
        else:
            color = AnalysisFormatter.RED
            status = "BEARISH"
            
        gauge = AnalysisFormatter.create_gauge(score, width=30)
        
        # Include symbol in the title if provided
        title = f"{symbol} {name}" if symbol else name
        
        # Standardize box width to 80 characters for consistent alignment
        border = "═" * 80
        
        # Calculate padding to center the title and score
        title_text = f"{title} FINAL SCORE: {score:.2f} ({status})"
        padding = (80 - len(title_text) - 4) // 2  # -4 for the box corners/edges
        left_padding = " " * padding
        
        # Create the formatted box with consistent width
        return f"\n╔{border}╗\n║{left_padding}{title} FINAL SCORE: {color}{score:.2f}{AnalysisFormatter.RESET} ({status}){left_padding} ║\n║ {gauge} {' ' * (80 - len(gauge) - 4)} ║\n╚{border}╝"

    @staticmethod
    def format_score_contribution_section(title, contributions):
        """
        Format a complete score contribution section with header and individual contributions.
        
        Args:
            title: Section title
            contributions: List of (component_name, score, weight, contribution) tuples
        
        Returns:
            str: Formatted section with header and all contributions
        """
        # Calculate total contribution
        total_score = sum(contrib for _, _, _, contrib in contributions)
        
        # Format header with box drawing
        header = f"\n┌{'─' * 64}┐"
        header += f"\n│ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}{' ' * (62 - len(title))}│"
        header += f"\n├{'─' * 16}┬{'─' * 8}┬{'─' * 7}┬{'─' * 8}┬{'─' * 22}┤"
        header += f"\n│ {'COMPONENT':<14} │ {'SCORE':<6} │ {'WEIGHT':<5} │ {'CONTRIB':<6} │ {'GAUGE':<20} │"
        header += f"\n├{'─' * 16}┼{'─' * 8}┼{'─' * 7}┼{'─' * 8}┼{'─' * 22}┤"
        
        # Format each contribution
        formatted_contributions = []
        for component, score, weight, contribution in contributions:
            # Color based on score
            if score >= 70:
                color = AnalysisFormatter.GREEN
            elif score >= 45:
                color = AnalysisFormatter.YELLOW
            else:
                color = AnalysisFormatter.RED
                
            # Create gauge
            gauge_width = 20
            filled = int((score / 100) * gauge_width)
            gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
            gauge = gauge_char * filled + "·" * (gauge_width - filled)
            
            # Format line
            line = f"│ {component:<14} │ {color}{score:<6.2f}{AnalysisFormatter.RESET} │ {weight:<5.2f} │ {contribution:<6.2f} │ {color}{gauge}{AnalysisFormatter.RESET} │"
            formatted_contributions.append(line)
        
        # Format footer with total
        footer = f"├{'─' * 16}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 22}┤"
        
        # Add total score at the bottom
        if total_score >= 70:
            total_color = AnalysisFormatter.GREEN
            status = "BULLISH"
        elif total_score >= 45:
            total_color = AnalysisFormatter.YELLOW
            status = "NEUTRAL"
        else:
            total_color = AnalysisFormatter.RED
            status = "BEARISH"
            
        total_gauge = AnalysisFormatter.create_gauge(total_score, width=20)
        
        footer += f"\n│ {'FINAL SCORE':<14} │ {total_color}{total_score:<6.2f}{AnalysisFormatter.RESET} │ {' ' * 5} │ {' ' * 6} │ {total_gauge} │"
        footer += f"\n└{'─' * 16}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 22}┘"
        
        # Combine all parts
        return header + "\n" + "\n".join(formatted_contributions) + "\n" + footer
        
    @staticmethod
    def format_component_analysis_section(title, components, detailed=False):
        """
        Format a complete component analysis section with header and individual components.
        
        Args:
            title: Section title
            components: List of (component_name, score, status) tuples
            detailed: Whether to include additional details
            
        Returns:
            str: Formatted section with header and all components
        """
        # Format header with box drawing
        header = f"\n┌{'─' * 64}┐"
        header += f"\n│ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}{' ' * (62 - len(title))}│"
        
        if detailed:
            header += f"\n├{'─' * 16}┬{'─' * 17}┬{'─' * 8}┬{'─' * 20}┤"
            header += f"\n│ {'COMPONENT':<14} │ {'STATUS':<15} │ {'SCORE':<6} │ {'GAUGE':<18} │"
            header += f"\n├{'─' * 16}┼{'─' * 17}┼{'─' * 8}┼{'─' * 20}┤"
        else:
            header += f"\n├{'─' * 16}┬{'─' * 17}┬{'─' * 8}┬{'─' * 3}┬{'─' * 15}┤"
            header += f"\n│ {'COMPONENT':<14} │ {'STATUS':<15} │ {'SCORE':<6} │ {'⬤':<1} │ {'INTERPRETATION':<13} │"
            header += f"\n├{'─' * 16}┼{'─' * 17}┼{'─' * 8}┼{'─' * 3}┼{'─' * 15}┤"
        
        # Format each component
        formatted_components = []
        for component, score, status in components:
            # Get color based on status
            if "strong bullish" in status.lower():
                color = AnalysisFormatter.GREEN
                indicator = "↑↑"
            elif "bullish" in status.lower():
                color = AnalysisFormatter.GREEN
                indicator = "↑"
            elif "strong bearish" in status.lower():
                color = AnalysisFormatter.RED
                indicator = "↓↓"
            elif "bearish" in status.lower():
                color = AnalysisFormatter.RED
                indicator = "↓"
            else:
                color = AnalysisFormatter.YELLOW
                indicator = "→"
                
            # Set indicator color
            if score >= 70:
                dot_color = AnalysisFormatter.GREEN
            elif score >= 45:
                dot_color = AnalysisFormatter.YELLOW
            else:
                dot_color = AnalysisFormatter.RED
                
            # Create gauge if detailed
            if detailed:
                gauge_width = 18
                filled = int((score / 100) * gauge_width)
                gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
                gauge = gauge_char * filled + "·" * (gauge_width - filled)
                
                line = f"│ {component:<14} │ {color}{status:<15}{AnalysisFormatter.RESET} │ {score:<6.2f} │ {color}{gauge}{AnalysisFormatter.RESET} │"
            else:
                # Simple formatting with color dot
                line = f"│ {component:<14} │ {color}{status:<15}{AnalysisFormatter.RESET} │ {score:<6.2f} │ {dot_color}⬤{AnalysisFormatter.RESET} │ {indicator} {color}{status.split()[0]}{AnalysisFormatter.RESET} │"
                
            formatted_components.append(line)
        
        # Format footer
        if detailed:
            footer = f"└{'─' * 16}┴{'─' * 17}┴{'─' * 8}┴{'─' * 20}┘"
        else:
            footer = f"└{'─' * 16}┴{'─' * 17}┴{'─' * 8}┴{'─' * 3}┴{'─' * 15}┘"
        
        # Combine all parts
        return header + "\n" + "\n".join(formatted_components) + "\n" + footer
                
    @staticmethod
    def format_technical_value(name, value, threshold_high=70, threshold_low=45):
        """
        Format a technical indicator value with color coding.
        
        Args:
            name: Indicator name
            value: Indicator value
            threshold_high: Threshold for high values (default: 70)
            threshold_low: Threshold for low values (default: 45)
            
        Returns:
            str: Formatted indicator value with color coding
        """
        # Determine color based on thresholds
        if value >= threshold_high:
            color = AnalysisFormatter.GREEN
            indicator = "↑"
        elif value >= threshold_low:
            color = AnalysisFormatter.YELLOW
            indicator = "→"
        else:
            color = AnalysisFormatter.RED
            indicator = "↓"
            
        # Format with color
        return f"{name}: {color}{value:.2f}{AnalysisFormatter.RESET} {indicator}"
        
    @staticmethod
    def format_detailed_calculation(title, metrics):
        """
        Format detailed calculation metrics with enhanced visualization.
        
        Args:
            title: Title for the calculation details section
            metrics: Dictionary of metric name -> value
            
        Returns:
            str: Formatted calculation details
        """
        # Format header with box drawing
        header = f"\n┌{'─' * 60}┐"
        header += f"\n│ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}{' ' * (58 - len(title))}│"
        header += f"\n├{'─' * 30}┬{'─' * 28}┤"
        header += f"\n│ {'METRIC':<28} │ {'VALUE':<26} │"
        header += f"\n├{'─' * 30}┼{'─' * 28}┤"
        
        # Format each metric
        formatted_metrics = []
        for metric, value in metrics.items():
            # Format metric name
            display_name = metric.replace('_', ' ').title()
            if len(display_name) > 28:
                display_name = display_name[:25] + "..."
            
            # Format value based on type
            if isinstance(value, float):
                # Color based on value if it's a score (between 0-100)
                if 0 <= value <= 100:
                    if value >= 70:
                        color = AnalysisFormatter.GREEN
                    elif value >= 45:
                        color = AnalysisFormatter.YELLOW
                    else:
                        color = AnalysisFormatter.RED
                    formatted_value = f"{color}{value:<26.2f}{AnalysisFormatter.RESET}"
                else:
                    # Regular float, no color
                    formatted_value = f"{value:<26.4f}"
            else:
                # Non-float value, just convert to string
                formatted_value = f"{str(value):<26}"
            
            # Format line
            line = f"│ {display_name:<28} │ {formatted_value} │"
            formatted_metrics.append(line)
        
        # Format footer
        footer = f"└{'─' * 30}┴{'─' * 28}┘"
        
        # Combine all parts
        return header + "\n" + "\n".join(formatted_metrics) + "\n" + footer

    @staticmethod
    def format_validation_result(component, is_valid, details=None):
        """
        Format validation result with color coding.
        
        Args:
            component: Component being validated
            is_valid: Whether validation passed
            details: Optional validation details
            
        Returns:
            str: Formatted validation result
        """
        if is_valid:
            status = f"{AnalysisFormatter.GREEN}✓ VALID{AnalysisFormatter.RESET}"
        else:
            status = f"{AnalysisFormatter.RED}✗ INVALID{AnalysisFormatter.RESET}"
            
        result = f"Validation for {AnalysisFormatter.BOLD}{component}{AnalysisFormatter.RESET}: {status}"
        
        if details:
            result += f"\n  {details}"
            
        return result

    @staticmethod
    def format_component_analysis(title, components):
        """
        Format component analysis with enhanced visualization.
        
        Args:
            title: Title for the component analysis
            components: Dictionary of component scores
            
        Returns:
            str: Formatted component analysis
        """
        # Format header with box drawing
        header = f"\n┌{'─' * 60}┐"
        header += f"\n│ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}{' ' * (58 - len(title))}│"
        header += f"\n├{'─' * 25}┬{'─' * 10}┬{'─' * 23}┤"
        header += f"\n│ {'COMPONENT':<23} │ {'SCORE':<8} │ {'GAUGE':<21} │"
        header += f"\n├{'─' * 25}┼{'─' * 10}┼{'─' * 23}┤"
        
        # Format each component
        formatted_components = []
        for component, score in sorted(components.items(), key=lambda x: x[1], reverse=True):
            # Format component name
            display_name = component.replace('_', ' ').title()
            if len(display_name) > 23:
                display_name = display_name[:20] + "..."
            
            # Color based on score
            if score >= 70:
                color = AnalysisFormatter.GREEN
            elif score >= 45:
                color = AnalysisFormatter.YELLOW
            else:
                color = AnalysisFormatter.RED
                
            # Create gauge
            gauge_width = 21
            filled = int((score / 100) * gauge_width)
            
            # Use the same characters as in create_gauge for consistency
            if score >= 70:
                gauge_char = "█"  # Solid block for bullish
            elif score >= 45:
                gauge_char = "▓"  # Medium-density dotted for neutral
            else:
                gauge_char = "░"  # Low-density dotted for bearish
                
            gauge = gauge_char * filled + "·" * (gauge_width - filled)
            
            # Format line
            line = f"│ {display_name:<23} │ {color}{score:<8.2f}{AnalysisFormatter.RESET} │ {color}{gauge}{AnalysisFormatter.RESET} │"
            formatted_components.append(line)
        
        # Format footer
        footer = f"└{'─' * 25}┴{'─' * 10}┴{'─' * 23}┘"
        
        # Combine all parts
        return header + "\n" + "\n".join(formatted_components) + "\n" + footer 