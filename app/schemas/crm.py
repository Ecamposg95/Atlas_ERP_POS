from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal

# --- Parte 1: Clientes ---

class CustomerBase(BaseModel):
    name: str
    tax_id: Optional[str] = None # RFC
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    # Configuración de Crédito
    has_credit: bool = False
    credit_limit: float = 0.0
    credit_days: int = 0

class CustomerCreate(CustomerBase):
    pass

class CustomerRead(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime
    
    # Campo calculado para mostrar saldo actual al leer el cliente
    current_balance: Decimal = Decimal("0.00")
    
    class Config:
        from_attributes = True

# --- Parte 2: Pagos y Abonos ---

class PaymentMethodSchema(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"

class CustomerPaymentCreate(BaseModel):
    amount: Decimal
    method: PaymentMethodSchema
    reference: Optional[str] = None # Para folios de transferencia
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    customer_id: int
    amount_paid: Decimal
    new_balance: Decimal
    transaction_id: str