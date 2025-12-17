# init_db.py
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Branch, User, UserRole
from app.security import get_pin_hash # Asegúrate de tener esta función en security.py

def init_db():
    # 1. Crear tablas
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Verificar si ya existe sucursal
        branch = db.query(Branch).first()
        if not branch:
            print("Creando Sucursal Matriz...")
            branch = Branch(name="Matriz Principal", address="Calle Reforma 123")
            db.add(branch)
            db.commit()
            db.refresh(branch)
        
        # 3. Verificar si ya existe admin
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Creando Usuario Admin...")
            # IMPORTANTE: Cambia "1234" por el PIN que quieras usar
            hashed_pin = get_pin_hash("1234") 
            
            admin = User(
                username="admin",
                password_hash=hashed_pin,
                pin="1234", # Opcional, solo si tu modelo lo pide
                role=UserRole.ADMINISTRADOR,
                branch_id=branch.id
            )
            db.add(admin)
            db.commit()
            print("¡Usuario 'admin' creado con PIN '1234'!")
        else:
            print("El usuario admin ya existe.")
            
    except Exception as e:
        print(f"Error al inicializar: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando configuración de Atlas ERP...")
    init_db()
    print("Finalizado.")