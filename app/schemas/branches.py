from pydantic import BaseModel
from typing import Optional

class BranchBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BranchBase):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

# CAMBIO: Renombrado de BranchResponse a BranchRead para coincidir con el Router
class BranchRead(BranchBase):
    id: int

    class Config:
        from_attributes = True