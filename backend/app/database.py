from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .core.config import config

# Handle SQLite specific config
engine_kwargs = {}
if config.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Use the effective DB URL
engine = create_engine(config.DB_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
