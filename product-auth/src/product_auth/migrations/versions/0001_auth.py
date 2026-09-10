"""Independent user, session and one-time login tables."""

# 0001_auth.py — первая миграция: создаёт физические таблицы auth_users,
# auth_sessions и auth_login_flows в базе данных.

import sqlalchemy as sa
from alembic import op

revision = "0001_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("telegram_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("telegram_id", sa.String(32)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.Integer, nullable=False),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("auth_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.Integer, nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table(
        "auth_login_flows",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("verifier", sa.String(128), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.Integer, nullable=False),
    )
    op.create_index(
        "ix_auth_login_flows_expires_at", "auth_login_flows", ["expires_at"]
    )


def downgrade():
    op.drop_table("auth_login_flows")
    op.drop_table("auth_sessions")
    op.drop_table("auth_users")
