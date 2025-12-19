from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Importaciones de tu proyecto
from app.database import get_db
from app.models import User
# Asegúrate de que UserUpdate esté en tu schema (ya lo agregamos antes)
from app.schemas.users import UserCreate, UserRead, UserUpdate 
from app.security import get_current_user, get_password_hash

router = APIRouter()

# --- 1. LEER TODOS (READ) ---
@router.get("/", response_model=List[UserRead])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Opcional: Solo admin ve todos, cajeros solo ven su perfil (ajustar según necesidad)
    return db.query(User).offset(skip).limit(limit).all()

# --- 2. LEER USUARIO ACTUAL (ME) ---
@router.get("/me", response_model=UserRead)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- 3. LEER POR ID ---
@router.get("/{user_id}", response_model=UserRead)
def read_user_by_id(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# --- 4. CREAR USUARIO (CREATE) ---
@router.post("/", response_model=UserRead)
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validar permisos (Solo Admin crea usuarios)
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="No autorizado")

    # Validar duplicados
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    # Hashear password
    hashed_password = get_password_hash(user.password)
    
    new_user = User(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        hashed_password=hashed_password,
        branch_id=user.branch_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 5. ACTUALIZAR USUARIO (UPDATE) - CAMBIO DE PIN, ROL, NOMBRE ---
@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, 
    user_in: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza datos del usuario. Si envías 'password', se actualiza el PIN/Pass encriptado.
    """
    # 1. Buscar usuario
    user_db = db.query(User).filter(User.id == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2. Permisos: Solo Admin o el mismo usuario pueden editar
    # (Ajusta esta lógica según tus roles: admin, cajero, etc.)
    # if current_user.role != "admin" and current_user.id != user_id:
    #     raise HTTPException(status_code=403, detail="No tienes permisos para editar este usuario")

    # 3. Filtrar datos enviados (excluir nulos)
    update_data = user_in.dict(exclude_unset=True)

    # 4. Manejo especial del Password (PIN)
    if 'password' in update_data:
        password_raw = update_data.pop('password')
        # Solo hashear si mandaron algo (no string vacío)
        if password_raw: 
            user_db.hashed_password = get_password_hash(password_raw)

    # 5. Actualizar resto de campos (nombre, rol, sucursal, etc.)
    for field, value in update_data.items():
        # Validar que el usuario (modelo) tenga ese atributo antes de asignarlo
        if hasattr(user_db, field):
            setattr(user_db, field, value)

    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return user_db

# --- 6. ELIMINAR/DESACTIVAR (SOFT DELETE) ---
# Cambiamos response_model=UserRead para devolver los datos del usuario afectado
@router.delete("/{user_id}", response_model=UserRead) 
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Realiza un borrado lógico (Soft Delete).
    Desactiva al usuario y devuelve sus datos actualizados.
    """
    # Validar permisos (descomentar cuando tengas roles listos)
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="No tienes permisos para realizar esta acción")

    user_db = db.query(User).filter(User.id == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # LÓGICA DE SOFT DELETE
    if not user_db.is_active:
        raise HTTPException(status_code=400, detail="Este usuario ya estaba desactivado")

    user_db.is_active = False  # Cambiamos la bandera a inactivo
    
    db.commit()
    db.refresh(user_db) # Recargamos para obtener el estado actualizado
    
    # Retornamos el objeto usuario completo. 
    # El frontend podrá leer user_db.username o user_db.full_name para mostrar a quién borró.
    return user_db