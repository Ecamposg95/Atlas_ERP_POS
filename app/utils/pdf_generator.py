from fpdf import FPDF
from io import BytesIO

def generate_quote_pdf(quote):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ATLAS ERP - COTIZACIÓN", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Folio: {quote.series}-{quote.folio}", ln=True, align="R")
    pdf.cell(0, 10, f"Fecha: {quote.created_at.strftime('%d/%m/%Y')}", ln=True, align="R")
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Cliente: {quote.customer.name if quote.customer else 'Público General'}", ln=True)
    
    # Tabla de productos
    pdf.ln(5)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(80, 10, "Descripción", 1, 0, "C", True)
    pdf.cell(30, 10, "Cant.", 1, 0, "C", True)
    pdf.cell(40, 10, "P. Unitario", 1, 0, "C", True)
    pdf.cell(40, 10, "Total", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 10)
    for line in quote.lines:
        pdf.cell(80, 10, line.description[:40], 1)
        pdf.cell(30, 10, str(line.quantity), 1, 0, "C")
        pdf.cell(40, 10, f"${line.unit_price:,.2f}", 1, 0, "R")
        pdf.cell(40, 10, f"${line.total_line:,.2f}", 1, 1, "R")
    
    # Gran Total
    pdf.set_font("Arial", "B", 12)
    pdf.cell(150, 10, "TOTAL:", 0, 0, "R")
    pdf.cell(40, 10, f"${quote.total_amount:,.2f}", 1, 1, "R")
    
    pdf.ln(20)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, "Esta cotización tiene una validez de 15 días naturales. Los precios están sujetos a cambios sin previo aviso.")

    return pdf.output()