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

    from sqlalchemy.orm import relationship
    user = relationship("User")
    variant = relationship("ProductVariant")
    branch = relationship("Branch")

class StockOnHand(Base):
    __tablename__ = "stock_on_hand"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, unique=True)
    
    qty_on_hand = Column(Numeric(10, 2), default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    from sqlalchemy.orm import relationship
    branch = relationship("Branch")
    variant = relationship("ProductVariant", backref="stock_levels")