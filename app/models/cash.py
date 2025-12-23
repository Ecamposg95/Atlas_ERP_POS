# app/models/cash.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class CashSession(Base):
    __tablename__ = "cash_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    # Tiempos de operación
    opening_time = Column(DateTime(timezone=True), server_default=func.now())
    closing_time = Column(DateTime(timezone=True), nullable=True)
    
    # Montos (Sincronizados con schemas/cash.py)
    opening_balance = Column(Numeric(10, 2), default=0.00)  # Saldo inicial / Fondo
    expected_amount = Column(Numeric(10, 2), default=0.00) # Calculado por sistema
    reported_amount = Column(Numeric(10, 2), default=0.00) # Contado por el cajero
    difference = Column(Numeric(10, 2), default=0.00)      # Faltante o sobrante
    
    status = Column(String, default="OPEN") # OPEN, CLOSED
    notes = Column(String, nullable=True)

    # Relaciones
    user = relationship("User")