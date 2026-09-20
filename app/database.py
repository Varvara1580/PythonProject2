from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = 'sqlite:///finance.db'
engine = create_engine(DATABASE_URL)
SESSION_LOCAL = sessionmaker(bind = engine)

class Base(DeclarativeBase):
    pass

def get_db():
    with SESSION_LOCAL() as db:
        yield db
