from .base import Base
from .users import User, Branch, Role
from .products import Product, ProductVariant, StockOnHand, Brand, Category, UnitOfMeasure
from .inventory import InventoryMovement, MovementType
# --- AQUÍ ESTÁ EL CAMBIO ---
# Agregamos PaymentMethod y CashSessionStatus a la lista
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