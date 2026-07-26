"""Test fixtures: real Postgres (docker locally, service container in CI).

Env contract: TEST_DB_HOST/TEST_DB_PORT point at a throwaway Postgres with
fixed credentials (user app / pass test / db app_test). Defaults match the
container `scripts/dev.sh` starts (host port 5433, so it never collides with
a real local Postgres on 5432); CI's service container sets TEST_DB_PORT=5432.
The DB_* vars the app reads are overwritten BEFORE the app is imported.
"""

import os
from pathlib import Path

import pytest

os.environ["DB_HOST"] = os.environ.get("TEST_DB_HOST", "localhost")
os.environ["DB_PORT"] = os.environ.get("TEST_DB_PORT", "5433")
os.environ["DB_NAME"] = "app_test"
os.environ["DB_USER"] = "app"
os.environ["DB_PASSWORD"] = "test"

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_TEST_ENGINE = None


def test_engine():
    global _TEST_ENGINE
    if _TEST_ENGINE is None:
        _TEST_ENGINE = sa.create_engine(
            f"postgresql+psycopg://app:test@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/app_test"
        )
    return _TEST_ENGINE


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Apply every alembic migration once per session — tests run against the
    real schema, exactly like the container entrypoint does in production."""
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def client(migrated_db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_tables(migrated_db):
    """Truncate every app table after each test so tests never depend on each
    other's data. alembic_version and app_meta (the template's example table)
    survive; add any other seed tables to the exclusion list."""
    yield
    with test_engine().begin() as conn:
        rows = (
            conn.execute(
                sa.text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename NOT IN ('alembic_version', 'app_meta')"
                )
            )
            .scalars()
            .all()
        )
        if rows:
            conn.execute(sa.text("TRUNCATE " + ", ".join(f'"{t}"' for t in rows) + " CASCADE"))
