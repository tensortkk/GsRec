from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from tfe import settings


Base = declarative_base()


def init_db(engine):
    Base.metadata.create_all(bind=engine)


def drop_db(engine):
    Base.metadata.drop_all(bind=engine)


def get_engine():
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=True,
        encoding="utf8",
        pool_size=100,
        pool_pre_ping=True,
        pool_recycle=600)
    return engine


db_session = sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=get_engine(),
    expire_on_commit=False
)


@contextmanager
def session_scope():
    session = db_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
