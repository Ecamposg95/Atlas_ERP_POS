from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SalesDocument, User, Payment, SalesLineItem
from app.models.cash import CashSession, CashMovement, CashSessionStatus
from app.models.sales import DocumentStatus, PaymentMethod
from sqlalchemy import func
from decimal import Decimal
from app.security import get_current_user
from app.pos_printer import PosPrinter

router = APIRouter()

class PrintRequest(BaseModel):
    order_id: int

@router.post("/print-ticket")
def print_ticket_endpoint(
    req: PrintRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Impresión original al momento de la venta."""
    sale = db.query(SalesDocument).filter(SalesDocument.id == req.order_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    # Fetch Organization for Ticket Config
    from app.models.organization import Organization
    organization = db.query(Organization).first()

    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    try:
        # Pass organization object
        success = printer.print_ticket(
            sale=sale, 
            cashier_name=current_user.username,
            organization=organization
        )
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo conectar con la impresora")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "printed", "printer": printer.printer_name}

@router.post("/reprint-ticket/{order_id}")
def reprint_ticket_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reimpresión de un ticket histórico."""
    sale = db.query(SalesDocument).filter(SalesDocument.id == order_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if hasattr(sale, 'reprint_count'):
        sale.reprint_count += 1
        db.commit()

    # Fetch Organization
    from app.models.organization import Organization
    organization = db.query(Organization).first()

    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    try:
        success = printer.print_ticket(
            sale=sale, 
            cashier_name=current_user.username,
            is_reprint=True,
            organization=organization
        )
        if not success:
            raise HTTPException(status_code=500, detail="Fallo en hardware de impresión")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de reimpresión: {str(e)}")

    return {
        "folio": f"{sale.series}-{sale.folio}",
        "reprint_count": getattr(sale, 'reprint_count', 'N/A')
    }

class PrintCashCutRequest(BaseModel):
    session_id: int

@router.post("/print-cash-cut")
def print_cash_cut_endpoint(
    req: PrintCashCutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(CashSession).filter(CashSession.id == req.session_id).first()
    if not session:
        raise HTTPException(404, "Sesión no encontrada")

    # Recalcular totales para impresión
    sales_cash = db.query(func.sum(Payment.amount)).join(SalesDocument).filter(
        Payment.method == PaymentMethod.CASH,
        SalesDocument.seller_id == session.user_id, 
        Payment.created_at >= session.opened_at,
        Payment.created_at <= (session.closed_at or datetime.now()),
        SalesDocument.status == DocumentStatus.PAID
    ).scalar() or Decimal(0)

    inflows = db.query(func.sum(CashMovement.amount)).filter(
        CashMovement.session_id == session.id,
        CashMovement.type == 'IN'
    ).scalar() or Decimal(0)

    outflows = db.query(func.sum(CashMovement.amount)).filter(
        CashMovement.session_id == session.id,
        CashMovement.type == 'OUT'
    ).scalar() or Decimal(0)

    # Identificar nombre de usuario y sucursal
    cashier_name = session.user.username if session.user else "Desconocido"
    branch_name = "Sucursal Principal" # Placeholder o tomar de session.user.branch

    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    try:
        success = printer.print_cash_cut(
            session=session,
            cashier_name=cashier_name,
            branch_name=branch_name,
            sales_cash=sales_cash,
            inflows=inflows,
            outflows=outflows
        )
        if not success:
            raise HTTPException(500, "Error de hardware al imprimir corte")
    except Exception as e:
        raise HTTPException(500, f"Error impresión: {str(e)}")

    return {"status": "printed", "session_id": session.id}