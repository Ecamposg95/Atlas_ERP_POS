from app.database import SessionLocal, engine
from app.models import Base
# Importamos todos los modelos para asegurar que se creen las tablas
from app.models import (
    User, Branch, Role,
    Product, ProductVariant, StockOnHand, ProductPrice, Category,
    Customer, CashSession
)
from app.security import get_password_hash

def init_db():
    print("--- 1. Eliminando y Creando Tablas ---")
    Base.metadata.drop_all(bind=engine) # Borrón y cuenta nueva
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    print("--- 2. Creando Sucursal y Usuarios ---")
    branch = Branch(name="Matriz Centro", address="Av. Reforma #123")
    db.add(branch)
    db.commit()

    # Usuarios
    users = [
        ("admin", "1234", Role.ADMINISTRADOR, "Admin General"),
        ("gerente", "5678", Role.GERENTE, "Gerente Tienda"),
        ("cajero1", "0000", Role.CAJERO, "Juan Pérez"),
    ]
    
    for user, pin, role, name in users:
        new_u = User(
            username=user, 
            password_hash=get_password_hash(pin),
            role=role, 
            full_name=name,
            branch_id=branch.id
        )
        db.add(new_u)
    db.commit()

    print("--- 3. Creando Departamentos ---")
    depts = ["Abarrotes", "Bebidas", "Botanas", "Limpieza", "Farmacia"]
    dept_objs = {}
    for d in depts:
        cat = Category(name=d)
        db.add(cat)
        db.flush()
        dept_objs[d] = cat.id
    db.commit()

    print("--- 4. Creando Productos con Variantes y Precios ---")
    # Formato: (Nombre, SKU, PrecioLista, Costo, Depto, Stock, PrecioMayoreo)
    products_data = [
        ("Coca Cola 600ml", "COCA600", 18.00, 12.50, "Bebidas", 100, 16.50),
        ("Coca Cola 2.5L", "COCA25", 42.00, 35.00, "Bebidas", 50, 40.00),
        ("Sabritas Sal 45g", "SABRITAS", 19.00, 13.00, "Botanas", 80, 17.00),
        ("Aceite 1-2-3 1L", "ACEITE1L", 45.00, 38.00, "Abarrotes", 40, 42.00),
        ("Cloralex 1L", "CLORALEX", 19.00, 12.00, "Limpieza", 60, 17.50),
        ("Paracetamol 500mg", "PARACET", 25.00, 10.00, "Farmacia", 100, 20.00),
    ]

    for name, sku, price, cost, dept, stock, wholesale in products_data:
        # Producto Padre
        prod = Product(
            name=name, 
            description=f"Producto {name}", 
            unit="pza",
            category_id=dept_objs.get(dept),
            is_active=True
        )
        db.add(prod)
        db.flush()

        # Variante
        var = ProductVariant(
            product_id=prod.id,
            sku=sku,
            variant_name="Estándar",
            price=price,
            cost=cost
        )
        db.add(var)
        db.flush()

        # Precio Extra (Mayoreo)
        if wholesale:
            p_price = ProductPrice(
                variant_id=var.id,
                price_name="Mayoreo",
                min_quantity=6, # A partir de 6 piezas
                unit_price=wholesale
            )
            db.add(p_price)

        # Stock
        db.add(StockOnHand(
            branch_id=branch.id,
            variant_id=var.id,
            qty_on_hand=stock
        ))

    db.commit()
    print("✅ Base de datos regenerada exitosamente.")
    db.close()

if __name__ == "__main__":
    init_db()