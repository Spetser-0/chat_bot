"""Phase 7: add device_fingerprint to referrals (Lesson 7.4 anti-fraud).

Revision ID: a7f3d91c2b48
Revises: f2029e7b9acb
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7f3d91c2b48'
down_revision: Union[str, None] = 'f2029e7b9acb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'referrals',
        sa.Column('device_fingerprint', sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f('ix_referrals_device_fingerprint'),
        'referrals', ['device_fingerprint'], unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_referrals_device_fingerprint'), table_name='referrals')
    op.drop_column('referrals', 'device_fingerprint')
