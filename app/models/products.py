from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .base import Base

# --- Modelos Opcionales (Stubs para evitar error de importación) ---
class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class UnitOfMeasure(Base):
    __tablename__ = "uom"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, index=True)

# --- Modelos Principales ---

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    
    # Clasificación (Opcional, foreign keys pueden ser null por ahora)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    has_variants = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    variants = relationship("ProductVariant", back_populates="product")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    sku = Column(String, unique=True, index=True)
    barcode = Column(String, index=True, nullable=True)
    variant_name = Column(String) # Ej: "Rojo/Grande" o "Estándar"
    
    price = Column(Numeric(10, 2)) # Precio Venta
    cost = Column(Numeric(10, 2))  # Costo
    
    product = relationship("Product", back_populates="variants")

# --- AQUÍ ESTABA EL FALTANTE ---
class StockOnHand(Base):
    __tablename__ = "stock_on_hand"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    qty_on_hand = Column(Numeric(10, 2), default=0.00)
    
    # location_id = ... (Para futuro multialmacén)