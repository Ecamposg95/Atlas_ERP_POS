# app/schemas/returns.py

from pydantic import BaseModel
from typing import List
from decimal import Decimal
from datetime import datetime

class ReturnItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal

class ReturnCreate(BaseModel):
    sale_id: int
    reason: str
    items: List[ReturnItemCreate]

class ReturnRead(BaseModel):
    id: int
    sale_id: int
    total_refunded: Decimal
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True