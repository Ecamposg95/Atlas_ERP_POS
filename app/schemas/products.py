from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

# --- Datos para crear un producto simple ---
class ProductCreate(BaseModel):
    name: str
    sku: str
    barcode: Optional[str] = None
    price: Decimal # Precio de venta
    cost: Decimal  # Costo
    
    # Opcionales
    category_id: Optional[int] = None
    brand_id: Optional[int] = None

# --- Datos para leer/devolver al frontend ---
class ProductVariantRead(BaseModel):
    id: int
    sku: str
    price: Decimal
    stock: float = 0.0 

    class Config:
        from_attributes = True

class ProductRead(BaseModel):
    id: int
    name: str
    variants: List[ProductVariantRead] = []

    class Config:
        from_attributes = True