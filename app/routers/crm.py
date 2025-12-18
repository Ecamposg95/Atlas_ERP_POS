from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.crm import CustomerCreate, CustomerRead
from app.crud import crm as crud_crm
from app.security import get_current_user
from app.models import User

router = APIRouter()

@router.post("/", response_model=CustomerRead)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar RFC duplicado (solo si se proporciona uno)
    if customer.tax_id:
        existing = crud_crm.get_customer_by_tax_id(db, tax_id=customer.tax_id)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un cliente con este RFC.")
            
    return crud_crm.create_customer(db=db, customer=customer)

@router.get("/", response_model=List[CustomerRead])
def read_customers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud_crm.get_customers(db, skip=skip, limit=limit)