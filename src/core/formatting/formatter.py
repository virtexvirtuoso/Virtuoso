"""
Formatter for analysis results.

This module provides utility functions and classes for formatting analysis results
in a visually appealing way.
"""

import datetime
import textwrap
from typing import Dict, Any, Optional

# Import PrettyTable for clean table formatting - required dependency
from prettytable import PrettyTable, SINGLE_BORDER, DOUBLE_BORDER, DEFAULT, MARKDOWN

# Import our centralized interpretation system
try:
    from src.core.interpretation.interpretation_manager import InterpretationManager
except ImportError:
    # Fallback if not available
    InterpretationManager = None

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
        """Format analysis results with enhanced visualization using PrettyTable.
        
        Args:
            analysis_result (dict): Analysis result data
            symbol_str (str): Symbol being analyzed
            
        Returns:
            str: Formatted analysis output
        """
        if not analysis_result:
            return f"No analysis results available for {symbol_str}"
        
        # Use PrettyTableFormatter for consistent formatting with proper borders
        score = analysis_result.get('score', analysis_result.get('confluence_score', 0))
        reliability = analysis_result.get('reliability', 0)
        components = analysis_result.get('components', {})
        results = analysis_result.get('results', {})
        
        # Use the enhanced confluence score table which provides complete PrettyTable formatting
        formatted_output = PrettyTableFormatter.format_enhanced_confluence_score_table(
            symbol=symbol_str,
            confluence_score=score,
            components=components,
            results=results,
            weights=analysis_result.get('weights', None),
            reliability=reliability,
            border_style="double"  # Use double borders for main dashboard
        )
        
        # Add signal notice if above threshold (preserve existing logic)
        if score is not None and score >= 70:
            signal_type = "BULLISH" if score > 50 else "BEARISH"
            formatted_output += f"\nSIGNAL GENERATED: {signal_type} with {score:.2f} score\n"
        else:
            formatted_output += f"\nNo signal generated (threshold: 70.00)\n"
        
        return formatted_output

    def _create_fancy_gauge(self, value):
        """Create a fancy gauge bar for the dashboard.
        
        Args:
            value (float): Value to represent (0-100)
            
        Returns:
            str: Formatted gauge bar
        """
        gauge_width = 20
        filled = int((value / 100) * gauge_width)
        
        # Use characters matching the screenshot for better visual representation
        if value >= 70:
            gauge_char = "█"  # Solid block for bullish (green)
        elif value >= 45:
            gauge_char = "▓"  # Medium-density dotted for neutral (amber)
        else:
            gauge_char = "░"  # Low-density dotted for bearish (red)
        
        gauge = gauge_char * filled + "·" * ((gauge_width-2) - filled)
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
        
        # Create mini gauge (15 chars wide) with color-appropriate characters
        gauge_char = "█" if value >= 70 else "▓" if value >= 45 else "░"
        gauge = gauge_char * filled + "·" * (gauge_width - filled)
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
    def format_score_contribution_section(title, contributions, symbol="", divergence_adjustments=None, final_score=None, use_pretty_table=True, border_style="single"):
        """
        Formats a section with a detailed breakdown of score contributions using PrettyTable.
        
        Args:
            title: Section title
            contributions: List of (component_name, score, weight, contribution) tuples
            symbol: Optional symbol to include in the title
            divergence_adjustments: Optional dict of components with divergence adjustments {component: adjustment}
            final_score: Optional final score to display at the bottom.
            use_pretty_table: Always True - kept for compatibility
            border_style: Can be 'single' or 'double'.
        """
        # Always use PrettyTable - no fallback
        return PrettyTableFormatter.format_score_contribution_section(
            title, 
            contributions, 
            symbol, 
            divergence_adjustments,
            final_score,
            border_style=border_style
        )
        
    @staticmethod
    def format_component_analysis_section(title, components, detailed=False, use_pretty_table=True, border_style="single"):
        """
        Format a complete component analysis section with header and individual components using PrettyTable.
        
        Args:
            title: Section title
            components: List of (component_name, score, status) tuples
            detailed: Whether to include additional details
            use_pretty_table: Whether to use PrettyTable formatting (default: True)
            border_style: Border style for PrettyTable ("single", "double", "markdown")
            
        Returns:
            str: Formatted section with header and all components
        """
        if not PrettyTable or not use_pretty_table:
            # Fallback to manual formatting if PrettyTable not available
            return LogFormatter._format_component_analysis_section_manual(title, components, detailed)
        
        # Create PrettyTable for component analysis
        table = PrettyTable()
        
        # Set border style
        if border_style == "single" and SINGLE_BORDER:
            table.set_style(SINGLE_BORDER)
        elif border_style == "double" and DOUBLE_BORDER:
            table.set_style(DOUBLE_BORDER)
        elif border_style == "markdown" and MARKDOWN:
            table.set_style(MARKDOWN)
        else:
            table.set_style(DEFAULT if DEFAULT else None)
        
        # Set field names based on detailed flag
        if detailed:
            table.field_names = ["Component", "Status", "Score", "Gauge"]
            table.align["Component"] = "l"
            table.align["Status"] = "l"
            table.align["Score"] = "r"
            table.align["Gauge"] = "l"
        else:
            table.field_names = ["Component", "Status", "Score", "Trend", "Interpretation"]
            table.align["Component"] = "l"
            table.align["Status"] = "l"
            table.align["Score"] = "r"
            table.align["Trend"] = "c"
            table.align["Interpretation"] = "l"
        
        # Add component rows
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
            
            # Format status with color
            colored_status = f"{color}{status}{AnalysisFormatter.RESET}"
            
            if detailed:
                # Create gauge for detailed view
                gauge_width = 18
                filled = int((score / 100) * gauge_width)
                gauge_char = "█" if score >= 70 else "▓" if score >= 45 else "░"
                gauge = gauge_char * filled + "·" * (gauge_width - filled)
                colored_gauge = f"{color}{gauge}{AnalysisFormatter.RESET}"
                
                table.add_row([component, colored_status, f"{score:.2f}", colored_gauge])
            else:
                # Simple view with trend indicator
                interpretation = f"{indicator} {status.split()[0]}"
                table.add_row([component, colored_status, f"{score:.2f}", indicator, interpretation])
        
        # Create section with header
        output = []
        output.append(f"{AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}{title}{AnalysisFormatter.RESET}")
        output.append(str(table))
        
        return "\n".join(output)
    
    @staticmethod
    def _format_component_analysis_section_manual(title, components, detailed=False):
        """Fallback manual formatting method for component analysis."""
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
    def format_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0, extra_right_borders=0, use_pretty_table=True, border_style="double"):
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
            extra_right_borders: Number of extra right borders to add
            use_pretty_table: Whether to use PrettyTable formatting (default: False for backward compatibility)
            border_style: Border style for PrettyTable ("default", "single", "double", "markdown")
            
        Returns:
            str: Formatted table with comprehensive analysis
        """
        # Use PrettyTable if requested and available
        if use_pretty_table and PrettyTable:
            return PrettyTableFormatter.format_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                weights=weights,
                reliability=reliability,
                border_style=border_style
            )
        # Set table width - ensure it's consistent throughout
        table_width = 80
        
        # Get thresholds from results if available (coming from signal_data)
        buy_threshold = None
        sell_threshold = None
        
        # Try to get thresholds from signal_data first
        if isinstance(results, dict):
            if 'buy_threshold' in results:
                buy_threshold = float(results['buy_threshold'])
            if 'sell_threshold' in results:
                sell_threshold = float(results['sell_threshold'])
        
        # If not found in results, use default values
        if buy_threshold is None:
            buy_threshold = 60.0  # Default buy threshold
        if sell_threshold is None:
            sell_threshold = 40.0  # Default sell threshold
        
        # Determine overall market bias using the thresholds from config
        if confluence_score is not None and confluence_score >= buy_threshold:
            overall_status = "BULLISH"
            overall_color = AnalysisFormatter.GREEN
        elif confluence_score is not None and confluence_score >= sell_threshold:
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
        
        # Format header with box drawing - ensure consistent width
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
            
        # Normalize and convert reliability to percentage to avoid 10000% displays
        try:
            raw_rel = float(reliability)
        except Exception:
            raw_rel = 0.0
        normalized_rel = raw_rel / 100.0 if raw_rel > 1.0 else raw_rel
        normalized_rel = max(0.0, min(1.0, normalized_rel))
        reliability_pct = normalized_rel * 100
        reliability_text = f"RELIABILITY: {reliability_color}{reliability_pct:.0f}%{AnalysisFormatter.RESET} ({reliability_status})"
        reliability_padding = table_width - len(reliability_text) - 2 + len(reliability_color) + len(AnalysisFormatter.RESET)
        header += f"\n║ {AnalysisFormatter.BOLD}{reliability_text}{' ' * reliability_padding}║"
        
        # Component columns widths - ensure they add up to table_width - 7
        comp_width = 20
        score_width = 8
        impact_width = 8
        gauge_width = table_width - comp_width - score_width - impact_width - 7  # -7 for borders and spaces
        
        # Create main components section with consistent box drawing
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
            
            # Use characters matching the screenshot for better visual representation
            if score >= 70:
                gauge_char = "█"  # Solid block for bullish (green)
            elif score >= 45:
                gauge_char = "▓"  # Medium-density dotted for neutral (amber)
            else:
                gauge_char = "░"  # Low-density dotted for bearish (red)
                
            # Ensure we don't exceed the available width and add proper fill characters
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
        
        # First check for dedicated top_influential section
        if 'top_influential' in results and isinstance(results['top_influential'], dict):
            top_influential = results['top_influential']
            
            if 'components' in top_influential and isinstance(top_influential['components'], dict):
                components = top_influential['components']
                
                for comp_name, comp_score in components.items():
                    if isinstance(comp_score, (int, float)):
                        # Format component name
                        comp_display_name = comp_name.replace('_', ' ')
                        
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
                            
                        # Create mini gauge (15 chars wide) with color-appropriate characters
                        mini_gauge_width = 15
                        filled = int((comp_score / 100) * mini_gauge_width)
                        gauge_char = "█" if comp_score >= 70 else "▓" if comp_score >= 45 else "░"
                        gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                        
                        # Format the component display part with consistent padding (using 30 chars for better alignment)
                        comp_display_part = f"  • {comp_display_name:<30}: {comp_color}{comp_score:<6.2f}{AnalysisFormatter.RESET} {indicator} "
                        
                        # Calculate visible length (without color codes) for the display part
                        visible_display_length = len(f"  • {comp_display_name:<30}: {comp_score:<6.2f} {indicator} ")
                        
                        # Calculate how much space is left for the gauge
                        remaining_width = table_width - visible_display_length - 2  # -2 for the borders
                        
                        # Ensure the gauge fits in the remaining space
                        if remaining_width < mini_gauge_width:
                            mini_gauge_width = max(5, remaining_width)  # Minimum 5 chars for gauge readability
                            filled = int((comp_score / 100) * mini_gauge_width)
                            gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                        
                        # Calculate right-side padding to ensure proper alignment with the right border
                        right_padding = remaining_width - mini_gauge_width
                        
                        # Ensure consistent right edge alignment
                        line = f"║{comp_display_part}{comp_color}{gauge}{AnalysisFormatter.RESET}{' ' * right_padding}║"
                        top_components_section.append(line)
                
                # If we found top influential components, add spacing
                if top_components_section:
                    top_components_section.append(f"║{' ' * table_width}║")
        
        # If no dedicated top_influential section or if it was empty, check for subcomponents marked as top_ranked
        if not top_components_section:
            # Look for components with subcomponents marked with (HIGH IMPACT)
            for indicator_name, indicator_data in results.items():
                # Skip if indicator_data is not a dictionary/mapping or if it's top_influential (already processed)
                if not isinstance(indicator_data, dict) or indicator_name == 'top_influential':
                    continue
                    
                if 'components' in indicator_data and indicator_data['components'] and isinstance(indicator_data['components'], dict):
                    # Find high impact components
                    high_impact_components = {}
                    for comp_name, comp_score in indicator_data['components'].items():
                        if '(HIGH IMPACT)' in comp_name and isinstance(comp_score, (int, float)):
                            high_impact_components[comp_name] = comp_score
                    
                    if high_impact_components:
                        # Format indicator name
                        display_name = indicator_name.replace('_', ' ').title()
                        
                        # Add indicator header with proper padding
                        indicator_score = indicator_data.get('score', 0)
                        indicator_text = f"{display_name} ({indicator_score:.2f})"
                        padding = table_width - len(indicator_text) - 2
                        top_components_section.append(f"║ {indicator_text}{' ' * padding}║")
                        
                        # Sort high impact components by score
                        sorted_components = sorted(
                            high_impact_components.items(),
                            key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
                            reverse=True
                        )
                        
                        # Format and add each high impact component
                        for comp_name, comp_score in sorted_components:
                            # Clean up the display name
                            clean_name = comp_name.replace('(HIGH IMPACT)', '').strip()
                            
                            # Determine color and indicator based on score
                            if comp_score >= 70:
                                comp_color = AnalysisFormatter.GREEN
                                indicator = "↑"
                            elif comp_score >= 45:
                                comp_color = AnalysisFormatter.YELLOW
                                indicator = "→"
                            else:
                                comp_color = AnalysisFormatter.RED
                                indicator = "↓"
                                
                            # Create mini gauge
                            mini_gauge_width = 15
                            filled = int((comp_score / 100) * mini_gauge_width)
                            gauge_char = "█" if comp_score >= 70 else "▓" if comp_score >= 45 else "░"
                            gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                            
                            # Format the component display part with consistent padding (using 30 chars for better alignment)
                            comp_display_part = f"  • {clean_name:<30}: {comp_color}{comp_score:<6.2f}{AnalysisFormatter.RESET} {indicator} "
                            visible_length = len(f"  • {clean_name:<30}: {comp_score:<6.2f} {indicator} ")
                            
                            # Calculate remaining space
                            remaining_width = table_width - visible_length - 2
                            
                            # Adjust gauge width if needed
                            if remaining_width < mini_gauge_width:
                                mini_gauge_width = max(5, remaining_width)
                                filled = int((comp_score / 100) * mini_gauge_width)
                                gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                            
                            # Calculate padding
                            right_padding = remaining_width - mini_gauge_width
                            
                            # Add formatted line
                            line = f"║{comp_display_part}{comp_color}{gauge}{AnalysisFormatter.RESET}{' ' * right_padding}║"
                            top_components_section.append(line)
                        
                        # Add spacing
                        top_components_section.append(f"║{' ' * table_width}║")
        
        # If we didn't find any top components in either way, check for top_weighted_subcomponents 
        # in the original result (backward compatibility)
        if not top_components_section:
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
                                
                            # Create mini gauge (15 chars wide) with color-appropriate characters
                            mini_gauge_width = 15
                            filled = int((comp_score / 100) * mini_gauge_width)
                            gauge_char = "█" if comp_score >= 70 else "▓" if comp_score >= 45 else "░"
                            gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                            
                            # Format the component display part with consistent padding (using 30 chars for better alignment)
                            comp_display_part = f"  • {comp_display_name:<30}: {comp_color}{comp_score:<6.2f}{AnalysisFormatter.RESET} {indicator} "
                            
                            # Calculate visible length (without color codes) for the display part
                            visible_display_length = len(f"  • {comp_display_name:<30}: {comp_score:<6.2f} {indicator} ")
                            
                            # Calculate how much space is left for the gauge
                            remaining_width = table_width - visible_display_length - 2  # -2 for the borders
                            
                            # Ensure the gauge fits in the remaining space
                            if remaining_width < mini_gauge_width:
                                mini_gauge_width = max(5, remaining_width)  # Minimum 5 chars for gauge readability
                                filled = int((comp_score / 100) * mini_gauge_width)
                                gauge = gauge_char * filled + "·" * (mini_gauge_width - filled)
                            
                            # Calculate right-side padding to ensure proper alignment with the right border
                            right_padding = remaining_width - mini_gauge_width
                            
                            # Ensure consistent right edge alignment
                            line = f"║{comp_display_part}{comp_color}{gauge}{AnalysisFormatter.RESET}{' ' * right_padding}║"
                            top_components_section.append(line)
                    
                    # Add separator between indicators - ensure it's the exact table width
                    top_components_section.append(f"║{' ' * table_width}║")
            
        # Add market interpretations section
        header += "\n" + "\n".join(top_components_section if top_components_section else [f"║{' ' * table_width}║"])
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
                        interpretations.append(f"║ {line}{' ' * padding}║")
                else:
                    # For shorter interpretations, keep them on a single line
                    line = f"• {display_name}: {interp_str}"
                    padding = table_width - len(line) - 2
                    interpretations.append(f"║ {line}{' ' * padding}║")
            
                # Add a blank line separator between components with exact width
                interpretations.append(f"║{' ' * table_width}║")
        
        # Add interpretations to the output
        if interpretations:
            for interp in interpretations:
                header += f"\n{interp}"
        else:
            # If no interpretations were found, add a placeholder
            padding = table_width - len("No detailed interpretations available") - 2
            header += f"\n║ No detailed interpretations available{' ' * padding}║"
            
        # Add footer with exact table width
        header += f"\n╚{'═' * table_width}╝"
        
        # Return the complete formatted table
        return header

    @staticmethod
    def format_enhanced_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0, use_pretty_table=True, border_style="double"):
        """
        Format a comprehensive confluence analysis table with enhanced interpretations.
        
        Args:
            symbol: Trading symbol
            confluence_score: Overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed results for each component
            weights: Optional dictionary of component weights
            reliability: Reliability score of the analysis (0.0-1.0)
            use_pretty_table: Whether to use PrettyTable formatting (default: True)
            border_style: Border style for PrettyTable ("default", "single", "double", "markdown")
            
        Returns:
            str: Formatted table with comprehensive analysis and enhanced interpretations
        """
        # Use PrettyTable if requested and available
        if use_pretty_table and PrettyTable:
            return PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                weights=weights,
                reliability=reliability,
                border_style=border_style
            )
        
        # Fallback to EnhancedFormatter if PrettyTable is not available or not requested
        return EnhancedFormatter.format_enhanced_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=reliability
        )

class EnhancedFormatter:
    """Enhanced formatter for market interpretations with improved readability."""
    
    @staticmethod
    def format_market_interpretations(results, table_width=80, extra_right_borders=0, use_pretty_table=True, border_style="single"):
        """Format market interpretations section with enhanced readability using PrettyTable and centralized InterpretationManager."""
        if use_pretty_table and PrettyTable:
            # Use PrettyTable for consistent formatting
            return PrettyTableFormatter._format_interpretations_table(results, border_style)
        
        # Fallback to manual formatting
        # Market interpretations title with enhanced styling
        title = f"{AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}MARKET INTERPRETATIONS{AnalysisFormatter.RESET}"
        # Calculate padding for title, accounting for the length of the visible text, not formatting codes
        visible_title_len = len("MARKET INTERPRETATIONS")
        padding = table_width - visible_title_len - 2
        # Use a horizontal border that connects with the previous section
        header = f"\n╠{'═' * table_width}╣"
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Extract interpretations from results using centralized InterpretationManager if available
        interpretations_section = []
        
        # Try to use InterpretationManager for consistent processing
        if InterpretationManager:
            try:
                # Convert results to format suitable for InterpretationManager
                raw_interpretations = []
                for component_name, component_data in results.items():
                    if not isinstance(component_data, dict):
                        continue
                    
                    # Extract both enhanced and basic interpretations from component data
                    enhanced_interpretation = None
                    basic_interpretation = None
                    
                    if 'enhanced_interpretation' in component_data:
                        enhanced_interpretation = component_data['enhanced_interpretation']
                    
                    if 'interpretation' in component_data:
                        interp = component_data['interpretation']
                        if isinstance(interp, str):
                            basic_interpretation = interp
                        elif isinstance(interp, dict) and 'summary' in interp:
                            basic_interpretation = interp['summary']
                    elif 'signals' in component_data:
                        signals = component_data['signals']
                        if signals:
                            basic_interpretation = ", ".join(f"{k}={v}" for k, v in signals.items())
                    
                    # Combine interpretations if both exist
                    interpretation = None
                    if enhanced_interpretation and basic_interpretation:
                        if enhanced_interpretation.strip().lower() != basic_interpretation.strip().lower():
                            interpretation = f"{enhanced_interpretation} | Basic: {basic_interpretation}"
                        else:
                            interpretation = enhanced_interpretation
                    elif enhanced_interpretation:
                        interpretation = enhanced_interpretation
                    elif basic_interpretation:
                        interpretation = basic_interpretation
                    
                    if interpretation:
                        raw_interpretations.append({
                            'component': component_name,
                            'display_name': component_name.replace('_', ' ').title(),
                            'interpretation': interpretation
                        })
                
                # Process through InterpretationManager
                if raw_interpretations:
                    manager = InterpretationManager()
                    interpretation_set = manager.process_interpretations(
                        raw_interpretations, 
                        'formatter',
                        None,  # No market data available in this context
                        datetime.datetime.now()
                    )
                    
                    # Format the standardized interpretations
                    for interpretation in interpretation_set.interpretations:
                        display_name = f"{AnalysisFormatter.BOLD}{interpretation.component_name.replace('_', ' ').title()}{AnalysisFormatter.RESET}"
                        visible_display_name_len = len(interpretation.component_name.replace('_', ' ').title())
                        
                        # Add severity indicator
                        severity_indicator = "🔴" if interpretation.severity.value == "critical" else "🟡" if interpretation.severity.value == "warning" else "🔵"
                        
                        # Calculate effective width for wrapping
                        effective_width = table_width - 6 - visible_display_name_len - 2  # -6 for "║ 🔵 • ", -2 for ": "
                        
                        # Format multi-line interpretations with proper wrapping
                        wrapped_lines = textwrap.wrap(interpretation.interpretation_text, width=effective_width)
                        if wrapped_lines:
                            first_line = wrapped_lines[0]
                            visible_line_len = len(f"{severity_indicator} • {interpretation.component_name.replace('_', ' ').title()}: {first_line}")
                            padding = table_width - visible_line_len - 2
                            interpretations_section.append(f"║ {severity_indicator} • {display_name}: {first_line}{' ' * padding}║")
                            
                            # Add subsequent lines with proper indentation
                            for subsequent_line in wrapped_lines[1:]:
                                visible_line_len = len(f"    {subsequent_line}")
                                padding = table_width - visible_line_len - 2
                                interpretations_section.append(f"║     {subsequent_line}{' ' * padding}║")
                            
                            # Add empty line between components for readability
                            interpretations_section.append(f"║{' ' * table_width}║")
                            
            except Exception as e:
                # Fallback to original processing if InterpretationManager fails
                pass
        
        # Fallback to original processing if InterpretationManager is not available or failed
        if not interpretations_section:
            for component_name, component_data in results.items():
                display_name = f"{AnalysisFormatter.BOLD}{component_name.replace('_', ' ').title()}{AnalysisFormatter.RESET}"
                visible_display_name_len = len(component_name.replace('_', ' ').title())
                
                # Skip non-dictionary values to prevent errors
                if not isinstance(component_data, dict):
                    continue
                
                # Try to get both enhanced and basic interpretations
                enhanced_interpretation = None
                basic_interpretation = None
                
                # Check for enhanced_interpretation field
                if 'enhanced_interpretation' in component_data:
                    enhanced_interpretation = component_data['enhanced_interpretation']
                
                # Check for basic interpretation field
                if 'interpretation' in component_data:
                    interp = component_data['interpretation']
                    if isinstance(interp, str):
                        basic_interpretation = interp
                    elif isinstance(interp, dict) and 'summary' in interp:
                        basic_interpretation = interp['summary']
                # If no interpretation, build from signals
                elif 'signals' in component_data:
                    signals = component_data['signals']
                    if signals:
                        basic_interpretation = ", ".join(f"{k}={v}" for k, v in signals.items())
                
                # Decide which interpretation(s) to show
                interpretation = None
                if enhanced_interpretation and basic_interpretation:
                    # If both exist and are different, show both
                    if enhanced_interpretation.strip().lower() != basic_interpretation.strip().lower():
                        interpretation = f"{enhanced_interpretation} | Basic: {basic_interpretation}"
                    else:
                        # If they're the same, just use the enhanced one
                        interpretation = enhanced_interpretation
                elif enhanced_interpretation:
                    # Only enhanced available
                    interpretation = enhanced_interpretation
                elif basic_interpretation:
                    # Only basic available
                    interpretation = basic_interpretation
                
                # If we have an interpretation, add it to the section
                if interpretation:
                    # Calculate effective width for wrapping to account for the leading "• Display_name: "
                    effective_width = table_width - 4 - visible_display_name_len - 2  # -4 for "║ • ", -2 for ": "
                    
                    # Format multi-line interpretations with proper wrapping
                    wrapped_lines = textwrap.wrap(interpretation, width=effective_width)
                    if wrapped_lines:
                        first_line = wrapped_lines[0]
                        # Calculate visible length of the line without formatting codes
                        visible_line_len = len(f"• {component_name.replace('_', ' ').title()}: {first_line}")
                        padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                        interpretations_section.append(f"║ • {display_name}: {first_line}{' ' * padding}║")
                        
                        # Add subsequent lines with proper indentation
                        for subsequent_line in wrapped_lines[1:]:
                            visible_line_len = len(f"  {subsequent_line}")
                            padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                            interpretations_section.append(f"║   {subsequent_line}{' ' * padding}║")
                        
                        # Add empty line between components for readability
                        interpretations_section.append(f"║{' ' * table_width}║")
        
        # Add the interpretations section to the header
        header += "\n" + "\n".join(interpretations_section)
        
        return header
    
    @staticmethod
    def format_cross_component_insights(cross_insights, table_width=80, extra_right_borders=0):
        """Format cross-component insights section."""
        if not cross_insights:
            return ""
        
        # Section title
        title = f"{AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}CROSS-COMPONENT INSIGHTS{AnalysisFormatter.RESET}"
        # Calculate visible length without formatting codes
        visible_title_len = len("CROSS-COMPONENT INSIGHTS")
        padding = table_width - visible_title_len - 2
        
        header = f"\n╠{'═' * table_width}╣"
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Format each insight
        insights_section = []
        for insight in cross_insights:
            # Calculate effective width for wrapping
            effective_width = table_width - 4  # -4 for "║ • "
            
            wrapped_lines = textwrap.wrap(insight, width=effective_width)
            if wrapped_lines:
                first_line = wrapped_lines[0]
                visible_line_len = len(f"• {first_line}")
                padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                insights_section.append(f"║ • {first_line}{' ' * padding}║")
                
                # Add subsequent lines with proper indentation
                for subsequent_line in wrapped_lines[1:]:
                    visible_line_len = len(f"  {subsequent_line}")
                    padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                    insights_section.append(f"║   {subsequent_line}{' ' * padding}║")
                
                # Add empty line between insights for readability
                insights_section.append(f"║{' ' * table_width}║")
        
        # Add the insights section to the header
        header += "\n" + "\n".join(insights_section)
        
        return header
    
    @staticmethod
    def format_actionable_insights(actionable_insights, table_width=80, extra_right_borders=0):
        """Format actionable trading insights section."""
        if not actionable_insights:
            return ""
        
        # Section title
        title = f"{AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}ACTIONABLE TRADING INSIGHTS{AnalysisFormatter.RESET}"
        # Calculate visible length without formatting codes
        visible_title_len = len("ACTIONABLE TRADING INSIGHTS")
        padding = table_width - visible_title_len - 2
        
        header = f"\n╠{'═' * table_width}╣"
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Format each insight
        insights_section = []
        for insight in actionable_insights:
            # Calculate effective width for wrapping
            effective_width = table_width - 4  # -4 for "║ • "
            
            wrapped_lines = textwrap.wrap(insight, width=effective_width)
            if wrapped_lines:
                first_line = wrapped_lines[0]
                visible_line_len = len(f"• {first_line}")
                padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                insights_section.append(f"║ • {first_line}{' ' * padding}║")
                
                # Add subsequent lines with proper indentation
                for subsequent_line in wrapped_lines[1:]:
                    visible_line_len = len(f"  {subsequent_line}")
                    padding = table_width - visible_line_len - 2  # -2 for "║ " at the start
                    insights_section.append(f"║   {subsequent_line}{' ' * padding}║")
                
                # Add empty line between insights for readability
                insights_section.append(f"║{' ' * table_width}║")
        
        # Add the insights section to the header
        header += "\n" + "\n".join(insights_section)
        
        return header
    
    @staticmethod
    def format_enhanced_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0, extra_right_borders=0):
        """
        Format a comprehensive table for the overall confluence score components,
        including enhanced market interpretations, cross-component insights, and actionable insights.
        
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
        
        # Always set extra_right_borders to 0 to ensure consistent alignment
        extra_right_borders = 0
        
        # Get the standard confluence score table
        # Since we're now in the same file as LogFormatter, we can use it directly
        header = LogFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=reliability,
            extra_right_borders=extra_right_borders
        )
        
        # Remove the basic market interpretations section from the header
        # Find the start of the market interpretations section
        marker = "MARKET INTERPRETATIONS"
        parts = header.split(marker)
        if len(parts) > 1:
            # Keep only the first part (before the MARKET INTERPRETATIONS section)
            # We need to find the line before "MARKET INTERPRETATIONS" which is the separator
            lines = parts[0].split('\n')
            separator_line = f"╠{'═' * table_width}╣"
            
            # Find the last occurrence of the separator line
            for i in range(len(lines) - 1, -1, -1):
                if separator_line in lines[i]:
                    # Keep everything up to and including this line
                    header = '\n'.join(lines[:i+1])
                    break
        
        # Create an interpretation generator
        from src.core.analysis.interpretation_generator import InterpretationGenerator
        interpretation_generator = InterpretationGenerator()
        
        # Get thresholds from the results if available
        buy_threshold = 65  # Default value
        sell_threshold = 35  # Default value
        
        if isinstance(results, dict):
            for component_data in results.values():
                if isinstance(component_data, dict) and 'buy_threshold' in component_data:
                    buy_threshold = component_data['buy_threshold']
                    break
            
            for component_data in results.values():
                if isinstance(component_data, dict) and 'sell_threshold' in component_data:
                    sell_threshold = component_data['sell_threshold']
                    break
        
        # Generate enhanced interpretations for each component while preserving existing interpretations
        enhanced_results = {}
        for component_name, component_data in results.items():
            if isinstance(component_data, dict):
                try:
                    # Check if we already have an enhanced interpretation
                    if 'enhanced_interpretation' not in component_data:
                        enhanced_interpretation = interpretation_generator.get_component_interpretation(
                            component_name, component_data
                        )
                        # Create a copy of the component data with the enhanced interpretation
                        enhanced_component = component_data.copy()
                        enhanced_component['enhanced_interpretation'] = enhanced_interpretation
                        enhanced_results[component_name] = enhanced_component
                    else:
                        # Already has enhanced interpretation, use as is
                        enhanced_results[component_name] = component_data
                except Exception:
                    # If there's an error, just use the original component data
                    enhanced_results[component_name] = component_data
            else:
                enhanced_results[component_name] = component_data
        
        # Add the market interpretations section with enhanced formatting
        market_interpretations = EnhancedFormatter.format_market_interpretations(enhanced_results, table_width, extra_right_borders)
        
        # Check if cross-component insights are already in results
        cross_insights = None
        if isinstance(results, dict) and 'cross_component_insights' in results:
            cross_insights = results['cross_component_insights']
        else:
            # Generate cross-component insights only if not already present
            cross_insights = interpretation_generator.generate_cross_component_insights(results)
        
        # Add cross-component insights section if available
        cross_component_section = ""
        if cross_insights:
            cross_component_section = EnhancedFormatter.format_cross_component_insights(cross_insights, table_width, extra_right_borders)
        
        # Check if actionable insights are already in results
        actionable_insights = None
        if isinstance(results, dict) and 'actionable_insights' in results:
            actionable_insights = results['actionable_insights']
        else:
            # Generate actionable insights only if not already present
            actionable_insights = interpretation_generator.generate_actionable_insights(
                results, confluence_score, buy_threshold, sell_threshold
            )
        
        # Add actionable insights section if available
        actionable_section = ""
        if actionable_insights:
            actionable_section = EnhancedFormatter.format_actionable_insights(actionable_insights, table_width, extra_right_borders)
        
        # Add footer to the enhanced table
        footer = f"\n╚{'═' * table_width}╝"
        
        # Combine all sections with footer
        enhanced_table = header + market_interpretations + cross_component_section + actionable_section + footer
        
        return enhanced_table 


