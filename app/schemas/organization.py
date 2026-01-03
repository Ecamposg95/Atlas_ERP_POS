from pydantic import BaseModel, EmailStr
from typing import Optional

class OrganizationBase(BaseModel):
    name: str
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    ticket_header: Optional[str] = None
    ticket_footer: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    pass

class OrganizationRead(OrganizationBase):
    id: int

    class Config:
        from_attributes = True
