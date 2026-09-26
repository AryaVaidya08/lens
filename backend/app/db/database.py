"""
SQLite engine + session setup.

One engine, one SQLite file, no external DB service — see the "explicit
scope decisions" in docs/architecture.md.

Owned by: Backend & data lane.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO: implement — point this at app.config.settings.database_url
engine = create_engine("sqlite:///./hcp.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a DB session per request.

    TODO: implement
    """
    # TODO: implement
    raise NotImplementedError
