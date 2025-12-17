from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ledger_user:ledger_password@localhost:5432/financial_ledger")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for database sessions outside of request handling"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
