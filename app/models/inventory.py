from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, DateTime
from sqlalchemy.sql import func
from app.database import Base
import enum

class MovementType(str, enum.Enum):
    PURCHASE_IN = "PURCHASE_IN"      # Entrada por Compra
    SALE_OUT = "SALE_OUT"            # Salida por Venta
    ADJUSTMENT_IN = "ADJUSTMENT_IN"  # Ajuste Inventario (+)
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"# Ajuste Inventario (-)
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    movement_type = Column(Enum(MovementType), nullable=False)
    qty_change = Column(Numeric(10, 2), nullable=False) # +10 o -5
    qty_before = Column(Numeric(10, 2), nullable=False)
    qty_after = Column(Numeric(10, 2), nullable=False)
    
    reference = Column(String, nullable=True) # ID Venta, ID Compra...
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())