# app/routers/customers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from decimal import Decimal

from app.database import get_db
from app.models import Customer, CustomerLedgerEntry
from app.schemas.customers import CustomerCreate, CustomerRead, CustomerUpdate, LedgerEntryResponse
from app.security import get_current_user, User

router = APIRouter()

# --------------------------------------------------------------------------
# 1. LISTAR CLIENTES
# --------------------------------------------------------------------------
@router.get("/", response_model=List[CustomerRead])
def get_customers(
    skip: int = 0, 
    limit: int = 100, 
    search: str = None, # Opción para buscar por nombre/RFC
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = db.query(Customer).filter(Customer.is_active == True)
    
    if search:
        # Búsqueda insensible a mayúsculas
        search_fmt = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(search_fmt)) | 
            (Customer.tax_id.ilike(search_fmt))
        )
        
    return query.order_by(Customer.name).offset(skip).limit(limit).all()

# --------------------------------------------------------------------------
# 2. OBTENER DETALLE (INDIVIDUAL)
# --------------------------------------------------------------------------
@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return customer

# --------------------------------------------------------------------------
# 3. CREAR CLIENTE
# --------------------------------------------------------------------------
@router.post("/", response_model=CustomerRead)
def create_customer(
    customer_in: CustomerCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validar RFC único (si no es nulo y no es el genérico XAXX010101000)
    if customer_in.tax_id and len(customer_in.tax_id) > 10: 
        exists = db.query(Customer).filter(
            Customer.tax_id == customer_in.tax_id, 
            Customer.tax_id != "XAXX010101000" # Excepción para Público General
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail=f"El RFC {customer_in.tax_id} ya está registrado.")

    new_customer = Customer(
        name=customer_in.name,
        tax_id=customer_in.tax_id,
        tax_system=customer_in.tax_system,
        email=customer_in.email,
        phone=customer_in.phone,
        address=customer_in.address,
        zip_code=customer_in.zip_code,
        has_credit=customer_in.has_credit,
        credit_limit=customer_in.credit_limit,
        credit_days=customer_in.credit_days,
        notes=customer_in.notes,
        current_balance=0 # Empieza en cero
    )
    
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

# --------------------------------------------------------------------------
# 4. ACTUALIZAR CLIENTE (PUT)
# --------------------------------------------------------------------------
@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int, 
    customer_in: CustomerUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Actualizamos campos dinámicamente
    update_data = customer_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(customer, field):
            setattr(customer, field, value)
            
    db.commit()
    db.refresh(customer)
    return customer

# --------------------------------------------------------------------------
# 5. ELIMINAR (SOFT DELETE)
# --------------------------------------------------------------------------
@router.delete("/{customer_id}", response_model=CustomerRead)
def delete_customer(
    customer_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # No eliminar si tiene deuda
    if customer.current_balance > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar. El cliente tiene una deuda pendiente de ${customer.current_balance}"
        )

    customer.is_active = False # Soft Delete
    db.commit()
    return customer

# --------------------------------------------------------------------------
# 6. ESTADO DE CUENTA (MOVIMIENTOS)
# --------------------------------------------------------------------------
@router.get("/{customer_id}/statement", response_model=List[LedgerEntryResponse])
def get_customer_statement(
    customer_id: int, 
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el historial de cargos y abonos del cliente.
    """
    # Verificar que el cliente exista
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # Consultar Ledger (Tabla customer_ledger_entries)
    # Asumiendo que definiste CustomerLedgerEntry en models/crm.py o models/customers.py
    entries = db.query(CustomerLedgerEntry)\
        .filter(CustomerLedgerEntry.customer_id == customer_id)\
        .order_by(desc(CustomerLedgerEntry.created_at))\
        .limit(limit)\
        .all()
        
    return entries

@router.post("/{customer_id}/pay", response_model=LedgerEntryResponse)
def register_customer_payment(
    customer_id: int,
    amount: Decimal,
    reference: str = "Abono a cuenta",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra un abono/pago de un cliente y actualiza su saldo.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")

    if amount <= 0:
        raise HTTPException(400, "El monto del pago debe ser mayor a cero")

    # 1. Actualizar saldo (restar el abono)
    customer.current_balance -= amount

    # 2. Registrar en el Ledger (Kardex de dinero)
    new_entry = CustomerLedgerEntry(
        customer_id=customer.id,
        amount=-amount,  # Negativo porque reduce la deuda
        description=f"PAGO RECIBIDO: {reference}",
        # created_by=current_user.id  <-- Opcional para auditoría
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

from fastapi import Response
from app.utils.pdf_generator import generate_account_statement_pdf

@router.get("/{customer_id}/pdf-statement")
def get_customer_statement_pdf(
    customer_id: int, 
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Cliente no encontrado")
        
    entries = db.query(CustomerLedgerEntry)\
        .filter(CustomerLedgerEntry.customer_id == customer_id)\
        .order_by(desc(CustomerLedgerEntry.created_at))\
        .limit(100)\
        .all()
        
    pdf_content = generate_account_statement_pdf(customer, entries)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=EdoCuenta_{customer.tax_id or 'Cliente'}.pdf"}
    )