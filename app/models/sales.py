import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

# --- Enums para definir el tipo de documento ---
class DocumentType(str, enum.Enum):
    QUOTE = "QUOTE"             # Cotización
    ORDER = "ORDER"             # Pedido de Venta (Apartado)
    INVOICE = "INVOICE"         # Venta Facturada / Ticket Final
    RETURN = "RETURN"           # Devolución
    CREDIT_NOTE = "CREDIT_NOTE" # Nota de Crédito

class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"         # Borrador / En captura
    ISSUED = "ISSUED"       # Emitido / Confirmado
    PAID = "PAID"           # Pagado (Totalmente)
    PARTIALLY_PAID = "PARTIALLY_PAID" # Pagado parcial (Crédito/Apartado)
    CANCELLED = "CANCELLED" # Cancelado
    COMPLETED = "COMPLETED" # Entregado y cerrado

# --- Cabecera del Documento ---
class SalesDocument(Base):
    """
    Tabla maestra que unifica Cotizaciones, Tickets y Devoluciones.
    """
    __tablename__ = "sales_documents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Clasificación
    doc_type = Column(Enum(DocumentType), default=DocumentType.INVOICE, nullable=False, index=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT, nullable=False, index=True)
    
    # Folios (ej. 'A-10023')
    series = Column(String, nullable=True) 
    folio = Column(Integer, nullable=True) 

    # Relaciones Organizacionales
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True) # Null = Cliente Público
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Totales (Snapshots para no recalcular siempre)
    currency = Column(String, default="MXN")
    subtotal = Column(Numeric(10, 2), default=0.00)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), default=0.00)
    
    # Auditoría
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True) # Para cotizaciones

    # Relaciones SQLAlchemy
    branch = relationship("Branch")
    customer = relationship("Customer")
    seller = relationship("User")
    
    lines = relationship("SalesLineItem", back_populates="document", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sales_document")


# --- Detalle del Documento (Partidas) ---
class SalesLineItem(Base):
    """
    Cada renglón de la venta. Guarda una 'foto' del precio y costo 
    en el momento de la venta (vital por si cambian los precios mañana).
    """
    __tablename__ = "sales_lines"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=False)
    
    # Relación con el Catálogo (Ahora apuntamos a la VARIANTE, no al producto genérico)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    description = Column(String, nullable=False) # Nombre del producto + Talla/Color
    
    quantity = Column(Float, nullable=False, default=1.0)
    
    # Precios unitarios (Snapshot)
    unit_price = Column(Numeric(10, 2), nullable=False) # Precio lista
    unit_cost = Column(Numeric(10, 2), nullable=False)  # Costo real (para reportes de utilidad)
    
    discount_rate = Column(Float, default=0.0) # Porcentaje descuento manual
    tax_rate = Column(Float, default=0.16)     # IVA
    
    total_line = Column(Numeric(10, 2), nullable=False) # (Cant * Precio) - Desc + Impuesto

    document = relationship("SalesDocument", back_populates="lines")
    variant = relationship("ProductVariant")