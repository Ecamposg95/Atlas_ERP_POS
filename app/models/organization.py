# app/models/organization.py
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # ESTA LÍNEA ES LA QUE FALTA:
    users = relationship("User", back_populates="branch")

class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)

class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Mi Empresa")
    tax_id = Column(String, nullable=True) # RFC / Tax ID
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    ticket_header = Column(String, nullable=True, default="ATLAS POS - Nota de Venta")
    ticket_footer = Column(String, nullable=True, default="Gracias por su compra!")
