import enum
# --- CORRECCIÓN AQUÍ: Agregué 'Boolean' a los imports ---
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Numeric, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"               # Efectivo
    CARD = "CARD"               # Tarjeta Crédito/Débito
    TRANSFER = "TRANSFER"       # Transferencia SPEI
    STORE_CREDIT = "STORE_CREDIT" # Nota de crédito / Monedero
    CHECK = "CHECK"             # Cheque
    OTHER = "OTHER"

class CashSessionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

# --- Sesión de Caja (Corte de Turno) ---
class CashSession(Base):
    """
    Controla el turno de un cajero. Todos los pagos en EFECTIVO
    deben estar vinculados a una sesión abierta.
    """
    __tablename__ = "cash_sessions"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # El Cajero
    
    status = Column(Enum(CashSessionStatus), default=CashSessionStatus.OPEN, nullable=False)
    
    opening_balance = Column(Numeric(10, 2), nullable=False) # Fondo inicial
    closing_balance = Column(Numeric(10, 2), nullable=True)  # Lo que contó el cajero al final
    
    # Calculados al cerrar
    total_cash_sales = Column(Numeric(10, 2), default=0.00) # Ventas sistema
    total_cash_withdrawals = Column(Numeric(10, 2), default=0.00) # Retiros parciales
    difference = Column(Numeric(10, 2), nullable=True)      # Sobrante/Faltante
    
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    branch = relationship("Branch")
    user = relationship("User")
    payments = relationship("Payment", back_populates="cash_session")

# --- El Pago Individual ---
class Payment(Base):
    """
    Representa una transacción monetaria. 
    Una Venta (SalesDocument) puede tener múltiples Pagos (Mixto).
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relación con la Venta (Puede ser null si es un anticipo sin venta creada aún)
    sales_document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=True)
    
    # Relación con la Caja (Solo obligatorio si method == CASH)
    cash_session_id = Column(Integer, ForeignKey("cash_sessions.id"), nullable=True)
    
    # Relación con Cliente (Para abonos a cuenta)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    
    # Datos extra
    reference = Column(String, nullable=True) # Num. Autorización Tarjeta / Folio Transferencia
    
    # --- AQUÍ OCURRÍA EL ERROR ANTES ---
    is_deposit = Column(Boolean, default=True) # True=Entrada dinero, False=Salida/Devolución
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    sales_document = relationship("SalesDocument", back_populates="payments")
    cash_session = relationship("CashSession", back_populates="payments")
    customer = relationship("Customer")