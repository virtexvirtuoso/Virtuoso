try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable
from datetime import datetime

class ValidationProvider(Protocol):
    async def validate(self, data: Any) -> ValidationResult: ...
    async def get_validation_rules(self) -> Dict[str, Any]: ...

class AlertProvider(Protocol):
    async def send_alert(self, message: str, level: str, context: str) -> None: ...