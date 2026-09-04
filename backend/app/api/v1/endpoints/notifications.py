from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.notification_service import notification_service, NotificationSchema, UnreadCountResponse

router = APIRouter()

@router.get("/notifications", response_model=List[NotificationSchema], tags=["Notifications"])
async def list_notifications_endpoint(
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    severity: Optional[str] = Query(None, description="Filter by severity level (INFO, SUCCESS, WARNING, ERROR, CRITICAL)"),
    limit: int = Query(50, ge=1, le=100, description="Max notification items to return"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve list of recovery lifecycle notifications."""
    return await notification_service.list_notifications(db, unread_only=unread_only, severity=severity, limit=limit)

@router.get("/notifications/unread-count", response_model=UnreadCountResponse, tags=["Notifications"])
async def get_unread_notification_count(db: AsyncSession = Depends(get_db)):
    """Retrieve total count of unread notifications for badge rendering."""
    count = await notification_service.count_unread(db)
    return UnreadCountResponse(unread_count=count)

@router.post("/notifications/{id}/read", response_model=NotificationSchema, tags=["Notifications"])
async def mark_notification_read_endpoint(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark a specific notification as read."""
    success = await notification_service.mark_as_read(db, id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{id}' not found")
    
    # Return updated notification item
    items = await notification_service.list_notifications(db, limit=100)
    target = next((item for item in items if item.id == id), None)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification '{id}' not found")
    return target

@router.post("/notifications/read-all", tags=["Notifications"])
async def mark_all_notifications_read_endpoint(db: AsyncSession = Depends(get_db)):
    """Mark all unread notifications as read."""
    count = await notification_service.mark_all_as_read(db)
    return {"status": "success", "marked_read_count": count}
