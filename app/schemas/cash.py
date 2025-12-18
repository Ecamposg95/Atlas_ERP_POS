from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum

class CashSessionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

# Para abrir caja
class SessionOpen(BaseModel):
    opening_balance: Decimal # Fondo de caja (ej. $500 pesos en monedas)

# Para cerrar caja
class SessionClose(BaseModel):
    closing_balance: Decimal # Lo que el cajero contó físicamente
    notes: Optional[str] = None

# Reporte del Corte
class SessionRead(BaseModel):
    id: int
    user_id: int
    status: CashSessionStatus
    opened_at: datetime
    closed_at: Optional[datetime]
    
    opening_balance: Decimal
    
    # Calculados por el sistema
    total_cash_sales: Decimal = Decimal(0)      # Ventas contado
    total_cash_payments: Decimal = Decimal(0)   # Abonos recibidos
    expected_balance: Decimal = Decimal(0)      # Cuánto DEBERÍA haber
    
    closing_balance: Optional[Decimal]          # Lo que contó el cajero
    difference: Optional[Decimal]               # Sobrante/Faltante (si cerró)

    class Config:
        from_attributes = True