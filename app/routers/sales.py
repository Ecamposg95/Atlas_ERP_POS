# app/routers/sales.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

# Asegúrate de que estas importaciones coincidan con la estructura de tu proyecto
from app.database import get_db
from app.models import (
    ProductVariant, StockOnHand, InventoryMovement,
    SalesDocument, SalesLineItem, Payment,
    User, DocumentType, DocumentStatus, MovementType,
    Customer, CustomerLedgerEntry, PaymentMethod
)
from app.schemas.sales import SaleCreate
from app.security import get_current_user
# --- NUEVA IMPORTACIÓN PARA FOLIOS ---
from app.utils.folios import get_next_folio 

router = APIRouter()

@router.post("/", response_model=Dict[str, Any])
def create_sale(
    sale_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra una nueva venta, descuenta stock, maneja créditos y pagos.
    Genera folios consecutivos automáticamente por sucursal.
    """
    if not sale_in.items:
        raise HTTPException(status_code=400, detail="El ticket está vacío")

    # --- 1. Cálculos iniciales y verificación de Stock ---
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

        # Convertimos item.quantity (probablemente float del frontend) a Decimal para operar con precisión
        qty_dec = Decimal(str(item.quantity))

        if current_stock < qty_dec:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para: {variant.sku}. Disponible: {current_stock}")

        # Matemáticas Financieras
        unit_price = variant.price
        # IMPORTANTE: Asegurar que el precio también sea Decimal para evitar errores de punto flotante
        if not isinstance(unit_price, Decimal):
             unit_price = Decimal(str(unit_price))

        line_total = unit_price * qty_dec
        total_sale += line_total

        # Preparar línea de venta para BD
        new_line = SalesLineItem(
            variant_id=variant.id,
            description=f"{variant.sku} - {variant.variant_name}",
            quantity=item.quantity, # Aquí se guarda el valor original (float o int)
            unit_price=unit_price,
            unit_cost=variant.cost,
            total_line=line_total
        )
        db_lines.append(new_line)

        # Kardex y Resta de Stock
        if stock_record:
            qty_before = stock_record.qty_on_hand
            stock_record.qty_on_hand -= qty_dec

            movement = InventoryMovement(
                branch_id=current_user.branch_id,
                variant_id=variant.id,
                user_id=current_user.id,
                movement_type=MovementType.SALE_OUT,
                qty_change=-qty_dec,
                qty_before=qty_before,
                qty_after=qty_before - qty_dec,
                reference="Venta POS",
                notes="Salida por venta directa"
            )
            db.add(movement)

    # --- 2. Análisis Financiero (Pagos y Crédito) ---
    # Sumar todos los pagos recibidos en este momento (Efectivo, Tarjeta, etc.)
    total_paid = sum(Decimal(str(p.amount)) for p in sale_in.payments)

    # Calcular saldo restante. Si es negativo, significa que pagaron de más (cambio).
    balance_difference = total_sale - total_paid

    remaining_debt = Decimal("0.00") # Deuda que queda en el cliente
    
    doc_status = DocumentStatus.PAID # Asumimos pagado inicialmente

    # Si balance_difference > 0, falta dinero. ¿Autorizamos crédito?
    if balance_difference > 0:
        remaining_debt = balance_difference
        if not sale_in.customer_id:
            # Si es público general y no paga completo, error.
            raise HTTPException(status_code=400, detail="Monto insuficiente. Se requiere asignar un Cliente para autorizar crédito.")

        customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        if not customer.has_credit:
            raise HTTPException(status_code=400, detail=f"El cliente {customer.name} no tiene crédito autorizado.")

        # Verificar límite de crédito
        # Asegurar que current_balance sea Decimal
        current_customer_balance = customer.current_balance if isinstance(customer.current_balance, Decimal) else Decimal(str(customer.current_balance))
        
        new_estimated_balance = current_customer_balance + remaining_debt
        if new_estimated_balance > customer.credit_limit:
             raise HTTPException(status_code=400, detail=f"Crédito insuficiente. Saldo actual: ${current_customer_balance:.2f}, Límite: ${customer.credit_limit:.2f}. Intenta cubrir: ${remaining_debt:.2f}")

        # Si todo OK con el crédito, la venta queda "Pendiente de Pago"
        doc_status = DocumentStatus.PENDING

    # --- 3. Guardar Documentos en BD ---
    
    # 3.1 OBTENER SIGUIENTE FOLIO DISPONIBLE
    current_series = "A" # Puedes parametrizar esto por caja o sucursal si deseas
    next_folio_number = get_next_folio(db, branch_id=current_user.branch_id, series=current_series)

    sales_doc = SalesDocument(
        doc_type=DocumentType.INVOICE,
        status=doc_status,
        branch_id=current_user.branch_id,
        seller_id=current_user.id,
        customer_id=sale_in.customer_id,
        total_amount=total_sale,
        subtotal=total_sale, # Ajustar si manejas impuestos separados
        series=current_series,    # Serie dinámica
        folio=next_folio_number   # <--- Folio consecutivo real
    )
    db.add(sales_doc)
    db.flush() # Obtenemos el ID del documento

    # Guardar líneas de productos
    for line in db_lines:
        line.document_id = sales_doc.id
        db.add(line)

    # Guardar los Pagos recibidos (si hubo alguno mayor a 0)
    for payment in sale_in.payments:
        if payment.amount > 0:
            new_payment = Payment(
                sales_document_id=sales_doc.id,
                amount=payment.amount,
                method=payment.method,
                created_by_id=current_user.id,
                reference=payment.reference # Guardar num de autorización de tarjeta si existe
            )
            db.add(new_payment)

    # --- 4. Registrar Deuda en Cta Cte (Si aplica) ---
    if remaining_debt > 0:
        customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
        # Aumentar saldo del cliente
        customer.current_balance += remaining_debt

        # Crear movimiento en el Ledger (Historial) del cliente
        ledger = CustomerLedgerEntry(
            customer_id=customer.id,
            sales_document_id=sales_doc.id,
            amount=remaining_debt, # Monto positivo = Incrementa la deuda
            description=f"Crédito por Venta #{sales_doc.series}-{sales_doc.folio}",
            entry_type="DEBT" # Define un tipo si tu modelo lo requiere
        )
        db.add(ledger)

    # --- COMMIT FINAL ---
    db.commit()
    db.refresh(sales_doc)

    # --- 5. CÁLCULO FINAL PARA LA RESPUESTA ---

    # Calcular el cambio (vuelto). Si pagaron de más (balance_difference es negativo).
    change_amount = Decimal("0.00")
    if balance_difference < 0:
        # Convertimos la diferencia negativa a positiva para mostrar el cambio
        change_amount = abs(balance_difference)

    # Devolvemos un diccionario plano.
    return {
        "status": "success",
        "message": "Venta registrada exitosamente",
        "sale_id": sales_doc.id,
        "folio": f"{sales_doc.series}-{sales_doc.folio}", # Retornamos el folio legible (Ej: A-1024)
        "total": float(sales_doc.total_amount),
        "paid": float(total_paid),
        "change": float(change_amount),
        "credit_debt": float(remaining_debt) if remaining_debt > 0 else 0.0
    }