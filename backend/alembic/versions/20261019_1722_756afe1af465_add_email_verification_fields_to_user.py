# alembic/script.py.mako — template for migration files
"""add email verification fields to user + developer panel

Revision ID: 756afe1af465
Revises: a7f3d91c2b48
Create Date: 2026-10-19 17:22:57.954114

P0.3 fixes applied (see docs/ERROR_LOG.md E-P03-1 … E-P03-6):
1. ix_api_keys_key_hash is now UNIQUE (prevents MultipleResultsFound).
2. api_keys.created_by is UUID with FK → students.id (ON DELETE CASCADE).
3. system_settings.updated_at has a server_default.
4. Postgres-only now() replaced with dialect-agnostic CURRENT_TIMESTAMP;
   boolean defaults use sa.true()/sa.false() instead of string literals.
5. allowed_skills uses JSONB on Postgres (JSON on SQLite) instead of Text.
6. Singleton system_settings row (id=1) seeded idempotently.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '756afe1af465'
down_revision: Union[str, None] = 'a7f3d91c2b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NOW = sa.text('CURRENT_TIMESTAMP')


def _jsonb_or_json() -> sa.types.TypeEngine:
    """JSONB on Postgres, generic JSON elsewhere (SQLite)."""
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def _uuid() -> sa.types.TypeEngine:
    """Native UUID on Postgres, CHAR(32) on SQLite — matches students.id."""
    return sa.Uuid(as_uuid=True)


def upgrade() -> None:
    # ── 1. api_keys table (developer panel) ────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', _uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('max_credits_per_day', sa.Integer(), nullable=True),
        sa.Column('allowed_skills', _jsonb_or_json(), nullable=True),          # FIX 5
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', _uuid(), nullable=False),                      # FIX 2
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),  # FIX 4
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),  # FIX 4
        sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys')),
        sa.ForeignKeyConstraint(
            ['created_by'], ['students.id'],
            name=op.f('fk_api_keys_created_by_students'),
            ondelete='CASCADE',
        ),                                                                      # FIX 2
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)  # FIX 1
    op.create_index(op.f('ix_api_keys_created_by'), 'api_keys', ['created_by'], unique=False)

    # ── 2. system_settings singleton (default credits control) ────────
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('default_new_user_credits', sa.Integer(), server_default='300', nullable=False),
        sa.Column('daily_free_credits', sa.Integer(), server_default='300', nullable=False),
        sa.Column('credits_per_message', sa.Integer(), server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=_NOW, nullable=False),  # FIX 3
        sa.PrimaryKeyConstraint('id', name=op.f('pk_system_settings')),
    )

    # FIX 6: seed the singleton row. ON CONFLICT … DO NOTHING is supported by
    # both PostgreSQL and SQLite (>= 3.24), so one statement covers both.
    op.execute(
        "INSERT INTO system_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    )

    # ── 3. Student email-verification fields ──────────────────────────
    op.add_column('students', sa.Column('is_verified', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('students', sa.Column('verification_code', sa.String(length=255), nullable=True))
    op.add_column('students', sa.Column('verification_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('students', sa.Column('verification_attempts', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    # batch_alter_table → works on SQLite (no native DROP COLUMN pre-3.35) and
    # degrades to plain ALTER TABLE on Postgres.
    with op.batch_alter_table('students') as batch_op:
        batch_op.drop_column('verification_attempts')
        batch_op.drop_column('verification_expires_at')
        batch_op.drop_column('verification_code')
        batch_op.drop_column('is_verified')

    op.drop_table('system_settings')

    op.drop_index(op.f('ix_api_keys_created_by'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
