# app/routers/inventory.py
from typing import List  # <--- ESTA ERA LA LÍNEA QUE FALTABA
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import InventoryMovement, StockOnHand, MovementType, User, ProductVariant
from app.schemas.inventory import AdjustmentCreate, MovementRead
from app.security import get_current_user

router = APIRouter()

@router.post("/adjust", response_model=MovementRead)
def create_adjustment(
    adj: AdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra entradas (Compras) o salidas (Mermas) manuales.
    """
    # 1. Verificar producto
    variant = db.query(ProductVariant).get(adj.variant_id)
    if not variant:
        raise HTTPException(404, "Producto no encontrado")

    # 2. Obtener Stock Actual
    stock_record = db.query(StockOnHand).filter_by(
        branch_id=current_user.branch_id, 
        variant_id=adj.variant_id
    ).first()

    qty_before = stock_record.qty_on_hand if stock_record else 0
    
    # 3. Determinar Tipo de Movimiento
    if adj.quantity > 0:
        mov_type = MovementType.ADJUSTMENT_IN
    else:
        mov_type = MovementType.ADJUSTMENT_OUT
        # Validar stock negativo si es salida
        if qty_before + adj.quantity < 0:
            raise HTTPException(400, "Stock insuficiente para realizar este ajuste.")

    # 4. Actualizar Stock
    if not stock_record:
        stock_record = StockOnHand(
            branch_id=current_user.branch_id,
            variant_id=adj.variant_id,
            qty_on_hand=0
        )
        db.add(stock_record)
    
    stock_record.qty_on_hand += adj.quantity

    # 5. Guardar Kardex
    movement = InventoryMovement(
        branch_id=current_user.branch_id,
        variant_id=adj.variant_id,
        user_id=current_user.id,
        movement_type=mov_type,
        qty_change=adj.quantity,
        qty_before=qty_before,
        qty_after=stock_record.qty_on_hand,
        reference=adj.reason,
        notes=adj.notes
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)

    # Construir respuesta manual para incluir nombre usuario
    return MovementRead(
        id=movement.id,
        movement_type=movement.movement_type,
        qty_change=movement.qty_change,
        qty_after=movement.qty_after,
        reference=movement.reference,
        created_at=movement.created_at,
        user_name=current_user.username
    )

@router.get("/kardex/{variant_id}", response_model=List[MovementRead])
def get_kardex(
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el historial de movimientos de un producto"""
    movements = db.query(InventoryMovement).filter(
        InventoryMovement.variant_id == variant_id,
        InventoryMovement.branch_id == current_user.branch_id
    ).order_by(InventoryMovement.created_at.desc()).limit(100).all()

    # Mapeo manual rápido para incluir user_name
    return [
        MovementRead(
            id=m.id,
            movement_type=m.movement_type,
            qty_change=m.qty_change,
            qty_after=m.qty_after,
            reference=m.reference,
            created_at=m.created_at,
            user_name=m.user.username if m.user else "Sistema"
        ) for m in movements
    ]