"""
Migration Integrity Test — P0.3
───────────────────────────────
Executes migration 756afe1af465 for real (via Alembic Operations) against an
on-disk SQLite database and verifies the six defects stay fixed:

1. ix_api_keys_key_hash is UNIQUE
2. api_keys.created_by is a FK → students.id
3. system_settings.updated_at has a server default (raw INSERT works)
4. No Postgres-only functions (the whole upgrade runs on SQLite)
5. allowed_skills is JSON (JSONB on Postgres)
6. The system_settings singleton row (id=1) is seeded

Also checks upgrade → downgrade → upgrade round-trip and ORM/DB parity.
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql

from app.db.session import Base

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261019_1722_756afe1af465_add_email_verification_fields_to_user.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_756afe1af465", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine: sa.Engine, fn_name: str) -> None:
    migration = _load_migration()
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            getattr(migration, fn_name)()


@pytest.fixture
def sqlite_engine(tmp_path: Path):
    """SQLite DB containing the minimal pre-migration `students` table."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")

    @sa.event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE students (id CHAR(32) PRIMARY KEY, email VARCHAR(255) NOT NULL)"
        )
    yield engine
    engine.dispose()


@pytest.fixture
def migrated_engine(sqlite_engine: sa.Engine) -> sa.Engine:
    _run(sqlite_engine, "upgrade")
    return sqlite_engine


# ── Defect-specific checks ─────────────────────────────────────────────────


def test_api_keys_key_hash_is_unique(migrated_engine: sa.Engine) -> None:
    """P0.3 #1: duplicate hashes would make scalar_one_or_none() raise."""
    indexes = sa.inspect(migrated_engine).get_indexes("api_keys")
    key_hash_idx = next((i for i in indexes if i["column_names"] == ["key_hash"]), None)
    assert key_hash_idx is not None, "api_keys must have an index on key_hash"
    assert bool(key_hash_idx["unique"]) is True, "api_keys.key_hash index MUST be unique"


def test_api_keys_created_by_is_fk_to_students(migrated_engine: sa.Engine) -> None:
    """P0.3 #2."""
    fks = sa.inspect(migrated_engine).get_foreign_keys("api_keys")
    fk = next((f for f in fks if f["constrained_columns"] == ["created_by"]), None)
    assert fk is not None, "api_keys.created_by must be a foreign key"
    assert fk["referred_table"] == "students"
    assert fk["referred_columns"] == ["id"]

    # Enforced: an orphan created_by is rejected.
    with pytest.raises(sa.exc.IntegrityError):
        with migrated_engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO api_keys (id, name, key_hash, key_prefix, created_by) "
                    "VALUES (:id, 'k', 'h', 'p', :owner)"
                ),
                {"id": uuid.uuid4().hex, "owner": uuid.uuid4().hex},
            )


def test_system_settings_updated_at_has_server_default(migrated_engine: sa.Engine) -> None:
    """P0.3 #3 + #4: raw INSERT without updated_at must succeed (on SQLite too)."""
    with migrated_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO system_settings (id) VALUES (2)"))
        updated_at = conn.execute(
            sa.text("SELECT updated_at FROM system_settings WHERE id = 2")
        ).scalar_one()
    assert updated_at is not None


def test_api_keys_timestamps_have_server_default(migrated_engine: sa.Engine) -> None:
    """P0.3 #4: CURRENT_TIMESTAMP default works on a non-Postgres dialect."""
    owner = uuid.uuid4().hex
    with migrated_engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO students (id, email) VALUES (:id, 'a@b.c')"), {"id": owner})
        conn.execute(
            sa.text(
                "INSERT INTO api_keys (id, name, key_hash, key_prefix, created_by) "
                "VALUES (:id, 'k', 'h', 'p', :owner)"
            ),
            {"id": uuid.uuid4().hex, "owner": owner},
        )
        row = conn.execute(
            sa.text("SELECT created_at, updated_at, is_active, total_requests FROM api_keys")
        ).one()
    assert row.created_at is not None and row.updated_at is not None
    assert bool(row.is_active) is True
    assert row.total_requests == 0


def test_allowed_skills_is_json(migrated_engine: sa.Engine) -> None:
    """P0.3 #5: JSON on SQLite, JSONB on Postgres."""
    cols = {c["name"]: c for c in sa.inspect(migrated_engine).get_columns("api_keys")}
    assert isinstance(cols["allowed_skills"]["type"], sa.JSON)

    pg_type = _load_migration()._jsonb_or_json().compile(dialect=postgresql.dialect())
    assert pg_type == "JSONB"


def test_system_settings_singleton_seeded(migrated_engine: sa.Engine) -> None:
    """P0.3 #6: seed row must exist with defaults."""
    with migrated_engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT default_new_user_credits, daily_free_credits, credits_per_message, updated_at "
                "FROM system_settings WHERE id = 1"
            )
        ).one_or_none()
    assert row is not None, "system_settings seed row (id=1) must be inserted by the migration"
    assert (row.default_new_user_credits, row.daily_free_credits, row.credits_per_message) == (300, 300, 1)
    assert row.updated_at is not None


def test_student_verification_columns_added(migrated_engine: sa.Engine) -> None:
    cols = {c["name"] for c in sa.inspect(migrated_engine).get_columns("students")}
    assert {"is_verified", "verification_code", "verification_expires_at", "verification_attempts"} <= cols


# ── Round-trip ──────────────────────────────────────────────────────────────


def test_upgrade_downgrade_upgrade_round_trip(migrated_engine: sa.Engine) -> None:
    _run(migrated_engine, "downgrade")
    insp = sa.inspect(migrated_engine)
    tables = set(insp.get_table_names())
    assert "api_keys" not in tables and "system_settings" not in tables
    assert "is_verified" not in {c["name"] for c in insp.get_columns("students")}

    _run(migrated_engine, "upgrade")
    tables = set(sa.inspect(migrated_engine).get_table_names())
    assert {"api_keys", "system_settings"} <= tables


# ── ORM ↔ schema parity ─────────────────────────────────────────────────────


def test_orm_models_match_migration() -> None:
    from app.models.api_key import APIKey
    from app.models.system_settings import SystemSettings

    api_keys = APIKey.__table__
    assert api_keys.c.key_hash.unique is True
    fk_targets = {fk.target_fullname for fk in api_keys.c.created_by.foreign_keys}
    assert fk_targets == {"students.id"}
    assert isinstance(api_keys.c.allowed_skills.type, sa.JSON)

    settings_tbl = SystemSettings.__table__
    assert settings_tbl.c.updated_at.server_default is not None
    assert settings_tbl.c.updated_at.nullable is False


@pytest.mark.asyncio
async def test_all_models_have_matching_tables(engine) -> None:
    """Every SQLAlchemy model should have a matching table in the test DB."""
    async with engine.connect() as conn:
        existing = set(await conn.run_sync(lambda c: sa.inspect(c).get_table_names()))
    missing = set(Base.metadata.tables) - existing
    assert not missing, f"Models without tables: {sorted(missing)}"
