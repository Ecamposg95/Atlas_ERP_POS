# app/models/products.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship

# --- CORRECCIÓN CRÍTICA ---
# Debe ser 'app.database' para que init_db reconozca las tablas
from app.database import Base 
# --------------------------

# --- Usaremos Category como "Departamento" ---
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)

class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class UnitOfMeasure(Base):
    __tablename__ = "uom"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, index=True)

# --- PRODUCTO PADRE ---
class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    unit = Column(String, default="pza") # Ej: pza, kg, lt
    
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True) # Departamento
    
    has_variants = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Relaciones
    department = relationship("Category") # Mapeamos category como department
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")

# --- VARIANTES (SKU) ---
class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    sku = Column(String, unique=True, index=True)
    barcode = Column(String, index=True, nullable=True)
    variant_name = Column(String) # Ej: "Estándar", "Rojo/Grande"
    
    price = Column(Numeric(10, 2)) # Precio Base (Lista 1)
    cost = Column(Numeric(10, 2))  # Costo Base
    
    product = relationship("Product", back_populates="variants")
    prices = relationship("ProductPrice", back_populates="variant", cascade="all, delete-orphan")

# --- NUEVO: PRECIOS ESCALONADOS ---
class ProductPrice(Base):
    __tablename__ = "product_prices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    price_name = Column(String) # Ej: "Mayoreo", "Distribuidor"
    min_quantity = Column(Numeric(10, 2), default=1) # A partir de cuántas piezas
    unit_price = Column(Numeric(10, 2), nullable=False)

    variant = relationship("ProductVariant", back_populates="prices")

# --- STOCK ---
class StockOnHand(Base):
    __tablename__ = "stock_on_hand"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    qty_on_hand = Column(Numeric(10, 2), default=0.00)