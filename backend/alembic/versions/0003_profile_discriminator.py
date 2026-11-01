"""add profile fields and display discriminator

Revision ID: 0003_profile_discriminator
Revises: 0002_session_appeals
"""

import secrets

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision = "0003_profile_discriminator"
down_revision = "0002_session_appeals"
branch_labels = None
depends_on = None


def _allocate(display_name: str, used: set[str]) -> str:
    for _ in range(10000):
        candidate = f"{secrets.randbelow(9999) + 1:04d}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise RuntimeError(f"No discriminator available for {display_name!r}")


def upgrade() -> None:
    op.add_column("users", sa.Column("discriminator", sa.String(4), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(2048), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        text("SELECT id, display_name FROM users ORDER BY display_name, id")
    ).mappings()
    used_by_name: dict[str, set[str]] = {}
    for row in rows:
        used = used_by_name.setdefault(row["display_name"], set())
        discriminator = _allocate(row["display_name"], used)
        connection.execute(
            text("UPDATE users SET discriminator = :discriminator WHERE id = :id"),
            {"discriminator": discriminator, "id": row["id"]},
        )

    op.alter_column("users", "discriminator", nullable=False)
    op.create_unique_constraint(
        "uq_users_display_name_discriminator",
        "users",
        ["display_name", "discriminator"],
    )
    op.create_index("ix_users_discriminator", "users", ["discriminator"])


def downgrade() -> None:
    op.drop_index("ix_users_discriminator", table_name="users")
    op.drop_constraint(
        "uq_users_display_name_discriminator", "users", type_="unique"
    )
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "bio")
    op.drop_column("users", "discriminator")
