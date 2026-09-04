from abc import ABC, abstractmethod
from typing import Dict, Any
from app.models.recovery_case import RecoveryCase

class BaseActionExecutor(ABC):
    """Abstract Base Class for Recovery Action Executions."""

    @property
    @abstractmethod
    def action_name(self) -> str:
        pass

    @abstractmethod
    def execute_action(self, case: RecoveryCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the recovery action and return status metadata."""
        pass
