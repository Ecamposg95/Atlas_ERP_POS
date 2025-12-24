# app/models/cash.py
import enum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class CashSessionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class CashSession(Base):
    __tablename__ = "cash_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Tiempos de operación
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Montos (Sincronizados con schemas/cash.py)
    opening_balance = Column(Numeric(10, 2), default=0.00)  # Saldo inicial / Fondo
    closing_balance = Column(Numeric(10, 2), default=0.00) # Contado por el cajero
    
    total_cash_sales = Column(Numeric(10, 2), default=0.00)
    difference = Column(Numeric(10, 2), default=0.00)      # Faltante o sobrante
    
    status = Column(Enum(CashSessionStatus), default=CashSessionStatus.OPEN)
    notes = Column(String, nullable=True)

    # Relaciones
    user = relationship("User")
    movements = relationship("CashMovement", back_populates="session")

class CashMovement(Base):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_sessions.id"))
    
    type = Column(String) # 'IN', 'OUT'
    amount = Column(Numeric(10, 2))
    reason = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CashSession", back_populates="movements")