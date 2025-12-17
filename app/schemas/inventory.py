from pydantic import BaseModel
from typing import Optional
from enum import Enum

# Replicamos el Enum del modelo para validación
class MovementTypeSchema(str, Enum):
    PURCHASE_IN = "PURCHASE_IN"      # Compra
    ADJUSTMENT_IN = "ADJUSTMENT_IN"  # Ajuste positivo
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"# Ajuste negativo (Merma)

class InventoryAdjustmentCreate(BaseModel):
    sku: str
    quantity: float # Cuánto entra o sale
    movement_type: MovementTypeSchema
    notes: Optional[str] = None

class InventoryResponse(BaseModel):
    sku: str
    new_stock: float
    message: str