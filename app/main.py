from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base 

# Routers
from app.routers import auth, products, inventory, sales, crm, cash, printer # <--- AGREGADO

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Atlas ERP & POS")

# --- Archivos Estáticos y Templates ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
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
app.include_router(printer.router, prefix="/api/printer", tags=["Impresora"]) # <--- AGREGADO

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})