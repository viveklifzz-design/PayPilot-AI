from fastapi import APIRouter
from app.api.v1.endpoints import health, payments, webhooks, cases, recovery, evaluation, analytics, audit, revenue_risk, customer_portal, receivables, mandates, communication, notifications, subscriptions, voice

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(payments.router)
api_router.include_router(webhooks.router)
api_router.include_router(cases.router)
api_router.include_router(recovery.router)
api_router.include_router(evaluation.router)
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
api_router.include_router(revenue_risk.router)
api_router.include_router(customer_portal.router)
api_router.include_router(receivables.router)
api_router.include_router(mandates.router)
api_router.include_router(communication.router)
api_router.include_router(notifications.router)
api_router.include_router(subscriptions.router)
api_router.include_router(voice.router)


