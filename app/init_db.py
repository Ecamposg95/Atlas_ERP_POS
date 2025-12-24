import sys
import os

# Agregamos el directorio raíz al path para poder importar 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from decimal import Decimal
import random

from app.database import SessionLocal, engine, Base
from app.models import (
    User, Branch, Product, ProductVariant, StockOnHand, 
    Category, ProductPrice, InventoryMovement, MovementType
)
from app.security import get_password_hash

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("--- INICIANDO SEED ---")

    # 1. Crear Sucursal
    branch = db.query(Branch).first()
    if not branch:
        branch = Branch(name="Matriz Principal", address="Calle Falsa 123", phone="555-5555")
        db.add(branch)
        db.commit()
        db.refresh(branch)
        print("Sucursal creada.")
    else:
        print("Sucursal ya existe.")

    # 2. Crear Usuario Admin
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            # email="admin@atlas.com",  <-- Removed as per model
            password_hash=get_password_hash("admin123"), # Matches User.password_hash
            full_name="Administrador",
            role="ADMINISTRADOR", # Matches Role enum string
            branch_id=branch.id
        )
        db.add(admin)
        db.commit()
        print("Usuario admin creado.")
    else:
        print("Usuario admin ya existe.")

    # 3. Categorías / Departamentos
    depts = ["Abarrotes", "Bebidas", "Farmacia", "Limpieza", "Carnicería", "Panadería", "Electrónica"]
    dept_map = {}
    for d_name in depts:
        cat = db.query(Category).filter(Category.name == d_name).first()
        if not cat:
            cat = Category(name=d_name, description=f"Productos de {d_name}")
            db.add(cat)
            db.flush()
        dept_map[d_name] = cat.id
    db.commit()
    print("Departamentos asegurados.")

    # 4. Productos (20 items)
    # Lista de ejemplos
    products_data = [
        ("Coca Cola 600ml", "Bebidas", 18.00, 15.00, "BOT001"),
        ("Pepsi 600ml", "Bebidas", 17.50, 14.50, "BOT002"),
        ("Agua Ciel 1L", "Bebidas", 12.00, 8.00, "BOT003"),
        ("Sabritas Sal 45g", "Abarrotes", 16.00, 12.00, "SNH001"),
        ("Doritos Nacho 58g", "Abarrotes", 17.00, 12.50, "SNH002"),
        ("Leche Lala 1L", "Abarrotes", 28.00, 24.00, "LAC001"),
        ("Huevo San Juan 12pz", "Abarrotes", 45.00, 38.00, "HUE001"),
        ("Paracetamol 500mg", "Farmacia", 25.00, 10.00, "MED001"),
        ("Aspirina 500mg", "Farmacia", 35.00, 20.00, "MED002"),
        ("Alcohol Etílico 1L", "Farmacia", 85.00, 60.00, "MED003"),
        ("Cloralex 1L", "Limpieza", 18.00, 14.00, "LIM001"),
        ("Fabuloso Lavanda 1L", "Limpieza", 22.00, 16.00, "LIM002"),
        ("Detergente Ace 1kg", "Limpieza", 35.00, 28.00, "LIM003"),
        ("Bistec de Res kg", "Carnicería", 180.00, 140.00, "CAR001"),
        ("Pollo Entero kg", "Carnicería", 85.00, 65.00, "CAR002"),
        ("Bolillo", "Panadería", 3.50, 1.50, "PAN001"),
        ("Concha Vainilla", "Panadería", 12.00, 6.00, "PAN002"),
        ("Cable USB-C", "Electrónica", 150.00, 50.00, "TEC001"),
        ("Cargador iPhone", "Electrónica", 350.00, 180.00, "TEC002"),
        ("Audífonos Básicos", "Electrónica", 120.00, 60.00, "TEC003"),
    ]

    count_new = 0
    for name, dept_name, price, cost, sku in products_data:
        # Check if exists by SKU in variants
        exists = db.query(ProductVariant).filter(ProductVariant.sku == sku).first()
        if exists:
            continue

        # Crear
        dept_id = dept_map.get(dept_name)
        new_prod = Product(
            name=name,
            description=f"Descripción de {name}",
            unit="pza" if "kg" not in name else "kg",
            category_id=dept_id,
            has_variants=True,
            is_active=True
        )
        db.add(new_prod)
        db.flush()

        # Variant
        variant = ProductVariant(
            product_id=new_prod.id,
            sku=sku,
            barcode=sku, # Use SKU as barcode for simplicity
            variant_name="Estándar",
            price=Decimal(price),
            cost=Decimal(cost)
        )
        db.add(variant)
        db.flush()

        # Tiered Prices (Example)
        # Mayoreo > 3 pzas, Distribuidor > 10 pzas
        p_mayoreo = round(price * 0.90, 2)
        p_distrib = round(price * 0.80, 2)

        db.add(ProductPrice(variant_id=variant.id, price_name="Mayoreo (3+)", min_quantity=3, unit_price=Decimal(p_mayoreo)))
        db.add(ProductPrice(variant_id=variant.id, price_name="Distrib. (10+)", min_quantity=10, unit_price=Decimal(p_distrib)))

        # Stock
        initial_stock = Decimal(random.randint(10, 100))
        db.add(StockOnHand(
            branch_id=branch.id,
            variant_id=variant.id,
            qty_on_hand=initial_stock
        ))

        # Movement
        db.add(InventoryMovement(
            branch_id=branch.id,
            variant_id=variant.id,
            user_id=admin.id if admin else None,
            movement_type=MovementType.ADJUSTMENT_IN,
            qty_change=initial_stock,
            qty_before=0,
            qty_after=initial_stock,
            reference="Seed Inicial",
            notes="Auto-generated"
        ))
        
        count_new += 1

    db.commit()
    print(f"--- SEED TERMINADO ---. Productos nuevos: {count_new}")
    db.close()

if __name__ == "__main__":
    init_db()