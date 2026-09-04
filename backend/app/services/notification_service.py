from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_

from app.models.notification import Notification
from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.core.logging import logger

class NotificationSchema(BaseModel):
    id: str
    case_id: Optional[str] = None
    merchant_id: str
    type: str
    severity: str
    title: str
    message: str
    is_read: bool
    action_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

class UnreadCountResponse(BaseModel):
    unread_count: int

class NotificationService:
    """
    Centralized PayPilot AI Notification Service.
    Handles idempotent lifecycle event notifications, false-success protection,
    unread counts, read state mutation, and seed notification generation.
    """

    async def create_notification(
        self,
        db: AsyncSession,
        type: str,
        severity: str,
        title: str,
        message: str,
        case_id: Optional[str] = None,
        merchant_id: str = "m_live_001",
        action_url: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Notification:
        # FALSE SUCCESS PROTECTION: If type is PAYMENT_RECOVERED or RECOVERY_COMPLETED,
        # verify case status is actually RECOVERED if case_id is provided!
        if type in ["PAYMENT_RECOVERED", "RECOVERY_COMPLETED"] and case_id:
            case = await db.get(RecoveryCase, case_id)
            if not case or case.status != "RECOVERED":
                logger.warning(f"BLOCKED false success notification '{type}' for unrecovered case '{case_id}'")
                type = "PAYMENT_VERIFICATION_PENDING"
                severity = "WARNING"
                title = "Payment Verification Pending"
                message = f"Payment recovery for case {case_id[:8]} is pending provider verification."

        # IDEMPOTENCY CHECK: Check if exact same case_id + type was created in last 5 minutes
        if case_id:
            recent_cut = datetime.now(timezone.utc) - timedelta(minutes=5)
            stmt = select(Notification).where(
                and_(
                    Notification.case_id == case_id,
                    Notification.type == type,
                    Notification.created_at >= recent_cut
                )
            )
            res = await db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                logger.info(f"Idempotent skip: Notification '{type}' already exists for case '{case_id}'")
                return existing

        notif = Notification(
            case_id=case_id,
            merchant_id=merchant_id,
            type=type,
            severity=severity,
            title=title,
            message=message,
            action_url=action_url or (f"/cases?id={case_id}" if case_id else "/cases"),
            metadata_json=metadata_json or {}
        )
        db.add(notif)
        
        try:
            # Audit log recording
            audit = AuditLog(
                case_id=case_id,
                event_type=f"NOTIFICATION_{type}",
                actor="NOTIFICATION_SERVICE",
                description=f"Created {severity} notification: {title}",
                metadata_json={"type": type, "severity": severity}
            )
            db.add(audit)
            await db.commit()
            await db.refresh(notif)
        except Exception as e:
            logger.warning(f"Notification audit write warning: {e}")
            await db.commit()
            await db.refresh(notif)

        return notif

    async def list_notifications(
        self,
        db: AsyncSession,
        unread_only: bool = False,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[NotificationSchema]:
        query = select(Notification)
        filters = []
        if unread_only:
            filters.append(Notification.is_read == False)
        if severity:
            filters.append(Notification.severity == severity.upper())

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Notification.created_at.desc()).limit(limit)
        res = await db.execute(query)
        items = res.scalars().all()

        # If zero notifications in DB, generate initial seed notifications based on live cases!
        if len(items) == 0 and not unread_only and not severity:
            await self.seed_initial_notifications(db)
            res = await db.execute(query)
            items = res.scalars().all()

        return [
            NotificationSchema(
                id=n.id,
                case_id=n.case_id,
                merchant_id=n.merchant_id,
                type=n.type,
                severity=n.severity,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                action_url=n.action_url,
                metadata_json=n.metadata_json,
                created_at=n.created_at
            )
            for n in items
        ]

    async def count_unread(self, db: AsyncSession) -> int:
        stmt = select(func.count(Notification.id)).where(Notification.is_read == False)
        res = await db.execute(stmt)
        return res.scalar() or 0

    async def mark_as_read(self, db: AsyncSession, notification_id: str) -> bool:
        stmt = update(Notification).where(Notification.id == notification_id).values(is_read=True)
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount > 0

    async def mark_all_as_read(self, db: AsyncSession) -> int:
        stmt = update(Notification).where(Notification.is_read == False).values(is_read=True)
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount or 0

    async def seed_initial_notifications(self, db: AsyncSession):
        stmt = select(RecoveryCase).limit(10)
        res = await db.execute(stmt)
        cases = res.scalars().all()

        for c in cases:
            if c.status == "RECOVERED":
                await self.create_notification(
                    db,
                    type="PAYMENT_RECOVERED",
                    severity="SUCCESS",
                    title="Payment Recovery Successful",
                    message=f"₹{c.recovered_amount or c.amount:.2f} payment recovered and verified with Razorpay for case {c.id[:8]}.",
                    case_id=c.id
                )
            elif c.status == "STOPPED":
                await self.create_notification(
                    db,
                    type="RECOVERY_STOPPED",
                    severity="WARNING",
                    title="Automated Recovery Halted",
                    message=f"Automated recovery for case {c.id[:8]} halted after reaching safety limit.",
                    case_id=c.id
                )
            elif c.status == "ESCALATED":
                await self.create_notification(
                    db,
                    type="HUMAN_REVIEW_REQUIRED",
                    severity="WARNING",
                    title="Human Review Required",
                    message=f"Case {c.id[:8]} escalated for operator review due to elevated risk score.",
                    case_id=c.id
                )
            else:
                await self.create_notification(
                    db,
                    type="PAYMENT_FAILED",
                    severity="INFO",
                    title="Payment Failure Diagnosed",
                    message=f"PayPilot AI diagnosed failure reason '{c.ai_root_cause or 'CARD_DECLINED'}' for case {c.id[:8]}.",
                    case_id=c.id
                )

notification_service = NotificationService()
