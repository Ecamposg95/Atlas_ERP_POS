from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone


from app.database import engine
from app.models import Base 
from app.routers import (
    auth, users, branches, departments, products, 
    inventory, sales, cash, customers, reports,
    printer, returns, documents, quotes
)

# 1. CREACIÓN AUTOMÁTICA DE TABLAS
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Atlas ERP & POS",
    description="Sistema robusto de administración de recursos y punto de venta",
    version="2.0.0"
)

# 2. CONFIGURACIÓN DE CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. ARCHIVOS ESTÁTICOS Y TEMPLATES
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
def jinja_now_utc(fmt: str = "%A, %d %B %Y") -> str:
    return datetime.now(timezone.utc).strftime(fmt)

templates.env.globals["now_utc"] = jinja_now_utc

# 4. REGISTRO DE ROUTERS (BACKEND API)
app.include_router(auth.router, prefix="/api/auth", tags=["🔑 Autenticación"])
app.include_router(users.router, prefix="/api/users", tags=["👤 Usuarios"])
app.include_router(branches.router, prefix="/api/branches", tags=["🏢 Sucursales"])
app.include_router(departments.router, prefix="/api/departments", tags=["📂 Departamentos"])
app.include_router(products.router, prefix="/api/products", tags=["📦 Catálogo de Productos"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["🔄 Inventario & Kardex"])
app.include_router(sales.router, prefix="/api/sales", tags=["🛒 Ventas POS"])
app.include_router(cash.router, prefix="/api/cash", tags=["💰 Control de Caja (Turnos)"])
app.include_router(returns.router, prefix="/api/returns", tags=["📦 Devoluciones"])
app.include_router(quotes.router, prefix="/api/quotes", tags=["📄 Cotizaciones"])
app.include_router(customers.router, prefix="/api/customers", tags=["👥 Clientes (CRM)"])
app.include_router(documents.router, prefix="/api/documents", tags=["📄 Documentos"])
app.include_router(reports.router, prefix="/api/reports", tags=["📊 Reportes & Auditoría"])
app.include_router(printer.router, prefix="/api/printer", tags=["🖨️ Hardware / Impresora"])

# --- 5. RUTAS DE NAVEGACIÓN (FRONTEND) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    """Dashboard Principal"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de acceso - Cambiado a auth.html según tu plan"""
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/pos", response_class=HTMLResponse)
async def pos_page(request: Request):
    return templates.TemplateResponse("pos.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request):
    """Gestión de productos"""
    return templates.TemplateResponse("products.html", {"request": request})

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    return templates.TemplateResponse("wip.html", {"request": request, "title": "Ventas"})

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request):
    return templates.TemplateResponse("wip.html", {"request": request, "title": "Clientes"})

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("wip.html", {"request": request, "title": "Reportes"})


# Ruta para el módulo de cotizaciones independiente
@app.get("/quotes", response_class=HTMLResponse)
async def quotes_page(request: Request):
    return templates.TemplateResponse("quotes.html", {"request": request})

# --- 6. MANEJO DE ERRORES ---
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    # Si es una petición API, devolver JSON. Si es navegador, devolver HTML.
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)