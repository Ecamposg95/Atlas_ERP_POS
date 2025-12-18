from .base import Base
from .users import User, Branch, Role
# --- AQUÍ ESTABA EL FALTANTE ---
from .products import (
    Product, 
    ProductVariant, 
    StockOnHand, 
    Brand, 
    Category, 
    UnitOfMeasure, 
    ProductPrice  # <--- Agregado nuevo
)
from .inventory import InventoryMovement, MovementType
from .sales import (
    SalesDocument, 
    SalesLineItem, 
    Payment, 
    CashSession, 
    DocumentStatus, 
    DocumentType, 
    PaymentMethod, 
    CashSessionStatus
)
from .crm import Customer, CustomerLedgerEntry