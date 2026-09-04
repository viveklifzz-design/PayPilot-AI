from pydantic import BaseModel, Field
from datetime import datetime

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    service: str = Field(..., json_schema_extra={"example": "PayPilot AI Revenue Recovery Engine"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    database: bool = True
    razorpay: bool = True
    ai: bool = True
    timestamp: datetime

class DatabaseHealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    database: str = Field(..., json_schema_extra={"example": "connected"})
    dialect: str
    timestamp: datetime

class RazorpayHealthResponse(BaseModel):
    configured: bool
    test_mode: bool
    webhook_configured: bool
    status: str
