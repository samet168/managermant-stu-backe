from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
from app.domain.models import Base

# SQLAlchemy Engine & SessionLocal
# Normalize postgres:// to postgresql:// if needed
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_connection():
    """
    Returns an active direct psycopg2 connection with RealDictCursor.
    Maintained for backward compatibility.
    """
    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

def init_db():
    """
    Initializes PostgreSQL tables using SQLAlchemy Base metadata
    and ensures compatibility columns like hashed_password exist.
    """
    Base.metadata.create_all(bind=engine)
    
    # Add hashed_password column if it does not exist yet
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);
    """)
    cur.close()
    conn.close()
    print("[POSTGRESQL_SUCCESS] Neon PostgreSQL tables verified/initialized via SQLAlchemy!")

if __name__ == "__main__":
    init_db()
