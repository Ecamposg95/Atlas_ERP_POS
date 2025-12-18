from app.database import SessionLocal, engine
# Importamos TODO desde app.models (usando el __init__.py que ya configuramos)
# Esto evita importar .base por separado y causar doble carga
from app.models import Base, User, Branch, Product, ProductVariant, StockOnHand, Customer, Role
from app.security import get_password_hash

def init_db():
    print("--- Creando Tablas ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("--- Iniciando Poblado ---")

    # 1. SUCURSAL
    branch = db.query(Branch).first()
    if not branch:
        branch = Branch(name="Sucursal Centro", address="Av. Reforma #123")
        db.add(branch)
        db.commit()
        db.refresh(branch)
        print("✅ Sucursal creada.")

    # 2. USUARIOS
    users_to_create = [
        ("admin", "1234", Role.ADMINISTRADOR),
        ("cajero1", "0000", Role.CAJERO),
        ("cajero2", "1111", Role.CAJERO),
    ]

    for uname, pin, role in users_to_create:
        if not db.query(User).filter(User.username == uname).first():
            user = User(
                username=uname,
                password_hash=get_password_hash(pin),
                role=role,
                branch_id=branch.id,
                full_name=uname.capitalize()
            )
            db.add(user)
            print(f"✅ Usuario '{uname}' creado.")

    db.commit()

    # 3. CLIENTES
    customers_data = [
        {"name": "Cliente General", "tax_id": "XAXX010101000", "has_credit": False},
        {"name": "Cliente VIP", "tax_id": "VIP001", "has_credit": True},
        {"name": "Abarrotes Don Pepe", "tax_id": "ADP990101", "has_credit": True},
    ]

    for c in customers_data:
        if not db.query(Customer).filter(Customer.name == c["name"]).first():
            new_c = Customer(
                name=c["name"],
                tax_id=c["tax_id"],
                has_credit=c["has_credit"],
                credit_limit=5000 if c["has_credit"] else 0,
                credit_days=30 if c["has_credit"] else 0
            )
            db.add(new_c)
    db.commit()
    print("✅ Clientes creados.")

    # 4. PRODUCTOS
    products_list = [
        ("Coca Cola 600ml", "COCA600", 18.00, 12.50),
        ("Pepsi 600ml", "PEPSI600", 17.00, 11.50),
        ("Agua Ciel 1L", "AGUA1L", 12.00, 6.00),
        ("Sabritas Sal", "SABRITAS", 19.00, 13.00),
        ("Galletas Emperador", "EMPERADOR", 16.00, 10.00),
    ]

    count = 0
    for name, sku, price, cost in products_list:
        existing = db.query(ProductVariant).filter(ProductVariant.sku == sku).first()
        if not existing:
            # Producto Padre
            prod = Product(name=name, has_variants=False)
            db.add(prod)
            db.flush()
            
            # Variante
            var = ProductVariant(
                product_id=prod.id, 
                sku=sku, 
                variant_name="Standard", 
                price=price, 
                cost=cost
            )
            db.add(var)
            db.flush()
            
            # Stock
            stock = StockOnHand(
                branch_id=branch.id, 
                variant_id=var.id, 
                qty_on_hand=100
            )
            db.add(stock)
            count += 1
    
    db.commit()
    print(f"✅ {count} Productos creados.")
    db.close()

if __name__ == "__main__":
    init_db()