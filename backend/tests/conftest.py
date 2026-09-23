from __future__ import annotations

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory


@pytest.fixture(scope="session", autouse=True)
def isolated_postgresql_database():
    """Run every test session in a disposable PostgreSQL database."""
    original_env = os.environ.get("ASSETGUARD_DATABASE_URL")
    base_url = get_settings().database_url
    database_name = f"assetguard_test_{uuid4().hex}"
    parsed = create_engine(base_url).url
    admin_url = parsed.set(database="postgres")
    test_url = parsed.set(database=database_name)
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')

    os.environ["ASSETGUARD_DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    get_session_factory.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    try:
        yield
    finally:
        factory = get_session_factory()
        factory.kw["bind"].dispose()
        get_session_factory.cache_clear()
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{database_name}' AND pid <> pg_backend_pid()"
            )
            connection.exec_driver_sql(f'DROP DATABASE "{database_name}"')
        admin_engine.dispose()
        if original_env is None:
            os.environ.pop("ASSETGUARD_DATABASE_URL", None)
        else:
            os.environ["ASSETGUARD_DATABASE_URL"] = original_env
        get_settings.cache_clear()
