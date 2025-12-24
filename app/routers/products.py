# app/routers/products.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List
from decimal import Decimal
from sqlalchemy import or_
import pandas as pd
import io

from app.database import get_db
from app.models import (
    Product, ProductVariant, StockOnHand, User,
    InventoryMovement, MovementType, Category, ProductPrice
)
from app.schemas.products import (
    ProductCreate, ProductRead, ProductUpdate,
    DepartmentRead, StockLevel
)
from app.security import get_current_user

router = APIRouter()


# -----------------------------
# Helpers
# -----------------------------
def _compute_product_read(
    p: Product,
    db: Session,
    current_user: User,
) -> ProductRead:
    """
    Convierte ORM Product -> ProductRead y agrega:
    - prices (de la variante principal)
    - stock_total / stock_levels (por sucursal del usuario)
    """
    p_read = ProductRead.model_validate(p)

    if p.variants:
        v = p.variants[0]
        p_read.sku = v.sku
        p_read.barcode = v.barcode
        p_read.price = v.price
        p_read.cost = v.cost

        # Precios escalonados de la variante principal
        p_read.prices = list(v.prices or [])

        # Stock por sucursal del usuario
        stock = (
            db.query(StockOnHand)
            .filter(
                StockOnHand.variant_id == v.id,
                StockOnHand.branch_id == current_user.branch_id
            )
            .first()
        )
        qty = stock.qty_on_hand if stock else Decimal(0)

        p_read.stock_total = qty
        p_read.stock_levels = [
            StockLevel(branch_id=current_user.branch_id, qty_on_hand=qty)
        ]

    return p_read


def _safe_str(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _safe_decimal(val, default: Decimal = Decimal(0)) -> Decimal:
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)) or (isinstance(val, str) and val.strip().lower() == "nan"):
            return default
        return Decimal(str(val))
    except Exception:
        return default


# -----------------------------
# 0. Departamentos (Categories)
# -----------------------------
@router.get("/departments", response_model=List[DepartmentRead], tags=["Departamentos"])
def read_departments(db: Session = Depends(get_db)):
    # Seed básico si está vacío
    if db.query(Category).count() == 0:
        db.add_all([
            Category(name="General"),
            Category(name="Abarrotes"),
            Category(name="Bebidas"),
            Category(name="Farmacia"),
            Category(name="Limpieza"),
        ])
        db.commit()
    return db.query(Category).all()


# -----------------------------
# 1. Listar productos
# -----------------------------
@router.get("/", response_model=List[ProductRead])
def read_products(
    skip: int = 0,
    limit: int = 100,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Product)
        .options(
            joinedload(Product.variants).joinedload(ProductVariant.prices),
            joinedload(Product.department),
        )
        .outerjoin(ProductVariant)
        .outerjoin(Category)
        .filter(Product.is_active == True)
    )

    if search:
        s = f"%{search}%"
        query = (
            query.filter(
                or_(
                    Product.name.ilike(s),
                    ProductVariant.sku.ilike(s),
                    ProductVariant.barcode.ilike(s),
                )
            )
            .distinct()
        )

    products_db = query.offset(skip).limit(limit).all()

    results: List[ProductRead] = []
    for p in products_db:
        results.append(_compute_product_read(p, db, current_user))

    return results


