from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal

# --- Deptos / Categorías ---
class DepartmentRead(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# --- Precios Escalonados ---
class ProductPriceBase(BaseModel):
    price_name: str
    min_quantity: Decimal
    unit_price: Decimal

class ProductPriceCreate(ProductPriceBase):
    pass

class ProductPriceRead(ProductPriceBase):
    id: int
    class Config:
        from_attributes = True

# --- Variantes ---
class ProductVariantRead(BaseModel):
    id: int
    sku: str
    barcode: Optional[str] = None
    price: Decimal
    cost: Decimal
    prices: List[ProductPriceRead] = [] # Incluimos la lista de precios
    class Config:
        from_attributes = True

# --- Producto Crear/Editar (Input) ---
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    unit: Optional[str] = "pza"
    
    sku: str
    barcode: Optional[str] = None
    
    price: Decimal      # Precio base (se guarda en variant.price)
    cost: Decimal
    
    department_id: Optional[int] = None
    
    initial_stock: Decimal = Decimal(0)
    uses_inventory: bool = True
    
    # Lista de precios extra (Mayoreo, etc)
    prices: List[ProductPriceCreate] = [] 

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    department_id: Optional[int] = None
    
    # Para editar, reemplazamos la lista de precios completa
    prices: Optional[List[ProductPriceCreate]] = None 

# --- Producto Lectura (Output) ---
class StockLevel(BaseModel):
    branch_id: int
    qty_on_hand: Decimal

class ProductRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    unit: Optional[str] = None
    is_active: bool
    department: Optional[DepartmentRead] = None
    
    # En listados simples, devolvemos la variante principal aplanada
    variants: List[ProductVariantRead] = []
    
    # Campos computados para facilitar el frontend
    stock_total: Decimal = Decimal(0)
    prices: List[ProductPriceRead] = [] # Precios de la variante principal

    # Info de stock detallada (opcional)
    stock_levels: List[StockLevel] = []

    class Config:
        from_attributes = True