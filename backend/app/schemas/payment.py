from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class OrderCreate(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    amount: float = Field(..., gt=0, description="Amount in INR or base currency unit")
    currency: str = Field("INR", description="Currency code")
    receipt: Optional[str] = None
    notes: Optional[Dict[str, Any]] = None

class OrderResponse(BaseModel):
    id: str
    merchant_id: str
    customer_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WebhookResponse(BaseModel):
    status: str
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    message: Optional[str] = None
