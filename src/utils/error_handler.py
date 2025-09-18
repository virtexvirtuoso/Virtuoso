from typing import Dict


class UserFriendlyError:
    ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
        "EXCHANGE_CONNECTION_FAILED": {
            "message": "Unable to connect to {exchange}",
            "suggestion": "Check your API keys and network connection",
            "docs_link": "/docs/troubleshooting/connection-issues",
        },
        "INVALID_SYMBOL": {
            "message": "Symbol '{symbol}' not found",
            "suggestion": "Use a valid trading pair like 'BTCUSDT'",
            "docs_link": "/docs/user-guides/symbols",
        },
    }

    @classmethod
    def format_error(cls, error_code: str, **kwargs) -> Dict[str, str]:
        template = cls.ERROR_MESSAGES.get(error_code, {})
        return {
            "error": template.get("message", "Unknown error").format(**kwargs),
            "suggestion": template.get("suggestion", "Check the documentation"),
            "docs_link": template.get("docs_link", "/docs"),
        }


