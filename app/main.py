from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles # <--- NUEVO
from fastapi.templating import Jinja2Templates # <--- NUEVO
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base 

# Routers
from app.routers import auth, products, inventory, sales, crm, cash

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Atlas ERP & POS")

# --- 1. Montar Archivos Estáticos (CSS/JS) ---
# Esto permite acceder a http://localhost:8000/static/css/estilo.css
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- 2. Configurar Motor de Plantillas ---
templates = Jinja2Templates(directory="app/templates")

# Config CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(products.router, prefix="/api/products", tags=["Catálogo"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventario"])
app.include_router(sales.router, prefix="/api/sales", tags=["Ventas POS"])
app.include_router(crm.router, prefix="/api/customers", tags=["CRM Clientes"])
app.include_router(cash.router, prefix="/api/cash", tags=["Corte de Caja"])

# --- 3. Ruta Principal (El Frontend) ---
@app.get("/")
def read_root(request: Request):
    # Busca el archivo 'index.html' en la carpeta app/templates
    return templates.TemplateResponse("index.html", {"request": request})