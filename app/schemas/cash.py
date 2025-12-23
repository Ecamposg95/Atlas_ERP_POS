
# schemas/cash.py
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class CashSessionBase(BaseModel):
    opening_balance: Decimal

class CashSessionCreate(CashSessionBase):
    pass # Solo necesitamos el saldo inicial

class CashSessionClose(BaseModel):
    closing_balance: Decimal # Lo que el cajero contó físicamente
    notes: Optional[str] = None

class CashSessionRead(CashSessionBase):
    id: int
    branch_id: int
    user_id: int
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    
    # Datos de cierre
    closing_balance: Optional[Decimal] = None
    total_cash_sales: Decimal = Decimal(0) # Ventas en efectivo calculadas
    difference: Decimal = Decimal(0)       # Sobrante o Faltante

    class Config:
        from_attributes = True