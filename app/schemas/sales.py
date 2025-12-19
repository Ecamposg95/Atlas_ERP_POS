from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from decimal import Decimal

# Replicamos el Enum de métodos de pago
class PaymentMethodSchema(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"

class SaleItemCreate(BaseModel):
    sku: str
    quantity: float = 1.0

class PaymentCreate(BaseModel):
    method: PaymentMethodSchema
    amount: Decimal
    reference: Optional[str] = None  # <--- ¡AQUÍ ESTÁ LA CORRECCIÓN!

class SaleCreate(BaseModel):
    # Si es null, es "Cliente Público"
    customer_id: Optional[int] = None 
    
    # CORREGIDO: Debe coincidir con el nombre de la clase de arriba
    items: List[SaleItemCreate] 
    payments: List[PaymentCreate]