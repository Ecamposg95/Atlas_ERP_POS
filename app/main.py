from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base 

# --- IMPORTACIÓN DE ROUTERS ---
# Asegúrate de que existan los archivos en app/routers/
from app.routers import (
    auth, 
    products, 
    inventory, 
    sales, 
    cash, 
    printer, 
    users,      # Nuevo
    customers,  # Nuevo (CRUD Clientes)
    branches,   # Nuevo
    departments # Nuevo
    # crm       # (Opcional: Si tienes lógica extra de CRM, impórtalo aquí)
)

# Crear tablas en BD (Si no existen)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Atlas ERP & POS")

# --- Archivos Estáticos y Templates ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Config CORS (Permitir todo para desarrollo local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ROUTERS (Backend) ---
# Aquí registramos todas las rutas que definimos en los otros archivos

# 1. Seguridad y Usuarios
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])

# 2. Operativos y Ventas
app.include_router(products.router, prefix="/api/products", tags=["Catálogo"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventario"])
app.include_router(sales.router, prefix="/api/sales", tags=["Ventas POS"])
app.include_router(cash.router, prefix="/api/cash", tags=["Corte de Caja"])

# 3. Administración y Clientes
app.include_router(customers.router, prefix="/api/customers", tags=["Clientes"]) # Antes crm
app.include_router(branches.router, prefix="/api/branches", tags=["Sucursales"])
app.include_router(departments.router, prefix="/api/departments", tags=["Departamentos"])

# 4. Hardware
app.include_router(printer.router, prefix="/api/printer", tags=["Impresora"])


# --- RUTAS DE PÁGINAS (Frontend - Jinja2) ---

# 1. Login
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 2. Dashboard (Home)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 3. Punto de Venta (POS)
@app.get("/pos", response_class=HTMLResponse)
async def pos_page(request: Request):
    return templates.TemplateResponse("pos.html", {"request": request})

# 4. Catálogo de Productos
@app.get("/products", response_class=HTMLResponse)
async def read_products_page(request: Request):
    return templates.TemplateResponse("products.html", {"request": request})

# 5. (Opcional) Página de Admin/Usuarios
# Podrías crear un admin.html en el futuro
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    # Por ahora reutilizamos index o creas un admin.html
    return templates.TemplateResponse("index.html", {"request": request})