# -----------------------------
# 2. Crear producto
# -----------------------------
@router.post("/", response_model=ProductRead)
def create_product(
    prod_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validar SKU único
    if db.query(ProductVariant).filter(ProductVariant.sku == prod_in.sku).first():
        raise HTTPException(status_code=400, detail=f"El SKU '{prod_in.sku}' ya existe.")

    # Crear producto padre
    new_prod = Product(
        name=prod_in.name,
        description=prod_in.description,
        unit=prod_in.unit or "pza",
        category_id=prod_in.department_id,
        has_variants=True,   # CONSISTENCIA: ya que se crea una variante estándar
        is_active=True,
    )
    db.add(new_prod)
    db.flush()

    # Crear variante estándar
    new_variant = ProductVariant(
        product_id=new_prod.id,
        sku=prod_in.sku,
        barcode=prod_in.barcode,
        variant_name="Estándar",
        price=prod_in.price,
        cost=prod_in.cost,
    )
    db.add(new_variant)
    db.flush()

    # Precios escalonados
    for p_price in (prod_in.prices or []):
        db.add(ProductPrice(
            variant_id=new_variant.id,
            price_name=p_price.price_name,
            min_quantity=p_price.min_quantity,
            unit_price=p_price.unit_price,
        ))

    # Stock inicial + movimiento inventario
    initial_stock = prod_in.initial_stock or Decimal(0)

    # Asegurar existencia stock_on_hand siempre
    db.add(StockOnHand(
        branch_id=current_user.branch_id,
        variant_id=new_variant.id,
        qty_on_hand=initial_stock if initial_stock > 0 else Decimal(0),
    ))

    if initial_stock > 0:
        db.add(InventoryMovement(
            branch_id=current_user.branch_id,
            variant_id=new_variant.id,
            user_id=current_user.id,
            movement_type=MovementType.ADJUSTMENT_IN,
            qty_change=initial_stock,
            qty_before=Decimal(0),
            qty_after=initial_stock,
            reference="Alta Inicial",
            notes="Creación de producto",
        ))

    db.commit()

    # Recargar con relaciones para respuesta completa
    p_db = (
        db.query(Product)
        .options(
            joinedload(Product.variants).joinedload(ProductVariant.prices),
            joinedload(Product.department),
        )
        .filter(Product.id == new_prod.id)
        .first()
    )
    if not p_db:
        raise HTTPException(500, "No se pudo recuperar el producto creado.")

    return _compute_product_read(p_db, db, current_user)


# -----------------------------
# 3. Actualizar producto
# -----------------------------
@router.put("/{product_id}")
def update_product(
    product_id: int,
    prod_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .options(joinedload(Product.variants).joinedload(ProductVariant.prices))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Campos producto
    if prod_in.name is not None:
        product.name = prod_in.name
    if prod_in.description is not None:
        product.description = prod_in.description
    if prod_in.unit is not None:
        product.unit = prod_in.unit
    if prod_in.department_id is not None:
        product.category_id = prod_in.department_id

    # Variante principal (si existe)
    if product.variants:
        v = product.variants[0]

        # SKU único si cambia
        if prod_in.sku and prod_in.sku != v.sku:
            if db.query(ProductVariant).filter(ProductVariant.sku == prod_in.sku).first():
                raise HTTPException(status_code=400, detail=f"El SKU '{prod_in.sku}' ya existe.")
            v.sku = prod_in.sku

        if prod_in.barcode is not None:
            v.barcode = prod_in.barcode
        if prod_in.price is not None:
            v.price = prod_in.price
        if prod_in.cost is not None:
            v.cost = prod_in.cost

        # Reemplazar lista de precios escalonados
        if prod_in.prices is not None:
            db.query(ProductPrice).filter(ProductPrice.variant_id == v.id).delete()
            for p_price in prod_in.prices:
                db.add(ProductPrice(
                    variant_id=v.id,
                    price_name=p_price.price_name,
                    min_quantity=p_price.min_quantity,
                    unit_price=p_price.unit_price,
                ))

        # 2. Add/Sync Extra Variants
        # Strategy: We will delete non-main variants and recreate them from the list, 
        # unless we want to be smarter. For simplicity: Delete all EXCEPT main, then add new ones.
        # Main variant is 'v' (variants[0]).
        
        if prod_in.extra_variants is not None:
             # Delete all variants of this product where id != v.id
             db.query(ProductVariant).filter(
                 ProductVariant.product_id == product.id,
                 ProductVariant.id != v.id
             ).delete()
             
             for extra in prod_in.extra_variants:
                 if extra.sku == v.sku: continue # Skip if matches main
                 
                 # Check global SKU uniqueness (optional but recommended)
                 # existing = db.query(ProductVariant).filter(ProductVariant.sku == extra.sku).first()
                 # if existing: raise ...
                 
                 db.add(ProductVariant(
                    product_id=product.id,
                    sku=extra.sku,
                    variant_name=extra.variant_name,
                    price=extra.price,
                    cost=extra.cost or v.cost
                 ))

    db.commit()
    return {"msg": "Actualizado correctamente"}


# -----------------------------
# 4. Eliminar (soft delete)
# -----------------------------
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="No existe")
    product.is_active = False
    db.commit()
    return {"status": "ok"}


# -----------------------------
# 5. Búsqueda rápida (CORREGIDA)
# -----------------------------
@router.get("/search", response_model=List[ProductRead])
def search_products(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve productos POS-friendly:
    - Incluye variants[0].sku y variants[0].price
    - Incluye prices escalonados y departamento
    - Incluye stock_total por sucursal del usuario
    """
    s = f"%{q}%"

    query = (
        db.query(Product)
        .options(
            joinedload(Product.variants).joinedload(ProductVariant.prices),
            joinedload(Product.department),
        )
        .join(ProductVariant)
        .filter(
            Product.is_active == True,
            or_(
                Product.name.ilike(s),
                ProductVariant.sku.ilike(s),
                ProductVariant.barcode.ilike(s),
            ),
        )
        .distinct()
        .limit(15)
    )

    products_db = query.all()
    return [_compute_product_read(p, db, current_user) for p in products_db]


# -----------------------------
# 6. Carga masiva CSV/Excel
# -----------------------------
# -----------------------------
# 6. Exportar Excel
# -----------------------------
@router.get("/export/excel")
def export_products_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Query flattening variants
    products = (
        db.query(Product)
        .options(
            joinedload(Product.variants).joinedload(ProductVariant.prices),
            joinedload(Product.department),
        )
        .filter(Product.is_active == True)
        .all()
    )

    data = []
    for p in products:
        # Use first variant for flattened logic
        v = p.variants[0] if p.variants else None
        
        row = {
            "SKU": v.sku if v else "",
            "Nombre": p.name,
            "Departamento": p.department.name if p.department else "General",
            "Costo": float(v.cost) if v else 0.0,
            "Precio Base": float(v.price) if v else 0.0,
            "Stock": 0, # Placeholder, logic below
            "Unidad": p.unit,
            "Codigo Barras": v.barcode if v else "",
            "Descripcion": p.description or ""
        }

        # Stock logic (sum of all branches or current branch?) -> Best to show current branch
        if v:
            stock = db.query(StockOnHand).filter(
                StockOnHand.variant_id == v.id,
                StockOnHand.branch_id == current_user.branch_id
            ).first()
            row["Stock"] = float(stock.qty_on_hand) if stock else 0.0

            # Tiered Prices (Flatten up to 3)
            # Layout: P1 Nombre, P1 Min, P1 Precio, P2...
            prices = sorted(v.prices, key=lambda x: x.unit_price, reverse=True) # or by order?
            for i, price in enumerate(prices[:5]): # Limit to 5 tiers
                idx = i + 1
                row[f"P{idx} Nombre"] = price.price_name
                row[f"P{idx} Min"] = float(price.min_quantity)
                row[f"P{idx} Precio"] = float(price.unit_price)

    data.append(row)

    df = pd.DataFrame(data)
    
    # Save to buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Productos')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="productos_atlas.xlsx"'
    }
    from fastapi.responses import StreamingResponse
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)


# -----------------------------
# 7. Carga masiva (Refactorizada)
# -----------------------------
@router.post("/upload")
async def upload_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = (file.filename or "").lower()
    is_csv = filename.endswith(".csv")
    is_excel = filename.endswith((".xlsx", ".xlsm", ".xls"))

    if not (is_csv or is_excel):
        raise HTTPException(status_code=400, detail=f"Formato inválido. Use Excel o CSV.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Archivo vacío.")

    try:
        if is_csv:
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error leyendo archivo: {str(e)}")

    # Normalize cols
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # Cache departments
    dept_map = {c.name.lower(): c.id for c in db.query(Category).all()}

    created_count = 0
    updated_count = 0
    failed_count = 0

    for _, row in df.iterrows():
        try:
            # Check basic fields
            raw_sku = str(row.get("sku", "")).strip()
            raw_name = str(row.get("nombre", "")).strip()

            if not raw_sku or raw_sku.lower() == "nan": 
                continue # Skip empty rows

            # Find or Create Product logic
            # Using SKU as key
            existing_variant = db.query(ProductVariant).filter(ProductVariant.sku == raw_sku).first()
            
            # --- PREPARE DATA ---
            # Department
            raw_dept = str(row.get("departamento", "General")).strip()
            if raw_dept.lower() == "nan" or not raw_dept: raw_dept = "General"
            
            dept_id = dept_map.get(raw_dept.lower())
            if not dept_id:
                new_dept = Category(name=raw_dept)
                db.add(new_dept)
                db.flush()
                dept_id = new_dept.id
                dept_map[raw_dept.lower()] = dept_id

            price_base = _safe_decimal(row.get("precio base", row.get("precio", 0)))
            cost = _safe_decimal(row.get("costo", 0))
            is_new = False
            
            if existing_variant:
                # Update
                prod = existing_variant.product
                prod.name = raw_name if raw_name else prod.name
                prod.category_id = dept_id
                
                existing_variant.price = price_base
                existing_variant.cost = cost
                updated_count += 1
                variant = existing_variant
            else:
                # Create
                if not raw_name: raw_name = "Producto sin Nombre"
                
                prod = Product(
                    name=raw_name,
                    description=str(row.get("descripcion", "")),
                    unit=str(row.get("unidad", "pza")),
                    category_id=dept_id,
                    has_variants=True,
                    is_active=True
                )
                db.add(prod)
                db.flush()
                
                variant = ProductVariant(
                    product_id=prod.id,
                    sku=raw_sku,
                    barcode=str(row.get("codigo barras", "")) or None,
                    variant_name="Estándar",
                    price=price_base,
                    cost=cost
                )
                db.add(variant)
                db.flush()
                created_count += 1
                is_new = True

            # --- STOCK ---
            # Only update stock if provided and > 0, usually for initial load. 
            # Or if user specifically wants to reset stock? Let's assume input is "Initial Stock" or "Adjustment"
            # For simplicity, if stock column exists and is different, we adjust.
            input_stock = _safe_decimal(row.get("stock", -1)) # -1 sentinel
            
            if input_stock >= 0:
                # Check current stock
                stock_record = db.query(StockOnHand).filter(
                    StockOnHand.variant_id == variant.id, 
                    StockOnHand.branch_id == current_user.branch_id
                ).first()
                
                if not stock_record:
                    stock_record = StockOnHand(
                        branch_id=current_user.branch_id, 
                        variant_id=variant.id, 
                        qty_on_hand=0
                    )
                    db.add(stock_record)
                    db.flush()
                
                diff = input_stock - stock_record.qty_on_hand
                if diff != 0:
                     stock_record.qty_on_hand = input_stock
                     # Log movement
                     reason = "Carga Masiva (Inicial)" if is_new else "Carga Masiva (Ajuste)"
                     db.add(InventoryMovement(
                        branch_id=current_user.branch_id,
                        variant_id=variant.id,
                        user_id=current_user.id,
                        movement_type=MovementType.ADJUSTMENT_IN if diff > 0 else MovementType.ADJUSTMENT_OUT,
                        qty_change=abs(diff),
                        qty_before=stock_record.qty_on_hand - diff,
                        qty_after=input_stock,
                        reference="Excel Upload",
                        notes=reason
                    ))

            # --- TIERED PRICES ---
            # Parse dynamic columns p1 nombre, p1 min, p1 precio, etc.
            # We first clear existing tiers if we detect new ones to avoid dups? 
            # Or maybe only if 'p1 nombre' is present?
            # Let's replace only if columns exist.
            
            has_tier_cols = any(c.startswith("p1") for c in df.columns)
            if has_tier_cols:
                # Delete existing
                db.query(ProductPrice).filter(ProductPrice.variant_id == variant.id).delete()
                
                for i in range(1, 6): # Up to 5
                    p_name = row.get(f"p{i} nombre")
                    p_min = row.get(f"p{i} min")
                    p_val = row.get(f"p{i} precio")
                    
                    if p_name and not pd.isna(p_name) and p_val and not pd.isna(p_val):
                        db.add(ProductPrice(
                            variant_id=variant.id,
                            price_name=str(p_name),
                            min_quantity=_safe_decimal(p_min, 1),
                            unit_price=_safe_decimal(p_val, 0)
                        ))

        except Exception as e:
            print(f"Error row: {e}")
            failed_count += 1

    db.commit()
    return {"created": created_count, "updated": updated_count, "failed": failed_count}
