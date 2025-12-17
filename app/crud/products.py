from sqlalchemy.orm import Session
from app.models import Product, ProductVariant, StockOnHand
from app.schemas.products import ProductCreate

def create_simple_product(db: Session, product_in: ProductCreate, branch_id: int):
    """
    Crea un flujo completo: Producto -> Variante -> Stock en 0.
    """
    # 1. Crear el Padre (Producto genérico)
    db_product = Product(
        name=product_in.name,
        category_id=product_in.category_id,
        brand_id=product_in.brand_id,
        has_variants=False # Es simple por ahora
    )
    db.add(db_product)
    db.flush() # Para obtener el ID del producto
    
    # 2. Crear la Variante (El SKU real)
    db_variant = ProductVariant(
        product_id=db_product.id,
        sku=product_in.sku,
        barcode=product_in.barcode,
        variant_name="Default", # Nombre estándar para productos sin talla/color
        price=product_in.price,
        cost=product_in.cost
    )
    db.add(db_variant)
    db.flush() # Para obtener el ID de la variante
    
    # 3. Inicializar Stock en 0 para la sucursal actual
    db_stock = StockOnHand(
        branch_id=branch_id,
        variant_id=db_variant.id,
        qty_on_hand=0.0
    )
    db.add(db_stock)
    
    db.commit()
    db.refresh(db_product)
    return db_product

def get_product_by_sku(db: Session, sku: str):
    return db.query(ProductVariant).filter(ProductVariant.sku == sku).first()