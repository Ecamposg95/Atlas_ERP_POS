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
    # 1. Buscar la venta
    sale = db.query(SalesDocument).filter(SalesDocument.id == req.order_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    # 2. Instanciar Impresora
    # IMPORTANTE: Cambia "POS-80" por el nombre de tu impresora
    printer = PosPrinter(printer_name="POS-80", paper_width_mm=80)
    
    # 3. Mandar a imprimir
    try:
        success = printer.print_ticket(sale=sale, cashier_name=current_user.username)
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo conectar con la impresora")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "printed", "printer": printer.printer_name}