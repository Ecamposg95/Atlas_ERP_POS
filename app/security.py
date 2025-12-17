from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# Importamos la configuración de DB y CRUD de usuarios
from app.database import get_db
from app.models import User
from app.crud import users as crud_users

# --- Configuración ---
# EN PRODUCCIÓN: Cambia esto por una variable de entorno
SECRET_KEY = "super-secret-key-atlas-erp-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12 # 12 Horas

# Configuración de Hashing (Bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de autenticación para FastAPI (apunta al endpoint de login)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Funciones de Hashing (PIN/Password) ---

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verifica si el PIN ingresado coincide con el hash guardado."""
    return pwd_context.verify(plain_pin, hashed_pin)

def get_pin_hash(pin: str) -> str:
    """Genera el hash seguro de un PIN."""
    return pwd_context.hash(pin)

# --- Funciones JWT ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera un Token JWT firmado."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencia: Obtener Usuario Actual ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Valida el token y recupera el usuario de la BD.
    Se usa en endpoints protegidos: current_user: User = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Buscamos el usuario en la BD
    user = crud_users.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
        
    return user