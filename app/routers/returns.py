from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.models import (
    SalesDocument, SalesLineItem, StockOnHand, 
    InventoryMovement, SaleReturn, SaleReturnItem, MovementType
)
from app.schemas.returns import ReturnCreate, ReturnRead
from app.security import get_current_user, User

router = APIRouter()

@router.post("/", response_model=ReturnRead)
def create_return(
    return_in: ReturnCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # 1. Verificar que la venta original existe
    sale = db.query(SalesDocument).get(return_in.sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Venta original no encontrada")

    total_refund = Decimal("0.00")
    
    # 2. Iniciar registro de devolución
    new_return = SaleReturn(
        sale_id=sale.id,
        user_id=current_user.id,
        branch_id=current_user.branch_id,
        reason=return_in.reason,
        total_refunded=0 # Se actualizará abajo
    )
    db.add(new_return)
    db.flush()

    for item in return_in.items:
        # Validar que el producto estaba en la venta original
        sale_line = db.query(SalesLineItem).filter(
            SalesLineItem.document_id == sale.id,
            SalesLineItem.variant_id == item.variant_id
        ).first()

        if not sale_line or sale_line.quantity < item.quantity:
            raise HTTPException(400, f"Cantidad inválida para el producto ID {item.variant_id}")

        # Calcular monto a devolver de este item
        item_refund = (sale_line.unit_price * item.quantity)
        total_refund += item_refund

        # 3. Reingresar Stock
        stock = db.query(StockOnHand).filter(
            StockOnHand.variant_id == item.variant_id,
            StockOnHand.branch_id == current_user.branch_id
        ).first()
        
        qty_before = stock.qty_on_hand
        stock.qty_on_hand += item.quantity

        # 4. Registrar en Kardex
        db.add(InventoryMovement(
            branch_id=current_user.branch_id,
            variant_id=item.variant_id,
            user_id=current_user.id,
            movement_type="RETURN_IN",
            qty_change=item.quantity,
            qty_before=qty_before,
            qty_after=stock.qty_on_hand,
            reference=f"Devolución de Venta #{sale.folio}",
            notes=return_in.reason
        ))

        # Registrar item de devolución
        db.add(SaleReturnItem(
            return_id=new_return.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            refund_amount=item_refund
        ))

    new_return.total_refunded = total_refund
    db.commit()
    db.refresh(new_return)
    return new_return