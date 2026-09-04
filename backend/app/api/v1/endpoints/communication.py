from fastapi import APIRouter
from app.services.recovery.communication_service import communication_service, RecoveryCommunicationPayload, RecoveryCommunicationResult

router = APIRouter(prefix="/communication", tags=["Communication Layer"])

@router.post("/generate", response_model=RecoveryCommunicationResult)
async def generate_communication(payload: RecoveryCommunicationPayload):
    """
    Generates Hinglish / Hindi / English recovery text messages and voice scripts.
    SECURITY & POLICY INVARIANT: Communication generation CANNOT move money directly or bypass Policy Gate.
    """
    return communication_service.generate_recovery_message(payload)
