from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

from app.database import get_db
from app.models import (
    SalesDocument, SalesLineItem, DocumentType, DocumentStatus, 
    ProductVariant, StockOnHand, InventoryMovement, MovementType, 
    Payment, Customer
)
from app.schemas.sales import SaleCreate
from app.security import get_current_user, User
from app.utils.folios import get_next_folio
from app.utils.pdf_generator import generate_quote_pdf

router = APIRouter()

@router.post("/", response_model=Dict[str, Any])
def create_quote(
    quote_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea una cotización (No afecta stock ni caja)."""
    if not quote_in.items:
        raise HTTPException(status_code=400, detail="La cotización está vacía")

    # Calcular folio de cotización
    next_folio = get_next_folio(db, branch_id=current_user.branch_id, series="Q")
    
    total_amount = Decimal("0.00")
    temp_lines = []

    # Validar productos
    for item in quote_in.items:
        variant = db.query(ProductVariant).filter(ProductVariant.sku == item.sku).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"SKU '{item.sku}' no encontrado")
        
        qty = Decimal(str(item.quantity))
        line_total = variant.price * qty
        total_amount += line_total
        
        temp_lines.append({
            "variant_id": variant.id,
            "description": f"{variant.sku} - {variant.variant_name}",
            "quantity": item.quantity,
            "unit_price": variant.price,
            "total_line": line_total
        })

    # Crear documento
    new_quote = SalesDocument(
        doc_type=DocumentType.QUOTE,
        status=DocumentStatus.PENDING,
        branch_id=current_user.branch_id,
        seller_id=current_user.id,
        customer_id=quote_in.customer_id,
        total_amount=total_amount,
        series="Q",
        folio=next_folio
    )
    db.add(new_quote)
    db.flush()

    # Agregar líneas
    for l in temp_lines:
        db_line = SalesLineItem(
            document_id=new_quote.id,
            variant_id=l["variant_id"],
            description=l["description"],
            quantity=l["quantity"],
            unit_price=l["unit_price"],
            total_line=l["total_line"]
        )
        db.add(db_line)

    db.commit()
    return {"status": "success", "quote_id": new_quote.id, "folio": f"Q-{next_folio}"}

@router.get("/{quote_id}/pdf")
def get_quote_pdf_file(quote_id: int, db: Session = Depends(get_db)):
    """Genera el PDF descargable de la cotización."""
    quote = db.query(SalesDocument).get(quote_id)
    if not quote or quote.doc_type != DocumentType.QUOTE:
        raise HTTPException(404, "Cotización no encontrada")
    
    pdf_content = generate_quote_pdf(quote)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Cotizacion_{quote.folio}.pdf"}
    )

@router.post("/{quote_id}/convert-to-sale")
def convert_quote_to_sale(
    quote_id: int,
    payment_method: str = "CASH",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toma una cotización y la convierte en una venta real."""
    quote = db.query(SalesDocument).filter(
        SalesDocument.id == quote_id, 
        SalesDocument.doc_type == DocumentType.QUOTE
    ).first()

    if not quote:
        raise HTTPException(404, "Cotización no encontrada")
    
    if quote.status == DocumentStatus.COMPLETED:
        raise HTTPException(400, "Esta cotización ya fue procesada")

    # Validar stock al momento de convertir
    for line in quote.lines:
        stock = db.query(StockOnHand).filter(
            StockOnHand.variant_id == line.variant_id,
            StockOnHand.branch_id == current_user.branch_id
        ).first()
        
        if not stock or stock.qty_on_hand < line.quantity:
            raise HTTPException(400, f"Sin stock para {line.description}")

    # Convertir a INVOICE
    quote.doc_type = DocumentType.INVOICE
    quote.status = DocumentStatus.COMPLETED
    quote.created_at = datetime.now()
    
    # Nuevo folio de venta (Serie A)
    quote.series = "A"
    quote.folio = get_next_folio(db, branch_id=current_user.branch_id, series="A")

    # Registrar Pago y Movimientos de Stock
    new_payment = Payment(
        sales_document_id=quote.id,
        amount=quote.total_amount,
        method=payment_method,
        created_by_id=current_user.id,
        reference=f"Conv. desde Q-{quote.folio}"
    )
    db.add(new_payment)

    for line in quote.lines:
        stock = db.query(StockOnHand).filter(
            StockOnHand.variant_id == line.variant_id,
            StockOnHand.branch_id == current_user.branch_id
        ).first()
        
        qty_before = stock.qty_on_hand
        stock.qty_on_hand -= Decimal(str(line.quantity))

        db.add(InventoryMovement(
            branch_id=current_user.branch_id,
            variant_id=line.variant_id,
            user_id=current_user.id,
            movement_type=MovementType.SALE_OUT,
            qty_change=-line.quantity,
            qty_before=qty_before,
            qty_after=stock.qty_on_hand,
            reference=f"Venta desde Q-{quote.folio}"
        ))

    db.commit()
    return {"status": "success", "new_folio": f"{quote.series}-{quote.folio}"}