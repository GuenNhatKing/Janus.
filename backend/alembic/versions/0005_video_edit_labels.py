"""add video visibility, comment settings and label sources

Revision ID: 0005_video_edit_labels
Revises: 0004_social_interactions
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_video_edit_labels"
down_revision = "0004_social_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column("visibility", sa.String(10), nullable=False, server_default="public"),
    )
    op.add_column(
        "videos",
        sa.Column("allow_comments", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint(
        "ck_videos_visibility",
        "videos",
        "visibility IN ('public', 'private')",
    )
    op.add_column(
        "video_labels",
        sa.Column("source", sa.String(10), nullable=False, server_default="ai"),
    )
    op.create_check_constraint(
        "ck_video_labels_source",
        "video_labels",
        "source IN ('ai', 'user')",
    )
    op.create_index("ix_video_labels_source", "video_labels", ["source"])
    op.alter_column("videos", "visibility", server_default=None)
    op.alter_column("videos", "allow_comments", server_default=None)
    op.alter_column("video_labels", "source", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_video_labels_source", table_name="video_labels")
    op.drop_constraint("ck_video_labels_source", "video_labels", type_="check")
    op.drop_column("video_labels", "source")
    op.drop_constraint("ck_videos_visibility", "videos", type_="check")
    op.drop_column("videos", "allow_comments")
    op.drop_column("videos", "visibility")
