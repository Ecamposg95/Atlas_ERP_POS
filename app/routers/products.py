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
        raise HTTPException(status_code=400, detail=f"Formato no válido. Usa .xlsx/.xlsm/.xls o .csv. Recibido: {file.filename}")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    # Leer archivo
    try:
        if is_csv:
            try:
                df = pd.read_csv(io.BytesIO(contents))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
        else:
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo: {str(e)}")

    # Normalizar columnas
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Mapeo deptos existentes
    dept_map = {c.name.lower(): c.id for c in db.query(Category).all()}

    created_count = 0
    failed_count = 0

    for _, row in df.iterrows():
        try:
            raw_sku = row.get("sku", "")
            raw_name = row.get("nombre", "")

            sku = _safe_str(raw_sku)
            name = _safe_str(raw_name)

            if not sku or not name:
                continue

            # SKU único
            if db.query(ProductVariant).filter(ProductVariant.sku == sku).first():
                failed_count += 1
                continue

            # Departamento
            raw_dept = row.get("departamento", "General")
            dept_name = _safe_str(raw_dept) or "General"

            dept_id = dept_map.get(dept_name.lower())
            if not dept_id:
                new_dept = Category(name=dept_name)
                db.add(new_dept)
                db.flush()
                dept_id = new_dept.id
                dept_map[dept_name.lower()] = dept_id

            # Crear producto
            prod = Product(
                name=name,
                description=_safe_str(row.get("descripcion", "")),
                unit=_safe_str(row.get("unidad", "pza")) or "pza",
                category_id=dept_id,
                has_variants=True,
                is_active=True,
            )
            db.add(prod)
            db.flush()

            price = _safe_decimal(row.get("precio", 0), default=Decimal(0))
            cost = _safe_decimal(row.get("costo", 0), default=Decimal(0))

            barcode = _safe_str(row.get("codigo_barras", "")) or None

            # Crear variante estándar
            variant = ProductVariant(
                product_id=prod.id,
                sku=sku,
                barcode=barcode,
                variant_name="Estándar",
                price=price,
                cost=cost,
            )
            db.add(variant)
            db.flush()

            # Stock
            stock_qty = _safe_decimal(row.get("stock", 0), default=Decimal(0))

            db.add(StockOnHand(
                branch_id=current_user.branch_id,
                variant_id=variant.id,
                qty_on_hand=stock_qty,
            ))

            if stock_qty > 0:
                db.add(InventoryMovement(
                    branch_id=current_user.branch_id,
                    variant_id=variant.id,
                    user_id=current_user.id,
                    movement_type=MovementType.ADJUSTMENT_IN,
                    qty_change=stock_qty,
                    qty_before=Decimal(0),
                    qty_after=stock_qty,
                    reference="Carga Masiva",
                    notes=f"Archivo: {file.filename}",
                ))

            created_count += 1

        except Exception as e:
            # Log local para debug (no romper toda la carga)
            print(f"[UPLOAD_PRODUCTS] Error fila: {e}")
            failed_count += 1

    db.commit()
    return {"created_count": created_count, "failed_count": failed_count}
