from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
# Asegúrate de tener el modelo Department en app/models/__init__.py o donde corresponda
# Si no tienes modelo Department aún, comenta este archivo y su línea en main.py
from app.models import Department 
from app.schemas.departments import DepartmentCreate, DepartmentResponse
from app.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.post("/", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_dept = Department(**dept.dict())
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept