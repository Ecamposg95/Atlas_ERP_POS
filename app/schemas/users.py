from typing import Optional
from pydantic import BaseModel
from app.models.users import Role

# Base común
class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: Role = Role.CAJERO
    is_active: bool = True

# Para crear usuarios (necesita password/PIN)
class UserCreate(UserBase):
    password: str

# Para leer usuarios (devuelve ID, pero NO el password)
class UserRead(UserBase):
    id: int
    branch_id: Optional[int] = None
    
    class Config:
        from_attributes = True

# Esquemas para el Token JWT
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None