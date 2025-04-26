from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.config_server import get_config
from models import Base


CONFIG_FILE_PATH = 'server/http_server/config/config.ini'

config = get_config(CONFIG_FILE_PATH)
database_url = config["database"]["database_url"]

engine = create_engine(database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_table():
    Base.metadata.create_all(bind=engine)


def disconnect_db():
    SessionLocal.close_all()
    engine.dispose()


def create_session() -> Session:
    return SessionLocal()


def get_session_factory() -> sessionmaker:
    return SessionLocal


def get_db():
    db = create_session()
    try:
        yield db
    finally:
        db.close()