from abc import ABC, abstractmethod
from typing import Dict, Any
from app.services.ai.schemas import AIDiagnosisOutput

class BaseAIService(ABC):
    """Abstract interface for AI Diagnosis services."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def diagnose_payment_failure(self, context: Dict[str, Any]) -> AIDiagnosisOutput:
        """Analyze transaction failure context and return structured AIDiagnosisOutput."""
        pass