class PrettyTableFormatter:
    """
    Modern table formatter using PrettyTable for clean, professional table formatting.
    
    This formatter provides a cleaner alternative to the box-drawing character tables,
    using PrettyTable for consistent formatting and better readability.
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
    def _get_score_color(score):
        """Get color based on score value."""
        if score is None:
            return PrettyTableFormatter.YELLOW  # Default to yellow for None values
        elif score >= 70:
            return PrettyTableFormatter.GREEN
        elif score >= 45:
            return PrettyTableFormatter.YELLOW
        else:
            return PrettyTableFormatter.RED
    
    @staticmethod
    def _create_gauge(score, width=30):
        """Create a visual gauge for the score."""
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Calculate filled portion
        filled = int((score / 100) * width)
        
        # Choose characters and color based on score
        if score >= 70:
            fill_char = "█"  # Solid block for bullish
            color = PrettyTableFormatter.GREEN
        elif score >= 45:
            fill_char = "▓"  # Medium-density for neutral
            color = PrettyTableFormatter.YELLOW
        else:
            fill_char = "░"  # Low-density for bearish
            color = PrettyTableFormatter.RED
        
        # Create the gauge
        gauge = color + fill_char * filled + "·" * (width - filled) + PrettyTableFormatter.RESET
        return gauge
    
    @staticmethod
    def _get_trend_indicator(score):
        """Get trend indicator based on score."""
        if score >= 70:
            return PrettyTableFormatter.GREEN + "↑" + PrettyTableFormatter.RESET
        elif score >= 45:
            return PrettyTableFormatter.YELLOW + "→" + PrettyTableFormatter.RESET
        else:
            return PrettyTableFormatter.RED + "↓" + PrettyTableFormatter.RESET
    
    @staticmethod
    def format_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0, border_style="double"):
        """
        Format a comprehensive confluence analysis table using PrettyTable.
        
        Args:
            symbol: Trading symbol
            confluence_score: Overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed results for each component
            weights: Optional dictionary of component weights
            reliability: Reliability score of the analysis (0.0-1.0)
            border_style: Border style ("default", "single", "double", "markdown")
            
        Returns:
            str: Formatted table with comprehensive analysis
        """
        if not PrettyTable:
            # Fallback to original formatter if PrettyTable is not available
            return LogFormatter.format_confluence_score_table(
                symbol, confluence_score, components, results, weights, reliability
            )
        
        output = []
        
        # Header section with enhanced styling
        if border_style == "double":
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}╔══ {symbol} CONFLUENCE ANALYSIS ══╗{PrettyTableFormatter.RESET}"
        elif border_style == "single":
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}┌── {symbol} CONFLUENCE ANALYSIS ──┐{PrettyTableFormatter.RESET}"
        else:
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}{symbol} CONFLUENCE ANALYSIS{PrettyTableFormatter.RESET}"
        
        output.append(f"\n{header_text}")
        
        # Choose separator based on border style
        if border_style == "double":
            separator = "═" * 80
        elif border_style == "single":
            separator = "─" * 80
        else:
            separator = "=" * 80
            
        output.append(separator)
        
        # Overall score and reliability
        score_color = PrettyTableFormatter._get_score_color(confluence_score)
        overall_status = "BULLISH" if confluence_score is not None and confluence_score >= 60 else "NEUTRAL" if confluence_score is not None and confluence_score >= 40 else "BEARISH"
        
        # Normalize reliability input to 0-1 range to avoid 10000% displays
        try:
            raw_rel = float(reliability)
        except Exception:
            raw_rel = 0.0
        # If the value looks like a percentage (e.g., 75 or 92.5), convert to 0-1
        normalized_rel = raw_rel / 100.0 if raw_rel > 1.0 else raw_rel
        # Clamp to [0,1] to prevent overflows
        normalized_rel = max(0.0, min(1.0, normalized_rel))
        reliability_pct = normalized_rel * 100
        reliability_color = PrettyTableFormatter.GREEN if normalized_rel >= 0.8 else PrettyTableFormatter.YELLOW if normalized_rel >= 0.5 else PrettyTableFormatter.RED
        reliability_status = "HIGH" if normalized_rel >= 0.8 else "MEDIUM" if normalized_rel >= 0.5 else "LOW"
        
        score_display = "N/A" if confluence_score is None else f"{confluence_score:.2f}"
        output.append(f"Overall Score: {score_color}{score_display}{PrettyTableFormatter.RESET} ({overall_status})")
        output.append(f"Reliability: {reliability_color}{reliability_pct:.0f}%{PrettyTableFormatter.RESET} ({reliability_status})")
        output.append("")
        
        # Main components table
        if components:
            # Calculate weighted contributions
            contributions = []
            if weights:
                for component, score in components.items():
                    # Coerce dict component values to numeric scores safely
                    try:
                        numeric_score = score.get('score', score) if isinstance(score, dict) else score
                        numeric_score = float(numeric_score) if numeric_score is not None else 50.0
                    except Exception:
                        numeric_score = 50.0
                    weight = weights.get(component, 0)
                    contribution = numeric_score * weight
                    contributions.append((component, numeric_score, weight, contribution))
            else:
                # Estimate equal weights if not provided
                weight = 1.0 / max(len(components), 1)
                for component, score in components.items():
                    try:
                        numeric_score = score.get('score', score) if isinstance(score, dict) else score
                        numeric_score = float(numeric_score) if numeric_score is not None else 50.0
                    except Exception:
                        numeric_score = 50.0
                    contribution = numeric_score * weight
                    contributions.append((component, numeric_score, weight, contribution))
            
            # Sort by contribution (descending)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Create main components table with enhanced borders
            table = PrettyTable()
            table.field_names = ["Component", "Score", "Impact", "Gauge"]
            table.align = "l"
            table.align["Score"] = "r"
            table.align["Impact"] = "r"
            
            # Apply border style
            if border_style == "double" and DOUBLE_BORDER:
                table.set_style(DOUBLE_BORDER)
            elif border_style == "single" and SINGLE_BORDER:
                table.set_style(SINGLE_BORDER)
            elif border_style == "markdown" and MARKDOWN:
                table.set_style(MARKDOWN)
            else:
                table.set_style(DEFAULT if DEFAULT else None)
            
            for component, score, weight, contribution in contributions:
                display_name = component.replace('_', ' ').title()
                score_color = PrettyTableFormatter._get_score_color(score)
                gauge = PrettyTableFormatter._create_gauge(score, 30)
                
                table.add_row([
                    display_name,
                    f"{score_color}{score:.2f}{PrettyTableFormatter.RESET}",
                    f"{contribution:.1f}",
                    gauge
                ])
            
            # Add Component Breakdown section header
            output.append(f"{PrettyTableFormatter.BOLD}Component Breakdown{PrettyTableFormatter.RESET}")
            
            # Add the table directly (PrettyTable handles its own borders)
            output.append(str(table))
            output.append("")
        
                # Top influential individual components (optimized with PrettyTable)
        if results:
            top_components_table = PrettyTableFormatter._format_top_components_table(results, border_style)
            if top_components_table:
                output.append(top_components_table)

        # Market interpretations (optimized with PrettyTable)
        interpretations_table = PrettyTableFormatter._format_interpretations_table(results, border_style)
        if interpretations_table:
            output.append(interpretations_table)
        
        # Actionable insights
        insights = PrettyTableFormatter._generate_actionable_insights(confluence_score, components, results)
        if insights:
            output.append(f"{PrettyTableFormatter.BOLD}Actionable Trading Insights:{PrettyTableFormatter.RESET}")
            for insight in insights:
                output.append(f"  • {insight}")
            output.append("")
        
        output.append(separator)
        return "\n".join(output)
    
    @staticmethod
    def _extract_top_components(results):
        """Extract top individual components from results."""
        top_components = []
        
        # Look for top_influential section first
        if 'top_influential' in results and isinstance(results['top_influential'], dict):
            top_influential = results['top_influential']
            if 'components' in top_influential and isinstance(top_influential['components'], dict):
                for comp_name, comp_score in top_influential['components'].items():
                    if isinstance(comp_score, (int, float)):
                        display_name = comp_name.replace('_', ' ')
                        top_components.append((display_name, comp_score))
        
        # Fallback: extract from individual component results
        if not top_components:
            for component_name, component_data in results.items():
                if isinstance(component_data, dict) and 'components' in component_data:
                    sub_components = component_data['components']
                    if isinstance(sub_components, dict):
                        for sub_name, sub_score in sub_components.items():
                            if isinstance(sub_score, (int, float)):
                                display_name = f"{sub_name} ({component_name})"
                                top_components.append((display_name, sub_score))
        
        # Sort by score descending
        top_components.sort(key=lambda x: x[1], reverse=True)
        return top_components
    
    @staticmethod
    def _format_interpretations(results):
        """Format market interpretations from results."""
        interpretations = []
        
        # PRIORITY 1: Check if market_interpretations field exists (from enhanced data generation)
        if results and isinstance(results, dict) and 'market_interpretations' in results:
            market_interpretations = results['market_interpretations']
            
            if isinstance(market_interpretations, list):
                for interp_data in market_interpretations:
                    if isinstance(interp_data, dict):
                        display_name = interp_data.get('display_name', interp_data.get('component', 'Unknown')).replace('_', ' ').title()
                        interpretation_text = interp_data.get('interpretation', '')
                        
                        if interpretation_text:
                            # Wrap long interpretations
                            wrapped_interp = textwrap.fill(interpretation_text, width=70)
                            interpretations.append(f"{display_name}: {wrapped_interp}")
                
                if interpretations:
                    return interpretations
        
        # PRIORITY 2: Fallback to component-level interpretation extraction
        for component_name, component_data in results.items():
            # Skip the market_interpretations field itself
            if component_name == 'market_interpretations':
                continue
                
            if not isinstance(component_data, dict):
                continue
            
            display_name = component_name.replace('_', ' ').title()
            
            # Try to get interpretation
            interpretation = None
            if 'enhanced_interpretation' in component_data:
                interpretation = component_data['enhanced_interpretation']
            elif 'interpretation' in component_data:
                interp = component_data['interpretation']
                if isinstance(interp, str):
                    interpretation = interp
                elif isinstance(interp, dict) and 'summary' in interp:
                    interpretation = interp['summary']
            
            if interpretation:
                # Wrap long interpretations
                wrapped_interp = textwrap.fill(interpretation, width=70)
                interpretations.append(f"{display_name}: {wrapped_interp}")
        
        return interpretations
    
    @staticmethod
    def _generate_actionable_insights(confluence_score, components, results):
        """Generate actionable trading insights based on analysis."""
        insights = []
        
        # Overall stance
        if confluence_score is not None and confluence_score >= 60:
            insights.append("BULLISH STANCE: Consider long positions with proper risk management")
        elif confluence_score is not None and confluence_score >= 40:
            insights.append("NEUTRAL STANCE: Range-bound conditions likely - consider mean-reversion strategies")
        else:
            insights.append("BEARISH STANCE: Consider short positions or avoid long exposure")
        
        # Risk assessment
        if hasattr(results, 'get') and results.get('risk_level'):
            risk_level = results['risk_level']
            if risk_level == 'HIGH':
                insights.append("RISK ASSESSMENT: HIGH - Avoid new positions until risk conditions improve")
            elif risk_level == 'MEDIUM':
                insights.append("RISK ASSESSMENT: MEDIUM - Use reduced position sizing")
            else:
                insights.append("RISK ASSESSMENT: LOW - Normal position sizing acceptable")
        
        # Component-specific insights
        if components:
            # Find strongest component
            strongest_component = max(components.items(), key=lambda x: x[1])
            if strongest_component[1] >= 70:
                comp_name = strongest_component[0].replace('_', ' ').title()
                insights.append(f"STRENGTH: {comp_name} shows strong bullish signals")
            
            # Find weakest component
            weakest_component = min(components.items(), key=lambda x: x[1])
            if weakest_component[1] <= 30:
                comp_name = weakest_component[0].replace('_', ' ').title()
                insights.append(f"WEAKNESS: {comp_name} shows concerning bearish signals")
        
        # Timing insights
        if confluence_score is not None and confluence_score >= 55:
            insights.append("TIMING: Bullish momentum building; favorable for trend-following entries")
        elif confluence_score is not None and confluence_score <= 45:
            insights.append("TIMING: Bearish pressure increasing; consider defensive positioning")
        else:
            insights.append("TIMING: Mixed signals; wait for clearer directional confirmation")
        
        return insights

    @staticmethod
    def format_score_contribution_section(title, contributions, symbol="", divergence_adjustments=None, final_score=None, border_style="single"):
        """
        Formats score contributions using PrettyTable for a clean, professional look.
        
        Args:
            title: Section title
            contributions: List of (name, score, weight, impact) tuples.
            symbol: Optional symbol to include in the title.
            divergence_adjustments: Optional dict of divergence adjustments.
            final_score: Optional final score to display.
            border_style: 'single' or 'double'.
        """
        # PrettyTable is required - no fallback
        
        # Calculate total contribution for reference only
        calculated_sum = sum(contrib for _, _, _, contrib in contributions)
        
        # ALWAYS use the provided final score if available, otherwise use the calculated sum
        total_score = final_score if final_score is not None else calculated_sum
        
        # Include symbol in the title if provided
        display_title = f"{symbol} {title}" if symbol else title
        
        # Check if we need to add a column for divergences
        has_divergences = divergence_adjustments and any(divergence_adjustments.values())
        
        output = []
        
        # Header section
        header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}{display_title}{PrettyTableFormatter.RESET}"
        output.append(f"\n{header_text}")
        output.append("=" * 80)
        
        # Create the main table with enhanced borders
        table = PrettyTable()
        
        # Set up field names based on whether divergences are included
        if has_divergences:
            table.field_names = ["Component", "Score", "Weight", "Impact", "Div", "Gauge"]
        else:
            table.field_names = ["Component", "Score", "Weight", "Impact", "Gauge"]
        
        # Set alignment
        table.align = "l"
        table.align["Score"] = "r"
        table.align["Weight"] = "r"
        table.align["Impact"] = "r"
        if has_divergences:
            table.align["Div"] = "r"
            
        # Apply border style - use DEFAULT for classic PrettyTable look
        if border_style == "markdown" and MARKDOWN:
            table.set_style(MARKDOWN)
        else:
            # Use DEFAULT style for classic PrettyTable look with + and | characters
            table.set_style(DEFAULT if DEFAULT else None)
        
        # Add component rows
        for component, score, weight, contribution in contributions:
            # Color based on score
            score_color = PrettyTableFormatter._get_score_color(score)
            
            # Create gauge with appropriate width for table
            gauge = PrettyTableFormatter._create_gauge(score, 30)
            
            # Format divergence adjustment if available
            row_data = [
                component,
                f"{score_color}{score:.2f}{PrettyTableFormatter.RESET}",
                f"{weight:.2f}",
                f"{contribution:.1f}",
            ]
            
            if has_divergences:
                div_value = divergence_adjustments.get(component, 0.0)
                if div_value > 0:
                    div_color = PrettyTableFormatter.GREEN
                    div_display = f"+{div_value:.1f}"
                elif div_value < 0:
                    div_color = PrettyTableFormatter.RED
                    div_display = f"{div_value:.1f}"
                else:
                    div_color = PrettyTableFormatter.RESET
                    div_display = "0.0"
                
                row_data.append(f"{div_color}{div_display}{PrettyTableFormatter.RESET}")
            
            row_data.append(gauge)
            table.add_row(row_data)
        
        # Add separator row
        separator_data = ["-" * 15, "-" * 8, "-" * 6, "-" * 6]
        if has_divergences:
            separator_data.append("-" * 6)
        separator_data.append("-" * 30)
        table.add_row(separator_data)
        
        # Add final score row
        if total_score >= 70:
            total_color = PrettyTableFormatter.GREEN
            status = "BULLISH"
        elif total_score >= 45:
            total_color = PrettyTableFormatter.YELLOW
            status = "NEUTRAL"
        else:
            total_color = PrettyTableFormatter.RED
            status = "BEARISH"
        
        total_gauge = PrettyTableFormatter._create_gauge(total_score, 30)
        
        final_row_data = [
            f"{PrettyTableFormatter.BOLD}FINAL SCORE{PrettyTableFormatter.RESET}",
            f"{total_color}{total_score:.2f}{PrettyTableFormatter.RESET}",
            "",
            "",
        ]
        
        if has_divergences:
            total_adjustment = sum(divergence_adjustments.values())
            if total_adjustment > 0:
                div_total_color = PrettyTableFormatter.GREEN
                div_total_display = f"+{total_adjustment:.1f}"
            elif total_adjustment < 0:
                div_total_color = PrettyTableFormatter.RED
                div_total_display = f"{total_adjustment:.1f}"
            else:
                div_total_color = PrettyTableFormatter.RESET
                div_total_display = "0.0"
            
            final_row_data.append(f"{div_total_color}{div_total_display}{PrettyTableFormatter.RESET}")
        
        final_row_data.append(total_gauge)
        table.add_row(final_row_data)
        
        # Add the table to output
        output.append(str(table))
        
        # Add status line
        output.append("")
        output.append(f"Status: {total_color}{status}{PrettyTableFormatter.RESET} ({total_score:.2f}/100)")
        
        # Add legend for divergence adjustment column if there are non-zero adjustments
        if has_divergences and any(divergence_adjustments.values()):
            output.append("* Div column shows timeframe divergence adjustments")
        
        output.append("=" * 80)
        return "\n".join(output)

    @staticmethod
    def format_enhanced_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0, border_style="double"):
        """
        Format a comprehensive confluence analysis table with enhanced interpretations using PrettyTable.
        
        This method provides the same rich interpretations and actionable insights as the EnhancedFormatter
        but uses clean PrettyTable formatting with enhanced border styling.
        
        Args:
            symbol: Trading symbol
            confluence_score: Overall confluence score
            components: Dictionary of component scores
            results: Dictionary of detailed results for each component
            weights: Optional dictionary of component weights
            reliability: Reliability score of the analysis (0.0-1.0)
            border_style: Border style ("default", "single", "double", "markdown")
            
        Returns:
            str: Formatted table with comprehensive analysis and enhanced interpretations
        """
        if not PrettyTable:
            # Fallback to EnhancedFormatter if PrettyTable is not available
            return EnhancedFormatter.format_enhanced_confluence_score_table(
                symbol, confluence_score, components, results, weights, reliability
            )
        
        output = []
        
        # Header section with enhanced styling based on border style
        if border_style == "double":
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}╔══ {symbol} CONFLUENCE ANALYSIS ══╗{PrettyTableFormatter.RESET}"
            separator = "═" * 80
        elif border_style == "single":
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}┌── {symbol} CONFLUENCE ANALYSIS ──┐{PrettyTableFormatter.RESET}"
            separator = "─" * 80
        else:
            header_text = f"{PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}{symbol} CONFLUENCE ANALYSIS{PrettyTableFormatter.RESET}"
            separator = "=" * 80
        
        output.append(f"\n{header_text}")
        output.append(separator)
        
        # Overall score and reliability
        score_color = PrettyTableFormatter._get_score_color(confluence_score)
        overall_status = "BULLISH" if confluence_score is not None and confluence_score >= 60 else "NEUTRAL" if confluence_score is not None and confluence_score >= 40 else "BEARISH"
        
        # Normalize reliability input to 0-1 range to avoid 10000% displays
        try:
            raw_rel = float(reliability)
        except Exception:
            raw_rel = 0.0
        normalized_rel = raw_rel / 100.0 if raw_rel > 1.0 else raw_rel
        normalized_rel = max(0.0, min(1.0, normalized_rel))
        reliability_pct = normalized_rel * 100
        reliability_color = PrettyTableFormatter.GREEN if normalized_rel >= 0.8 else PrettyTableFormatter.YELLOW if normalized_rel >= 0.5 else PrettyTableFormatter.RED
        reliability_status = "HIGH" if normalized_rel >= 0.8 else "MEDIUM" if normalized_rel >= 0.5 else "LOW"
        
        score_display = "N/A" if confluence_score is None else f"{confluence_score:.2f}"
        output.append(f"Overall Score: {score_color}{score_display}{PrettyTableFormatter.RESET} ({overall_status})")
        output.append(f"Reliability: {reliability_color}{reliability_pct:.0f}%{PrettyTableFormatter.RESET} ({reliability_status})")
        output.append("")
        
        # Main components table
        if components:
            # Calculate weighted contributions
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
            
            # Sort by contribution (descending)
            contributions.sort(key=lambda x: x[3], reverse=True)
            
            # Create main components table with enhanced borders
            table = PrettyTable()
            table.field_names = ["Component", "Score", "Impact", "Gauge"]
            table.align = "l"
            table.align["Score"] = "r"
            table.align["Impact"] = "r"
            
            # Apply border style
            if border_style == "double" and DOUBLE_BORDER:
                table.set_style(DOUBLE_BORDER)
            elif border_style == "single" and SINGLE_BORDER:
                table.set_style(SINGLE_BORDER)
            elif border_style == "markdown" and MARKDOWN:
                table.set_style(MARKDOWN)
            else:
                table.set_style(DEFAULT if DEFAULT else None)
            
            for component, score, weight, contribution in contributions:
                display_name = component.replace('_', ' ').title()
                score_color = PrettyTableFormatter._get_score_color(score)
                gauge = PrettyTableFormatter._create_gauge(score, 30)
                
                table.add_row([
                    display_name,
                    f"{score_color}{score:.2f}{PrettyTableFormatter.RESET}",
                    f"{contribution:.1f}",
                    gauge
                ])
            
            # Add Component Breakdown section header
            output.append(f"{PrettyTableFormatter.BOLD}Component Breakdown{PrettyTableFormatter.RESET}")
            
            # Add the table directly (PrettyTable handles its own borders)
            output.append(str(table))
            output.append("")
        
        # Top influential individual components (optimized with PrettyTable)
        if results:
            top_components_table = PrettyTableFormatter._format_top_components_table(results, border_style)
            if top_components_table:
                output.append(top_components_table)
        
        # Enhanced Market Interpretations (optimized with PrettyTable)
        interpretations_table = PrettyTableFormatter._format_interpretations_table(results, border_style)
        if interpretations_table:
            output.append(interpretations_table)
        
        # Enhanced Actionable insights using PrettyTable for consistency
        enhanced_insights = PrettyTableFormatter._generate_enhanced_actionable_insights(confluence_score, components, results)
        if enhanced_insights:
            # Create PrettyTable for actionable insights
            insights_table = PrettyTable()
            
            # Set border style to match other tables
            if border_style == "double" and DOUBLE_BORDER:
                insights_table.set_style(DOUBLE_BORDER)
            elif border_style == "single" and SINGLE_BORDER:
                insights_table.set_style(SINGLE_BORDER)
            elif border_style == "markdown" and MARKDOWN:
                insights_table.set_style(MARKDOWN)
            else:
                insights_table.set_style(DEFAULT if DEFAULT else None)
            
            # Single column table for insights
            insights_table.field_names = ["Actionable Trading Insights"]
            insights_table.align["Actionable Trading Insights"] = "l"
            insights_table.max_width["Actionable Trading Insights"] = 75
            
            # Add each insight as a table row
            for insight in enhanced_insights:
                if insight.strip():  # Skip empty lines
                    insights_table.add_row([insight.strip()])
            
            # Add the insights table
            output.append(f"{PrettyTableFormatter.BOLD}Actionable Trading Insights{PrettyTableFormatter.RESET}")
            output.append(str(insights_table))
            output.append("")
        
        output.append(separator)
        return "\n".join(output)

    @staticmethod
    def _format_enhanced_interpretations(results):
        """Format enhanced market interpretations using InterpretationManager logic."""
        interpretations = []
        
        # Debug logging to see what data we're working with
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"_format_enhanced_interpretations called with results keys: {list(results.keys()) if results else 'None'}")
        
        # Helper: summarize dict-valued signals into readable narrative
        def _summarize_signals(signals_dict):
            try:
                parts = []
                for raw_name, raw_value in signals_dict.items():
                    display = raw_name.replace('_', ' ').title()
                    # Dict-valued signal → extract common fields
                    if isinstance(raw_value, dict):
                        signal_text = str(
                            raw_value.get('signal')
                            or raw_value.get('trend')
                            or raw_value.get('state')
                            or raw_value.get('direction')
                            or 'neutral'
                        ).replace('_', ' ')
                        bias = raw_value.get('bias')
                        strength = raw_value.get('strength')
                        interp = raw_value.get('interpretation')
                        details = []
                        if isinstance(strength, (str, int, float)) and str(strength).strip():
                            details.append(str(strength).replace('_', ' '))
                        if isinstance(bias, (str,)) and bias and bias.lower() != 'neutral':
                            details.append(bias)
                        detail_str = f" ({', '.join(details)})" if details else ""
                        part = f"{display}: {signal_text}{detail_str}"
                        if isinstance(interp, str) and interp.strip():
                            part += f" - {interp.strip()}"
                        parts.append(part)
                    else:
                        # Simple value (number/string)
                        parts.append(f"{display}: {raw_value}")
                return "; ".join(parts)
            except Exception:
                # Fallback to simple join if anything goes wrong
                try:
                    return ", ".join(f"{k}={v}" for k, v in signals_dict.items())
                except Exception:
                    return ""
        
        # PRIORITY 1: Check if market_interpretations field exists (from enhanced data generation)
        if results and isinstance(results, dict) and 'market_interpretations' in results:
            market_interpretations = results['market_interpretations']
            logger.debug(f"Found market_interpretations field with {len(market_interpretations)} items")
            
            if isinstance(market_interpretations, list):
                for interp_data in market_interpretations:
                    if isinstance(interp_data, dict):
                        component_name = interp_data.get('component', '')
                        display_name = interp_data.get('display_name', component_name.replace('_', ' ').title())
                        interpretation_text = interp_data.get('interpretation', '')
                        
                        # Skip divergence analysis and enhanced analysis - they get handled separately
                        if component_name.lower() in ['divergence_analysis', 'enhanced_analysis']:
                            continue
                            
                        if interpretation_text:
                            # Wrap long interpretations for clean display
                            wrapped_lines = textwrap.fill(interpretation_text, width=70).split('\n')
                            
                            if wrapped_lines:
                                first_line = wrapped_lines[0]
                                interpretations.append(f"  🔵 • {display_name}: {first_line}")
                                
                                # Add subsequent lines with proper indentation
                                for subsequent_line in wrapped_lines[1:]:
                                    interpretations.append(f"     {subsequent_line}")
                
                logger.debug(f"Processed market_interpretations field: generated {len(interpretations)} interpretation lines")
                if interpretations:
                    return interpretations
        
        # PRIORITY 2: Try to use InterpretationManager for consistent processing (existing logic)
        try:
            from src.core.interpretation.interpretation_manager import InterpretationManager
            
            # Convert results to format suitable for InterpretationManager
            raw_interpretations = []
            for component_name, component_data in results.items():
                # Skip the market_interpretations field itself
                if component_name == 'market_interpretations':
                    continue
                    
                if not isinstance(component_data, dict):
                    logger.debug(f"Skipping {component_name}: not a dict ({type(component_data)})")
                    continue
                
                logger.debug(f"Processing {component_name} with keys: {list(component_data.keys())}")
                
                # Extract interpretation from component data
                interpretation = None
                if 'enhanced_interpretation' in component_data:
                    interpretation = component_data['enhanced_interpretation']
                    logger.debug(f"Found enhanced_interpretation for {component_name}")
                elif 'interpretation' in component_data:
                    interp = component_data['interpretation']
                    if isinstance(interp, str):
                        interpretation = interp
                        logger.debug(f"Found string interpretation for {component_name}")
                    elif isinstance(interp, dict) and 'summary' in interp:
                        interpretation = interp['summary']
                        logger.debug(f"Found dict interpretation.summary for {component_name}")
                elif 'signals' in component_data:
                    signals = component_data['signals']
                    if signals and isinstance(signals, dict):
                        interpretation = _summarize_signals(signals)
                        logger.debug(f"Built summarized interpretation from dict-valued signals for {component_name}")
                
                if interpretation:
                    raw_interpretations.append({
                        'component': component_name,
                        'display_name': component_name.replace('_', ' ').title(),
                        'interpretation': interpretation
                    })
                else:
                    logger.debug(f"No interpretation found for {component_name}")
            
            # Process through InterpretationManager
            if raw_interpretations:
                logger.debug(f"Processing {len(raw_interpretations)} interpretations through InterpretationManager")
                import datetime
                manager = InterpretationManager()
                interpretation_set = manager.process_interpretations(
                    raw_interpretations, 
                    'formatter',
                    None,  # No market data available in this context
                    datetime.datetime.now()
                )
                
                # Format the standardized interpretations for PrettyTable
                for interpretation in interpretation_set.interpretations:
                    display_name = interpretation.component_name.replace('_', ' ').title()
                    
                    # Add severity indicator
                    severity_indicator = "🔴" if interpretation.severity.value == "critical" else "🟡" if interpretation.severity.value == "warning" else "🔵"
                    
                    # Wrap long interpretations for clean display
                    wrapped_lines = textwrap.fill(interpretation.interpretation_text, width=70).split('\n')
                    
                    if wrapped_lines:
                        first_line = wrapped_lines[0]
                        interpretations.append(f"  {severity_indicator} • {display_name}: {first_line}")
                        
                        # Add subsequent lines with proper indentation
                        for subsequent_line in wrapped_lines[1:]:
                            interpretations.append(f"     {subsequent_line}")
                        
                        # Add empty line between components for readability
                        interpretations.append("")
            else:
                logger.debug("No raw interpretations found for InterpretationManager")
                        
        except Exception as e:
            # Fallback to basic interpretation processing
            logger.debug(f"InterpretationManager processing failed: {e}")
            pass
        
        # PRIORITY 3: Fallback to basic processing if InterpretationManager is not available or failed
        if not interpretations:
            logger.debug("Falling back to basic interpretation processing")
            for component_name, component_data in results.items():
                # Skip the market_interpretations field itself
                if component_name == 'market_interpretations':
                    continue
                    
                if not isinstance(component_data, dict):
                    continue
                
                display_name = component_name.replace('_', ' ').title()
                
                # Try to get interpretation
                interpretation = None
                if 'enhanced_interpretation' in component_data:
                    interpretation = component_data['enhanced_interpretation']
                elif 'interpretation' in component_data:
                    interp = component_data['interpretation']
                    if isinstance(interp, str):
                        interpretation = interp
                    elif isinstance(interp, dict) and 'summary' in interp:
                        interpretation = interp['summary']
                elif 'signals' in component_data and isinstance(component_data['signals'], dict):
                    # Safety net: narrate signals directly when no explicit interpretation provided
                    summarized = _summarize_signals(component_data['signals'])
                    if summarized:
                        interpretation = summarized
                else:
                    # Check if component_data itself contains dict-valued signal fields (Price Structure pattern)
                    potential_signals = {}
                    for key, value in component_data.items():
                        if key not in ['score', 'enhanced_interpretation', 'interpretation', 'reliability', 'components'] and isinstance(value, dict):
                            # This looks like a signal dict (e.g., support_resistance, order_blocks)
                            potential_signals[key] = value

                    if potential_signals:
                        # Found signal-like dictionaries at top level - summarize them
                        summarized = _summarize_signals(potential_signals)
                        if summarized:
                            interpretation = summarized
                
                if interpretation:
                    # Wrap long interpretations
                    wrapped_interp = textwrap.fill(interpretation, width=70)
                    interpretations.append(f"  🔵 • {display_name}: {wrapped_interp}")
        
        # PRIORITY 4: If still no interpretations, generate basic ones from available data
        if not interpretations:
            logger.debug("No interpretations found, generating basic ones from component data")
            for component_name, component_data in results.items():
                # Skip the market_interpretations field itself
                if component_name == 'market_interpretations':
                    continue
                    
                if not isinstance(component_data, dict):
                    continue
                
                display_name = component_name.replace('_', ' ').title()
                
                # Generate basic interpretation from component structure
                if 'components' in component_data:
                    sub_components = component_data['components']
                    if isinstance(sub_components, dict):
                        # Count bullish/bearish signals
                        bullish_count = 0
                        bearish_count = 0
                        neutral_count = 0
                        
                        for sub_name, sub_data in sub_components.items():
                            if isinstance(sub_data, dict) and 'signal' in sub_data:
                                signal = sub_data['signal'].lower()
                                if 'bull' in signal:
                                    bullish_count += 1
                                elif 'bear' in signal:
                                    bearish_count += 1
                                else:
                                    neutral_count += 1
                        
                        # Generate interpretation based on signal distribution
                        total_signals = bullish_count + bearish_count + neutral_count
                        if total_signals > 0:
                            if bullish_count > bearish_count:
                                bias = "bullish"
                                strength = "strong" if bullish_count > total_signals * 0.6 else "moderate"
                            elif bearish_count > bullish_count:
                                bias = "bearish"
                                strength = "strong" if bearish_count > total_signals * 0.6 else "moderate"
                            else:
                                bias = "neutral"
                                strength = "balanced"
                            
                            interpretation = f"{display_name} shows {strength} {bias} signals with {bullish_count} bullish, {bearish_count} bearish, and {neutral_count} neutral indicators."
                            interpretations.append(f"  🔵 • {display_name}: {interpretation}")
                
                # If no components, try to generate from score if available
                elif 'score' in component_data:
                    score = component_data['score']
                    if score >= 70:
                        interpretation = f"{display_name} shows strong bullish conditions with high score ({score:.1f})."
                    elif score >= 55:
                        interpretation = f"{display_name} indicates moderate bullish bias with score ({score:.1f})."
                    elif score >= 45:
                        interpretation = f"{display_name} reflects neutral market conditions with balanced score ({score:.1f})."
                    elif score >= 30:
                        interpretation = f"{display_name} suggests moderate bearish pressure with score ({score:.1f})."
                    else:
                        interpretation = f"{display_name} indicates strong bearish conditions with low score ({score:.1f})."
                    
                    interpretations.append(f"  🔵 • {display_name}: {interpretation}")
        
        logger.debug(f"Generated {len(interpretations)} interpretation lines")
        return interpretations

    @staticmethod
    def _generate_enhanced_actionable_insights(confluence_score, components, results):
        """Generate enhanced actionable trading insights using EnhancedFormatter logic."""
        insights = []
        
        # Determine buy/sell thresholds from results if available
        buy_threshold = 60.0
        sell_threshold = 40.0
        
        if results and isinstance(results, dict):
            for component_data in results.values():
                if isinstance(component_data, dict):
                    if 'buy_threshold' in component_data:
                        buy_threshold = component_data['buy_threshold']
                    if 'sell_threshold' in component_data:
                        sell_threshold = component_data['sell_threshold']
                    break
        
        # Overall stance with enhanced logic
        if confluence_score is not None and confluence_score >= buy_threshold:
            insights.append(f"  • BULLISH BIAS: Score ({confluence_score:.2f}) above buy threshold - consider long positions")
        elif confluence_score is not None and confluence_score >= sell_threshold:
            insights.append(f"  • NEUTRAL STANCE: Range-bound conditions likely - consider mean-reversion strategies")
        elif confluence_score is not None:
            insights.append(f"  • BEARISH BIAS: Score ({confluence_score:.2f}) below sell threshold - avoid long exposure")
        else:
            insights.append(f"  • NO DATA: Score unavailable - insufficient data for analysis")
        
        # Risk assessment from components and results
        risk_assessment_added = False
        if results:
            # Look for explicit risk level in results first
            for component_name, component_data in results.items():
                if isinstance(component_data, dict) and 'risk_level' in component_data:
                    risk_level = component_data['risk_level']
                    if risk_level == 'HIGH':
                        insights.append("  • RISK ASSESSMENT: HIGH - Avoid new positions until risk conditions improve")
                    elif risk_level == 'MEDIUM':
                        insights.append("  • RISK ASSESSMENT: MEDIUM - Use reduced position sizing")
                    elif risk_level == 'LOW':
                        insights.append("  • RISK ASSESSMENT: LOW - Normal position sizing acceptable")
                    risk_assessment_added = True
                    break
        
        # Fallback risk assessment from components if not found in results
        if not risk_assessment_added and components:
            sentiment_score = components.get('sentiment', 50.0)
            if sentiment_score > 80 or sentiment_score < 20:
                insights.append("  • RISK ASSESSMENT: HIGH - Extreme sentiment conditions detected")
                risk_assessment_added = True
            elif sentiment_score > 65 or sentiment_score < 35:
                insights.append("  • RISK ASSESSMENT: MEDIUM - Elevated sentiment conditions")
                risk_assessment_added = True
            else:
                insights.append("  • RISK ASSESSMENT: LOW - Normal sentiment conditions")
                risk_assessment_added = True
        
        # Component-specific insights
        if components:
            # Component-specific insights
            strongest_component = max(components.items(), key=lambda x: x[1])
            if strongest_component[1] > 70:
                component_name = strongest_component[0].replace('_', ' ').title()
                insights.append(f"  • STRENGTH: {component_name} shows strong bullish signals")
            
            # Check for divergences
            component_scores = list(components.values())
            if max(component_scores) - min(component_scores) > 30:
                insights.append("  • DIVERGENCE: Mixed signals across components - wait for clearer direction")
        
        # Extract specific insights from results
        if results:
            # Look for key levels or specific insights
            for component_name, component_data in results.items():
                if isinstance(component_data, dict):
                    if 'key_levels' in component_data:
                        insights.append("  • KEY LEVELS: Strong bid liquidity cluster")
        
        # Strategy recommendations
        if confluence_score is not None and confluence_score >= buy_threshold:
            insights.append("  • STRATEGY: Monitor for pullbacks to key support levels for entry opportunities")
        elif confluence_score is not None and confluence_score >= sell_threshold:
            insights.append("  • STRATEGY: Monitor for further confirmation before implementing directional strategies")
        else:
            insights.append("  • STRATEGY: Wait for trend reversal signals before considering long positions")
        
        return insights

    @staticmethod
    def _format_top_components_table(results, border_style="double"):
        """Format top influential components using PrettyTable for clean presentation."""
        if not results:
            return ""
            
        top_components = PrettyTableFormatter._extract_top_components(results)
        if not top_components:
            return ""
            
        # Create PrettyTable for top components
        table = PrettyTable()
        
        # Set border style
        if border_style == "single":
            table.set_style(SINGLE_BORDER)
        elif border_style == "double":
            table.set_style(DOUBLE_BORDER)
        elif border_style == "markdown":
            table.set_style(MARKDOWN)
        else:
            table.set_style(DEFAULT)
        
        # Define field names
        table.field_names = ["Component", "Parent", "Score", "Trend", "Gauge"]
        
        # Set column alignments
        table.align["Component"] = "l"
        table.align["Parent"] = "l" 
        table.align["Score"] = "r"
        table.align["Trend"] = "c"
        table.align["Gauge"] = "l"
        
        # Set column widths for optimal display
        table.max_width["Component"] = 25
        table.max_width["Parent"] = 12
        table.max_width["Score"] = 8
        table.max_width["Trend"] = 5
        table.max_width["Gauge"] = 25
        
        # Add top 5 components
        for comp_name, comp_score in top_components[:5]:
            # Extract parent component if available
            parent = "Unknown"
            if "(" in comp_name and ")" in comp_name:
                # Extract parent from format like "spread (orderbook)"
                parent_match = comp_name.split("(")
                if len(parent_match) > 1:
                    parent = parent_match[1].replace(")", "").strip().title()
                    comp_name = parent_match[0].strip()
            
            # Get color and formatting
            gauge = PrettyTableFormatter._create_gauge(comp_score, 20)  # Shorter gauge for table
            trend = PrettyTableFormatter._get_trend_indicator(comp_score)
            score_color = PrettyTableFormatter._get_score_color(comp_score)
            
            # Format score with color
            formatted_score = f"{score_color}{comp_score:>6.2f}{PrettyTableFormatter.RESET}"
            
            # Add row to table
            table.add_row([
                comp_name,
                parent,
                formatted_score,
                trend,
                gauge
            ])
        
        # Create section with header
        output = []
        output.append(f"{PrettyTableFormatter.BOLD}Top Influential Individual Components{PrettyTableFormatter.RESET}")
        output.append(str(table))
        output.append("")
        
        return "\n".join(output)


    @staticmethod
    def _format_enhanced_analysis_section(enhanced_analysis_text):
        """
        Format the Enhanced Analysis section with improved visual hierarchy and structure.
        
        Args:
            enhanced_analysis_text (str): The raw enhanced analysis text from _generate_enhanced_synthesis
            
        Returns:
            str: Formatted enhanced analysis with proper visual hierarchy
        """
        if not enhanced_analysis_text or not enhanced_analysis_text.strip():
            return ""
        
        # The enhanced analysis comes as a single line with sections separated by patterns
        # We need to split on the section markers and parse each section
        
        import re
        
        # Use regex to split the text into sections
        # This handles the case where everything is on one line
        text = enhanced_analysis_text
        
        # Extract sections using regex patterns
        market_state_match = re.search(r'\*\*MARKET STATE:\s*([^*]+?)(?=\s*\*\*|\s*$)', text)
        drivers_match = re.search(r'\*\*PRIMARY MARKET DRIVERS:\*\*\s*(.*?)(?=\s*\*\*🎯|\s*$)', text, re.DOTALL)
        recommendations_match = re.search(r'\*\*🎯 ACTIONABLE RECOMMENDATIONS:\*\*\s*(.*?)(?=\s*\*\*⚠️|\s*$)', text, re.DOTALL)
        risk_match = re.search(r'\*\*⚠️ RISK ASSESSMENT:\*\*\s*(.*?)$', text, re.DOTALL)
        
        sections = []
        
        if market_state_match:
            market_state_content = market_state_match.group(1).strip()
            sections.append(("MARKET_STATE", [f"**MARKET STATE: {market_state_content}**"]))
        
        if drivers_match:
            drivers_content = drivers_match.group(1).strip()
            sections.append(("PRIMARY_DRIVERS", ["**PRIMARY MARKET DRIVERS:**", drivers_content]))
        
        if recommendations_match:
            recommendations_content = recommendations_match.group(1).strip()
            sections.append(("ACTIONABLE_RECOMMENDATIONS", ["**🎯 ACTIONABLE RECOMMENDATIONS:**", recommendations_content]))
        
        if risk_match:
            risk_content = risk_match.group(1).strip()
            sections.append(("RISK_ASSESSMENT", ["**⚠️ RISK ASSESSMENT:**", risk_content]))
        
        # Format each section with proper visual hierarchy
        formatted_sections = []
        
        for section_type, content in sections:
            if section_type == "MARKET_STATE":
                # Format market state as a prominent header
                market_state_line = content[0] if content else ""
                market_state = market_state_line.replace('**MARKET STATE:', '').replace('**', '').strip()
                formatted_sections.append(f"📊 {PrettyTableFormatter.BOLD}{PrettyTableFormatter.CYAN}MARKET STATE:{PrettyTableFormatter.RESET} {PrettyTableFormatter.BOLD}{market_state}{PrettyTableFormatter.RESET}")
                
            elif section_type == "PRIMARY_DRIVERS":
                # Format primary drivers as a structured list
                formatted_sections.append(f"\n🎯 {PrettyTableFormatter.BOLD}{PrettyTableFormatter.YELLOW}PRIMARY MARKET DRIVERS:{PrettyTableFormatter.RESET}")
                
                # Parse the drivers from the content
                drivers_text = ' '.join(content[1:]) if len(content) > 1 else ""
                
                # Split drivers by • pattern
                driver_items = drivers_text.split('• **')
                for item in driver_items:
                    if item.strip():
                        # Clean up the item
                        item = item.strip()
                        if not item.startswith('**'):
                            item = '**' + item
                        
                        # Parse driver line: **Component** (impact%, bias): description
                        parts = item.split(':', 1)
                        if len(parts) == 2:
                            driver_info = parts[0].replace('**', '').strip()
                            description = parts[1].strip()
                            formatted_sections.append(f"  ▪ {PrettyTableFormatter.BOLD}{driver_info}{PrettyTableFormatter.RESET}: {description}")
                        else:
                            formatted_sections.append(f"  ▪ {item.replace('**', '').strip()}")
                
            elif section_type == "ACTIONABLE_RECOMMENDATIONS":
                # Format actionable recommendations as a clear action list
                formatted_sections.append(f"\n🎯 {PrettyTableFormatter.BOLD}{PrettyTableFormatter.GREEN}ACTIONABLE RECOMMENDATIONS:{PrettyTableFormatter.RESET}")
                
                # Parse the recommendations from the content
                recs_text = ' '.join(content[1:]) if len(content) > 1 else ""
                
                # Split recommendations by • pattern
                rec_items = recs_text.split('• **')
                for item in rec_items:
                    if item.strip():
                        # Clean up the item
                        item = item.strip()
                        if not item.startswith('**'):
                            item = '**' + item
                        
                        # Parse recommendation: **Type**: description
                        parts = item.split(':', 1)
                        if len(parts) == 2:
                            rec_type = parts[0].replace('**', '').strip()
                            description = parts[1].replace('**', '').strip()
                            formatted_sections.append(f"  ✓ {PrettyTableFormatter.BOLD}{rec_type}{PrettyTableFormatter.RESET}: {description}")
                        else:
                            formatted_sections.append(f"  ✓ {item.replace('**', '').strip()}")
                
            elif section_type == "RISK_ASSESSMENT":
                # Format risk assessment as a highlighted warning section
                formatted_sections.append(f"\n⚠️  {PrettyTableFormatter.BOLD}{PrettyTableFormatter.RED}RISK ASSESSMENT:{PrettyTableFormatter.RESET}")
                
                # Parse the risk items from the content
                risk_text = ' '.join(content[1:]) if len(content) > 1 else ""
                
                # Split risk items by • pattern
                risk_items = risk_text.split('• **')
                for item in risk_items:
                    if item.strip():
                        # Clean up the item
                        item = item.strip()
                        if not item.startswith('**'):
                            item = '**' + item
                        
                        # Parse risk item: **Risk Level**: description
                        parts = item.split(':', 1)
                        if len(parts) == 2:
                            risk_type = parts[0].replace('**', '').strip()
                            description = parts[1].replace('**', '').strip()
                            # Color code risk levels
                            if 'HIGH' in risk_type.upper():
                                color = PrettyTableFormatter.RED
                            elif 'MODERATE' in risk_type.upper() or 'MEDIUM' in risk_type.upper():
                                color = PrettyTableFormatter.YELLOW
                            else:
                                color = PrettyTableFormatter.GREEN
                            formatted_sections.append(f"  ⚠ {color}{PrettyTableFormatter.BOLD}{risk_type}{PrettyTableFormatter.RESET}: {description}")
                        else:
                            formatted_sections.append(f"  ⚠ {item.replace('**', '').strip()}")
        
        # Join all sections with proper spacing
        return '\n'.join(formatted_sections)

    @staticmethod
    def _format_interpretations_table(results, border_style="double"):
        """Format market interpretations using PrettyTable for clean presentation."""
        interpretations = PrettyTableFormatter._format_enhanced_interpretations(results)
        if not interpretations:
            return ""
        
        # Create PrettyTable for interpretations
        table = PrettyTable()
        
        # Set border style
        if border_style == "single":
            table.set_style(SINGLE_BORDER)
        elif border_style == "double":
            table.set_style(DOUBLE_BORDER)
        elif border_style == "markdown":
            table.set_style(MARKDOWN)
        else:
            table.set_style(DEFAULT)
        
        # Define field names
        table.field_names = ["Component", "Interpretation"]
        
        # Set column alignments
        table.align["Component"] = "l"
        table.align["Interpretation"] = "l"
        
        # Set column widths for optimal display
        table.max_width["Component"] = 20
        table.max_width["Interpretation"] = 55
        
        # Process interpretations into table rows
        current_component = None
        current_interpretation_lines = []
        enhanced_analysis_text = None
        
        # Debug logging to show what interpretations we're processing
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Processing {len(interpretations)} interpretation lines for table display")
        
        for interp_line in interpretations:
            if not interp_line.strip():
                # Empty line - if we have accumulated interpretation, add it to table
                if current_component and current_interpretation_lines:
                    full_interpretation = " ".join(current_interpretation_lines)
                    
                    # Check if this is Enhanced Analysis or Divergence Analysis - handle them specially
                    if current_component.lower() in ["enhanced analysis", "divergence analysis"]:
                        enhanced_analysis_text = full_interpretation
                    else:
                        table.add_row([current_component, full_interpretation])
                    
                    current_component = None
                    current_interpretation_lines = []
                continue
                
            # Check if this is a new component line (starts with emoji and bullet)
            if interp_line.strip().startswith(("🔵 •", "🟡 •", "🔴 •")):
                # If we have a previous component, add it first
                if current_component and current_interpretation_lines:
                    full_interpretation = " ".join(current_interpretation_lines)
                    
                    # Check if this is Enhanced Analysis or Divergence Analysis - handle them specially
                    if current_component.lower() in ["enhanced analysis", "divergence analysis"]:
                        enhanced_analysis_text = full_interpretation
                    else:
                        table.add_row([current_component, full_interpretation])
                
                # Parse new component
                parts = interp_line.split(":", 1)
                if len(parts) >= 2:
                    # Extract component name (remove emoji and bullet)
                    component_part = parts[0].replace("🔵 •", "").replace("🟡 •", "").replace("🔴 •", "").strip()
                    current_component = component_part
                    current_interpretation_lines = [parts[1].strip()]
                else:
                    current_component = interp_line.strip()
                    current_interpretation_lines = []
            else:
                # This is a continuation line
                if current_component:
                    current_interpretation_lines.append(interp_line.strip())
        
        # Add final component if exists
        if current_component and current_interpretation_lines:
            full_interpretation = " ".join(current_interpretation_lines)
            
            # Check if this is Enhanced Analysis - handle it specially
            if current_component.lower() == "enhanced analysis":
                enhanced_analysis_text = full_interpretation
            else:
                table.add_row([current_component, full_interpretation])
        
        # Create section with header
        output = []
        output.append(f"{PrettyTableFormatter.BOLD}Market Interpretations{PrettyTableFormatter.RESET}")
        
        # Debug logging to show how many rows are in the table
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Market Interpretations table has {len(table._rows)} rows")
        for i, row in enumerate(table._rows):
            logger.debug(f"Row {i+1}: {row[0] if row else 'Empty'}")
        
        output.append(str(table))
        
        # Add Enhanced Analysis section separately with improved formatting
        if enhanced_analysis_text:
            output.append("")  # Add spacing
            formatted_enhanced_analysis = PrettyTableFormatter._format_enhanced_analysis_section(enhanced_analysis_text)
            if formatted_enhanced_analysis:
                output.append(f"{PrettyTableFormatter.BOLD}Enhanced Analysis{PrettyTableFormatter.RESET}")
                output.append("─" * 60)  # Visual separator
                output.append(formatted_enhanced_analysis)
        
        output.append("")
        
        return "\n".join(output)