from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from io import BytesIO
from xhtml2pdf import pisa
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.models import Customer, SalesDocument, CustomerLedgerEntry
from app.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/customer/{customer_id}/statement-pdf")
def generate_statement_pdf(
    customer_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Genera un Estado de Cuenta profesional en PDF."""
    customer = db.query(Customer).get(customer_id)
    entries = db.query(CustomerLedgerEntry).filter(
        CustomerLedgerEntry.customer_id == customer_id
    ).order_by(CustomerLedgerEntry.created_at.desc()).limit(50).all()

    # Renderizar HTML usando Jinja2
    html_content = templates.get_template("pdf/statement.html").render({
        "customer": customer,
        "entries": entries,
        "today": datetime.now()
    })

    # Convertir HTML a PDF
    pdf_out = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_out)

    if pisa_status.err:
        raise HTTPException(500, "Error al generar el PDF")

    return Response(
        content=pdf_out.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=EdoCuenta_{customer.id}.pdf"}
    )