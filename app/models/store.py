from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Branch(Base):
    """
    Representa una Sucursal física o Almacén.
    """
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relaciones (Strings para evitar ciclos)
    users = relationship("User", back_populates="branch")
    # customers = relationship("Customer", back_populates="branch") # Opcional si el cliente es por sucursal