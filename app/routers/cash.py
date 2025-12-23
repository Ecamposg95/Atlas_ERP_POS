# app/routers/cash.py
from typing import Optional  # <--- IMPORTACIÓN AGREGADA
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from decimal import Decimal
from datetime import datetime
from app.database import get_db
from app.models import CashSession, CashSessionStatus, Payment, PaymentMethod, SalesDocument, DocumentStatus
from app.schemas.cash import CashSessionCreate, CashSessionRead, CashSessionClose
from app.security import get_current_user, User

router = APIRouter()

@router.get("/status", response_model=Optional[CashSessionRead])
def get_current_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Devuelve la sesión abierta actual del usuario, o null si no hay."""
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.branch_id == current_user.branch_id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    return session

@router.post("/open", response_model=CashSessionRead)
def open_session(
    session_in: CashSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validar que no tenga ya una abierta
    active = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    if active:
        raise HTTPException(400, "Ya tienes una sesión de caja abierta.")

    # 2. Crear Sesión
    new_session = CashSession(
        branch_id=current_user.branch_id,
        user_id=current_user.id,
        status=CashSessionStatus.OPEN,
        opening_balance=session_in.opening_balance,
        opened_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.post("/close", response_model=CashSessionRead)
def close_session(
    close_data: CashSessionClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscar sesión activa
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    
    if not session:
        raise HTTPException(400, "No hay sesión abierta para cerrar.")

    # 2. Calcular Ventas en Efectivo durante este turno (Sistema)
    # Buscamos pagos hechos entre opened_at y ahora, por este usuario
    sales_total = db.query(func.sum(Payment.amount)).join(SalesDocument).filter(
        Payment.method == PaymentMethod.CASH,
        SalesDocument.user_id == current_user.id, # Asumiendo que el pago lo cobró el usuario de la sesión
        Payment.created_at >= session.opened_at,
        SalesDocument.status == DocumentStatus.COMPLETED
    ).scalar() or Decimal(0)

    # 3. Calcular Diferencia (Real vs Esperado)
    # Esperado = Inicio + Ventas Efectivo
    expected = session.opening_balance + sales_total
    diff = close_data.closing_balance - expected

    # 4. Actualizar y Cerrar
    session.status = CashSessionStatus.CLOSED
    session.closed_at = datetime.utcnow()
    session.closing_balance = close_data.closing_balance
    session.total_cash_sales = sales_total
    session.difference = diff
    session.notes = close_data.notes

    db.commit()
    db.refresh(session)
    return session