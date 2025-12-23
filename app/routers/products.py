# app/routers/products.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from sqlalchemy import or_
import pandas as pd
import io

from app.database import get_db
from app.models import (
    Product, ProductVariant, StockOnHand, User, Branch, 
    InventoryMovement, MovementType, Category, ProductPrice
)
from app.schemas.products import (
    ProductCreate, ProductRead, ProductUpdate, 
    DepartmentRead, StockLevel
)
from app.security import get_current_user

router = APIRouter()

# --- 0. ENDPOINT DEPARTAMENTOS ---
@router.get("/departments", response_model=List[DepartmentRead], tags=["Departamentos"])
def read_departments(db: Session = Depends(get_db)):
    if db.query(Category).count() == 0:
        db.add_all([
            Category(name="General"),
            Category(name="Abarrotes"),
            Category(name="Bebidas"),
            Category(name="Farmacia"),
            Category(name="Limpieza")
        ])
        db.commit()
    return db.query(Category).all()

# --- 1. LISTAR PRODUCTOS ---
@router.get("/", response_model=List[ProductRead])
def read_products(
    skip: int = 0, 
    limit: int = 100, 
    search: str = "", 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Product).outerjoin(ProductVariant).outerjoin(Category).filter(Product.is_active == True)
    
    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(s),
                ProductVariant.sku.ilike(s),
                ProductVariant.barcode.ilike(s)
            )
        ).distinct()
    
    products_db = query.offset(skip).limit(limit).all()
    results = []

    for p in products_db:
        p_read = ProductRead.model_validate(p)
        if p.variants:
            v = p.variants[0]
            p_read.prices = v.prices 
            
            stock = db.query(StockOnHand).filter(
                StockOnHand.variant_id == v.id,
                StockOnHand.branch_id == current_user.branch_id
            ).first()
            qty = stock.qty_on_hand if stock else Decimal(0)
            
            p_read.stock_total = qty
            p_read.stock_levels = [StockLevel(branch_id=current_user.branch_id, qty_on_hand=qty)]
        results.append(p_read)

    return results

# --- 2. CREAR PRODUCTO ---
@router.post("/", response_model=ProductRead)
def create_product(
    prod_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if db.query(ProductVariant).filter(ProductVariant.sku == prod_in.sku).first():
        raise HTTPException(status_code=400, detail=f"El SKU '{prod_in.sku}' ya existe.")

    new_prod = Product(
        name=prod_in.name,
        description=prod_in.description,
        unit=prod_in.unit,
        category_id=prod_in.department_id,
        is_active=True
    )
    db.add(new_prod)
    db.flush()

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

    for p_price in prod_in.prices:
        db.add(ProductPrice(
            variant_id=new_variant.id,
            price_name=p_price.price_name,
            min_quantity=p_price.min_quantity,
            unit_price=p_price.unit_price
        ))

    if prod_in.initial_stock > 0:
        db.add(StockOnHand(
            branch_id=current_user.branch_id,
            variant_id=new_variant.id,
            qty_on_hand=prod_in.initial_stock
        ))
        db.add(InventoryMovement(
            branch_id=current_user.branch_id,
            variant_id=new_variant.id,
            user_id=current_user.id,
            movement_type=MovementType.ADJUSTMENT_IN,
            qty_change=prod_in.initial_stock,
            qty_before=0,
            qty_after=prod_in.initial_stock,
            reference="Alta Inicial",
            notes="Creación de producto"
        ))
    else:
        db.add(StockOnHand(branch_id=current_user.branch_id, variant_id=new_variant.id, qty_on_hand=0))

    db.commit()
    db.refresh(new_prod)
    return read_products(search=prod_in.sku, db=db, current_user=current_user)[0]

# --- 3. ACTUALIZAR PRODUCTO ---
@router.put("/{product_id}")
def update_product(
    product_id: int,
    prod_in: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    
    if prod_in.name: product.name = prod_in.name
    if prod_in.description is not None: product.description = prod_in.description
    if prod_in.unit: product.unit = prod_in.unit
    if prod_in.department_id is not None: product.category_id = prod_in.department_id

    if product.variants:
        v = product.variants[0]
        if prod_in.sku: v.sku = prod_in.sku
        if prod_in.barcode is not None: v.barcode = prod_in.barcode
        if prod_in.price is not None: v.price = prod_in.price
        if prod_in.cost is not None: v.cost = prod_in.cost
        
        if prod_in.prices is not None:
            db.query(ProductPrice).filter(ProductPrice.variant_id == v.id).delete()
            for p_price in prod_in.prices:
                db.add(ProductPrice(
                    variant_id=v.id,
                    price_name=p_price.price_name,
                    min_quantity=p_price.min_quantity,
                    unit_price=p_price.unit_price
                ))

    db.commit()
    return {"msg": "Actualizado correctamente"}

# --- 4. ELIMINAR ---
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product: raise HTTPException(404, "No existe")
    product.is_active = False
    db.commit()
    return {"status": "ok"}

# --- 5. BÚSQUEDA RÁPIDA ---
@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db)):
    s = f"%{q}%"
    return db.query(Product).join(ProductVariant).filter(
        Product.is_active == True,
        or_(
            Product.name.ilike(s),
            ProductVariant.sku.ilike(s),
            ProductVariant.barcode.ilike(s)
        )
    ).limit(15).all()

