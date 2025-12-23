from pydantic import BaseModel
from typing import List, Dict
from datetime import date
from decimal import Decimal

# ... Tus clases TopProduct y DailySummary se mantienen igual ...

class CustomerAging(BaseModel):
    customer_id: int
    customer_name: str
    total_balance: Decimal
    # Cubetas de antigüedad
    current_0_30: Decimal
    overdue_31_60: Decimal
    overdue_61_90: Decimal
    overdue_91_plus: Decimal

class AgingReportResponse(BaseModel):
    report_date: date
    total_receivable: Decimal  # Suma total de lo que deben todos los clientes
    customers: List[CustomerAging]

    class Config:
        from_attributes = True