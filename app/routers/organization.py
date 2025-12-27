from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.organization import Organization
from app.schemas.organization import OrganizationRead, OrganizationUpdate, OrganizationCreate
from app.security import get_current_user

router = APIRouter()

@router.get("/", response_model=OrganizationRead)
def get_organization(db: Session = Depends(get_db)):
    org = db.query(Organization).first()
    if not org:
        # Auto-create if not exists
        org = Organization(name="Mi Empresa - Atlas ERP")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org

from app.models.users import Role

@router.put("/", response_model=OrganizationRead)
def update_organization(
    org_in: OrganizationUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    # Role check: Ensure comparison with Enum value or Uppercase string
    if current_user.role != Role.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    
    org = db.query(Organization).first()
    if not org:
        org = Organization(**org_in.dict())
        db.add(org)
    else:
        for key, value in org_in.dict(exclude_unset=True).items():
            setattr(org, key, value)
    
    db.commit()
    db.refresh(org)
    return org
