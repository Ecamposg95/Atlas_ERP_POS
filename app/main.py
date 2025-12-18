from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base 
from app.routers import auth, products, inventory, sales, crm # <--- Agregar crm
# Importamos los routers que acabamos de crear
from app.routers import auth, products

# Inicializar Base de Datos
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Atlas ERP & POS",
    description="API unificada para administración empresarial, inventarios y punto de venta.",
    version="1.0.0-alpha"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AQUI ESTA LA MAGIA: Registramos los endpoints ---
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(products.router, prefix="/api/products", tags=["Catálogo"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventario"]) 
app.include_router(sales.router, prefix="/api/sales", tags=["Ventas POS"]) 
app.include_router(crm.router, prefix="/api/customers", tags=["CRM Clientes"]) 
@app.get("/")
def health_check():
    return {
        "system": "Atlas ERP & POS Core",
        "status": "Online",
        "version": "1.0.0"
    }