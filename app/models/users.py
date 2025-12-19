import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base 

class Role(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    GERENTE = "GERENTE"
    CAJERO = "CAJERO"
    DUEÑO = "DUEÑO"

# --- NOTA: He eliminado la clase Branch de aquí ---
# Como ya existe en 'app/models/organization.py', no debemos repetirla.

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    
    password_hash = Column(String, nullable=False)
    
    role = Column(Enum(Role), default=Role.CAJERO, nullable=False)
    
    is_active = Column(Boolean, default=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # SQLAlchemy buscará la clase "Branch" automáticamente en el registro
    branch = relationship("Branch", back_populates="users")