import math

class FormatPercentage:
    def _format_percentage(self, value: float) -> str:
        """Format a percentage value for display.
        
        Args:
            value: The percentage value to format
            
        Returns:
            Formatted percentage string with appropriate sign
        """
        if value is None or math.isnan(value):
            return "0.0%"
            
        # Add a plus sign for positive values
        if value > 0:
            return f"+{value:.1f}%"
        else:
            return f"{value:.1f}%" 