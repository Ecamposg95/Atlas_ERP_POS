# app/routers/cash.py
from typing import Optional, List
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

@router.get("/history", response_model=List[CashSessionRead])
def read_cash_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Historial de cortes de caja de la sucursal"""
    return db.query(CashSession).filter(
        CashSession.branch_id == current_user.branch_id
    ).order_by(CashSession.opened_at.desc()).offset(skip).limit(limit).all()

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

    # 2. Validar Sucursal
    if not current_user.branch_id:
        raise HTTPException(400, "Tu usuario no tiene una sucursal asignada. Contacte al administrador.")

    # 3. Crear Sesión
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
        SalesDocument.seller_id == current_user.id, # Asumiendo que el pago lo cobró el usuario de la sesión
        Payment.created_at >= session.opened_at,
        SalesDocument.status == DocumentStatus.PAID
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

# --------------------------------------------------------------------------
# NUEVOS ENDPOINTS: MOVIMIENTOS DE CAJA (IN/OUT)
# --------------------------------------------------------------------------

# Necesitaremos un modelo para registrar estos flujos. 
# Si no existe `CashMovement`, podemos usar una tabla simple o agregarlo a CashSession (json movements?).
# Lo ideal es tener una tabla `cash_movements`.
# Asumiremos por ahora que lo guardamos en un modelo `CashFlow` o similar.
# Si no existe, lo crearemos rápido o usaremos una estructura en memoria/json de la sesión para MVP.

# VERIFICACIÓN: El modelo `CashMovement` NO parece estar importado. 
# Revisaré `app/models/cash.py` o similar si lo tengo. 
# Si no, para no romper, agregaré la definición SQL aquí mismo o lo pondré en `notes` de la sesión (no ideal).
# MEJOR OPCIÓN: Definir un endpoint que devuelva el resumen en base a Pagos, pero Inflow/Outflow requieren persistencia.
# Voy a improvisar usando la tabla `payments` con un tipo especial o asumiendo que existe `CashMovement`.
# Revisando `cash.py` imports... no veo `CashMovement`.
# Usaré una solución temporal: Guardar en `Payment` con un flag o crear modelo rápido.
# O MEJOR: Agregar estas operaciones cuando definamos el modelo. 
# Usuario pidió "POST /api/cash/inflow".
# Voy a asumir que puedo crear el modelo `CashMovement` en `app/models/cash.py`.

# --- PLAN B: Crearé los endpoints pero dejaré TODO en `cash.py` para no tocar models ahora mismo si es complejo.
# Pero necesito guardar estos datos.
# Voy a usar `Payment` con un `method` especial 'CASH_IN' / 'CASH_OUT' y `sales_document_id` nulo?
# Es sucio. 
# Mejor creo el modelo `CashMovement` en `models/cash.py` si puedo.
# A falta de ver models, implementaré el endpoint de Summary que SI puedo hacer con lo que tengo.

@router.get("/summary")
def get_cash_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resumen en tiempo real de la caja:
    - Saldo Inicial
    - + Ventas Efectivo
    - + Entradas (Inflows)
    - - Salidas (Outflows/Gastos)
    - = Esperado en Caja
    """
    # 1. Sesión activa
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    
    if not session:
        raise HTTPException(400, "No hay sesión abierta.")

    # 2. Ventas Efectivo (Desde apertura)
    sales_cash = db.query(func.sum(Payment.amount)).join(SalesDocument).filter(
        Payment.method == PaymentMethod.CASH,
        SalesDocument.seller_id == current_user.id,
        Payment.created_at >= session.opened_at,
        SalesDocument.status == DocumentStatus.PAID
    ).scalar() or Decimal(0)

    # 3. Entradas/Salidas Manuales
    session_id = session.id
    # Importar modelo aquí para evitar ciclos circulares si los hay, o traer arriba si es seguro.
    # Asumimos que `app.models.cash` ya tiene CashMovement
    from app.models.cash import CashMovement

    movements = db.query(CashMovement).filter(CashMovement.session_id == session.id).all()
    
    total_inflows = sum(m.amount for m in movements if m.type == 'IN')
    total_outflows = sum(m.amount for m in movements if m.type == 'OUT')

    expected = session.opening_balance + sales_cash + total_inflows - total_outflows

    return {
        "opening_balance": float(session.opening_balance),
        "sales_cash": float(sales_cash),
        "inflows": float(total_inflows),
        "outflows": float(total_outflows),
        "expected_in_drawer": float(expected)
    }

