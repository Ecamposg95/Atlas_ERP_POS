from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales_documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    
    total_refunded = Column(Numeric(10, 2), nullable=False)
    reason = Column(String, nullable=False) # Ej: Defectuoso, Error de cliente
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    sale = relationship("SalesDocument")
    items = relationship("SaleReturnItem", back_populates="parent_return")

class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("sale_returns.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    quantity = Column(Numeric(10, 2), nullable=False)
    refund_amount = Column(Numeric(10, 2), nullable=False)

    parent_return = relationship("SaleReturn", back_populates="items")