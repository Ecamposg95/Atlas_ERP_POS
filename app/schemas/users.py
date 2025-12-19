from pydantic import BaseModel, EmailStr
from typing import Optional

# --- DEFINICIÓN DE CLASES (Sin self-imports) ---

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str = "seller" # O usa tu Enum si lo tienes definido
    branch_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    # branch_id ya se hereda de UserBase, así que ya puedes asignarlo al crear

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserRead(UserBase):
    id: int
    
    class Config:
        from_attributes = True