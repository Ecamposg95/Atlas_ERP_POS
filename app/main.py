# app/main.py
from fastapi import FastAPI
from app.models import Base
from app.database import engine

# Crear tablas automáticamente (solo dev)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Atlas ERP & POS")

@app.get("/")
def root():
    return {"system": "Atlas ERP", "status": "Online"}