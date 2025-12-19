from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# Input para crear un ajuste manual
class AdjustmentCreate(BaseModel):
    variant_id: int
    quantity: Decimal # Positivo para entrada, Negativo para salida
    reason: str       # "Compra", "Merma", "Inventario Inicial"
    notes: Optional[str] = None

# Output para leer el Kardex
class MovementRead(BaseModel):
    id: int
    movement_type: str
    qty_change: Decimal
    qty_after: Decimal
    reference: Optional[str]
    created_at: datetime
    user_name: str # Extraemos el nombre del usuario

    class Config:
        from_attributes = True