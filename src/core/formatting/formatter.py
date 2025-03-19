"""
Formatter for analysis results.

This module provides utility functions and classes for formatting analysis results
in a visually appealing way.
"""

import datetime
from typing import Dict, Any, Optional

class AnalysisFormatter:
    """Formatter for analysis results with enhanced visualizations.
    
    This class provides methods to format analysis results in a visually
    appealing way, including component breakdowns, gauges, and trend indicators.
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
    
    def __init__(self):
        """Initialize the AnalysisFormatter."""
        pass
    
    def get_color_code(self, value):
        """Get color code based on score value.
        
        Args:
            value (float): Score value
            
        Returns:
            str: ANSI color code
        """
        if value >= 70:
            return "\033[92m"  # Green for bullish
        elif value >= 45:
            return "\033[93m"  # Yellow for neutral
        else:
            return "\033[91m"  # Red for bearish
    
    @classmethod
    def create_gauge(cls, value, width=20):
        """Create ASCII gauge representation of value.
        
        Args:
            value (float): Value to represent (0-100)
            width (int, optional): Width of the gauge. Defaults to 20.
            
        Returns:
            str: ASCII gauge with appropriate coloring
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
                    bar_char = "▒"  # Medium block for neutral
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
        reliability_text = f"Reliability: {self.get_color_code(reliability)}{reliability:.2f}{self.RESET} ({'HIGH' if reliability >= 0.8 else 'MEDIUM' if reliability >= 0.5 else 'LOW'})"
        reliability_padding = 56 - len(reliability_text) + len(self.get_color_code(reliability)) + len(self.RESET)
        output += f"║ {reliability_text}{' ' * reliability_padding}║\n"
        
        # Add detailed component breakdown if available
        has_detailed_components = False
        for component_name, component_data in results.items():
            # Skip non-dictionary component data
            if not isinstance(component_data, dict):
                continue
            
            if 'components' in component_data and component_data['components'] and isinstance(component_data['components'], dict):
                has_detailed_components = True
                break
        
        if has_detailed_components:
            output += "\n╠══════════════════════════════════════════════════════════════╣\n"
            output += "║ DETAILED COMPONENT BREAKDOWN:                                ║\n"
            
            # Add details for each component that has sub-components
            for component_name, component_data in results.items():
                # Skip non-dictionary component data
                if not isinstance(component_data, dict):
                    continue
                    
                if 'components' in component_data and component_data['components'] and isinstance(component_data['components'], dict):
                    # Format display name
                    display_name = component_name.replace('_', ' ').title()
                    output += f"║ {display_name} Analysis:                                         ║\n"
                    
                    # Create mini-table for component details
                    output += "║ ┌──────────────────────┬─────────┬──────────────────────┐ ║\n"
                    output += "║ │ Indicator            │ Score   │ Gauge                │ ║\n"
                    output += "║ ├──────────────────────┼─────────┼──────────────────────┤ ║\n"
                    
                    # Sort sub-components by score
                    sorted_subcomponents = []
                    try:
                        sorted_subcomponents = sorted(
                            component_data['components'].items(),
                            key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
                            reverse=True
                        )
                    except (TypeError, ValueError, AttributeError) as e:
                        # Log warning but continue with empty sorted_subcomponents
                        # This avoids breaking the entire report if one component is malformed
                        sorted_subcomponents = []
                    
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
            output += "\n╠══════════════════════════════════════════════════════════════╣\n"
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
    """Format analysis results with enhanced visualization (convenience function).
    
    This is a convenience wrapper around the AnalysisFormatter.format_analysis_result method.
    
    Args:
        analysis_result (dict): Analysis result data
        symbol_str (str): Symbol being analyzed
        previous_result (dict, optional): Previous analysis result for comparison
        
    Returns:
        str: Formatted analysis output
    """
    formatter = AnalysisFormatter()
    return formatter.format_analysis_result(analysis_result, symbol_str)

