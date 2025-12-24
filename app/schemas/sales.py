from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime

# Replicamos el Enum de métodos de pago
class PaymentMethodSchema(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"

# --- Models for Creation ---

class SaleItemCreate(BaseModel):
    sku: str
    quantity: float = 1.0

class PaymentCreate(BaseModel):
    method: PaymentMethodSchema
    amount: Decimal
    reference: Optional[str] = None

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None 
    items: List[SaleItemCreate] 
    payments: List[PaymentCreate]

# --- Models for Reading (History) ---

class SaleLineRead(BaseModel):
    id: int
    variant_id: int
    description: str
    quantity: float
    unit_price: Decimal
    total_line: Decimal

    class Config:
        from_attributes = True

class PaymentRead(BaseModel):
    id: int
    amount: Decimal
    method: PaymentMethodSchema
    created_at: datetime

    class Config:
        from_attributes = True

class SaleRead(BaseModel):
    id: int
    doc_type: str
    status: str
    branch_id: int
    seller_id: int
    customer_id: Optional[int]
    
    series: Optional[str]
    folio: Optional[int]
    
    total_amount: Decimal
    created_at: datetime
    
    # We can include details if needed, but for list view usually lightweight is better.
    # We will include them for now for simplicity of the "View Details" modal
    lines: List[SaleLineRead] = []
    payments: List[PaymentRead] = []

    class Config:
        from_attributes = True