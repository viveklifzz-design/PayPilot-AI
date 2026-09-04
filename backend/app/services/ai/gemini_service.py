import json
from typing import Dict, Any
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.logging import logger
from app.services.ai.base import BaseAIService
from app.services.ai.schemas import AIDiagnosisOutput
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.ai.fallback_service import fallback_ai_service

class GeminiAIService(BaseAIService):
    """
    Google Gemini AI Diagnosis Service using the official google-genai SDK.
    Enforces strict structured JSON output validation via Pydantic AIDiagnosisOutput.
    Reverts safely to DeterministicAIFallbackService on timeout or failure.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.model = model or settings.GEMINI_MODEL
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self) -> genai.Client:
        if not self.is_configured:
            raise ValueError("GEMINI_API_KEY environment variable is not configured.")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def diagnose_payment_failure(self, context: Dict[str, Any]) -> AIDiagnosisOutput:
        if not self.is_configured:
            logger.info("GEMINI_API_KEY not configured in environment. Engaging fallback service.")
            return fallback_ai_service.diagnose_payment_failure(context)

        prompt_text = build_user_prompt(context)
        logger.info(f"Calling Gemini API model '{self.model}' for structured diagnosis...")

        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=AIDiagnosisOutput,
                temperature=0.1
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt_text,
                config=config
            )
            
            raw_text = response.text
            logger.debug(f"Gemini API raw response: {raw_text}")
            
            parsed_json = json.loads(raw_text)
            diagnosis = AIDiagnosisOutput(**parsed_json)
            logger.info(f"Gemini diagnosis complete: action={diagnosis.recommended_action}, confidence={diagnosis.confidence}")
            return diagnosis
        except Exception as e:
            logger.error(f"Gemini API error or invalid response ({e}). Falling back safely.")
            return fallback_ai_service.diagnose_payment_failure(context)

gemini_ai_service = GeminiAIService()