# --- 6. CARGA MASIVA (CSV + EXCEL) ---
@router.post("/upload")
async def upload_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validar extensión (Excel o CSV)
    filename = file.filename.lower()
    is_csv = filename.endswith('.csv')
    is_excel = filename.endswith(('.xlsx', '.xlsm'))

    if not (is_csv or is_excel):
        raise HTTPException(400, f"Formato no válido. Usa .xlsx, .xlsm o .csv. Recibido: {file.filename}")

    try:
        contents = await file.read()
        if not contents:
             raise HTTPException(status_code=400, detail="El archivo está vacío.")

        # 2. Leer según formato
        if is_csv:
            try:
                # Intentamos UTF-8 primero (estándar moderno)
                df = pd.read_csv(io.BytesIO(contents))
            except UnicodeDecodeError:
                # Si falla (común en Excel en español), probamos latin-1
                df = pd.read_csv(io.BytesIO(contents), encoding='latin-1')
        else:
            # Excel
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        
        # Normalizar columnas
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        created_count = 0
        failed_count = 0
        
        dept_map = {c.name.lower(): c.id for c in db.query(Category).all()}

        for _, row in df.iterrows():
            try:
                # Lógica de filas (idéntica)
                raw_sku = row.get('sku', '')
                raw_name = row.get('nombre', '')
                
                if pd.isna(raw_sku) or pd.isna(raw_name): continue

                sku = str(raw_sku).strip()
                name = str(raw_name).strip()
                
                if not sku or not name: continue
                
                if db.query(ProductVariant).filter(ProductVariant.sku == sku).first():
                    failed_count += 1
                    continue

                raw_dept = row.get('departamento', 'General')
                dept_name = str(raw_dept).strip() if not pd.isna(raw_dept) else 'General'
                
                dept_id = dept_map.get(dept_name.lower())
                if not dept_id:
                    new_dept = Category(name=dept_name)
                    db.add(new_dept)
                    db.flush()
                    dept_id = new_dept.id
                    dept_map[dept_name.lower()] = dept_id

                prod = Product(
                    name=name,
                    description=str(row.get('descripcion', '')),
                    unit=str(row.get('unidad', 'pza')),
                    category_id=dept_id,
                    is_active=True
                )
                db.add(prod)
                db.flush()

                price_val = row.get('precio', 0)
                cost_val = row.get('costo', 0)

                variant = ProductVariant(
                    product_id=prod.id,
                    sku=sku,
                    barcode=str(row.get('codigo_barras', '')).replace('nan', '') or None,
                    variant_name="Estándar",
                    price=float(price_val) if not pd.isna(price_val) else 0,
                    cost=float(cost_val) if not pd.isna(cost_val) else 0
                )
                db.add(variant)
                db.flush()

                stock_val = row.get('stock', 0)
                stock_qty = float(stock_val) if not pd.isna(stock_val) else 0
                
                db.add(StockOnHand(branch_id=current_user.branch_id, variant_id=variant.id, qty_on_hand=stock_qty))
                
                if stock_qty > 0:
                    db.add(InventoryMovement(
                        branch_id=current_user.branch_id, variant_id=variant.id, user_id=current_user.id,
                        movement_type=MovementType.ADJUSTMENT_IN, qty_change=stock_qty, qty_before=0, qty_after=stock_qty,
                        reference="Carga Masiva", notes=f"Archivo: {file.filename}"
                    ))
                
                created_count += 1
            except Exception as e:
                print(f"Error fila: {e}")
                failed_count += 1

        db.commit()
        return {"created_count": created_count, "failed_count": failed_count}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error backend: {e}")
        raise HTTPException(500, f"Error al procesar archivo: {str(e)}")