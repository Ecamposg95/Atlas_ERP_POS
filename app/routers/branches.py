from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Branch
from app.schemas.branches import BranchCreate, BranchRead, BranchUpdate
from app.security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[BranchRead])
def get_branches(db: Session = Depends(get_db)):
    return db.query(Branch).all()

@router.post("/", response_model=BranchRead)
def create_branch(branch: BranchCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_branch = Branch(**branch.dict())
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch

@router.put("/{branch_id}", response_model=BranchRead)
def update_branch(branch_id: int, branch: BranchUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not db_branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    
    for key, value in branch.dict(exclude_unset=True).items():
        setattr(db_branch, key, value)
    
    db.commit()
    db.refresh(db_branch)
    return db_branch

@router.delete("/{branch_id}")
def delete_branch(branch_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not db_branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    
    db.delete(db_branch)
    db.commit()
    return {"ok": True}