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
        printer_name: str = "POS-80", # <--- AJUSTA ESTO AL NOMBRE DE TU IMPRESORA EN WINDOWS
        vendor_id: int = 0x04B8,      # <--- ID USB (Solo Linux)
        product_id: int = 0x0E28,     # <--- ID USB (Solo Linux)
        paper_width_mm: int = 80,
    ):
        self.printer_name = printer_name
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.paper_width_mm = paper_width_mm
        # 80mm ~ 48 cols, 58mm ~ 32 cols
        self.cols = 48 if paper_width_mm >= 80 else 32

        # Comandos ESC/POS
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
        }

    def print_ticket(self, sale: SalesDocument, cashier_name: str) -> bool:
        # Calcular totales de pagos para obtener cambio
        total_paid = sum(p.amount for p in sale.payments)
        change = total_paid - sale.total_amount
        if change < 0: change = Decimal(0)
        
        # Obtener método de pago principal
        method = sale.payments[0].method.value if sale.payments else "N/A"

        raw = self._build_ticket_raw(sale, total_paid, change, method, cashier_name)

        if IS_WINDOWS:
            if not win32print:
                print("Error: pywin32 no instalado. Ejecuta 'pip install pywin32'")
                return False
            return self._print_windows_raw(raw, job_name=f"Ticket #{sale.id}")
        else:
            if not Usb:
                print("Error: python-escpos no instalado. Ejecuta 'pip install python-escpos pyusb'")
                return False
            return self._print_linux_usb(raw)

    def _build_ticket_raw(self, sale: SalesDocument, paid: Decimal, change: Decimal, method: str, cashier: str) -> bytes:
        sep = ("-" * self.cols + "\n").encode("latin-1", "replace")
        
        raw = b""
        raw += self.CMD["INIT"] + self.CMD["SIZE_NORMAL"] + self.CMD["CENTER"] + self.CMD["BOLD_ON"]
        raw += b"ATLAS TECHNOLOGIES\n"
        raw += self.CMD["BOLD_OFF"]
        raw += b"Sucursal Centro\n" 
        
        # Fecha
        fecha = sale.created_at.strftime("%d/%m/%Y %H:%M") if sale.created_at else datetime.now().strftime("%d/%m/%Y %H:%M")
        raw += f"{fecha}\n".encode("latin-1", "replace") + self.CMD["LF"]

        # Info
        raw += self.CMD["LEFT"] + sep
        raw += f"Ticket:  #{sale.id}\n".encode("latin-1", "replace")
        
        c_name = sale.customer.name if sale.customer else "Publico General"
        raw += self._wrap_line(f"Cliente: {c_name}", indent=9)
        raw += self._wrap_line(f"Cajero:  {cashier}", indent=9)
        raw += sep

        # Items
        qty_w, total_w, gap = 5, 10, 1
        name_w = self.cols - qty_w - total_w - gap
        
        raw += self.CMD["BOLD_ON"]
        header = "Cant".ljust(qty_w) + "Producto".ljust(name_w) + (" " * gap) + "Total".rjust(total_w) + "\n"
        raw += header.encode("latin-1", "replace") + self.CMD["BOLD_OFF"]

        for line in sale.lines:
            qty_str = f"{line.quantity:g}"[:qty_w].ljust(qty_w)
            
            # Usamos line.description que ya tiene el nombre
            name_lines = self._wrap_text(line.description, width=name_w) or [""]
            
            total_val = float(line.total_line)
            total_str = f"${total_val:.2f}"[:total_w].rjust(total_w)

            # Primera linea
            l1 = qty_str + name_lines[0].ljust(name_w) + (" " * gap) + total_str + "\n"
            raw += l1.encode("latin-1", "replace")
            
            # Resto del nombre (wrap)
            for extra in name_lines[1:]:
                raw += ((" " * qty_w) + extra.ljust(name_w) + "\n").encode("latin-1", "replace")

        raw += sep

        # Totales
        raw += self.CMD["RIGHT"] + self.CMD["BOLD_ON"]
        raw += self._rline("TOTAL", float(sale.total_amount))
        raw += self.CMD["BOLD_OFF"]
        raw += self._rline("Pagado", float(paid))
        raw += self._rline("Cambio", float(change))
        raw += self.CMD["LF"]

        # Pie
        raw += self.CMD["CENTER"]
        raw += f"Forma de Pago: {method}\n".encode("latin-1", "replace")
        raw += b"Gracias por su compra!\n"
        raw += self.CMD["LF"] * 4
        raw += self.CMD["CUT"]
        
        return raw

    # --- Helpers de Texto ---
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
            # Requiere configurar permisos udev para el usuario
            p = Usb(self.vendor_id, self.product_id, 0)
            p._raw(raw)
            p.close()
            return True
        except Exception as e:
            print(f"Error impresión Linux: {e}")
            return False