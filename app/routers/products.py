from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.products import ProductCreate, ProductRead
from app.crud import products as crud_products
from app.security import get_current_user
from app.models import User

router = APIRouter()

@router.post("/", response_model=ProductRead)
def create_product(
    product: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Requiere Login
):
    # 1. Validar duplicados
    if crud_products.get_product_by_sku(db, sku=product.sku):
        raise HTTPException(status_code=400, detail="El SKU ya existe.")
    
    # 2. Crear usando la sucursal del usuario logueado
    return crud_products.create_simple_product(
        db=db, 
        product_in=product, 
        branch_id=current_user.branch_id
    )