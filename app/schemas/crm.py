from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

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
    
    # Opcional: Podríamos incluir saldo actual aquí en el futuro
    
    class Config:
        from_attributes = True