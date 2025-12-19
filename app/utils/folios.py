from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import SalesDocument

def get_next_folio(db: Session, branch_id: int, series: str = "A") -> int:
    """
    Obtiene el siguiente folio disponible para una serie y sucursal específicas.
    Realiza una consulta MAX(folio) en la base de datos.
    """
    # Buscamos el folio más alto actual para esta sucursal y serie
    max_folio = db.query(func.max(SalesDocument.folio)).filter(
        SalesDocument.branch_id == branch_id,
        SalesDocument.series == series
    ).scalar()

    # Si no hay ventas, empezamos en 1. Si hay, sumamos 1.
    if max_folio is None:
        return 1
    return max_folio + 1