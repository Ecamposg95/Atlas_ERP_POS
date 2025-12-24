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

def init_db():
    db_file = "sql_app.db"
    if os.path.exists(db_file):
        print(f"Deleting existing database: {db_file}")
        os.remove(db_file)
    
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

        # 2. Crear Usuarios (Admin, Cajero, Inventario -> Gerente)
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
                    password_hash=get_password_hash(u_data["password"]), # FIX: Field name correct
                    role=u_data["role"],
                    branch_id=branch.id,
                    is_active=True
                )
                db.add(user)
        db.commit()

        # 3. Crear Categorías (Departamentos)
        categories = ["Abarrotes", "Bebidas", "Lácteos", "Carnes", "Frutas y Verduras", "Limpieza", "Farmacia", "Electrónica"]
        cat_objs = []
        for cat_name in categories:
            cat = db.query(Category).filter_by(name=cat_name).first()
            if not cat:
                cat = Category(name=cat_name)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_objs.append(cat)

        # 4. Crear Productos (25 ejemplos variados)
        products_seed = [
            ("Coca Cola 600ml", "Bebidas", 18.00, 12.50, "Pza"),
            ("Pepsi 600ml", "Bebidas", 17.00, 11.50, "Pza"),
            ("Leche Lala Entera 1L", "Lácteos", 28.00, 24.00, "Lt"),
            ("Leche Alpura Entera 1L", "Lácteos", 27.50, 23.50, "Lt"),
            ("Pan Bimbo Blanco Grande", "Abarrotes", 45.00, 38.00, "Pza"),
            ("Arroz Verde Valle 1kg", "Abarrotes", 32.00, 25.00, "Kg"),
            ("Frijol Negro 1kg", "Abarrotes", 35.00, 28.00, "Kg"),
            ("Aceite 1-2-3 1L", "Abarrotes", 42.00, 34.00, "Lt"),
            ("Atún Dolores Agua", "Abarrotes", 22.00, 16.00, "Lata"),
            ("Mayonesa McCormick 390g", "Abarrotes", 38.00, 31.00, "Frasco"),
            ("Sabritas Sal 45g", "Abarrotes", 18.00, 13.00, "Bolsa"),
            ("Doritos Nacho 58g", "Abarrotes", 19.00, 14.00, "Bolsa"),
            ("Jabón Zote Rosa", "Limpieza", 15.00, 10.00, "Barra"),
            ("Cloralex 1L", "Limpieza", 18.00, 12.00, "Lt"),
            ("Detergente Ace 1kg", "Limpieza", 35.00, 26.00, "Kg"),
            ("Papel Higiénico Regio 4uds", "Limpieza", 30.00, 22.00, "Paq"),
            ("Paracetamol 500mg", "Farmacia", 25.00, 5.00, "Caja"),
            ("Aspirina 500mg", "Farmacia", 30.00, 15.00, "Caja"),
            ("Manzana Red Delicious", "Frutas y Verduras", 45.00, 30.00, "Kg"),
            ("Plátano Chiapas", "Frutas y Verduras", 22.00, 12.00, "Kg"),
            ("Jitomate Saladet", "Frutas y Verduras", 28.00, 15.00, "Kg"),
            ("Carne Molida Res", "Carnes", 120.00, 95.00, "Kg"),
            ("Pechuga de Pollo", "Carnes", 110.00, 85.00, "Kg"),
            ("Cargador USB-C", "Electrónica", 150.00, 50.00, "Pza"),
            ("Audífonos Básicos", "Electrónica", 80.00, 25.00, "Pza"),
        ]

        admin_user = db.query(User).filter_by(username="admin").first()

        print(f"Adding {len(products_seed)} products...")
        count = 0
        for name, cat_name, price, cost, unit in products_seed:
            clean_name = name.replace(" ", "").upper()[:3]
            sku = f"SKU-{clean_name}-{random.randint(100, 999)}"
            
            # Check if exists by name to avoid duplicates if run multiple times (though we wipe db)
            existing = db.query(Product).filter_by(name=name).first()
            
            if not existing:
                cat = next((c for c in cat_objs if c.name == cat_name), None)
                cat_id = cat.id if cat else None
                
                barcode_val = f"750{random.randint(100000000, 999999999)}"

                product = Product(
                    name=name,
                    description=f"Descripción de {name}",
                    unit=unit,
                    category_id=cat_id,
                    has_variants=True,
                    is_active=True
                )
                db.add(product)
                db.flush()

                # Crear Variante Principal
                variant = ProductVariant(
                    product_id=product.id,
                    sku=sku,
                    barcode=barcode_val,
                    variant_name="Estándar",
                    price=price,
                    cost=cost  # Add cost here too
                )
                db.add(variant)
                db.flush()

                # Precios Escalonados
                prices = [
                    ProductPrice(variant_id=variant.id, price_name="Menudeo", min_quantity=1, unit_price=price),
                    ProductPrice(variant_id=variant.id, price_name="Mayoreo (>10)", min_quantity=10, unit_price=price * 0.90),
                    ProductPrice(variant_id=variant.id, price_name="Distribuidor (>50)", min_quantity=50, unit_price=price * 0.85),
                ]
                db.add_all(prices)

                # Stock Inicial
                initial_stock = random.randint(10, 100)
                stock = StockOnHand(
                    branch_id=branch.id,
                    variant_id=variant.id,
                    qty_on_hand=initial_stock,
                    last_updated=datetime.now()
                )
                db.add(stock)

                # Movimiento Inicial (Kardex)
                movement = InventoryMovement(
                    branch_id=branch.id,
                    variant_id=variant.id,
                    user_id=admin_user.id,
                    movement_type=MovementType.ADJUSTMENT_IN,
                    qty_change=initial_stock,
                    qty_before=0,
                    qty_after=initial_stock,
                    reference="INV-INI",
                    notes="Carga Inicial"
                )
                db.add(movement)
                db.commit()
                count += 1

        print(f"Database initialized successfully! Added {count} products.")

    except Exception as e:
        print(f"Error initializing DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()