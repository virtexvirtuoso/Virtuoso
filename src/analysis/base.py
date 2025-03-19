"""Base classes for analysis components."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

class BaseAnalyzer:
    """Base class for analysis components."""
    
    def __init__(self) -> None:
        """Initialize base analyzer."""
        self.logger = logging.getLogger("BaseAnalyzer")
    
    def create_result(self) -> AnalysisResult:
        """Create a new analysis result."""
        return AnalysisResult()
    
    async def handle_error(self, error: Exception, context: str) -> AnalysisResult:
        """Handle an error during analysis."""
        result = self.create_result()
        error_msg = f"{context}: {str(error)}"
        self.logger.error(error_msg)
        result.add_error(error_msg)
        return result
    
    def get_error_response(self, error_message: str) -> Dict[str, Any]:
        """Get standardized error response."""
        return {
            'status': 'error',
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'data': None
        } 