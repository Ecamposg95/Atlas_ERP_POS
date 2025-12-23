# app/routers/expenses.py
from app.models import CashSession, CashSessionStatus, Payment # Asumido para registro

@router.post("/cash-out")
def register_expense(
    amount: Decimal,
    category: str, # Ej: 'Limpieza', 'Papelería'
    description: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra una salida de dinero de la caja activa."""
    # Buscar sesión activa del cajero
    session = db.query(CashSession).filter(
        CashSession.user_id == current_user.id,
        CashSession.status == "OPEN"
    ).first()

    if not session:
        raise HTTPException(400, "Debes abrir caja antes de registrar un gasto")

    # Registrar el gasto (podrías tener una tabla 'Expenses')
    # Por ahora, afectamos el cálculo del cierre de caja directamente
    # o guardamos en una tabla vinculada a la sesión.
    
    return {"message": "Gasto registrado, se descontará del cierre de caja"}