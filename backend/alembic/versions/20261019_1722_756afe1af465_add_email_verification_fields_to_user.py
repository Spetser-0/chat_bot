# alembic/script.py.mako — template for migration files
"""add email verification fields to user

Revision ID: 756afe1af465
Revises: a7f3d91c2b48
Create Date: 2026-10-19 17:22:57.954114

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '756afe1af465'
down_revision: Union[str, None] = 'a7f3d91c2b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. API Keys table for developer panel
    op.create_table(
        'api_keys',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('max_credits_per_day', sa.Integer(), nullable=True),
        sa.Column('allowed_skills', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.Integer(), server_default='0', nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=False)

    # 2. System Settings table for default credits control
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('default_new_user_credits', sa.Integer(), server_default='300', nullable=False),
        sa.Column('daily_free_credits', sa.Integer(), server_default='300', nullable=False),
        sa.Column('credits_per_message', sa.Integer(), server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Student verification fields
    op.add_column('students', sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('students', sa.Column('verification_code', sa.String(length=255), nullable=True))
    op.add_column('students', sa.Column('verification_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('students', sa.Column('verification_attempts', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('students', 'verification_attempts')
    op.drop_column('students', 'verification_expires_at')
    op.drop_column('students', 'verification_code')
    op.drop_column('students', 'is_verified')
    op.drop_table('system_settings')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