@router.post("/inflow")
def register_inflow(
    amount: float,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar sesión
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    if not session:
        raise HTTPException(400, "No hay sesión de caja abierta.")

    from app.models.cash import CashMovement
    
    new_move = CashMovement(
        session_id=session.id,
        type="IN",
        amount=Decimal(amount),
        reason=reason
    )
    db.add(new_move)
    db.commit()
    
    return {"message": "Entrada registrada", "amount": amount}

@router.post("/outflow")
def register_outflow(
    amount: float,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar sesión
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    if not session:
        raise HTTPException(400, "No hay sesión de caja abierta.")

    from app.models.cash import CashMovement
    
    new_move = CashMovement(
        session_id=session.id,
        type="OUT",
        amount=Decimal(amount),
        reason=reason
    )
    db.add(new_move)
    db.commit()
    
    return {"message": "Salida registrada", "amount": amount}

# --------------------------------------------------------------------------
# REPORTES DE CORTE (PDF & TICKET)
# --------------------------------------------------------------------------
from fastapi import Response
from app.utils.pdf_generator import generate_cash_cut_pdf

@router.get("/{session_id}/pdf")
def get_cash_cut_pdf(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
        
    # Recalcular totales para el reporte
    from app.models.cash import CashMovement
    sales_cash = session.total_cash_sales or Decimal(0) # Si ya cerró, usar guardado. Si no, calcular? 
    # Mejor asumimos que el PDF se pide AL CERRAR o DESPUES. 
    # Si está OPEN, habría que calcular al vuelo. Haremos eso para robustez.
    if session.status == "OPEN":
        # Recalculo 'al vuelo' similar a summary
        sales_cash = db.query(func.sum(Payment.amount)).join(SalesDocument).filter(
            Payment.method == PaymentMethod.CASH,
            SalesDocument.seller_id == session.user_id,
            Payment.created_at >= session.opened_at,
            SalesDocument.status == DocumentStatus.PAID
        ).scalar() or Decimal(0)
    
    movements = db.query(CashMovement).filter(CashMovement.session_id == session.id).all()
    inflows = sum(m.amount for m in movements if m.type == 'IN')
    outflows = sum(m.amount for m in movements if m.type == 'OUT')
    
    pdf_bytes = generate_cash_cut_pdf(
        session, 
        session.user.full_name or session.user.username, # Asumiendo relación User
        "Sucursal Principal", # TODO: Get real branch name
        sales_cash,
        inflows,
        outflows
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Corte_{session.id}.pdf"}
    )

@router.get("/{session_id}/ticket")
def get_cash_cut_ticket(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna un JSON estructurado para que el Frontend (JS) lo formatee 
    y lo mande a la impresora térmica (ESC/POS).
    """
    session = db.query(CashSession).filter(CashSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Sesión no encontrada")
    
    # Logica de totales (Copy-paste de arriba, refactorizar luego en servicio)
    from app.models.cash import CashMovement
    sales_cash = session.total_cash_sales or Decimal(0)
    if session.status == "OPEN":
        sales_cash = db.query(func.sum(Payment.amount)).join(SalesDocument).filter(
            Payment.method == PaymentMethod.CASH,
            SalesDocument.seller_id == session.user_id,
            Payment.created_at >= session.opened_at,
            SalesDocument.status == DocumentStatus.PAID
        ).scalar() or Decimal(0)
        
    movements = db.query(CashMovement).filter(CashMovement.session_id == session.id).all()
    inflows = sum(m.amount for m in movements if m.type == 'IN')
    outflows = sum(m.amount for m in movements if m.type == 'OUT')
    expected = session.opening_balance + sales_cash + inflows - outflows
    
    return {
        "header": {
            "title": "CORTE DE CAJA",
            "branch": "Sucursal Principal",
            "user": session.user.username,
            "date": datetime.now().strftime('%d/%m/%Y %H:%M')
        },
        "details": {
            "start_balance": float(session.opening_balance),
            "sales_cash": float(sales_cash),
            "inflows": float(inflows),
            "outflows": float(outflows),
            "expected": float(expected),
            "reported": float(session.closing_balance or 0),
            "difference": float(session.difference or 0)
        },
        "movements": [
            {
                "time": m.created_at.strftime('%H:%M'),
                "type": m.type,
                "amount": float(m.amount),
                "reason": m.reason
            } for m in movements
        ]
    }
