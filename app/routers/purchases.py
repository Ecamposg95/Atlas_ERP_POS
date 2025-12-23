from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.models import ProductVariant, StockOnHand, InventoryMovement, MovementType
from app.security import get_current_user, User

router = APIRouter()

@router.post("/receive")
def receive_inventory(
    variant_id: int, 
    quantity: Decimal, 
    cost: Decimal, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Registra la entrada de mercancía y actualiza el costo promedio."""
    # 1. Buscar o crear registro de stock en la sucursal del usuario
    stock = db.query(StockOnHand).filter(
        StockOnHand.variant_id == variant_id,
        StockOnHand.branch_id == current_user.branch_id
    ).first()

    if not stock:
        stock = StockOnHand(variant_id=variant_id, branch_id=current_user.branch_id, qty_on_hand=0)
        db.add(stock)

    # 2. Actualizar costo en la variante (Importante para reportes de utilidad)
    variant = db.query(ProductVariant).get(variant_id)
    variant.cost = cost 

    # 3. Aumentar Stock y registrar movimiento
    qty_before = stock.qty_on_hand
    stock.qty_on_hand += quantity

    movement = InventoryMovement(
        branch_id=current_user.branch_id,
        variant_id=variant_id,
        user_id=current_user.id,
        movement_type="PURCHASE",
        qty_change=quantity,
        qty_before=qty_before,
        qty_after=stock.qty_on_hand,
        reference="Compra de Proveedor"
    )
    
    db.add(movement)
    db.commit()
    return {"status": "success", "new_stock": float(stock.qty_on_hand)}