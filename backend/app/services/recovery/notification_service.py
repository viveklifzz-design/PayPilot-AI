from typing import Dict, Any
from app.services.recovery.base import BaseActionExecutor
from app.models.recovery_case import RecoveryCase
from app.core.logging import logger

class ReminderActionExecutor(BaseActionExecutor):
    """Executes customer payment reminder notification log generation."""

    @property
    def action_name(self) -> str:
        return "REMINDER"

    def execute_action(self, case: RecoveryCase, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Executing payment reminder notification for case '{case.id}'")
        return {
            "status": "SUCCEEDED",
            "provider_reference": f"reminder_notif_{case.id[:8]}",
            "message": f"Payment reminder notification generated for case '{case.id}'."
        }

reminder_action_executor = ReminderActionExecutor()
