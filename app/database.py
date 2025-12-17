from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Usaremos SQLite para desarrollo. En producción cambiará a PostgreSQL.
DATABASE_URL = "sqlite:///./atlas_erp.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} # Solo necesario para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()