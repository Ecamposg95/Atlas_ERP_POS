from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SalesDocument, User
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

    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    try:
        # Aquí podrías pasar un flag 'is_reprint=False' a tu clase PosPrinter
        success = printer.print_ticket(sale=sale, cashier_name=current_user.username)
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

    # Auditoría: Incrementar contador de reimpresiones si tienes el campo
    if hasattr(sale, 'reprint_count'):
        sale.reprint_count += 1
        db.commit()

    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    try:
        # Pasamos un parámetro extra para que el ticket diga "COPIA" o "REIMPRESIÓN"
        success = printer.print_ticket(
            sale=sale, 
            cashier_name=current_user.username,
            is_reprint=True 
        )
        if not success:
            raise HTTPException(status_code=500, detail="Fallo en hardware de impresión")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de reimpresión: {str(e)}")

    return {
        "status": "reprinted", 
        "folio": f"{sale.series}-{sale.folio}",
        "reprint_count": getattr(sale, 'reprint_count', 'N/A')
    }