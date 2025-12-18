from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from app.database import get_db
from app.models import Product, ProductVariant, StockOnHand, User, Branch, InventoryMovement, MovementType
from app.schemas.products import ProductCreate, ProductRead, ProductUpdate
from app.security import get_current_user

router = APIRouter()

# --- 1. LISTAR PRODUCTOS ---
@router.get("/", response_model=List[ProductRead])
def read_products(
    skip: int = 0, 
    limit: int = 100, 
    search: str = "", 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Product).filter(Product.is_active == True)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    products = query.offset(skip).limit(limit).all()

    # Inyectar el stock actual de la sucursal del usuario
    results = []
    for p in products:
        # Tomamos la variante principal (la primera)
        if p.variants:
            v = p.variants[0]
            stock = db.query(StockOnHand).filter(
                StockOnHand.variant_id == v.id,
                StockOnHand.branch_id == current_user.branch_id
            ).first()
            p.stock_total = stock.qty_on_hand if stock else Decimal(0)
        results.append(p)

    return results

# --- 2. CREAR PRODUCTO ---
@router.post("/", response_model=ProductRead)
def create_product(
    prod_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar SKU único
    existing = db.query(ProductVariant).filter(ProductVariant.sku == prod_in.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="El SKU ya existe")

    # 1. Crear Padre
    new_prod = Product(
        name=prod_in.name,
        description=prod_in.description,
        is_active=True
    )
    db.add(new_prod)
    db.flush()

    # 2. Crear Variante
    new_variant = ProductVariant(
        product_id=new_prod.id,
        sku=prod_in.sku,
        barcode=prod_in.barcode,
        variant_name="Estándar",
        price=prod_in.price,
        cost=prod_in.cost
    )
    db.add(new_variant)
    db.flush()

    # 3. Crear Stock Inicial (Si se especificó)
    if prod_in.initial_stock > 0:
        stock = StockOnHand(
            branch_id=current_user.branch_id,
            variant_id=new_variant.id,
            qty_on_hand=prod_in.initial_stock
        )
        db.add(stock)
        
        # Registrar movimiento de ajuste inicial
        mov = InventoryMovement(
            branch_id=current_user.branch_id,
            variant_id=new_variant.id,
            user_id=current_user.id,
            movement_type=MovementType.ADJUSTMENT_IN,
            qty_change=prod_in.initial_stock,
            qty_before=0,
            qty_after=prod_in.initial_stock,
            reference="Carga Inicial",
            notes="Alta de producto"
        )
        db.add(mov)
    else:
        # Crear registro de stock en 0 para que no falle luego
        stock = StockOnHand(branch_id=current_user.branch_id, variant_id=new_variant.id, qty_on_hand=0)
        db.add(stock)

    db.commit()
    db.refresh(new_prod)
    new_prod.stock_total = prod_in.initial_stock
    return new_prod

# --- 3. ACTUALIZAR PRODUCTO ---
@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    prod_in: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Actualizar padre
    if prod_in.name: product.name = prod_in.name
    if prod_in.description: product.description = prod_in.description
    
    # Actualizar variante (asumimos 1 variante por ahora)
    if product.variants:
        variant = product.variants[0]
        if prod_in.sku: variant.sku = prod_in.sku
        if prod_in.price is not None: variant.price = prod_in.price
        if prod_in.cost is not None: variant.cost = prod_in.cost
    
    db.commit()
    db.refresh(product)
    return product

# --- 4. ELIMINAR (Soft Delete) ---
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    product.is_active = False # Soft delete
    db.commit()
    return {"msg": "Producto desactivado correctamente"}

# --- 5. BÚSQUEDA RÁPIDA (Ya existía, la mantenemos para el POS) ---
@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db)):
    products = db.query(Product).join(ProductVariant).filter(
        Product.is_active == True,
        (Product.name.ilike(f"%{q}%")) | (ProductVariant.sku.ilike(f"%{q}%"))
    ).limit(10).all()
    return products