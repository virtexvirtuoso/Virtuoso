"""
Reporting interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

@runtime_checkable
class ReportGeneratorInterface(Protocol):
    """Interface for report generators."""
    
    @abstractmethod
    async def generate_report(self, data: Dict[str, Any], template: Optional[str] = None) -> Union[str, bytes]:
        """
        Generate a report from data.
        
        Args:
            data: Report data
            template: Optional template name
            
        Returns:
            Generated report content
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported report formats."""
        pass
    
    @abstractmethod
    def set_template_path(self, path: Path) -> None:
        """Set template directory path."""
        pass

@runtime_checkable
class PDFGeneratorInterface(Protocol):
    """Interface for PDF generators."""
    
    @abstractmethod
    async def generate_pdf(self, html_content: str, options: Optional[Dict[str, Any]] = None) -> bytes:
        """Generate PDF from HTML content."""
        pass
    
    @abstractmethod
    def add_watermark(self, pdf_content: bytes, watermark_text: str) -> bytes:
        """Add watermark to PDF."""
        pass
    
    @abstractmethod
    def merge_pdfs(self, pdf_files: List[bytes]) -> bytes:
        """Merge multiple PDFs into one."""
        pass

@runtime_checkable
class ChartGeneratorInterface(Protocol):
    """Interface for chart generators."""
    
    @abstractmethod
    def generate_chart(self, data: Any, chart_type: str, options: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Generate a chart.
        
        Args:
            data: Chart data
            chart_type: Type of chart (line, bar, candlestick, etc.)
            options: Chart options
            
        Returns:
            Chart image bytes
        """
        pass
    
    @abstractmethod
    def get_supported_chart_types(self) -> List[str]:
        """Get list of supported chart types."""
        pass

@runtime_checkable
class NotificationInterface(Protocol):
    """Interface for notification services."""
    
    @abstractmethod
    async def send_notification(self, message: str, channel: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a notification.
        
        Args:
            message: Notification message
            channel: Notification channel (email, discord, telegram, etc.)
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    def get_supported_channels(self) -> List[str]:
        """Get list of supported notification channels."""
        pass
    
    @abstractmethod
    def format_message(self, data: Dict[str, Any], template: str) -> str:
        """Format message using template."""
        pass

@runtime_checkable
class DashboardInterface(Protocol):
    """Interface for dashboard providers."""
    
    @abstractmethod
    async def update_dashboard(self, data: Dict[str, Any]) -> None:
        """Update dashboard with new data."""
        pass
    
    @abstractmethod
    def get_dashboard_url(self) -> str:
        """Get dashboard URL."""
        pass
    
    @abstractmethod
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration."""
        pass
    
    @abstractmethod
    async def export_dashboard(self, format: str = 'html') -> Union[str, bytes]:
        """Export dashboard to specified format."""
        pass

class ReportingAdapter:
    """Adapter to make existing reporters compatible with ReportGeneratorInterface."""
    
    def __init__(self, reporter: Any):
        self.reporter = reporter
        
    async def generate_report(self, data: Dict[str, Any], template: Optional[str] = None) -> Union[str, bytes]:
        """Generate a report from data."""
        if hasattr(self.reporter, 'generate_report'):
            if template:
                return await self.reporter.generate_report(data, template)
            return await self.reporter.generate_report(data)
        elif hasattr(self.reporter, 'create_report'):
            return await self.reporter.create_report(data)
        elif hasattr(self.reporter, 'generate'):
            return await self.reporter.generate(data)
        else:
            raise NotImplementedError(f"Reporter {type(self.reporter)} has no report generation method")
            
    def get_supported_formats(self) -> List[str]:
        """Get list of supported report formats."""
        if hasattr(self.reporter, 'get_supported_formats'):
            return self.reporter.get_supported_formats()
        elif hasattr(self.reporter, 'supported_formats'):
            return self.reporter.supported_formats
        else:
            return ['html', 'pdf', 'json']
            
    def set_template_path(self, path: Path) -> None:
        """Set template directory path."""
        if hasattr(self.reporter, 'set_template_path'):
            self.reporter.set_template_path(path)
        elif hasattr(self.reporter, 'template_path'):
            self.reporter.template_path = path