# app/models/crm.py
from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# --- CORRECCIÓN CRÍTICA: Usar la Base de app.database ---
from app.database import Base 

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    
    # Datos Fiscales (Agregados para que init_db funcione)
    tax_id = Column(String, index=True, nullable=True) # RFC
    tax_system = Column(String, nullable=True)         # Régimen Fiscal
    zip_code = Column(String, nullable=True)           # CP
    
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)

    # --- Campos de Crédito ---
    has_credit = Column(Boolean, default=False)
    credit_limit = Column(Numeric(10, 2), default=0.00)
    credit_days = Column(Integer, default=0)
    current_balance = Column(Numeric(10, 2), default=0.00) # Cuánto nos debe
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación con sus movimientos financieros
    ledger_entries = relationship("CustomerLedgerEntry", back_populates="customer")

class CustomerLedgerEntry(Base):
    """
    Bitácora financiera del cliente (Kardex de dinero).
    Positivo (+) = Deuda aumenta (Venta a crédito)
    Negativo (-) = Deuda baja (Pago/Abono)
    """
    __tablename__ = "customer_ledger_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    sales_document_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    customer = relationship("Customer", back_populates="ledger_entries")