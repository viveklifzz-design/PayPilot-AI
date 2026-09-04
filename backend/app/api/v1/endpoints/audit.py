from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogItemResponse

router = APIRouter()

SENSITIVE_KEYS = {
    "key_secret", "razorpay_key_secret", "webhook_secret", "razorpay_webhook_secret",
    "authorization", "basic_auth", "password", "secret", "token", "api_key"
}

def sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not meta or not isinstance(meta, dict):
        return meta
    
    clean: Dict[str, Any] = {}
    for k, v in meta.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            clean[k] = "[REDACTED_SECRET]"
        elif isinstance(v, dict):
            clean[k] = sanitize_metadata(v)
        else:
            clean[k] = v
    return clean

@router.get("/audit", response_model=List[AuditLogItemResponse], tags=["Audit Trail"])
async def list_audit_logs(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_time: Optional[datetime] = Query(None, description="Filter starting timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter ending timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Max logs returned"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch structured audit log trail with secret redaction enforced.
    Supports filtering by case_id, event_type, start_time, end_time.
    """
    query = select(AuditLog)
    if case_id:
        query = query.where(AuditLog.case_id == case_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if start_time:
        query = query.where(AuditLog.created_at >= start_time)
    if end_time:
        query = query.where(AuditLog.created_at <= end_time)

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    output = []
    for log in logs:
        clean_meta = sanitize_metadata(log.metadata_json)
        output.append(AuditLogItemResponse(
            id=log.id,
            case_id=log.case_id,
            actor=log.actor,
            event_type=log.event_type,
            description=log.description,
            metadata_json=clean_meta,
            created_at=log.created_at
        ))
    return output
