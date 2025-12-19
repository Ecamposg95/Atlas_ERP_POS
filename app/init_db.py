from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import SessionLocal, engine
from app.models import Base

# Importamos modelos y el Enum de Role
from app.models import (
    User, Role,                  
    Branch, Department,          
    Customer,                    
    Product, ProductVariant,     
    Category, StockOnHand,       
    ProductPrice                
)
from app.security import get_password_hash

def init_db():
    print("⚠️  ATENCIÓN: Se borrarán todos los datos actuales...")
    
    # 1. Reset Total
    Base.metadata.drop_all(bind=engine) 
    Base.metadata.create_all(bind=engine) 
    
    db = SessionLocal()
    
    try:
        print("🏢 1. Creando Estructura Organizacional...")
        # --- SUCURSALES ---
        matriz = Branch(name="Matriz Centro", address="Av. Reforma #123", phone="555-111-222")
        norte = Branch(name="Sucursal Norte", address="Blvd. Norte #99", phone="555-333-444")
        db.add_all([matriz, norte])
        db.commit() 

        # --- DEPARTAMENTOS ---
        dept_ventas = Department(name="Ventas", description="Fuerza de ventas y caja")
        dept_admin = Department(name="Administración", description="Gerencia y Contabilidad")
        dept_almacen = Department(name="Almacén", description="Logística")
        db.add_all([dept_ventas, dept_admin, dept_almacen])
        db.commit()

        print("👤 2. Creando Usuarios...")
        # --- USUARIOS (Ajustado a tu Modelo) ---
        # Nota: Usamos los ROLES exactos de tu Enum
        users_data = [
            ("admin", "admin123", Role.ADMINISTRADOR, "Administrador General", matriz),
            ("gerente", "1234", Role.GERENTE, "Gerente de Tienda", matriz),
            ("cajero", "0000", Role.CAJERO, "Cajero Matriz", matriz),
            ("cajeronorte", "0000", Role.CAJERO, "Cajero Norte", norte),
            ("dueno", "9999", Role.DUEÑO, "Dueño del Negocio", matriz),
        ]

        for username, password, role_enum, fullname, branch_obj in users_data:
            user = User(
                username=username,
                # AQUI EL CAMBIO: Usamos 'password_hash' para coincidir con tu modelo
                password_hash=get_password_hash(password), 
                role=role_enum, # Pasamos el Enum correcto
                full_name=fullname,
                branch_id=branch_obj.id,
                is_active=True
            )
            db.add(user)
        db.commit()

        print("👥 3. Creando Clientes (CRM)...")
        # --- CLIENTES ---
        publico_general = Customer(
            name="Público General",
            tax_id="XAXX010101000",
            tax_system="616",
            email="ventas@mostrador.com",
            address="Mostrador",
            zip_code="00000",
            has_credit=False,
            current_balance=0
        )
        db.add(publico_general)

        cliente_vip = Customer(
            name="Empresa Distribuidora S.A.",
            tax_id="EDI190101ABC",
            tax_system="601",
            email="compras@distribuidora.com",
            address="Parque Industrial #500",
            zip_code="37000",
            has_credit=True,
            credit_limit=50000.00,
            credit_days=30,
            current_balance=0
        )
        db.add(cliente_vip)
        db.commit()

        print("📦 4. Creando Catálogo de Productos...")
        # --- CATEGORÍAS ---
        cats = ["Bebidas", "Botanas", "Limpieza", "Farmacia", "Electrónica"]
        cat_objs = {}
        for c_name in cats:
            cat = Category(name=c_name)
            db.add(cat)
            db.flush()
            cat_objs[c_name] = cat.id
        
        # --- PRODUCTOS ---
        products_data = [
            ("Coca Cola 600ml", "Bebidas", "COCA600", 18.00, 12.50, 100, 50),
            ("Sabritas Sal 45g", "Botanas", "SABRITAS", 19.00, 13.00, 80, 40),
            ("Paracetamol 500mg", "Farmacia", "PARACET", 25.00, 8.00, 200, 100),
        ]

        for name, cat_name, sku, price, cost, s_matriz, s_norte in products_data:
            prod = Product(
                name=name,
                description=f"Descripción de {name}",
                category_id=cat_objs.get(cat_name),
                unit="pza",
                is_active=True
            )
            db.add(prod)
            db.flush()

            variant = ProductVariant(
                product_id=prod.id,
                sku=sku,
                variant_name="Estándar",
                price=Decimal(str(price)),
                cost=Decimal(str(cost)),
                barcode=sku
            )
            db.add(variant)
            db.flush()

            # Stock
            db.add(StockOnHand(branch_id=matriz.id, variant_id=variant.id, qty_on_hand=Decimal(s_matriz)))
            db.add(StockOnHand(branch_id=norte.id, variant_id=variant.id, qty_on_hand=Decimal(s_norte)))

        db.commit()
        print("✅ ¡Base de datos poblada exitosamente!")
        print(f"👉 Admin: admin / admin123")
        print(f"👉 Cajero: cajero / 0000")

    except Exception as e:
        print(f"❌ Error al poblar la base de datos: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()