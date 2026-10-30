from enum import Enum


class UserRole(str, Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class VideoStatus(str, Enum):
    processing = "processing"
    pending_review = "pending_review"
    published = "published"
    rejected = "rejected"
    failed = "failed"
    deleted = "deleted"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ReportStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    rejected = "rejected"


class ModerationAction(str, Enum):
    approve = "approve"
    reject = "reject"
