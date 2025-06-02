"""
Security utilities for protecting sensitive information in logs and reports.
"""
import re
from typing import Any, Dict, List, Union
from copy import deepcopy


class CredentialRedactor:
    """Utility class for redacting sensitive information from data structures."""
    
    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = [
        'api_key', 'api_secret', 'access_token', 'refresh_token',
        'webhook_url', 'webhook', 'password', 'token', 'secret',
        'credential', 'auth', 'private_key', 'client_secret'
    ]
    
    # URL patterns that should be redacted
    URL_PATTERNS = [
        r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+',
        r'https://hooks\.slack\.com/services/[A-Z0-9/]+',
        r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
        r'[A-Za-z0-9]{40}',     # GitHub tokens (basic pattern)
    ]
    
    REDACTED_TEXT = "[REDACTED]"
    
    @classmethod
    def redact_data(cls, data: Any) -> Any:
        """
        Recursively redact sensitive information from any data structure.
        
        Args:
            data: The data structure to redact (dict, list, string, etc.)
            
        Returns:
            A copy of the data with sensitive information redacted
        """
        if data is None:
            return None
            
        # Create a deep copy to avoid modifying the original
        redacted_data = deepcopy(data)
        cls._redact_recursive(redacted_data)
        return redacted_data
    
    @classmethod
    def _redact_recursive(cls, obj: Any) -> None:
        """Recursively redact sensitive data in-place."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if cls._is_sensitive_key(key):
                    obj[key] = cls.REDACTED_TEXT
                elif isinstance(value, str) and cls._contains_sensitive_url(value):
                    obj[key] = cls._redact_url(value)
                elif isinstance(value, (dict, list)):
                    cls._redact_recursive(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str) and cls._contains_sensitive_url(item):
                    obj[i] = cls._redact_url(item)
                elif isinstance(item, (dict, list)):
                    cls._redact_recursive(item)
    
    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        """Check if a key name indicates sensitive data."""
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in cls.SENSITIVE_PATTERNS)
    
    @classmethod
    def _contains_sensitive_url(cls, value: str) -> bool:
        """Check if a string contains a sensitive URL pattern."""
        return any(re.search(pattern, value) for pattern in cls.URL_PATTERNS)
    
    @classmethod
    def _redact_url(cls, url: str) -> str:
        """Redact sensitive parts of URLs while keeping structure."""
        # Redact Discord webhook URLs
        url = re.sub(
            r'(https://discord\.com/api/webhooks/)\d+/[A-Za-z0-9_-]+',
            r'\1[WEBHOOK_ID]/[WEBHOOK_TOKEN]',
            url
        )
        
        # Redact Slack webhook URLs
        url = re.sub(
            r'(https://hooks\.slack\.com/services/)[A-Z0-9/]+',
            r'\1[REDACTED]',
            url
        )
        
        # Redact other token patterns
        for pattern in cls.URL_PATTERNS[2:]:  # Skip already handled Discord/Slack
            url = re.sub(pattern, cls.REDACTED_TEXT, url)
        
        return url
    
    @classmethod
    def redact_config_for_logging(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specifically redact configuration data for safe logging.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Redacted configuration safe for logging
        """
        return cls.redact_data(config)
    
    @classmethod
    def redact_log_message(cls, message: str) -> str:
        """
        Redact sensitive information from log messages.
        
        Args:
            message: Log message string
            
        Returns:
            Log message with sensitive data redacted
        """
        if not isinstance(message, str):
            return message
            
        redacted = message
        for pattern in cls.URL_PATTERNS:
            redacted = re.sub(pattern, cls.REDACTED_TEXT, redacted)
        
        return redacted


def redact_sensitive_data(data: Any) -> Any:
    """
    Convenience function for redacting sensitive data.
    
    Args:
        data: Any data structure that might contain sensitive information
        
    Returns:
        Data with sensitive information redacted
    """
    return CredentialRedactor.redact_data(data)


def safe_log_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for redacting configuration before logging.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration safe for logging
    """
    return CredentialRedactor.redact_config_for_logging(config)


# Example usage in diagnostic reports:
def create_safe_diagnostic_report(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a diagnostic report with all sensitive data redacted.
    
    Args:
        config: Full configuration object
        
    Returns:
        Safe configuration for diagnostic reports
    """
    return {
        'timestamp': 'generated_timestamp_here',
        'config': redact_sensitive_data(config),
        'note': 'Sensitive data has been redacted for security'
    } 