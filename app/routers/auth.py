from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm # <--- IMPORTANTE
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.security import verify_pin, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.auth import Token
from app.crud.users import get_user_by_username

router = APIRouter()

# Eliminamos LoginRequest y usamos el estándar OAuth2PasswordRequestForm
@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), # <--- ESTO CAMBIA TODO
    db: Session = Depends(get_db)
):
    # 1. Buscar usuario
    user = get_user_by_username(db, username=form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Verificar PIN
    # NOTA: OAuth2 siempre envía los campos como 'username' y 'password'.
    # Nosotros usaremos el campo 'password' para recibir el PIN.
    if not verify_pin(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Generar Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}