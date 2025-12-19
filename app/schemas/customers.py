from pydantic import BaseModel, EmailStr
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# --- CLASES BASE ---

class CustomerBase(BaseModel):
    name: str
    tax_id: Optional[str] = None       # RFC / RUT / NIT
    tax_system: Optional[str] = None   # Régimen Fiscal (Ej. "601 - General")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None     # Código Postal (Vital para facturar)
    
    # Configuración de Crédito
    has_credit: bool = False
    credit_limit: Decimal = Decimal("0.00")
    credit_days: int = 0               # Días de crédito (Ej. 15, 30)
    
    is_active: bool = True
    notes: Optional[str] = None

# --- CREACIÓN ---
class CustomerCreate(CustomerBase):
    pass

# --- ACTUALIZACIÓN ---
class CustomerUpdate(CustomerBase):
    name: Optional[str] = None
    # Permitimos editar todo de forma opcional
    has_credit: Optional[bool] = None
    credit_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None

# --- ESTADO DE CUENTA (Movimientos) ---
class LedgerEntryResponse(BaseModel):
    id: int
    date: datetime
    amount: Decimal          # Positivo = Cargo (Deuda), Negativo = Abono (Pago)
    description: str
    reference_id: Optional[str] = None # ID Venta o Folio Pago
    
    class Config:
        from_attributes = True

# --- LECTURA (RESPONSE) ---
class CustomerRead(CustomerBase):
    id: int
    current_balance: Decimal = Decimal("0.00") # Saldo actual calculado
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True