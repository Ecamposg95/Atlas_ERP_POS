import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class MovementType(str, enum.Enum):
    PURCHASE_IN = "PURCHASE_IN"      # Compra
    SALE_OUT = "SALE_OUT"            # Venta
    ADJUSTMENT_IN = "ADJUSTMENT_IN"  # Ajuste positivo (inventario inicial)
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"# Ajuste negativo (mermas)
    TRANSFER_IN = "TRANSFER_IN"      # Traspaso (entrada)
    TRANSFER_OUT = "TRANSFER_OUT"    # Traspaso (salida)
    RETURN = "RETURN"                # Devolución cliente

class StockOnHand(Base):
    """
    Caché de existencias actuales por Sucursal y Variante.
    Se actualiza automáticamente al procesar movimientos.
    """
    __tablename__ = "stock_on_hand"
    
    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    qty_on_hand = Column(Float, default=0.0)
    qty_reserved = Column(Float, default=0.0) # Para pedidos no entregados

    variant = relationship("ProductVariant", back_populates="stock_points")
    # branch = relationship("Branch") # Asumiendo que definas esto en store.py si lo necesitas bidireccional

class InventoryMovement(Base):
    """
    Kardex: Historial inmutable de cada cambio en el inventario.
    """
    __tablename__ = "inventory_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    movement_type = Column(Enum(MovementType), nullable=False)
    
    qty_change = Column(Float, nullable=False) # Positivo o Negativo
    qty_before = Column(Float, nullable=False) # Snapshot antes del movimiento
    qty_after = Column(Float, nullable=False)  # Snapshot después del movimiento
    
    cost_at_time = Column(Numeric(10, 2), nullable=True) # Costo en el momento del movimiento
    
    reference = Column(String, nullable=True) # Ej. "Order #1024" o "PO #500"
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("ProductVariant", back_populates="movements")