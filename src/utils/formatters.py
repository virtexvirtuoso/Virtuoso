"""
Data formatting utilities for Virtuoso.

Provides formatting services for various data types including
market data, timestamps, numbers, and text formatting.
"""

from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import json
import logging
from ..core.interfaces.services import IFormattingService

logger = logging.getLogger(__name__)


class DataFormatter(IFormattingService):
    """
    Data formatting service that implements IFormattingService interface.
    
    Provides consistent formatting for:
    - Numbers and percentages
    - Timestamps and dates
    - Market data
    - JSON serialization
    - Text formatting
    """
    
    def __init__(self):
        """Initialize data formatter."""
        self._logger = logging.getLogger(__name__)
    
    def format_number(
        self, 
        value: Union[int, float, Decimal], 
        precision: int = 2, 
        use_thousands_separator: bool = True
    ) -> str:
        """
        Format number with specified precision.
        
        Args:
            value: Number to format
            precision: Decimal places
            use_thousands_separator: Whether to use comma separators
            
        Returns:
            Formatted number string
        """
        try:
            if value is None:
                return "N/A"
            
            if isinstance(value, str):
                value = float(value)
            
            # Convert to Decimal for precise formatting
            decimal_value = Decimal(str(value))
            
            # Round to specified precision
            rounded = decimal_value.quantize(
                Decimal('0.' + '0' * precision), 
                rounding=ROUND_HALF_UP
            )
            
            # Format with thousands separator if requested
            if use_thousands_separator:
                return f"{rounded:,}"
            else:
                return str(rounded)
        
        except Exception as e:
            self._logger.warning(f"Error formatting number {value}: {e}")
            return str(value)
    
    def format_percentage(
        self, 
        value: Union[int, float, Decimal], 
        precision: int = 2,
        include_sign: bool = True
    ) -> str:
        """
        Format value as percentage.
        
        Args:
            value: Value to format (0.15 = 15%)
            precision: Decimal places
            include_sign: Whether to include + for positive values
            
        Returns:
            Formatted percentage string
        """
        try:
            if value is None:
                return "N/A"
            
            percentage = float(value) * 100
            formatted = self.format_number(percentage, precision, False)
            
            if include_sign and percentage > 0:
                return f"+{formatted}%"
            else:
                return f"{formatted}%"
        
        except Exception as e:
            self._logger.warning(f"Error formatting percentage {value}: {e}")
            return f"{value}%"
    
    def format_currency(
        self, 
        value: Union[int, float, Decimal], 
        currency: str = "USD",
        precision: int = 2
    ) -> str:
        """
        Format value as currency.
        
        Args:
            value: Amount to format
            currency: Currency symbol or code
            precision: Decimal places
            
        Returns:
            Formatted currency string
        """
        try:
            if value is None:
                return f"N/A {currency}"
            
            formatted_amount = self.format_number(value, precision)
            
            # Common currency symbols
            symbols = {
                'USD': '$',
                'EUR': '€',
                'GBP': '£',
                'JPY': '¥',
                'BTC': '₿',
                'ETH': 'Ξ'
            }
            
            symbol = symbols.get(currency.upper(), currency)
            
            if symbol in ['$', '€', '£', '¥', '₿', 'Ξ']:
                return f"{symbol}{formatted_amount}"
            else:
                return f"{formatted_amount} {currency}"
        
        except Exception as e:
            self._logger.warning(f"Error formatting currency {value}: {e}")
            return f"{value} {currency}"
    
    def format_timestamp(
        self, 
        timestamp: Union[datetime, float, int], 
        format_str: str = "%Y-%m-%d %H:%M:%S UTC"
    ) -> str:
        """
        Format timestamp to string.
        
        Args:
            timestamp: Timestamp to format
            format_str: Format string
            
        Returns:
            Formatted timestamp string
        """
        try:
            if timestamp is None:
                return "N/A"
            
            if isinstance(timestamp, (int, float)):
                # Convert Unix timestamp
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, datetime):
                dt = timestamp
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                return str(timestamp)
            
            return dt.strftime(format_str)
        
        except Exception as e:
            self._logger.warning(f"Error formatting timestamp {timestamp}: {e}")
            return str(timestamp)
    
    def format_duration(self, seconds: Union[int, float]) -> str:
        """
        Format duration in seconds to human-readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        try:
            if seconds is None:
                return "N/A"
            
            seconds = int(seconds)
            
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                minutes = seconds // 60
                remaining_seconds = seconds % 60
                return f"{minutes}m {remaining_seconds}s"
            elif seconds < 86400:
                hours = seconds // 3600
                remaining_minutes = (seconds % 3600) // 60
                return f"{hours}h {remaining_minutes}m"
            else:
                days = seconds // 86400
                remaining_hours = (seconds % 86400) // 3600
                return f"{days}d {remaining_hours}h"
        
        except Exception as e:
            self._logger.warning(f"Error formatting duration {seconds}: {e}")
            return f"{seconds}s"
    
    def format_market_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Format market data for display.
        
        Args:
            data: Market data dictionary
            
        Returns:
            Dictionary with formatted values
        """
        formatted = {}
        
        try:
            for key, value in data.items():
                if key.lower() in ['price', 'high', 'low', 'open', 'close', 'vwap']:
                    formatted[key] = self.format_currency(value, precision=4)
                elif key.lower() in ['volume', 'amount']:
                    formatted[key] = self.format_number(value, precision=0)
                elif key.lower() in ['change', 'percentage', 'change_percent']:
                    formatted[key] = self.format_percentage(value)
                elif key.lower() in ['timestamp', 'time', 'datetime']:
                    formatted[key] = self.format_timestamp(value)
                else:
                    formatted[key] = str(value)
        
        except Exception as e:
            self._logger.warning(f"Error formatting market data: {e}")
            formatted = {k: str(v) for k, v in data.items()}
        
        return formatted
    
    def format_json(
        self, 
        data: Any, 
        indent: int = 2, 
        ensure_ascii: bool = False
    ) -> str:
        """
        Format data as JSON string.
        
        Args:
            data: Data to format
            indent: JSON indentation
            ensure_ascii: Whether to ensure ASCII encoding
            
        Returns:
            Formatted JSON string
        """
        try:
            return json.dumps(
                data, 
                indent=indent, 
                ensure_ascii=ensure_ascii,
                default=self._json_default
            )
        except Exception as e:
            self._logger.warning(f"Error formatting JSON: {e}")
            return str(data)
    
    def _json_default(self, obj: Any) -> Any:
        """JSON serialization for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def format_table(
        self, 
        data: List[Dict[str, Any]], 
        headers: Optional[List[str]] = None
    ) -> str:
        """
        Format data as ASCII table.
        
        Args:
            data: List of dictionaries to format
            headers: Optional header list
            
        Returns:
            Formatted table string
        """
        try:
            if not data:
                return "No data available"
            
            if headers is None:
                headers = list(data[0].keys())
            
            # Calculate column widths
            col_widths = {}
            for header in headers:
                col_widths[header] = len(header)
                for row in data:
                    value = str(row.get(header, ''))
                    col_widths[header] = max(col_widths[header], len(value))
            
            # Build table
            lines = []
            
            # Header
            header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
            lines.append(header_line)
            lines.append("-" * len(header_line))
            
            # Data rows
            for row in data:
                row_line = " | ".join(
                    str(row.get(h, '')).ljust(col_widths[h]) for h in headers
                )
                lines.append(row_line)
            
            return "\n".join(lines)
        
        except Exception as e:
            self._logger.warning(f"Error formatting table: {e}")
            return str(data)
    
    def format_size(self, bytes_value: Union[int, float]) -> str:
        """
        Format byte size to human-readable string.
        
        Args:
            bytes_value: Size in bytes
            
        Returns:
            Formatted size string
        """
        try:
            if bytes_value is None:
                return "N/A"
            
            bytes_value = float(bytes_value)
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            
            return f"{bytes_value:.1f} PB"
        
        except Exception as e:
            self._logger.warning(f"Error formatting size {bytes_value}: {e}")
            return f"{bytes_value} B"
    
    def truncate_text(
        self, 
        text: str, 
        max_length: int, 
        suffix: str = "..."
    ) -> str:
        """
        Truncate text to maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix for truncated text
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        truncated_length = max_length - len(suffix)
        return text[:truncated_length] + suffix
    
    # IFormattingService interface methods
    
    def format_analysis_result(self, result: Dict[str, Any]) -> str:
        """Format analysis results for display."""
        try:
            formatted_parts = []
            
            if 'confluence_score' in result:
                score = result['confluence_score']
                formatted_parts.append(f"Confluence Score: {self.format_number(score, 1)}")
            
            if 'signal' in result:
                signal = result['signal']
                formatted_parts.append(f"Signal: {signal}")
            
            if 'components' in result:
                components = result['components']
                if isinstance(components, dict):
                    for name, data in components.items():
                        if isinstance(data, dict) and 'score' in data:
                            score = data['score']
                            formatted_parts.append(f"{name.title()}: {self.format_number(score, 1)}")
            
            return " | ".join(formatted_parts) if formatted_parts else "No analysis data"
            
        except Exception as e:
            self._logger.warning(f"Error formatting analysis result: {e}")
            return str(result)
    
    def format_signal(self, signal: Dict[str, Any]) -> str:
        """Format trading signals for display."""
        try:
            signal_type = signal.get('signal', 'UNKNOWN')
            score = signal.get('score', 'N/A')
            confidence = signal.get('confidence', 'N/A')
            
            if isinstance(score, (int, float)):
                score_str = self.format_number(score, 1)
            else:
                score_str = str(score)
            
            return f"{signal_type} (Score: {score_str}, Confidence: {confidence})"
            
        except Exception as e:
            self._logger.warning(f"Error formatting signal: {e}")
            return str(signal)
    
    def format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics data for display."""
        try:
            formatted_metrics = []
            
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    if 'percentage' in key.lower() or 'percent' in key.lower():
                        formatted_value = self.format_percentage(value / 100)
                    elif 'price' in key.lower() or 'amount' in key.lower():
                        formatted_value = self.format_currency(value)
                    elif 'time' in key.lower() or 'duration' in key.lower():
                        formatted_value = self.format_duration(value)
                    else:
                        formatted_value = self.format_number(value)
                else:
                    formatted_value = str(value)
                
                formatted_metrics.append(f"{key}: {formatted_value}")
            
            return ", ".join(formatted_metrics)
            
        except Exception as e:
            self._logger.warning(f"Error formatting metrics: {e}")
            return str(metrics)
    
    def format_for_display(self, data: Dict[str, Any], format_type: str) -> str:
        """Format data for specific display type (console, web, mobile)."""
        try:
            if format_type.lower() == 'json':
                return self.format_json(data, indent=2)
            elif format_type.lower() == 'table':
                if isinstance(data, list):
                    return self.format_table(data)
                else:
                    # Convert single dict to list for table formatting
                    return self.format_table([data])
            elif format_type.lower() in ['console', 'terminal']:
                # Simple key-value format for console
                formatted_items = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        formatted_items.append(f"{key}: {self.format_json(value)}")
                    else:
                        formatted_items.append(f"{key}: {value}")
                return "\n".join(formatted_items)
            else:
                # Default formatting
                return str(data)
                
        except Exception as e:
            self._logger.warning(f"Error formatting for display type '{format_type}': {e}")
            return str(data)
    
    def format_chart_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data for chart display."""
        try:
            chart_data = {}
            
            for key, value in data.items():
                if isinstance(value, list):
                    # Assume time series data
                    chart_data[key] = [
                        {'x': i, 'y': float(v) if isinstance(v, (int, float)) else v}
                        for i, v in enumerate(value)
                    ]
                elif isinstance(value, (int, float)):
                    chart_data[key] = float(value)
                else:
                    chart_data[key] = str(value)
            
            return chart_data
            
        except Exception as e:
            self._logger.warning(f"Error formatting chart data: {e}")
            return data