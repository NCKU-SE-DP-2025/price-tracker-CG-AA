from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Database:
    def __init__(self, db_url: str = "sqlite:///news_database.db", echo: bool = True):
        self.engine = create_engine(db_url, echo=echo)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self._create_tables()

    def _create_tables(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


# Global database instance
db_instance = Database()


# Dependency for FastAPI or other frameworks
def get_db():
    with db_instance.get_session() as session:
        yield session
