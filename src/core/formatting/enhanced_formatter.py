"""
Enhanced formatter for market interpretations.
Provides methods to format market interpretations with improved readability.
"""

import textwrap
from typing import Dict, Any, List, Optional

from src.core.formatting.formatter import AnalysisFormatter
from src.core.analysis.interpretation_generator import InterpretationGenerator

class EnhancedFormatter:
    """Enhanced formatter for market interpretations with improved readability."""
    
    @staticmethod
    def format_market_interpretations(results, table_width=80):
        """Format market interpretations section with enhanced readability."""
        # Market interpretations title with enhanced styling
        title = f"{AnalysisFormatter.BOLD}{AnalysisFormatter.CYAN}MARKET INTERPRETATIONS{AnalysisFormatter.RESET}"
        # Calculate padding for title, accounting for the length of the visible text, not formatting codes
        visible_title_len = len("MARKET INTERPRETATIONS")
        padding = table_width - visible_title_len - 2
        header = f"\n╠{'═' * table_width}╣"
        header += f"\n║ {title}{' ' * padding}║"
        header += f"\n╠{'═' * table_width}╣"
        
        # Extract interpretations from results
        interpretations_section = []
        for component_name, component_data in results.items():
            display_name = f"{AnalysisFormatter.BOLD}{component_name.replace('_', ' ').title()}{AnalysisFormatter.RESET}"
            # Calculate visible length without formatting codes
            visible_display_name_len = len(component_name.replace('_', ' ').title())
            
            # Skip non-dictionary values to prevent errors
            if not isinstance(component_data, dict):
                continue
            
            # Try to get enhanced interpretation
            interpretation = None
            
            # First check for enhanced_interpretation field that might be added
            if 'enhanced_interpretation' in component_data:
                interpretation = component_data['enhanced_interpretation']
            # Then try the interpretation field
            elif 'interpretation' in component_data:
                interp = component_data['interpretation']
                if isinstance(interp, str):
                    interpretation = interp
                elif isinstance(interp, dict) and 'summary' in interp:
                    interpretation = interp['summary']
            # Finally, build from signals
            elif 'signals' in component_data:
                signals = component_data['signals']
                if signals:
                    interpretation = ", ".join(f"{k}={v}" for k, v in signals.items())
            
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
    def format_cross_component_insights(cross_insights, table_width=80):
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
    def format_actionable_insights(actionable_insights, table_width=80):
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
    def format_enhanced_confluence_score_table(symbol, confluence_score, components, results, weights=None, reliability=0.0):
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
        
        # Get the standard confluence score table
        from src.core.formatting import LogFormatter
        header = LogFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=confluence_score,
            components=components,
            results=results,
            weights=weights,
            reliability=reliability
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
        
        # Generate enhanced interpretations for each component
        enhanced_results = {}
        for component_name, component_data in results.items():
            if isinstance(component_data, dict):
                try:
                    enhanced_interpretation = interpretation_generator.get_component_interpretation(
                        component_name, component_data
                    )
                    # Create a copy of the component data with the enhanced interpretation
                    enhanced_component = component_data.copy()
                    enhanced_component['enhanced_interpretation'] = enhanced_interpretation
                    enhanced_results[component_name] = enhanced_component
                except Exception:
                    # If there's an error, just use the original component data
                    enhanced_results[component_name] = component_data
            else:
                enhanced_results[component_name] = component_data
        
        # Add the market interpretations section with enhanced formatting
        market_interpretations = EnhancedFormatter.format_market_interpretations(enhanced_results, table_width)
        
        # Generate cross-component insights
        cross_insights = interpretation_generator.generate_cross_component_insights(results)
        
        # Add cross-component insights section if available
        cross_component_section = ""
        if cross_insights:
            cross_component_section = EnhancedFormatter.format_cross_component_insights(cross_insights, table_width)
        
        # Generate actionable insights
        actionable_insights = interpretation_generator.generate_actionable_insights(
            results, confluence_score, buy_threshold, sell_threshold
        )
        
        # Add actionable insights section if available
        actionable_section = ""
        if actionable_insights:
            actionable_section = EnhancedFormatter.format_actionable_insights(actionable_insights, table_width)
        
        # Combine all sections
        enhanced_table = header + market_interpretations + cross_component_section + actionable_section
        
        return enhanced_table 