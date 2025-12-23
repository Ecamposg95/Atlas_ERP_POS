#app/routers/reports.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from app.database import get_db
from app.models import (
    SalesDocument, SalesLineItem, Payment, 
    ProductVariant, Customer, CashSession, DocumentStatus, CustomerLedgerEntry
)
from app.security import get_current_user, User
from app.schemas.reports import AgingReportResponse


router = APIRouter()

@router.get("/daily-summary")
def get_daily_summary(
    target_date: date = date.today(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resumen de ventas, métodos de pago y utilidad del día."""
    
    # 1. Ventas Totales por Estatus
    sales_query = db.query(
        func.count(SalesDocument.id).label("count"),
        func.sum(SalesDocument.total_amount).label("total")
    ).filter(
        func.date(SalesDocument.created_at) == target_date,
        SalesDocument.branch_id == current_user.branch_id
    ).first()

    # 2. Desglose por Métodos de Pago
    payments_breakdown = db.query(
        Payment.method,
        func.sum(Payment.amount).label("total")
    ).join(SalesDocument).filter(
        func.date(Payment.created_at) == target_date,
        SalesDocument.branch_id == current_user.branch_id
    ).group_by(Payment.method).all()

    # 3. Top 5 Productos más vendidos
    top_products = db.query(
        SalesLineItem.description,
        func.sum(SalesLineItem.quantity).label("qty")
    ).join(SalesDocument).filter(
        func.date(SalesDocument.created_at) == target_date
    ).group_by(SalesLineItem.description).order_by(desc("qty")).limit(5).all()

    # 4. Cálculo de Utilidad Bruta (Venta - Costo)
    profit_data = db.query(
        func.sum(SalesLineItem.total_line - (SalesLineItem.unit_cost * SalesLineItem.quantity))
    ).join(SalesDocument).filter(
        func.date(SalesDocument.created_at) == target_date,
        SalesDocument.status == DocumentStatus.COMPLETED
    ).scalar() or Decimal(0)

    return {
        "date": target_date,
        "transactions_count": sales_query.count or 0,
        "total_revenue": float(sales_query.total or 0),
        "gross_profit": float(profit_data),
        "payments": {p.method: float(p.total) for p in payments_breakdown},
        "top_selling_items": [{"name": p.description, "quantity": float(p.qty)} for p in top_products]
    }

@router.get("/audit/discrepancies")
def get_cash_discrepancies(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista las últimas sesiones de caja con faltantes o sobrantes significativos."""
    discrepancies = db.query(CashSession).filter(
        CashSession.difference != 0
    ).order_by(desc(CashSession.closed_at)).limit(limit).all()
    
    return discrepancies

@router.get("/aging-report", response_model=AgingReportResponse)
def get_aging_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calcula la antigüedad de saldos: Clasifica la deuda de los clientes 
    en periodos de 30, 60, 90 y +90 días.
    """
    now = datetime.now()
    # 1. Obtener solo clientes que tengan saldo deudor actual
    debtor_customers = db.query(Customer).filter(Customer.current_balance > 0).all()
    
    report_list = []
    total_receivable = Decimal("0.00")

    for customer in debtor_customers:
        # Inicializamos los acumuladores para este cliente
        buckets = {
            "current": Decimal("0.00"),  # 0-30 días
            "31_60": Decimal("0.00"),
            "61_90": Decimal("0.00"),
            "91_plus": Decimal("0.00")
        }

        # 2. Analizar cargos pendientes (donde amount > 0)
        # Nota: En un sistema real, aquí podrías filtrar facturas específicas no pagadas
        ledger_entries = db.query(CustomerLedgerEntry).filter(
            CustomerLedgerEntry.customer_id == customer.id,
            CustomerLedgerEntry.amount > 0 
        ).all()

        for entry in ledger_entries:
            days_old = (now - entry.created_at).days

            if days_old <= 30:
                buckets["current"] += entry.amount
            elif days_old <= 60:
                buckets["31_60"] += entry.amount
            elif days_old <= 90:
                buckets["61_90"] += entry.amount
            else:
                buckets["91_plus"] += entry.amount

        # 3. Construir objeto de respuesta para el cliente
        report_list.append({
            "customer_id": customer.id,
            "customer_name": customer.name,
            "total_balance": customer.current_balance,
            "current_0_30": buckets["current"],
            "overdue_31_60": buckets["31_60"],
            "overdue_61_90": buckets["61_90"],
            "overdue_91_plus": buckets["91_plus"]
        })
        total_receivable += customer.current_balance

    return {
        "report_date": now.date(),
        "total_receivable": total_receivable,
        "customers": report_list
    }