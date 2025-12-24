import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
# --- Enums ---
class DocumentType(str, enum.Enum):
    QUOTE = "QUOTE"       # Cotización
    ORDER = "ORDER"       # Pedido
    INVOICE = "INVOICE"   # Ticket/Factura
    RETURN = "RETURN"     # Devolución

class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"       # Borrador
    PENDING = "PENDING"   # Crédito / Por cobrar
    PAID = "PAID"         # Pagado
    CANCELLED = "CANCELLED"

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"

class CashSessionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

# --- Modelo 1: Encabezado de Venta ---
class SalesDocument(Base):
    __tablename__ = "sales_documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    doc_type = Column(Enum(DocumentType), default=DocumentType.INVOICE, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PAID, nullable=False)
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    series = Column(String, nullable=True)
    folio = Column(Integer, nullable=True)
    
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

# --- Modelo 2: Detalle de Venta (Items) ---
class SalesLineItem(Base):
    __tablename__ = "sales_lines"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    description = Column(String) 
    quantity = Column(Float, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    total_line = Column(Numeric(10, 2), nullable=False)

    document = relationship("SalesDocument", back_populates="lines")
    variant = relationship("ProductVariant")

# --- Modelo 3: Pagos (¡ESTE FALTABA!) ---
class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # Puede pertenecer a una venta específica O ser un abono a cuenta global (sales_document_id=null)
    sales_document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    reference = Column(String, nullable=True) # Referencia bancaria / Folio
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sales_document = relationship("SalesDocument", back_populates="payments")