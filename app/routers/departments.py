from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
# Asegúrate de tener el modelo Department en app/models/__init__.py o donde corresponda
# Si no tienes modelo Department aún, comenta este archivo y su línea en main.py
from app.models import Category  # Usamos Category como Departamento para consistencia con Productos
from app.schemas.departments import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    # Mapeamos Category -> DepartmentResponse
    # DepartmentResponse espera id, name, description
    return db.query(Category).all()

@router.post("/", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_dept = Category(name=dept.name, description=dept.description)
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept

@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, dept_in: DepartmentUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    dept = db.query(Category).filter(Category.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    
    if dept_in.name is not None:
        dept.name = dept_in.name
    if dept_in.description is not None:
        dept.description = dept_in.description
        
    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    dept = db.query(Category).filter(Category.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
        
    # Optional: Check if used in products before delete, or let FK constraints handle/fail
    db.delete(dept)
    db.commit()
    return {"status": "ok"}