"""Encrypted profiles, audit trail, and idempotent import markers."""

import sqlalchemy as sa
from alembic import op

revision = "0001_profiles"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("pii_ciphertext", sa.Text(), nullable=False),
        sa.Column("phone_index", sa.String(64), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "marketing_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("phone_index", name="uq_profiles_phone_index"),
    )
    op.create_table(
        "profile_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_profile_audit_created_at", "profile_audit", ["created_at"]
    )
    op.create_table(
        "imported_profiles", sa.Column("user_id", sa.Uuid(), primary_key=True)
    )


def downgrade() -> None:
    op.drop_table("imported_profiles")
    op.drop_table("profile_audit")
    op.drop_table("profiles")
