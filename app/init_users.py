import sys
import os
import random
from datetime import datetime, timedelta

# Agregar el directorio raíz al path para poder importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.security import get_password_hash
from app.models.users import User, Role
from app.models.organization import Branch, Department
from app.models.products import Product, ProductVariant, ProductPrice, Category
from app.models.inventory import InventoryMovement, StockOnHand, MovementType

def init_users():
    db_file = "sql_app.db"
    
    # 0. Limpieza (Opcional, si queremos asegurar empezar de 0 siempre que se corra este script específico)
    # El usuario pidió "borra la base de datos", así que lo incluimos.
    if os.path.exists(db_file):
        print(f"Deleting existing database: {db_file}")
        try:
            os.remove(db_file)
        except PermissionError:
            print("Error: No se pudo borrar la base de datos. Asegúrate de detener el servidor (uvicorn) primero.")
            return

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Crear Sucursal Principal
        branch = db.query(Branch).first()
        if not branch:
            print("Creating default branch...")
            branch = Branch(name="Sucursal Principal", address="Calle Principal #123", phone="555-1234")
            db.add(branch)
            db.commit()
            db.refresh(branch)

        # 2. Crear Usuarios (Admin, Cajero, Gerente)
        users_data = [
            {"username": "admin", "role": Role.ADMINISTRADOR, "password": "admin123"},
            {"username": "cajero", "role": Role.CAJERO, "password": "cajero123"},
            {"username": "almacen", "role": Role.GERENTE, "password": "almacen123"}
        ]        
        for u_data in users_data:
            user = db.query(User).filter_by(username=u_data["username"]).first()
            if not user:
                print(f"Creating user {u_data['username']}...")
                user = User(
                    username=u_data["username"], 
                    password_hash=get_password_hash(u_data["password"]),
                    role=u_data["role"],
                    branch_id=branch.id,
                    is_active=True
                )
                db.add(user)
        db.commit()

        # 3. Crear Categorías (Departamentos)
        categories = ["Abarrotes", "Bebidas", "Lácteos", "Carnes", "Frutas y Verduras", "Limpieza", "Farmacia", "Electrónica"]
        for cat_name in categories:
            cat = db.query(Category).filter_by(name=cat_name).first()
            if not cat:
                print(f"Creating category {cat_name}...")
                cat = Category(name=cat_name)
                db.add(cat)
        
        db.commit()
        print("Database initialized successfully! Users and Categories created. No products added.")

    except Exception as e:
        print(f"Error initializing DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_users()
