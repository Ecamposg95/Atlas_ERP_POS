import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base

class UserRole(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    GERENTE = "GERENTE"
    VENDEDOR = "VENDEDOR"
    CAJERO = "CAJERO"
    ALMACENISTA = "ALMACENISTA" # ¡Nuevo!

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True) # Modernizamos para ERP
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False) # Antes pin_hash, ahora más genérico
    pin = Column(String, nullable=True) # Para acceso rápido en POS
    
    role = Column(Enum(UserRole), default=UserRole.VENDEDOR)
    is_active = Column(Boolean, default=True)
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    branch = relationship("Branch", back_populates="users")