from sqlalchemy.orm import Session
from app.models import User

def get_user_by_username(db: Session, username: str):
    """Busca un usuario activo por su username."""
    return db.query(User).filter(User.username == username, User.is_active == True).first()