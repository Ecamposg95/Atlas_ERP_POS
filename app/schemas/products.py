from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

# --- Esquemas Base ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None

class ProductVariantBase(BaseModel):
    sku: str
    barcode: Optional[str] = None
    variant_name: str = "Estándar"
    price: Decimal
    cost: Decimal

# --- Esquema para CREAR (Input) ---
class ProductCreate(ProductBase):
    # Datos de la variante principal
    sku: str
    barcode: Optional[str] = None
    price: Decimal
    cost: Decimal
    # Opcional: Stock inicial al crear
    initial_stock: Decimal = Decimal("0.00") 

# --- Esquema para EDITAR (Input) ---
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    is_active: Optional[bool] = None

# --- Esquema para LEER (Output) ---
class ProductVariantRead(ProductVariantBase):
    id: int
    class Config:
        from_attributes = True

class ProductRead(ProductBase):
    id: int
    is_active: bool
    variants: List[ProductVariantRead] = []
    
    # Campo calculado para facilitar el frontend
    stock_total: Optional[Decimal] = Decimal(0) 

    class Config:
        from_attributes = True