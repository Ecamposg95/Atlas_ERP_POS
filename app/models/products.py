from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Numeric, Float
from sqlalchemy.orm import relationship
from .base import Base

# --- Entidades Auxiliares ---

class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    products = relationship("Product", back_populates="brand")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True) # Para jerarquías futuras
    
    products = relationship("Product", back_populates="category")

class UnitOfMeasure(Base):
    __tablename__ = "uoms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False) # e.g. "Pieza", "Kg", "Litro"
    code = Column(String, unique=True, nullable=False) # e.g. "PZA", "KG"

# --- Producto Padre (El Modelo) ---

class Product(Base):
    """
    Define el concepto general (ej. 'Camisa Polo Nike').
    No se vende directamente, actua como plantilla para las variantes.
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    has_variants = Column(Boolean, default=False) # True si tiene tallas/colores
    is_active = Column(Boolean, default=True)
    
    # Impuestos (Simplificado por ahora)
    tax_rate = Column(Float, default=0.16) # 0.16 para IVA general

    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")

# --- Variante de Producto (El SKU Vendible) ---

class ProductVariant(Base):
    """
    El ítem tangible que se mueve en inventario (ej. 'Camisa Polo Nike - Roja - M').
    Si el producto no tiene variantes, se crea una variante 'default' oculta.
    """
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    sku = Column(String, unique=True, index=True, nullable=False)
    barcode = Column(String, unique=True, index=True, nullable=True)
    
    # Atributos específicos (JSON o columnas planas para simplicidad inicial)
    variant_name = Column(String) # "Roja / M" o "Default"
    
    cost = Column(Numeric(10, 2), default=0.00)
    price = Column(Numeric(10, 2), default=0.00) # Precio base (puede ser sobreescrito por listas de precios)
    
    weight = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="variants")
    stock_points = relationship("StockOnHand", back_populates="variant")
    movements = relationship("InventoryMovement", back_populates="variant")