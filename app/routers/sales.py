from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal # <--- ¡IMPORTANTE! Importar Decimal
from app.database import get_db
from app.models import (
    ProductVariant, StockOnHand, InventoryMovement, 
    SalesDocument, SalesLineItem, Payment, 
    User, DocumentType, DocumentStatus, MovementType
)
from app.schemas.sales import SaleCreate
from app.security import get_current_user

router = APIRouter()

@router.post("/", response_model=dict)
def create_sale(
    sale_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validaciones previas
    if not sale_in.items:
        raise HTTPException(status_code=400, detail="El ticket está vacío")

    # --- INICIO DE TRANSACCIÓN ---
    total_sale = Decimal("0.00") # Inicializar como Decimal
    db_lines = []
    
    # 2. Procesar cada ITEM
    for item in sale_in.items:
        # A. Buscar producto
        variant = db.query(ProductVariant).filter(ProductVariant.sku == item.sku).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"SKU '{item.sku}' no encontrado")
        
        # B. Verificar Stock
        stock_record = db.query(StockOnHand).filter(
            StockOnHand.variant_id == variant.id,
            StockOnHand.branch_id == current_user.branch_id
        ).first()
        
        current_stock = stock_record.qty_on_hand if stock_record else 0.0
        if current_stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{variant.sku}'. Disponible: {current_stock}")

        # C. Calcular dineros (CORRECCIÓN CRÍTICA AQUÍ)
        unit_price = variant.price # Esto es Decimal
        quantity_decimal = Decimal(str(item.quantity)) # Convertimos float a Decimal
        
        line_total = unit_price * quantity_decimal  # Ahora Decimal * Decimal funciona
        total_sale += line_total
        
        # D. Preparar Línea de Venta
        new_line = SalesLineItem(
            variant_id=variant.id,
            description=f"{variant.sku} - {variant.variant_name}",
            quantity=item.quantity, # Guardamos float en BD (compatible)
            unit_price=unit_price,
            unit_cost=variant.cost,
            total_line=line_total
        )
        db_lines.append(new_line)
        
        # E. Actualizar Inventario (Stock y Kardex)
        if stock_record:
            qty_before = stock_record.qty_on_hand
            stock_record.qty_on_hand -= item.quantity
            
            # Kardex
            movement = InventoryMovement(
                branch_id=current_user.branch_id,
                variant_id=variant.id,
                user_id=current_user.id,
                movement_type=MovementType.SALE_OUT,
                qty_change=-item.quantity,
                qty_before=qty_before,
                qty_after=qty_before - item.quantity,
                reference="Venta POS",
                notes=f"Salida por venta"
            )
            db.add(movement)

    # 3. Validar Pagos
    # Convertimos los montos de los pagos a Decimal también por seguridad
    total_paid = sum(Decimal(str(p.amount)) for p in sale_in.payments)
    
    if total_paid < total_sale:
        raise HTTPException(status_code=400, detail=f"Falta dinero. Total: ${total_sale}, Recibido: ${total_paid}")

    # 4. Crear DOCUMENTO DE VENTA
    sales_doc = SalesDocument(
        doc_type=DocumentType.INVOICE,
        status=DocumentStatus.PAID,
        branch_id=current_user.branch_id,
        seller_id=current_user.id,
        customer_id=sale_in.customer_id,
        total_amount=total_sale,
        subtotal=total_sale,
        series="A",
        folio=1
    )
    db.add(sales_doc)
    db.flush() 
    
    # 5. Guardar Líneas
    for line in db_lines:
        line.document_id = sales_doc.id
        db.add(line)
        
    # 6. Guardar Pagos
    for payment in sale_in.payments:
        new_payment = Payment(
            sales_document_id=sales_doc.id,
            amount=payment.amount,
            method=payment.method,
        )
        db.add(new_payment)

    db.commit()
    db.refresh(sales_doc)

    return {
        "status": "success",
        "ticket_id": sales_doc.id,
        "total": sales_doc.total_amount,
        "items_sold": len(db_lines)
    }