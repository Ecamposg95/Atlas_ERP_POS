from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ProductVariant, StockOnHand, InventoryMovement, User, Branch
from app.schemas.inventory import InventoryAdjustmentCreate, InventoryResponse
from app.security import get_current_user

router = APIRouter()

@router.post("/adjust", response_model=InventoryResponse)
def adjust_inventory(
    adjustment: InventoryAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Buscar la variante por SKU
    variant = db.query(ProductVariant).filter(ProductVariant.sku == adjustment.sku).first()
    if not variant:
        raise HTTPException(status_code=404, detail="SKU no encontrado")

    # 2. Buscar (o crear) el registro de Stock para la sucursal del usuario
    stock_record = db.query(StockOnHand).filter(
        StockOnHand.variant_id == variant.id,
        StockOnHand.branch_id == current_user.branch_id
    ).first()

    if not stock_record:
        # Si es la primera vez que esta sucursal toca este producto
        stock_record = StockOnHand(
            branch_id=current_user.branch_id,
            variant_id=variant.id,
            qty_on_hand=0.0
        )
        db.add(stock_record)
    
    # Snapshot del stock antes del movimiento
    qty_before = stock_record.qty_on_hand

    # 3. Calcular cambio (Signo)
    # Si es salida (ADJUSTMENT_OUT), convertimos a negativo
    qty_change = adjustment.quantity
    if adjustment.movement_type == "ADJUSTMENT_OUT":
        qty_change = -abs(qty_change)
    else:
        qty_change = abs(qty_change)

    # 4. Crear el Movimiento en el Kardex (Histórico)
    movement = InventoryMovement(
        branch_id=current_user.branch_id,
        variant_id=variant.id,
        user_id=current_user.id,
        movement_type=adjustment.movement_type,
        qty_change=qty_change,
        qty_before=qty_before,
        qty_after=qty_before + qty_change,
        reference="Ajuste Manual",
        notes=adjustment.notes
    )
    db.add(movement)

    # 5. Actualizar el Stock Actual (Caché)
    stock_record.qty_on_hand += qty_change

    db.commit()
    
    return {
        "sku": variant.sku,
        "new_stock": stock_record.qty_on_hand,
        "message": "Movimiento registrado exitosamente"
    }