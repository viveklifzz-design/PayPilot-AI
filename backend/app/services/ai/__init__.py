from app.services.ai.base import BaseAIService
from app.services.ai.schemas import AIDiagnosisOutput
from app.services.ai.gemini_service import GeminiAIService, gemini_ai_service
from app.services.ai.fallback_service import DeterministicAIFallbackService, fallback_ai_service
from app.services.ai.prompts import PROMPT_VERSION

def get_ai_service() -> BaseAIService:
    """Factory function providing the active AI Diagnosis Service."""
    if gemini_ai_service.is_configured:
        return gemini_ai_service
    return fallback_ai_service

__all__ = [
    "BaseAIService",
    "AIDiagnosisOutput",
    "GeminiAIService",
    "gemini_ai_service",
    "DeterministicAIFallbackService",
    "fallback_ai_service",
    "get_ai_service",
    "PROMPT_VERSION"
]
