from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Branch
from app.schemas.branches import BranchCreate, BranchRead
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