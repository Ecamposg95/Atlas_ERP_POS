import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

# --- Enums ---
class DocumentType(str, enum.Enum):
    QUOTE = "QUOTE"       # Cotización
    ORDER = "ORDER"       # Pedido
    INVOICE = "INVOICE"   # Ticket/Factura
    RETURN = "RETURN"     # Devolución

class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"       # Borrador
    PENDING = "PENDING"   # <--- ¡ESTE FALTABA! (Crédito / Por cobrar)
    PAID = "PAID"         # Pagado
    CANCELLED = "CANCELLED"

# --- Encabezado de Venta ---
class SalesDocument(Base):
    __tablename__ = "sales_documents"

    id = Column(Integer, primary_key=True, index=True)
    
    doc_type = Column(Enum(DocumentType), default=DocumentType.INVOICE, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PAID, nullable=False)
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    series = Column(String, nullable=True) # A, B, T...
    folio = Column(Integer, nullable=True) # 1, 2, 3...
    
    subtotal = Column(Numeric(10, 2), default=0.00)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), default=0.00)
    
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    branch = relationship("Branch")
    seller = relationship("User")
    customer = relationship("Customer")
    
    lines = relationship("SalesLineItem", back_populates="document", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sales_document")

# --- Detalle de Venta (Items) ---
class SalesLineItem(Base):
    __tablename__ = "sales_lines"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    description = Column(String) # Guardamos el nombre al momento de la venta (snapshot)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=True) # Para calcular utilidad
    total_line = Column(Numeric(10, 2), nullable=False)

    document = relationship("SalesDocument", back_populates="lines")
    variant = relationship("ProductVariant")