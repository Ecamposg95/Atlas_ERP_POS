# app/models/users.py
import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Role(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    GERENTE = "GERENTE"
    CAJERO = "CAJERO"
    DUEÑO = "DUEÑO"

class Branch(Base):
    __tablename__ = "branches"
    # --- AGREGAR ESTA LÍNEA ---
    __table_args__ = {'extend_existing': True} 
    # --------------------------

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="branch")

class User(Base):
    __tablename__ = "users"
    # --- AGREGAR ESTA LÍNEA TAMBIÉN POR SEGURIDAD ---
    __table_args__ = {'extend_existing': True}
    # ------------------------------------------------

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.CAJERO, nullable=False)
    is_active = Column(Boolean, default=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    branch = relationship("Branch", back_populates="users")