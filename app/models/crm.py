from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False) # Razón Social o Nombre
    tax_id = Column(String, index=True, nullable=True) # RFC / RUC / NIT
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # Configuración de Crédito
    has_credit = Column(Boolean, default=False)
    credit_limit = Column(Numeric(10, 2), default=0.00)
    credit_days = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación con sus movimientos financieros
    ledger_entries = relationship("CustomerLedgerEntry", back_populates="customer")

class CustomerLedgerEntry(Base):
    """
    Kardex Financiero del Cliente. 
    Permite reconstruir el saldo histórico y auditar deudas.
    """
    __tablename__ = "customer_ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Tipo de movimiento: 'INVOICE' (Cargo), 'PAYMENT' (Abono), 'CREDIT_NOTE' (Abono)
    document_type = Column(String, nullable=False) 
    document_id = Column(Integer, nullable=True)   # ID del SalesDocument o Payment
    document_ref = Column(String, nullable=True)   # Folio legible (ej. "FAC-001")
    
    # Monto: Positivo aumenta deuda, Negativo disminuye deuda
    amount = Column(Numeric(10, 2), nullable=False) 
    
    concept = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer = relationship("Customer", back_populates="ledger_entries")