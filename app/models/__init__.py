# app/models/__init__.py

# 1. Base de datos (Origen de la clase declarativa)
from app.database import Base

# 2. Organización (Sucursales y Deptos)
# IMPORTANTE: Branch y Department ahora viven aquí
from .organization import Branch, Department 

# 3. Usuarios y Roles
# NOTA: Ya no importamos Branch de aquí, solo User y Role
from .users import User, Role 

# 4. Inventario y Productos
from .products import (
    Product, 
    ProductVariant, 
    Brand, 
    Category, 
    UnitOfMeasure, 
    ProductPrice  # <--- Nuevo
)
from .inventory import InventoryMovement, MovementType, StockOnHand

# 5. Ventas y Caja
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

# 6. Clientes
from .crm import Customer, CustomerLedgerEntry
# (Si cambiaste el nombre del archivo a 'customers.py', cambia '.crm' por '.customers')

from .returns import SaleReturn, SaleReturnItem