"""PostgreSQL session boundary for AssetGuard modules."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from assetguard.infrastructure.config import get_settings


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a short-lived database session for one HTTP request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()

