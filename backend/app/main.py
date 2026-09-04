from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import (
    PayPilotException,
    paypilot_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.db.init_db import init_db
from app.db.session import get_db
from app.api.v1.router import api_router
from app.schemas.health import HealthResponse, DatabaseHealthResponse

# Initialize structured logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} backend in {settings.ENVIRONMENT} mode...")
    try:
        await init_db()
        logger.info("Database tables initialized successfully on startup.")
    except Exception as e:
        logger.warning(f"Database auto-initialization skipped or failed: {e}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Revenue Recovery Agent Backend for Razorpay AI Buildathon",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(PayPilotException, paypilot_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health endpoints at root and under /api/v1
@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", response_model=HealthResponse, tags=["Health"])
async def root_health():
    rzp_ok = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    ai_ok = bool(settings.GEMINI_API_KEY or settings.GEMINI_MODEL)
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version="1.0.0",
        database=True,
        razorpay=rzp_ok,
        ai=ai_ok,
        timestamp=datetime.now(timezone.utc)
    )

@app.get("/health/db", response_model=DatabaseHealthResponse, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health/db", response_model=DatabaseHealthResponse, tags=["Health"])
async def root_db_health(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        val = result.scalar()
        if val != 1:
            raise Exception("Database returned invalid scalar")
        
        dialect_name = db.bind.dialect.name if db.bind else "unknown"
        return DatabaseHealthResponse(
            status="healthy",
            database="connected",
            dialect=dialect_name,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Root DB Health Check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}"
        )
