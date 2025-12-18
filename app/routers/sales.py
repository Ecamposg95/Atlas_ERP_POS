from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from app.database import get_db
from app.models import (
    ProductVariant, StockOnHand, InventoryMovement, 
    SalesDocument, SalesLineItem, Payment, 
    User, DocumentType, DocumentStatus, MovementType,
    Customer, CustomerLedgerEntry, PaymentMethod # Aseguramos importar PaymentMethod
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
    if not sale_in.items:
        raise HTTPException(status_code=400, detail="El ticket está vacío")

    # --- 1. Cálculos y Stock ---
    total_sale = Decimal("0.00")
    db_lines = []
    
    for item in sale_in.items:
        variant = db.query(ProductVariant).filter(ProductVariant.sku == item.sku).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"SKU '{item.sku}' no encontrado")
        
        # Validar Stock
        stock_record = db.query(StockOnHand).filter(
            StockOnHand.variant_id == variant.id,
            StockOnHand.branch_id == current_user.branch_id
        ).first()
        
        current_stock = stock_record.qty_on_hand if stock_record else Decimal(0.0)
        
        # Convertimos item.quantity (float) a Decimal para operar
        qty_dec = Decimal(str(item.quantity))

        if current_stock < qty_dec:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente: {variant.sku}")

        # Matemáticas
        unit_price = variant.price
        line_total = unit_price * qty_dec
        total_sale += line_total
        
        # Línea de venta
        new_line = SalesLineItem(
            variant_id=variant.id,
            description=f"{variant.sku} - {variant.variant_name}",
            quantity=item.quantity, # Aquí guardamos float (está bien para el registro)
            unit_price=unit_price,
            unit_cost=variant.cost,
            total_line=line_total
        )
        db_lines.append(new_line)
        
        # Kardex y Resta de Stock
        if stock_record:
            qty_before = stock_record.qty_on_hand
            
            # CORRECCIÓN: Usamos qty_dec (Decimal) en lugar de item.quantity (float)
            stock_record.qty_on_hand -= qty_dec 
            
            movement = InventoryMovement(
                branch_id=current_user.branch_id,
                variant_id=variant.id,
                user_id=current_user.id,
                movement_type=MovementType.SALE_OUT,
                qty_change=-qty_dec, # Decimal
                qty_before=qty_before,
                qty_after=qty_before - qty_dec, # Decimal
                reference="Venta POS",
                notes="Salida venta"
            )
            db.add(movement)

    # --- 2. Análisis Financiero (Crédito) ---
    total_paid = sum(Decimal(str(p.amount)) for p in sale_in.payments)
    remaining_balance = total_sale - total_paid
    
    doc_status = DocumentStatus.PAID
    
    # Si no cubrió el total, ¿Autorizamos crédito?
    if remaining_balance > 0:
        if not sale_in.customer_id:
            # Si es público general y no paga completo, error (no se fía a desconocidos)
            raise HTTPException(status_code=400, detail="Monto insuficiente. Se requiere Cliente para crédito.")
        
        customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        if not customer.has_credit:
            raise HTTPException(status_code=400, detail=f"Cliente {customer.name} no tiene crédito autorizado.")
            
        # Verificar límite
        new_balance = customer.current_balance + remaining_balance # current_balance debe ser Decimal en modelo
        if new_balance > customer.credit_limit:
             raise HTTPException(status_code=400, detail=f"Crédito insuficiente. Saldo actual: ${customer.current_balance}, Límite: ${customer.credit_limit}")

        # Todo OK -> La venta queda "Pendiente de Pago"
        doc_status = DocumentStatus.PENDING

    # --- 3. Guardar Documentos ---
    sales_doc = SalesDocument(
        doc_type=DocumentType.INVOICE,
        status=doc_status,
        branch_id=current_user.branch_id,
        seller_id=current_user.id,
        customer_id=sale_in.customer_id,
        total_amount=total_sale,
        subtotal=total_sale,
        series="A",
        folio=1 # TODO: Folios dinámicos
    )
    db.add(sales_doc)
    db.flush() 
    
    # Guardar líneas
    for line in db_lines:
        line.document_id = sales_doc.id
        db.add(line)
        
    # Guardar Pagos recibidos (si hubo abono parcial o total)
    for payment in sale_in.payments:
        if payment.amount > 0:
            new_payment = Payment(
                sales_document_id=sales_doc.id,
                amount=payment.amount,
                method=payment.method,
                created_by_id=current_user.id # Importante para cortes de caja
            )
            db.add(new_payment)

    # --- 4. Registrar Deuda (Si aplica) ---
    if remaining_balance > 0:
        # Aumentar saldo del cliente
        customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
        customer.current_balance += remaining_balance
        
        # Crear movimiento en Ledger
        ledger = CustomerLedgerEntry(
            customer_id=customer.id,
            sales_document_id=sales_doc.id,
            amount=remaining_balance, # Positivo = Deuda
            description=f"Crédito por Venta #{sales_doc.id}"
        )
        db.add(ledger)

    db.commit()
    db.refresh(sales_doc)

    return {
        "status": "success",
        "ticket_id": sales_doc.id,
        "total": sales_doc.total_amount,
        "paid": total_paid,
        "credit_debt": remaining_balance if remaining_balance > 0 else 0
    }