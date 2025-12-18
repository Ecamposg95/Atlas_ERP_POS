from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.database import get_db
from app.schemas.crm import CustomerCreate, CustomerRead, CustomerPaymentCreate, PaymentResponse
from app.crud import crm as crud_crm
from app.security import get_current_user
from app.models import User, Customer, Payment, CustomerLedgerEntry # <--- Nuevos modelos

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

@router.post("/{customer_id}/payment", response_model=PaymentResponse)
def register_customer_payment(
    customer_id: int,
    payment_in: CustomerPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscar al cliente
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # 2. Validar montos lógicos
    if payment_in.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
    # (Opcional) ¿Permitir saldo a favor? 
    # Por ahora, advertimos si paga de más, pero lo permitimos (saldo negativo = a favor)
    
    # 3. Registrar el Pago Global
    new_payment = Payment(
        sales_document_id=None, # No está ligado a una venta específica, sino a la cuenta global
        customer_id=customer.id,
        amount=payment_in.amount,
        method=payment_in.method,
        reference=payment_in.reference,
        created_by_id=current_user.id
    )
    db.add(new_payment)
    
    # 4. Actualizar Saldo del Cliente (Resta deuda)
    customer.current_balance -= payment_in.amount
    
    # 5. Registrar en el Kardex Financiero (Ledger)
    ledger_entry = CustomerLedgerEntry(
        customer_id=customer.id,
        amount=-payment_in.amount, # Negativo porque disminuye la deuda
        description=f"Abono a cuenta ({payment_in.method})",
    )
    db.add(ledger_entry)
    
    db.commit()
    db.refresh(customer)
    
    return {
        "customer_id": customer.id,
        "amount_paid": payment_in.amount,
        "new_balance": customer.current_balance,
        "transaction_id": f"PAY-{new_payment.id}"
    }