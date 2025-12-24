from fpdf import FPDF
from datetime import datetime

class PDFQuote(FPDF):
    def header(self):
        # Logo placeholder or Company Name
        self.set_font('Arial', 'B', 20)
        self.set_text_color(33, 37, 41) # Dark Gray
        self.cell(0, 10, 'ATLAS ERP', 0, 1, 'L')
        
        self.set_font('Arial', '', 10)
        self.set_text_color(108, 117, 125) # Gray
        self.cell(0, 5, 'Soluciones Tecnológicas y Suministros', 0, 1, 'L')
        self.ln(5)
        
        # Line break
        self.set_draw_color(200, 200, 200)
        self.line(10, 35, 200, 35)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generate_quote_pdf(quote):
    pdf = PDFQuote()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- INFO HEADER ---
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 10, f"COTIZACIÓN #{quote.series}-{quote.folio}", 0, 0, 'L')
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(50, 50, 50)
    # Right align date
    pdf.cell(90, 10, f"Fecha: {quote.created_at.strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    
    pdf.ln(5)

    # --- CLIENTE INFO ---
    pdf.set_fill_color(245, 247, 250) # Very light gray
    pdf.rect(10, pdf.get_y(), 190, 25, 'F')
    
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(20, 5, "Cliente:", 0, 0)
    pdf.set_font("Arial", "", 10)
    customer_name = quote.customer.name if quote.customer else "Público General"
    pdf.cell(100, 5, customer_name.upper(), 0, 1)

    pdf.set_x(15)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(20, 5, "RFC:", 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.cell(100, 5, (quote.customer.tax_id if quote.customer and quote.customer.tax_id else "XAXX010101000"), 0, 1)
    
    pdf.ln(15)

    # --- TABLE HEADER ---
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(33, 37, 41) # Dark header
    pdf.set_text_color(255, 255, 255)
    
    # Columns: SKU(30), Description(80), Qty(20), Price(30), Total(30)
    pdf.cell(30, 8, "SKU", 0, 0, 'C', True)
    pdf.cell(80, 8, "DESCRIPCIÓN", 0, 0, 'L', True)
    pdf.cell(20, 8, "CANT", 0, 0, 'C', True)
    pdf.cell(30, 8, "P. UNIT", 0, 0, 'R', True)
    pdf.cell(30, 8, "TOTAL", 0, 1, 'R', True)

    # --- TABLE BODY ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 9)
    fill = False
    
    for line in quote.lines:
        sku = "" 
        # Si tuvieras acceso al SKU desde line, úsalo. Si no, usa description o recorta.
        # Asumiendo description contiene "SKU - Nombre" como lo guardamos en quotes.py
        desc_parts = line.description.split(" - ", 1)
        sku_text = desc_parts[0] if len(desc_parts) > 1 else ""
        desc_text = desc_parts[1] if len(desc_parts) > 1 else line.description

        pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
        
        # MultiCell height handling calculation could be complex, using single line for simplicity or basic clipping
        pdf.cell(30, 8, sku_text[:14], 0, 0, 'C', fill)
        pdf.cell(80, 8, desc_text[:45], 0, 0, 'L', fill)
        pdf.cell(20, 8, str(line.quantity), 0, 0, 'C', fill)
        pdf.cell(30, 8, f"${line.unit_price:,.2f}", 0, 0, 'R', fill)
        pdf.cell(30, 8, f"${line.total_line:,.2f}", 0, 1, 'R', fill)
        
        fill = not fill
        # Dotted line separador
        pdf.set_draw_color(230,230,230)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())

    # --- TOTALS ---
    pdf.ln(5)
    pdf.set_draw_color(0,0,0)
    
    x_totals = 140
    pdf.set_x(x_totals)
    pdf.set_font("Arial", "", 10)
    pdf.cell(30, 6, "Subtotal", 0, 0, 'R')
    pdf.cell(30, 6, f"${quote.total_amount:,.2f}", 0, 1, 'R')
    
    pdf.set_x(x_totals)
    pdf.set_font("Arial", "", 10)
    pdf.cell(30, 6, "IVA (16%)", 0, 0, 'R')
    pdf.cell(30, 6, f"$0.00", 0, 1, 'R') # Assuming prices include tax or 0 tax logic for now
    
    pdf.set_x(x_totals)
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(30, 10, "TOTAL", 0, 0, 'R', True)
    pdf.cell(30, 10, f"${quote.total_amount:,.2f}", 0, 1, 'R', True)

    # --- TERMS ---
    pdf.ln(20)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, "Términos y Condiciones:", 0, 1, 'L')
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(0, 4, 
        "1. Precios sujetos a cambio sin previo aviso.\n"
        "2. La vigencia de esta cotización es de 15 días naturales.\n"
        "3. En pedidos especiales se requiere el 50% de anticipo.\n"
        "4. Tiempos de entrega sujetos a disponibilidad de stock."
    )

    return pdf.output()