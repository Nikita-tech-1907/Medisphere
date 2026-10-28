import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Configurable Database URL: defaults to persistent SQLite in the backend directory
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BACKEND_DIR, "medisphere.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

# If PostgreSQL URL uses deprecated postgres://, update to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Verify active database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection successful"
    except Exception as e:
        return False, str(e)
