"""create MVP tables

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("email", sa.String(320), nullable=False), sa.Column("display_name", sa.String(120), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.Enum("user", "moderator", "admin", name="userrole"), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("email"))
    op.create_table("labels", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(80), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.UniqueConstraint("name"))
    op.create_table("videos", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False), sa.Column("mime_type", sa.String(100), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("caption", sa.Text()), sa.Column("status", sa.Enum("processing", "pending_review", "published", "rejected", "failed", "deleted", name="videostatus"), nullable=False), sa.Column("is_deleted", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("storage_path"))
    op.create_table("ai_jobs", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id"), nullable=False), sa.Column("status", sa.Enum("pending", "running", "succeeded", "failed", name="jobstatus"), nullable=False), sa.Column("error_message", sa.Text()), sa.Column("transcript", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_table("video_labels", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id"), nullable=False), sa.Column("label_id", sa.Uuid(), sa.ForeignKey("labels.id"), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("level", sa.String(10), nullable=False), sa.UniqueConstraint("video_id", "label_id", name="uq_video_label"))
    op.create_table("moderation_reviews", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id"), nullable=False), sa.Column("moderator_id", sa.Uuid(), sa.ForeignKey("users.id")), sa.Column("action", sa.Enum("approve", "reject", name="moderationaction")), sa.Column("reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("reports", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("video_id", sa.Uuid(), sa.ForeignKey("videos.id"), nullable=False), sa.Column("reporter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("status", sa.Enum("open", "resolved", "rejected", name="reportstatus"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("video_id", "reporter_id", name="uq_video_reporter"))
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_labels_name", "labels", ["name"], unique=False)
    op.create_index("ix_videos_owner_id", "videos", ["owner_id"], unique=False)
    op.create_index("ix_videos_status", "videos", ["status"], unique=False)
    op.create_index("ix_videos_is_deleted", "videos", ["is_deleted"], unique=False)
    op.create_index("ix_ai_jobs_video_id", "ai_jobs", ["video_id"], unique=False)
    op.create_index("ix_video_labels_video_id", "video_labels", ["video_id"], unique=False)
    op.create_index("ix_video_labels_label_id", "video_labels", ["label_id"], unique=False)
    op.create_index("ix_moderation_reviews_video_id", "moderation_reviews", ["video_id"], unique=False)
    op.create_index("ix_reports_video_id", "reports", ["video_id"], unique=False)
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"], unique=False)


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_reports_reporter_id", "reports"),
        ("ix_reports_video_id", "reports"),
        ("ix_moderation_reviews_video_id", "moderation_reviews"),
        ("ix_video_labels_label_id", "video_labels"),
        ("ix_video_labels_video_id", "video_labels"),
        ("ix_ai_jobs_video_id", "ai_jobs"),
        ("ix_videos_is_deleted", "videos"),
        ("ix_videos_status", "videos"),
        ("ix_videos_owner_id", "videos"),
        ("ix_labels_name", "labels"),
        ("ix_users_email", "users"),
    ):
        op.drop_index(index_name, table_name=table_name)
    for table in ("reports", "moderation_reviews", "video_labels", "ai_jobs", "videos", "labels", "users"):
        op.drop_table(table)
    for enum_name in ("reportstatus", "moderationaction", "jobstatus", "videostatus", "userrole"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
