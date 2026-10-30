from datetime import datetime, timezone

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["Base", "utcnow"]
