from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.audit_log import AuditLog
from app.services.policy import policy_engine
from app.services.recovery.razorpay_recovery import razorpay_link_executor
from app.services.recovery.retry_service import retry_action_executor
from app.services.recovery.notification_service import reminder_action_executor
from app.core.logging import logger

class RecoveryActionExecutorService:
    """
    Main Recovery Action Execution Engine.
    Guarantees Policy Engine safety validation and idempotency protection before executing any financial action.
    """

    async def execute_recovery(
        self,
        case: RecoveryCase,
        db: AsyncSession,
        proposed_action: Optional[str] = None,
        ai_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        
        # 1. Idempotency Check: Already Recovered
        if case.status == "RECOVERED":
            logger.info(f"Execution rejected for case '{case.id}': Case is already RECOVERED.")
            return {
                "allowed": False,
                "case_id": case.id,
                "action_id": None,
                "requested_action": proposed_action or case.ai_recommended_action or "RECOVERY_LINK",
                "effective_action": "NONE",
                "policy_allowed": False,
                "execution_status": "BLOCKED",
                "status": "BLOCKED",
                "amount": float(case.amount),
                "recovered_amount": float(case.recovered_amount),
                "payment_url": None,
                "payment_link_url": None,
                "provider_reference": None,
                "message": "Recovery case is already RECOVERED. Execution prevented."
            }

        target_action = (proposed_action or case.ai_recommended_action or "RECOVERY_LINK").upper()
        confidence = ai_confidence if ai_confidence is not None else (float(case.ai_confidence) if case.ai_confidence else 0.85)

        # Audit event: RECOVERY_EXECUTION_STARTED
        db.add(AuditLog(
            case_id=case.id,
            actor="RECOVERY_EXECUTOR",
            event_type="RECOVERY_EXECUTION_STARTED",
            description=f"Initiating recovery execution for action '{target_action}'",
            metadata_json={"requested_action": target_action, "confidence": confidence, "amount": float(case.amount)}
        ))

        try:
            # 2. Idempotency Check: Check if active recovery link or action already exists
            existing_action_res = await db.execute(
                select(RecoveryAction)
                .where(RecoveryAction.case_id == case.id)
                .where(RecoveryAction.action_type == target_action)
                .where(RecoveryAction.status.in_(["CREATED", "SUCCEEDED", "COMPLETED", "EXECUTING", "PENDING"]))
                .order_by(RecoveryAction.executed_at.desc())
            )
            existing_action = existing_action_res.scalars().first()

            if existing_action:
                logger.info(f"Duplicate recovery execution detected for case '{case.id}' ({target_action}). Returning existing action result.")
                payload = existing_action.payload or {}
                payment_url = existing_action.short_url or payload.get("payment_link_url")
                provider_ref = existing_action.razorpay_payment_link_id or payload.get("provider_reference")
                return {
                    "allowed": True,
                    "case_id": case.id,
                    "action_id": existing_action.id,
                    "requested_action": target_action,
                    "effective_action": target_action,
                    "action": target_action,
                    "policy_allowed": True,
                    "execution_status": existing_action.status,
                    "status": existing_action.status,
                    "provider": "RAZORPAY",
                    "provider_reference": provider_ref,
                    "payment_url": payment_url,
                    "payment_link_url": payment_url,
                    "amount": float(case.amount),
                    "currency": "INR",
                    "recovered_amount": float(case.recovered_amount),
                    "message": "Duplicate recovery action execution prevented. Returned existing action result."
                }

            # Fetch last action timestamp for Policy Engine
            last_act_res = await db.execute(
                select(RecoveryAction)
                .where(RecoveryAction.case_id == case.id)
                .order_by(RecoveryAction.executed_at.desc())
                .limit(1)
            )
            last_act = last_act_res.scalar_one_or_none()
            last_action_ts = last_act.executed_at if last_act else None

            txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
            txn = txn_res.scalar_one_or_none()
        except Exception as db_err:
            logger.error(f"Database query error during recovery execution for case '{case.id}': {db_err}")
            return {
                "allowed": False,
                "case_id": case.id,
                "action_id": None,
                "requested_action": target_action,
                "effective_action": "NONE",
                "policy_allowed": False,
                "execution_status": "FAILED",
                "status": "FAILED",
                "amount": float(case.amount),
                "recovered_amount": float(case.recovered_amount),
                "payment_url": None,
                "payment_link_url": None,
                "provider_reference": None,
                "message": f"Database operation failed safely: {db_err}"
            }

        # 3. Policy Safety Gate Validation (Mandatory Step)
        policy_result = policy_engine.evaluate_action(
            proposed_action=target_action,
            case_status=case.status,
            amount=float(case.amount),
            retry_count=case.retry_count,
            ai_confidence=confidence,
            last_action_timestamp=last_action_ts,
            error_code=txn.error_code if txn else None
        )

        effective_action = policy_result.effective_action

        # 4. Handle Policy Rejection / Override
        if not policy_result.allowed:
            logger.warning(f"Policy Gate BLOCKED recovery execution for case '{case.id}': violations={policy_result.violations}")
            
            blocked_action = RecoveryAction(
                case_id=case.id,
                action_type=target_action,
                status="BLOCKED",
                payload={
                    "violations": policy_result.violations,
                    "reason": policy_result.reason,
                    "effective_action": effective_action
                }
            )
            db.add(blocked_action)

            case.policy_passed = False
            case.policy_failure_reason = policy_result.reason
            if effective_action == "ESCALATE":
                case.status = "ESCALATED"
            elif effective_action == "STOP":
                case.status = "STOPPED"
                case.stop_reason = policy_result.reason
            db.add(case)

            db.add(AuditLog(
                case_id=case.id,
                actor="POLICY_ENGINE",
                event_type="RECOVERY_POLICY_BLOCKED",
                description=f"Blocked proposed action '{target_action}': {policy_result.reason}",
                metadata_json={"violations": policy_result.violations, "effective_action": effective_action}
            ))
            await db.commit()

            return {
                "allowed": False,
                "case_id": case.id,
                "action_id": blocked_action.id,
                "requested_action": target_action,
                "effective_action": effective_action,
                "action": target_action,
                "policy_allowed": False,
                "execution_status": "BLOCKED",
                "status": "BLOCKED",
                "amount": float(case.amount),
                "currency": "INR",
                "recovered_amount": float(case.recovered_amount),
                "payment_url": None,
                "payment_link_url": None,
                "provider_reference": None,
                "message": f"Policy Safety Gate blocked action: {policy_result.reason}"
            }

        # 5. Execute Approved Recovery Action
        logger.info(f"Executing Policy-Approved Action '{effective_action}' for case '{case.id}'")
        
        cust_name = None
        cust_email = None
        if case.customer_id:
            c_res = await db.execute(select(Customer).where(Customer.id == case.customer_id))
            cust = c_res.scalar_one_or_none()
            if cust:
                cust_name = cust.name
                cust_email = cust.email

        exec_context = {
            "customer_name": cust_name,
            "customer_email": cust_email
        }

        try:
            if effective_action == "RECOVERY_LINK":
                exec_result = razorpay_link_executor.execute_action(case, exec_context)
            elif effective_action == "RETRY":
                exec_result = retry_action_executor.execute_action(case, exec_context)
            elif effective_action == "REMINDER":
                exec_result = reminder_action_executor.execute_action(case, exec_context)
            elif effective_action == "ESCALATE":
                exec_result = {"status": "SUCCEEDED", "message": "Case escalated to human merchant review."}
            elif effective_action == "STOP":
                exec_result = {"status": "SUCCEEDED", "message": "Recovery stopped safely."}
            else:
                exec_result = {"status": "SUCCEEDED", "message": f"Action '{effective_action}' completed."}
        except Exception as e:
            logger.error(f"Execution failed for action '{effective_action}' on case '{case.id}': {e}")
            failed_action = RecoveryAction(
                case_id=case.id,
                action_type=effective_action,
                status="FAILED",
                payload={"error": str(e)}
            )
            db.add(failed_action)
            case.status = "FAILED"
            db.add(case)

            db.add(AuditLog(
                case_id=case.id,
                actor="RECOVERY_EXECUTOR",
                event_type="RECOVERY_EXECUTION_FAILED",
                description=f"Recovery execution for action '{effective_action}' failed: {e}",
                metadata_json={"error": str(e), "action": effective_action}
            ))
            await db.commit()

            return {
                "allowed": True,
                "case_id": case.id,
                "action_id": failed_action.id,
                "requested_action": target_action,
                "effective_action": effective_action,
                "action": effective_action,
                "policy_allowed": True,
                "execution_status": "FAILED",
                "status": "FAILED",
                "amount": float(case.amount),
                "currency": "INR",
                "recovered_amount": float(case.recovered_amount),
                "payment_url": None,
                "payment_link_url": None,
                "provider_reference": None,
                "message": f"Recovery action execution failed: {e}"
            }

        # 6. Persist Successful Recovery Action State
        final_action_status = "CREATED" if effective_action == "RECOVERY_LINK" else "SUCCEEDED"
        provider_ref = exec_result.get("provider_reference") if isinstance(exec_result, dict) else None
        payment_url = exec_result.get("payment_link_url") if isinstance(exec_result, dict) else None

        action_record = RecoveryAction(
            case_id=case.id,
            action_type=effective_action,
            status=final_action_status,
            razorpay_payment_link_id=provider_ref,
            short_url=payment_url,
            payload=exec_result
        )
        db.add(action_record)

        if effective_action in {"RETRY", "RECOVERY_LINK", "REMINDER"}:
            case.retry_count += 1
            case.status = "RECOVERING"
            case.actual_action_taken = effective_action
        elif effective_action == "ESCALATE":
            case.status = "ESCALATED"
        elif effective_action == "STOP":
            case.status = "STOPPED"
            case.stop_reason = "Stopped by policy or diagnosis."

        case.policy_passed = True
        db.add(case)

        # Audit Event for Link Creation / Action Success
        event_type = "RECOVERY_PAYMENT_LINK_CREATED" if effective_action == "RECOVERY_LINK" else "RECOVERY_ACTION_SUCCEEDED"
        db.add(AuditLog(
            case_id=case.id,
            actor="RECOVERY_EXECUTOR",
            event_type=event_type,
            description=f"Recovery action '{effective_action}' executed ({final_action_status}). Provider Ref: '{provider_ref}'",
            metadata_json={
                "provider": "RAZORPAY",
                "provider_reference": provider_ref,
                "payment_url": payment_url,
                "amount": int(round(float(case.amount) * 100.0)),
                "currency": "INR",
                "action_id": action_record.id,
                "effective_action": effective_action
            }
        ))
        await db.commit()

        # Dispatch WhatsApp notification if payment link and customer phone are present
        cust_phone = getattr(cust, "phone", None) if 'cust' in locals() and cust else None
        if effective_action == "RECOVERY_LINK" and payment_url and cust_phone:
            try:
                from app.services.whatsapp_service import whatsapp_service
                await whatsapp_service.send_payment_link_message(
                    to_phone=cust_phone,
                    customer_name=cust_name or "Valued Customer",
                    invoice_number=f"INV-{case.id[:8]}",
                    amount=float(case.amount),
                    payment_url=payment_url
                )
            except Exception as wa_err:
                logger.warning(f"WhatsApp notification dispatch warning for case '{case.id}': {wa_err}")

        return {
            "allowed": True,
            "case_id": case.id,
            "action_id": action_record.id,
            "requested_action": target_action,
            "effective_action": effective_action,
            "action": effective_action,
            "status": final_action_status,
            "execution_status": final_action_status,
            "provider": "RAZORPAY",
            "provider_reference": provider_ref,
            "payment_url": payment_url,
            "payment_link_url": payment_url,
            "amount": float(case.amount),
            "currency": "INR",
            "recovered_amount": float(case.recovered_amount),
            "message": exec_result.get("message") or f"Recovery payment link created successfully."
        }

recovery_executor = RecoveryActionExecutorService()
