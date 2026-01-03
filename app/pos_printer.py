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
    except ImportError as e:
        print(f"WARNING: win32print not found. Printers will not be detected. Error: {e}")
        win32print = None
else:
    try:
        from escpos.printer import Usb
    except ImportError:
        Usb = None

class PosPrinter:
    def __init__(
        self,
        printer_name: str = None, # If None, tries to use default or first available
        vendor_id: int = 0x04B8,
        product_id: int = 0x0E28,
        paper_width_mm: int = 80,
    ):
        self.printer_name = printer_name or "POS-80"
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

    @staticmethod
    def get_available_printers() -> List[str]:
        printers = []
        if IS_WINDOWS:
            # Method 1: win32print (Preferred if installed)
            if win32print:
                try:
                    for p in win32print.EnumPrinters(2): 
                        if p and len(p) > 2:
                            printers.append(p[2])
                except Exception as e:
                    print(f"Error win32print enum: {e}")
            
            # Method 2: PowerShell (Fallback)
            if not printers:
                try:
                    import subprocess
                    cmd = ["powershell", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"]
                    # Use specific encoding for Windows console (often cp850 or similar, but text=True usually handles it)
                    output = subprocess.check_output(cmd, text=True)
                    for line in output.splitlines():
                        line = line.strip()
                        if line:
                            printers.append(line)
                except Exception as e:
                    print(f"Error PowerShell printer enum: {e}")

        else:
            # Linux logic via lpstat -p
            # Example output: "printer HP-LaserJet-1020 is idle.  enabled since..."
            try:
                import subprocess
                output = subprocess.check_output(['lpstat', '-p'], text=True)
                for line in output.split('\n'):
                    if line.startswith('printer '):
                        # Extract name between 'printer ' and ' is'
                        parts = line.split(' ')
                        if len(parts) > 1:
                            printers.append(parts[1])
            except Exception:
                pass 
                
        return printers

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
        
        # --- Config Values ---
        org_name = "ATLAS POS SYSTEM"
        header_msg = None
        footer_msg = "Gracias por su compra!"
        
        if organization:
            org_name = organization.name or org_name
            header_msg = organization.ticket_header
            footer_msg = organization.ticket_footer or footer_msg

        # --- 1. ENCABEZADO (Organization Name First) ---
        raw += self.CMD["INIT"] + self.CMD["SIZE_NORMAL"] + self.CMD["CENTER"]
        
        # Org Name (Bold)
        raw += self.CMD["BOLD_ON"]
        raw += self._wrap_line(org_name, 0).replace(b"\n", b"\n" + self.CMD["CENTER"]) 
        raw += self.CMD["BOLD_OFF"]
        
        # Address & Phone
        if organization:
             if organization.address:
                 addr_lines = self._wrap_text(organization.address, self.cols)
                 for l in addr_lines: raw += (l + "\n").encode("latin-1", "replace")
             if organization.phone:
                 raw += (f"Tel: {organization.phone}\n").encode("latin-1", "replace")
        
        # Date
        fecha = sale.created_at.strftime("%d/%m/%Y %H:%M") if sale.created_at else datetime.now().strftime("%d/%m/%Y %H:%M")
        raw += (f"{fecha}\n").encode("latin-1", "replace")
        
        # Custom Header (if any, e.g. "Nota de Venta")
        if header_msg:
             raw += self.CMD["LF"]
             headers = self._wrap_text(header_msg, self.cols)
             for h in headers: raw += (h + "\n").encode("latin-1", "replace")
        else:
             raw += b"NOTA DE VENTA\n"

        # --- 2. DATOS VENTA ---
        raw += self.CMD["LF"] + self.CMD["LEFT"] + sep
        
        # Ticket ID - Aligned Left
        raw += f"Nota: {sale.series or ''}-{sale.folio}\n".encode("latin-1", "replace")
        
        # Customer & Cashier
        c_name = sale.customer.name if sale.customer else "Publico General"
        raw += self._wrap_line(f"Cliente: {c_name}", indent=9)
        raw += f"Cajero:  {cashier}\n".encode("latin-1", "replace")
        raw += sep

        # --- 3. PRODUCTOS ---
        # Layout: Cant (4) | Desc (variable) | Total (10)
        # We need to maximize Description space.
        
        cols_qty = 4
        cols_total = 10
        cols_desc = self.cols - cols_qty - cols_total - 2 # 2 spaces padding
        
        # Titles
        raw += self.CMD["BOLD_ON"]
        header_line = "Cant".ljust(cols_qty) + " " + "Producto".ljust(cols_desc) + " " + "Total".rjust(cols_total) + "\n"
        raw += header_line.encode("latin-1", "replace")
        raw += self.CMD["BOLD_OFF"]
        
        for line in sale.lines:
            # Resolve Product Name
            # Try to get clean name from relation, fallback to cleaned description
            p_name = line.description or "Item"
            try:
                if line.variant and line.variant.product:
                     p_name = line.variant.product.name
                     # Append variant name if significant
                     if line.variant.variant_name and line.variant.variant_name.lower() not in ["estándar", "standard", "default"]:
                         p_name += f" ({line.variant.variant_name})"
            except:
                pass # Fallback to description
            
            # Format Quantity
            qty_str = f"{line.quantity:g}"
            
            # Format Total
            total_val = float(line.total_line)
            total_str = f"${total_val:.2f}"
            
            # Wrap Name
            name_lines = self._wrap_text(p_name, cols_desc)
            
            # First Line: Qty | Name[0] | Total
            l1 = qty_str.ljust(cols_qty) + " " + (name_lines[0] if name_lines else "").ljust(cols_desc) + " " + total_str.rjust(cols_total) + "\n"
            raw += l1.encode("latin-1", "replace")
            
            # Subsequent Lines (Name wrapping)
            for extra in name_lines[1:]:
                l_extra = (" " * cols_qty) + " " + extra.ljust(cols_desc) + "\n"
                raw += l_extra.encode("latin-1", "replace")
                
        raw += sep

        # --- 4. TOTALES ---
        raw += self.CMD["RIGHT"] + self.CMD["BOLD_ON"]
        raw += self._rline("TOTAL", float(sale.total_amount))
        raw += self.CMD["BOLD_OFF"]
        
        raw += self._rline("Pagado", float(paid))
        raw += self._rline("Cambio", float(change))
        raw += self.CMD["LF"]

        # --- 5. PIE DE PAGINA ---
        raw += self.CMD["CENTER"]
        
        # Translate Method
        method_map = {
            "CASH": "EFECTIVO",
            "CARD": "TARJETA",
            "TRANSFER": "TRANSFERENCIA",
            "OTHER": "OTRO"
        }
        method_es = method_map.get(str(method).upper(), str(method))
        raw += f"Metodo: {method_es}\n".encode("latin-1", "replace")
        raw += self.CMD["LF"]

        if is_reprint:
            raw += b"*** COPIA - REIMPRESION ***\n"
        
        if footer_msg:
            lines = self._wrap_text(footer_msg, self.cols)
            for l in lines: raw += (l + "\n").encode("latin-1", "replace")
            
        # Branding
        raw += self.CMD["LF"]
        raw += b"Software: Atlas ERPPOS\n"
        
        current_year = datetime.now().year
        raw += b"www.rmazh.mx\n"
        
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

    def print_test_ticket(self, organization) -> bool:
        """
        Imprime un ticket de prueba con la configuración actual.
        """
        sep = ("-" * self.cols + "\n").encode("latin-1", "replace")
        raw = b""
        
        # Header
        raw += self.CMD["INIT"] + self.CMD["SIZE_NORMAL"] + self.CMD["CENTER"]
        raw += self.CMD["BOLD_ON"] + b"IMPRESION DE PRUEBA\n" + self.CMD["BOLD_OFF"]
        raw += b"ATLAS ERP & POS\n"
        raw += self.CMD["LF"]
        
        # Organization Info
        if organization:
             headers = self._wrap_text(organization.ticket_header or "Sin Encabezado", self.cols)
             for h in headers: raw += (h + "\n").encode("latin-1", "replace")
        
        raw += sep
        raw += b"Si puedes leer esto,\n"
        raw += b"la impresora esta configurada\n"
        raw += b"correctamente.\n"
        raw += sep
        
        # Footer
        if organization and organization.ticket_footer:
            raw += (organization.ticket_footer + "\n").encode("latin-1", "replace")
            
        raw += self.CMD["LF"] * 4
        raw += self.CMD["CUT"]
        
        if IS_WINDOWS:
            if not win32print: return False
            return self._print_windows_raw(raw, job_name="Test Print")
        else:
            if not Usb: return False
            return self._print_linux_usb(raw)