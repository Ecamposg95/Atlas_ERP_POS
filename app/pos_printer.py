# app/pos_printer.py
from __future__ import annotations
import os
import platform
from datetime import datetime
from typing import List
from decimal import Decimal

# Importamos tus modelos reales
from app.models import SalesDocument, Payment, SalesLineItem

IS_WINDOWS = platform.system().lower() == "windows"

if IS_WINDOWS:
    try:
        import win32print
    except ImportError:
        win32print = None
else:
    try:
        from escpos.printer import Usb
    except ImportError:
        Usb = None

class PosPrinter:
    def __init__(
        self,
        printer_name: str = "POS-80",
        vendor_id: int = 0x04B8,
        product_id: int = 0x0E28,
        paper_width_mm: int = 80,
    ):
        self.printer_name = printer_name
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.paper_width_mm = paper_width_mm
        self.cols = 48 if paper_width_mm >= 80 else 32

        # Comandos ESC/POS extendidos
        self.CMD = {
            "INIT": b"\x1B\x40",
            "LF": b"\x0A",
            "CUT": b"\x1D\x56\x42\x00",
            "CENTER": b"\x1B\x61\x01",
            "LEFT": b"\x1B\x61\x00",
            "RIGHT": b"\x1B\x61\x02",
            "BOLD_ON": b"\x1B\x45\x01",
            "BOLD_OFF": b"\x1B\x45\x00",
            "SIZE_NORMAL": b"\x1D\x21\x00",
            "SIZE_LARGE": b"\x1D\x21\x11", # Doble alto y ancho
        }

    def print_ticket(self, sale: SalesDocument, cashier_name: str, is_reprint: bool = False, organization = None) -> bool:
        """
        Método principal de impresión. 
        is_reprint: Si es True, añade la leyenda de copia al inicio.
        """
        total_paid = sum(p.amount for p in sale.payments)
        change = total_paid - sale.total_amount
        if change < 0: change = Decimal(0)
        
        method = sale.payments[0].method.value if sale.payments else "N/A"

        # Construir el contenido binario del ticket
        raw = self._build_ticket_raw(sale, total_paid, change, method, cashier_name, is_reprint, organization)

        if IS_WINDOWS:
            if not win32print: return False
            return self._print_windows_raw(raw, job_name=f"Ticket #{sale.folio}")
        else:
            if not Usb: return False
            return self._print_linux_usb(raw)

    def _build_ticket_raw(self, sale: SalesDocument, paid: Decimal, change: Decimal, method: str, cashier: str, is_reprint: bool, organization = None) -> bytes:
        sep = ("-" * self.cols + "\n").encode("latin-1", "replace")
        raw = b""
        
        # Defaults
        header_text = "ATLAS TECHNOLOGIES"
        sub_header = "Sucursal Centro"
        footer_text = "Gracias por su compra!"
        
        if organization:
            if organization.ticket_header: header_text = organization.ticket_header
            # If you want organization name as subheader or part of header, adjust logic here.
            # usually organization.name is the main header, ticket_header enables a custom message.
            # based on user request "modify my ticket", ticket_header is often the company name line.
            
            if organization.ticket_footer: footer_text = organization.ticket_footer
            
            # Uncomment if you want to use the Organization Name instead of Header string
            # header_text = organization.name or header_text

        # 1. Inicio y Encabezado
        raw += self.CMD["INIT"] + self.CMD["SIZE_NORMAL"] + self.CMD["CENTER"]
        
        # Si es reimpresión, mostrar alerta visual clara
        if is_reprint:
            raw += self.CMD["BOLD_ON"] + self.CMD["SIZE_LARGE"]
            raw += b"*** REIMPRESION ***\n"
            raw += self.CMD["SIZE_NORMAL"] + b"--- COPIA DEL TICKET ---\n" + self.CMD["BOLD_OFF"]
            raw += self.CMD["LF"]

        raw += self.CMD["BOLD_ON"]
        # Allow multi-line header
        if organization and organization.ticket_header:
             headers = self._wrap_text(organization.ticket_header, self.cols)
             for h in headers:
                 raw += (h + "\n").encode("latin-1", "replace")
        else:
             raw += b"ATLAS POS SYSTEM\n"

        raw += self.CMD["BOLD_OFF"]
        
        # Optional: Print Org info like address/phone if needed
        if organization:
             if organization.address:
                 raw += self._wrap_line(organization.address, 0)
             if organization.phone:
                 raw += (f"Tel: {organization.phone}\n").encode("latin-1", "replace")

        # 2. Datos de la Venta
        fecha = sale.created_at.strftime("%d/%m/%Y %H:%M") if sale.created_at else datetime.now().strftime("%d/%m/%Y %H:%M")
        raw += f"{fecha}\n".encode("latin-1", "replace") + self.CMD["LF"]

        raw += self.CMD["LEFT"] + sep
        raw += f"Ticket:  {sale.series}-{sale.folio}\n".encode("latin-1", "replace")
        
        c_name = sale.customer.name if sale.customer else "Publico General"
        raw += self._wrap_line(f"Cliente: {c_name}", indent=9)
        raw += self._wrap_line(f"Cajero:  {cashier}", indent=9)
        raw += sep

        # 3. Lista de Productos
        qty_w, total_w, gap = 5, 10, 1
        name_w = self.cols - qty_w - total_w - gap
        
        raw += self.CMD["BOLD_ON"]
        header = "Cant".ljust(qty_w) + "Producto".ljust(name_w) + (" " * gap) + "Total".rjust(total_w) + "\n"
        raw += header.encode("latin-1", "replace") + self.CMD["BOLD_OFF"]

        for line in sale.lines:
            qty_str = f"{line.quantity:g}"[:qty_w].ljust(qty_w)
            name_lines = self._wrap_text(line.description, width=name_w) or [""]
            total_val = float(line.total_line)
            total_str = f"${total_val:.2f}"[:total_w].rjust(total_w)

            l1 = qty_str + name_lines[0].ljust(name_w) + (" " * gap) + total_str + "\n"
            raw += l1.encode("latin-1", "replace")
            
            for extra in name_lines[1:]:
                raw += ((" " * qty_w) + extra.ljust(name_w) + "\n").encode("latin-1", "replace")

        raw += sep

        # 4. Totales y Pago
        raw += self.CMD["RIGHT"] + self.CMD["BOLD_ON"]
        raw += self._rline("TOTAL", float(sale.total_amount))
        raw += self.CMD["BOLD_OFF"]
        raw += self._rline("Pagado", float(paid))
        raw += self._rline("Cambio", float(change))
        raw += self.CMD["LF"]

        # 5. Pie de página
        raw += self.CMD["CENTER"]
        raw += f"Metodo: {method}\n".encode("latin-1", "replace")
        
        if is_reprint:
            raw += b"Documento sin valor contable (COPIA)\n"
        
        raw += (footer_text + "\n").encode("latin-1", "replace")
        raw += self.CMD["LF"] * 4
        raw += self.CMD["CUT"]
        
        return raw

    def print_cash_cut(self, session, cashier_name: str, branch_name: str, sales_cash: Decimal, inflows: Decimal, outflows: Decimal) -> bool:
        """
        Imprime el corte de caja.
        """
        raw = self._build_cash_cut_raw(session, cashier_name, branch_name, sales_cash, inflows, outflows)

        if IS_WINDOWS:
            if not win32print: return False
            return self._print_windows_raw(raw, job_name=f"Corte #{session.id}")
        else:
            if not Usb: return False
            return self._print_linux_usb(raw)

    def _build_cash_cut_raw(self, session, cashier: str, branch: str, sales: Decimal, inflows: Decimal, outflows: Decimal) -> bytes:
        sep = ("-" * self.cols + "\n").encode("latin-1", "replace")
        raw = b""
        
        # 1. Header
        raw += self.CMD["INIT"] + self.CMD["SIZE_NORMAL"] + self.CMD["CENTER"]
        raw += self.CMD["BOLD_ON"] + b"CORTE DE CAJA\n" + self.CMD["BOLD_OFF"]
        raw += f"{branch}\n".encode("latin-1", "replace")
        
        fecha = session.closed_at.strftime("%d/%m/%Y %H:%M") if session.closed_at else datetime.now().strftime("%d/%m/%Y %H:%M")
        raw += f"{fecha}\n".encode("latin-1", "replace") + self.CMD["LF"]

        raw += self.CMD["LEFT"]
        raw += f"Cajero: {cashier}\n".encode("latin-1", "replace")
        raw += f"Corte #: {session.id}\n".encode("latin-1", "replace")
        raw += sep

        # 2. Resumen
        expected = session.opening_balance + sales + inflows - outflows
        reported = session.closing_balance or Decimal(0)
        diff = reported - expected

        raw += self.CMD["BOLD_ON"] + b"BALANCE GENERAL\n" + self.CMD["BOLD_OFF"]
        raw += self._rline("Fondo Inicial", float(session.opening_balance))
        raw += self._rline("(+) Ventas Efec", float(sales))
        raw += self._rline("(+) Entradas", float(inflows))
        raw += self._rline("(-) Salidas", float(outflows))
        raw += sep
        
        raw += self.CMD["BOLD_ON"]
        raw += self._rline("(=) Esperado", float(expected))
        raw += self._rline("Reportado", float(reported))
        
        start_diff = b""
        if diff < 0: start_diff = b"FALTANTE"
        elif diff > 0: start_diff = b"SOBRANTE"
        else: start_diff = b"DIFERENCIA"
        
        curr_diff_label = start_diff.decode('latin-1') 
        raw += self._rline(curr_diff_label, float(diff))
        raw += self.CMD["BOLD_OFF"]
        raw += sep

        # 3. Observaciones
        if session.notes:
            raw += b"OBSERVACIONES:\n"
            raw += self._wrap_line(session.notes, 0)
            raw += self.CMD["LF"]

        # 4. Firma
        raw += self.CMD["LF"] * 3
        raw += self.CMD["CENTER"] + ("_" * 20).encode("latin-1") + b"\n"
        raw += b"Firma Cajero/Supervisor\n"
        
        raw += self.CMD["LF"] * 4
        raw += self.CMD["CUT"]
        
        return raw

    # --- Helpers de formato ---
    def _rline(self, label: str, value: float) -> bytes:
        txt = f"{label}: ${value:.2f}"
        return (txt.rjust(self.cols) + "\n").encode("latin-1", "replace")

    def _wrap_text(self, text: str, width: int) -> List[str]:
        if not text: return []
        words = text.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= width: cur += (" " if cur else "") + w
            else: 
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines

    def _wrap_line(self, text: str, indent: int) -> bytes:
        if len(text) <= self.cols: return (text + "\n").encode("latin-1", "replace")
        lines = self._wrap_text(text[indent:], self.cols - indent)
        res = (text[:indent] + lines[0] + "\n")
        for l in lines[1:]: res += (" " * indent) + l + "\n"
        return res.encode("latin-1", "replace")

    def _print_windows_raw(self, raw: bytes, job_name: str) -> bool:
        try:
            h = win32print.OpenPrinter(self.printer_name)
            try:
                win32print.StartDocPrinter(h, 1, (job_name, None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, raw)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
                return True
            finally:
                win32print.ClosePrinter(h)
        except Exception as e:
            print(f"Error impresión Windows: {e}")
            return False

    def _print_linux_usb(self, raw: bytes) -> bool:
        try:
            p = Usb(self.vendor_id, self.product_id, 0)
            p._raw(raw)
            p.close()
            return True
        except Exception as e:
            print(f"Error impresión Linux: {e}")
            return False