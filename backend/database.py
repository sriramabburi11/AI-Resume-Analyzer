import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
load_dotenv()

# Database connection URL
# Configured for PostgreSQL by default: postgresql+psycopg://user:password@localhost:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg://postgres:postgrespassword@localhost:5432/resume_analyzer"

# Normalize legacy postgres:// and postgresql:// prefixes to psycopg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

def init_engine():
    global DATABASE_URL
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    # Attempt PostgreSQL connection
    pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        with pg_engine.connect() as conn:
            pass
        return pg_engine
    except Exception as e:
        print(f"\n[DATABASE NOTICE] PostgreSQL connection failed ({e}).")
        print("[DATABASE NOTICE] Automatically using local SQLite fallback database (resume_analyzer.db) so you can test the application immediately without running a local PostgreSQL container.\n")
        DATABASE_URL = "sqlite:///./resume_analyzer.db"
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

engine = init_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency that yields a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
