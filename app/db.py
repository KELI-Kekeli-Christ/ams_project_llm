import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    db_url = os.getenv("DB_URL", "sqlite:///./ceribot.db")
    return create_engine(db_url, connect_args={"check_same_thread": False})

def get_session():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    from app import models
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