class LogFormatter:
    """
    Provides methods for formatting log messages with enhanced readability.
    """
    
    # Reference to AnalysisFormatter attributes for consistency
    GREEN = AnalysisFormatter.GREEN
    YELLOW = AnalysisFormatter.YELLOW
    RED = AnalysisFormatter.RED
    CYAN = AnalysisFormatter.CYAN
    BLUE = AnalysisFormatter.BLUE
    MAGENTA = AnalysisFormatter.MAGENTA
    BOLD = AnalysisFormatter.BOLD
    RESET = AnalysisFormatter.RESET
    
    @staticmethod
    def format_score_contribution(component_name, score, weight, contribution):
        """Format a single score contribution with visual elements."""
        # Color based on score
        if score >= 70:
            color = AnalysisFormatter.GREEN
        elif score >= 45:
            color = AnalysisFormatter.YELLOW
        else:
            color = AnalysisFormatter.RED
            
        # Create gauge with consistent width
        gauge_width = 20
        filled = int((score / 100) * gauge_width)
        gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
        gauge = gauge_char * filled + "·" * (gauge_width - filled)
        
        # Format with consistent spacing for impact value
        impact_str = f"{contribution:6.1f}"  # Fixed width with 1 decimal place for better alignment
        line = f"{component_name:<15}: {color}{score:<6.2f}{AnalysisFormatter.RESET} × {weight:<4.2f} = {impact_str} {color}{gauge}{AnalysisFormatter.RESET}"
        return line
    
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
    def format_score_contribution_section(title, contributions, symbol="", divergence_adjustments=None, final_score=None):
        """
        Format a complete score contribution section with header and individual contributions.
        
        Args:
            title: Section title
            contributions: List of (component_name, score, weight, contribution) tuples
            symbol: Optional symbol to include in the title
            divergence_adjustments: Optional dict of components with divergence adjustments {component: adjustment}
            final_score: Optional final score to override the calculated sum
        
        Returns:
            str: Formatted section with header and all contributions
        """
        # Calculate total contribution for reference only
        calculated_sum = sum(contrib for _, _, _, contrib in contributions)
        
        # ALWAYS use the provided final score if available, otherwise use the calculated sum
        # This ensures the final score in the breakdown matches the timeframe analysis score
        total_score = final_score if final_score is not None else calculated_sum
        
        # Include symbol in the title if provided
        display_title = f"{symbol} {title}" if symbol else title
        
        # Check if we need to add a column for divergences
        has_divergences = divergence_adjustments and any(divergence_adjustments.values())
        column_width = 8 if has_divergences else 0
        
        # Standardize box width to 80 characters for consistent alignment with final score box
        header = f"\n┌{'─' * 80}┐"
        header += f"\n│ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{display_title}{AnalysisFormatter.RESET}{' ' * (78 - len(display_title))}│"
        
        if has_divergences:
            # Include divergence column
            header += f"\n├{'─' * 20}┬{'─' * 8}┬{'─' * 7}┬{'─' * 8}┬{'─' * 8}┬{'─' * 26}┤"
            header += f"\n│ {'COMPONENT':<18} │ {'SCORE':<6} │ {'WEIGHT':<5} │ {'IMPACT':<6} │ {'DIV':<6} │ {'GAUGE':<24} │"
            header += f"\n├{'─' * 20}┼{'─' * 8}┼{'─' * 7}┼{'─' * 8}┼{'─' * 8}┼{'─' * 26}┤"
        else:
            # Original format without divergence column
            header += f"\n├{'─' * 20}┬{'─' * 8}┬{'─' * 7}┬{'─' * 8}┬{'─' * 34}┤"
            header += f"\n│ {'COMPONENT':<18} │ {'SCORE':<6} │ {'WEIGHT':<5} │ {'IMPACT':<6} │ {'GAUGE':<32} │"
            header += f"\n├{'─' * 20}┼{'─' * 8}┼{'─' * 7}┼{'─' * 8}┼{'─' * 34}┤"
        
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
                
            # Create gauge with consistent width and characters
            gauge_width = 24 if has_divergences else 32  # Adjusted width if showing divergences
            filled = int((score / 100) * gauge_width)
            
            # Use the same characters as in create_gauge for consistency
            if score >= 70:
                gauge_char = "█"  # Solid block for bullish
            elif score >= 45:
                gauge_char = "▓"  # Medium-density dotted for neutral
            else:
                gauge_char = "░"  # Low-density dotted for bearish
                
            gauge = gauge_char * filled + "·" * (gauge_width - filled)
            
            # Format divergence adjustment if available
            div_part = ""
            if has_divergences:
                div_value = divergence_adjustments.get(component, 0.0)
                
                # Determine color and prefix for divergence
                if div_value > 0:
                    div_color = AnalysisFormatter.GREEN
                    div_display = f"+{div_value:.1f}"
                elif div_value < 0:
                    div_color = AnalysisFormatter.RED
                    div_display = f"{div_value:.1f}"
                else:
                    div_color = AnalysisFormatter.RESET
                    div_display = "0.0"
                
                div_part = f" │ {div_color}{div_display:<6}{AnalysisFormatter.RESET}"
            
            # Format line with increased component width and fixed decimal places for better alignment
            # Use a consistent format for the contribution value to ensure proper alignment
            impact_str = f"{contribution:6.1f}"  # Fixed width with 1 decimal place for better alignment
            
            if has_divergences:
                line = f"│ {component:<18} │ {color}{score:<6.2f}{AnalysisFormatter.RESET} │ {weight:<5.2f} │ {impact_str}{div_part} │ {color}{gauge}{AnalysisFormatter.RESET} │"
            else:
                line = f"│ {component:<18} │ {color}{score:<6.2f}{AnalysisFormatter.RESET} │ {weight:<5.2f} │ {impact_str} │ {color}{gauge}{AnalysisFormatter.RESET} │"
            
            formatted_contributions.append(line)
        
        # Format footer with total
        if has_divergences:
            footer = f"├{'─' * 20}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 8}┴{'─' * 26}┤"
        else:
            footer = f"├{'─' * 20}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 34}┤"
        
        # Add total score at the bottom - use the provided final_score
        if total_score >= 70:
            total_color = AnalysisFormatter.GREEN
            status = "BULLISH"
        elif total_score >= 45:
            total_color = AnalysisFormatter.YELLOW
            status = "NEUTRAL"
        else:
            total_color = AnalysisFormatter.RED
            status = "BEARISH"
            
        # Create gauge with same style as individual components
        gauge_width = 24 if has_divergences else 32  # Adjusted width if showing divergences
        filled = int((total_score / 100) * gauge_width)
        if total_score >= 70:
            gauge_char = "█"
        elif total_score >= 45:
            gauge_char = "▓"
        else:
            gauge_char = "░"
            
        total_gauge = gauge_char * filled + "·" * (gauge_width - filled)
        
        # Calculate total divergence adjustment if available
        div_total_part = ""
        if has_divergences:
            total_adjustment = sum(divergence_adjustments.values())
            
            # Determine color and prefix for total divergence
            if total_adjustment > 0:
                div_total_color = AnalysisFormatter.GREEN
                div_total_display = f"+{total_adjustment:.1f}"
            elif total_adjustment < 0:
                div_total_color = AnalysisFormatter.RED
                div_total_display = f"{total_adjustment:.1f}"
            else:
                div_total_color = AnalysisFormatter.RESET
                div_total_display = "0.0"
                
            div_total_part = f" │ {div_total_color}{div_total_display:<6}{AnalysisFormatter.RESET}"
        
        # Format the final score line
        if has_divergences:
            footer += f"\n│ {'FINAL SCORE':<18} │ {total_color}{total_score:<6.2f}{AnalysisFormatter.RESET} │ {' ' * 5} │ {' ' * 6}{div_total_part} │ {total_color}{total_gauge}{AnalysisFormatter.RESET} │"
            footer += f"\n└{'─' * 20}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 8}┴{'─' * 26}┘"
            
            # Add legend for divergence adjustment column if there are non-zero adjustments
            if any(divergence_adjustments.values()):
                footer += f"\n* DIV column shows timeframe divergence adjustments"
        else:
            footer += f"\n│ {'FINAL SCORE':<18} │ {total_color}{total_score:<6.2f}{AnalysisFormatter.RESET} │ {' ' * 5} │ {' ' * 6} │ {total_color}{total_gauge}{AnalysisFormatter.RESET} │"
            footer += f"\n└{'─' * 20}┴{'─' * 8}┴{'─' * 7}┴{'─' * 8}┴{'─' * 34}┘"
        
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

    @staticmethod
    def format_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0):
        """
        Format a comprehensive table for the overall confluence score components,
        including top influential individual components and market interpretations.
        
        Args:
            symbol: Trading symbol
            confluence_score: Overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed results for each component
            weights: Optional dictionary of component weights
            reliability: Reliability score of the analysis (0.0-1.0)
            
        Returns:
            str: Formatted table with comprehensive analysis
        """
        # Set table width - ensure it's consistent throughout
        table_width = 80
        
        # Determine overall market bias
        if confluence_score >= 70:
            overall_status = "BULLISH"
            overall_color = AnalysisFormatter.GREEN
        elif confluence_score >= 45:
            overall_status = "NEUTRAL"
            overall_color = AnalysisFormatter.YELLOW
        else:
            overall_status = "BEARISH"
            overall_color = AnalysisFormatter.RED
            
        # Calculate weighted contributions if weights are provided
        contributions = []
        if weights:
            for component, score in components.items():
                weight = weights.get(component, 0)
                contribution = score * weight
                contributions.append((component, score, weight, contribution))
        else:
            # Estimate equal weights if not provided
            weight = 1.0 / max(len(components), 1)
            for component, score in components.items():
                contribution = score * weight
                contributions.append((component, score, weight, contribution))
                
        # Sort contributions by impact (descending)
        contributions.sort(key=lambda x: x[3], reverse=True)
        
        # Format header with box drawing
        header = f"\n╔{'═' * table_width}╗"
        title = f"{symbol} CONFLUENCE ANALYSIS BREAKDOWN"
        padding = table_width - len(title) - 2  # -2 for the border characters
        header += f"\n║ {AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Overall score line
        score_text = f"OVERALL SCORE: {overall_color}{confluence_score:.2f}{AnalysisFormatter.RESET} ({overall_status})"
        padding = table_width - len(score_text) - 2 + len(overall_color) + len(AnalysisFormatter.RESET)  # Account for color codes
        header += f"\n║ {AnalysisFormatter.BOLD}{score_text}{' ' * padding}║"
        
        # Add reliability score line
        # Color code reliability
        if reliability >= 0.8:
            reliability_color = AnalysisFormatter.GREEN
            reliability_status = "HIGH"
        elif reliability >= 0.5:
            reliability_color = AnalysisFormatter.YELLOW
            reliability_status = "MEDIUM"
        else:
            reliability_color = AnalysisFormatter.RED
            reliability_status = "LOW"
            
        # Convert reliability to percentage
        reliability_pct = reliability * 100
        reliability_text = f"RELIABILITY: {reliability_color}{reliability_pct:.0f}%{AnalysisFormatter.RESET} ({reliability_status})"
        reliability_padding = table_width - len(reliability_text) - 2 + len(reliability_color) + len(AnalysisFormatter.RESET)
        header += f"\n║ {AnalysisFormatter.BOLD}{reliability_text}{' ' * reliability_padding}║"
        
        # Component columns widths - ensure they add up to table_width - 7
        comp_width = 20
        score_width = 8
        impact_width = 8
        gauge_width = table_width - comp_width - score_width - impact_width - 7  # -7 for borders and spaces
        
        # Create main components section
        header += f"\n╠{'═' * comp_width}╦{'═' * score_width}╦{'═' * impact_width}╦{'═' * gauge_width}╣"
        header += f"\n║ {'COMPONENT':<{comp_width-2}} ║ {'SCORE':<{score_width-2}} ║ {'IMPACT':<{impact_width-2}} ║ {'GAUGE':<{gauge_width-2}} ║"
        header += f"\n╠{'═' * comp_width}╬{'═' * score_width}╬{'═' * impact_width}╬{'═' * gauge_width}╣"
        
        # Format each main component
        component_lines = []
        for component, score, weight, contribution in contributions:
            # Format component name
            display_name = component.replace('_', ' ').title()
            if len(display_name) > comp_width-2:
                display_name = display_name[:comp_width-5] + "..."
                
            # Color based on score
            if score >= 70:
                color = AnalysisFormatter.GREEN
            elif score >= 45:
                color = AnalysisFormatter.YELLOW
            else:
                color = AnalysisFormatter.RED
                
            # Create gauge
            filled = int((score / 100) * (gauge_width-2))
            
            # Use the same characters as in create_gauge for consistency
            if score >= 70:
                gauge_char = "█"  # Solid block for bullish
            elif score >= 45:
                gauge_char = "▓"  # Medium-density dotted for neutral
            else:
                gauge_char = "░"  # Low-density dotted for bearish
                
            gauge = gauge_char * filled + "·" * ((gauge_width-2) - filled)
            
            # Format line
            impact_str = f"{contribution:.1f}"
            line = f"║ {display_name:<{comp_width-2}} ║ {color}{score:<{score_width-2}.2f}{AnalysisFormatter.RESET} ║ {impact_str:<{impact_width-2}} ║ {color}{gauge}{AnalysisFormatter.RESET} ║"
            component_lines.append(line)
            
        # Add top influential individual components section
        header += "\n" + "\n".join(component_lines)
        header += f"\n╠{'═' * comp_width}╩{'═' * score_width}╩{'═' * impact_width}╩{'═' * gauge_width}╣"
        
        # Top components section title
        title = f"{AnalysisFormatter.BOLD}TOP INFLUENTIAL INDIVIDUAL COMPONENTS{AnalysisFormatter.RESET}"
        padding = table_width - len(title) - 2 + len(AnalysisFormatter.BOLD) + len(AnalysisFormatter.RESET)
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Find top 3 components from each indicator
        top_components_section = []
        for indicator_name, indicator_data in results.items():
            # Skip if indicator_data is not a dictionary/mapping
            if not isinstance(indicator_data, dict):
                continue
                
            if 'components' in indicator_data and indicator_data['components'] and isinstance(indicator_data['components'], dict):
                # Get indicator score
                indicator_score = indicator_data.get('score', 0)
                
                # Determine color based on score
                if indicator_score >= 70:
                    indicator_color = AnalysisFormatter.GREEN
                elif indicator_score >= 45:
                    indicator_color = AnalysisFormatter.YELLOW
                else:
                    indicator_color = AnalysisFormatter.RED
                
                # Format indicator name
                display_name = indicator_name.replace('_', ' ').title()
                
                # Add indicator header with proper padding
                indicator_text = f"{indicator_color}{display_name}{AnalysisFormatter.RESET} ({indicator_score:.2f})"
                padding = table_width - len(display_name) - len(f" ({indicator_score:.2f})") - 2
                top_components_section.append(f"║ {indicator_text}{' ' * padding}║")
                
                # Sort components by score
                sorted_components = []
                try:
                    # Check if components exists and is a dictionary
                    if 'components' in indicator_data and isinstance(indicator_data['components'], dict):
                        sorted_components = sorted(
                            indicator_data['components'].items(),
                            key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
                            reverse=True
                        )
                    elif isinstance(indicator_data, dict):
                        # Try to find other potential component data
                        for key, value in indicator_data.items():
                            if isinstance(value, dict) and 'score' in value:
                                sorted_components.append((key, value.get('score', 0)))
                        
                        # Sort the collected components
                        sorted_components.sort(key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0, reverse=True)
                except (TypeError, ValueError, AttributeError) as e:
                    # This avoids breaking the entire report if one component is malformed
                    sorted_components = []
                
                # Take top 3 components
                for i, (comp_name, comp_score) in enumerate(sorted_components[:3]):
                    if isinstance(comp_score, (int, float)):
                        # Format component name
                        comp_display_name = comp_name.replace('_', ' ').title()
                        
                        # Determine color based on score
                        if comp_score >= 70:
                            comp_color = AnalysisFormatter.GREEN
                            indicator = "↑"
                        elif comp_score >= 45:
                            comp_color = AnalysisFormatter.YELLOW
                            indicator = "→"
                        else:
                            comp_color = AnalysisFormatter.RED
                            indicator = "↓"
                            
                        # Create mini gauge (15 chars wide)
                        mini_gauge_width = 15
                        filled = int((comp_score / 100) * mini_gauge_width)
                        gauge_char = "█" if comp_score >= 70 else "▓" if comp_score >= 45 else "░"
                        gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                        
                        # Format line with fixed width for consistent alignment
                        comp_line = f"  • {comp_display_name:<20}: {comp_color}{comp_score:<6.2f}{AnalysisFormatter.RESET} {indicator} {comp_color}{gauge}{AnalysisFormatter.RESET}"
                        
                        # Calculate visible length (without color codes)
                        visible_length = len(f"  • {comp_display_name:<20}: {comp_score:<6.2f} {indicator} {gauge}")
                        
                        # Calculate padding to align right border
                        padding = table_width - visible_length - 2
                        
                        # Ensure padding is not negative
                        padding = max(0, padding)
                        
                        line = f"║{comp_line}{' ' * padding}║"
                        top_components_section.append(line)
                
                # Add separator between indicators
                top_components_section.append(f"║{' ' * table_width}║")
        
        # Add market interpretations section
        header += "\n" + "\n".join(top_components_section)
        header += f"\n╠{'═' * table_width}╣"
        
        # Market interpretations title
        title = f"{AnalysisFormatter.BOLD}MARKET INTERPRETATIONS{AnalysisFormatter.RESET}"
        padding = table_width - len(title) - 2 + len(AnalysisFormatter.BOLD) + len(AnalysisFormatter.RESET)
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Extract interpretations from results - use the interpretation field directly for more detailed insights
        interpretations = []
        for indicator_name, indicator_data in results.items():
            display_name = indicator_name.replace('_', ' ').title()
            interp_str = None
            
            # Check if indicator_data is a dictionary before trying to access keys
            if not isinstance(indicator_data, dict):
                # Skip non-dictionary values to prevent errors
                continue
                
            # First try to get the interpretation from the interpretation field
            if 'interpretation' in indicator_data:
                interp = indicator_data['interpretation']
                if isinstance(interp, dict) and 'summary' in interp:
                    interp_str = interp['summary']
                elif isinstance(interp, str):
                    interp_str = interp  # Use the full interpretation string
            
            # If no interpretation found but we have signals, use those
            if not interp_str and 'signals' in indicator_data:
                signals = indicator_data['signals']
                if isinstance(signals, dict):
                    signal_parts = []
                    for signal_name, signal_data in signals.items():
                        if isinstance(signal_data, dict) and 'signal' in signal_data:
                            signal_parts.append(f"{signal_name}={signal_data['signal']}")
                        elif isinstance(signal_data, (str, int, float, bool)):
                            # Handle primitive value signals
                            signal_parts.append(f"{signal_name}={signal_data}")
                    if signal_parts:
                        interp_str = ", ".join(signal_parts)
                elif isinstance(signals, list) and signals:
                    # Handle list of signals
                    interp_str = ", ".join(str(s) for s in signals if s is not None)
                elif signals is not None:
                    # Handle any other signal format
                    interp_str = str(signals)
            
            # If we found an interpretation, format and add it
            if interp_str:
                # For longer interpretations, split them into multiple lines for better readability
                # The max line length (with some padding for format characters)
                max_line_length = table_width - len(f" • {display_name}: ") - 5  
                
                if len(interp_str) > max_line_length:
                    # Split the interpretation into multiple lines if it's too long
                    interp_lines = []
                    remaining_text = interp_str
                    
                    # Add first line with the component name
                    first_line = f"• {display_name}: {remaining_text[:max_line_length]}"
                    interp_lines.append(first_line)
                    remaining_text = remaining_text[max_line_length:]
                    
                    # Add continuation lines if needed
                    while remaining_text:
                        continuation_line = f"  {remaining_text[:max_line_length]}"
                        interp_lines.append(continuation_line)
                        remaining_text = remaining_text[max_line_length:]
                    
                    # Format each line with proper padding
                    for i, line in enumerate(interp_lines):
                        padding = table_width - len(line) - 2
                        padding = max(0, padding)  # Ensure padding is not negative
                        interpretations.append(f"║ {line}{' ' * padding}║")
                else:
                    # For shorter interpretations, keep them on a single line
                    line = f"• {display_name}: {interp_str}"
                    padding = table_width - len(line) - 2
                    padding = max(0, padding)  # Ensure padding is not negative
                    interpretations.append(f"║ {line}{' ' * padding}║")
            
                # Add a small separator between components for readability
                interpretations.append(f"║{' ' * table_width}║")
        
        # Add interpretations to the output
        if interpretations:
            for interp in interpretations:
                header += f"\n{interp}"
        else:
            # If no interpretations were found, add a placeholder
            padding = table_width - len("No detailed interpretations available") - 2
            header += f"\n║ No detailed interpretations available{' ' * padding}║"
            
        # Add footer
        header += f"\n╚{'═' * table_width}╝"
        
        # Return the complete formatted table
        return header 

    @staticmethod
    def format_enhanced_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0):
        """
        Format a comprehensive table with enhanced market interpretations.
        
        This method uses the EnhancedFormatter to provide richer market interpretations,
        cross-component insights, and actionable trading insights.
        
        Args:
            symbol: Trading symbol
            confluence_score: Overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed results for each component
            weights: Optional dictionary of component weights
            reliability: Reliability score of the analysis (0.0-1.0)
            
        Returns:
            str: Formatted table with enhanced comprehensive analysis
        """
        from src.core.formatting.enhanced_formatter import EnhancedFormatter
        return EnhancedFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=reliability
        ) 