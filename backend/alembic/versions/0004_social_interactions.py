"""add social interaction tables

Revision ID: 0004_social_interactions
Revises: 0003_profile_discriminator
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_social_interactions"
down_revision = "0003_profile_discriminator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_likes",
        sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "video_bookmarks",
        sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "user_follows",
        sa.Column("follower_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("following_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("follower_id <> following_id", name="ck_user_follows_no_self"),
    )
    op.create_table(
        "video_comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_video_comments_video_id", "video_comments", ["video_id"])
    op.create_index("ix_video_comments_author_id", "video_comments", ["author_id"])
    op.create_index("ix_video_comments_is_deleted", "video_comments", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_video_comments_is_deleted", table_name="video_comments")
    op.drop_index("ix_video_comments_author_id", table_name="video_comments")
    op.drop_index("ix_video_comments_video_id", table_name="video_comments")
    op.drop_table("video_comments")
    op.drop_table("user_follows")
    op.drop_table("video_bookmarks")
    op.drop_table("video_likes")
