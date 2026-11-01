"""Public search queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import InvalidInputError
from app.models import Label, User, Video, VideoLabel, VideoStatus

SEARCH_LIMIT = 50


def search_videos_by_tag(db: Session, tag: str) -> list[Video]:
    tag = tag.strip()
    if not tag:
        raise InvalidInputError("Tag không được để trống")
    query = (
        select(Video)
        .join(VideoLabel, VideoLabel.video_id == Video.id)
        .join(Label, Label.id == VideoLabel.label_id)
        .options(selectinload(Video.owner))
        .where(
            Video.status == VideoStatus.published,
            Video.is_deleted.is_(False),
            Label.is_active.is_(True),
            Label.name.ilike(f"%{tag}%"),
        )
        .distinct()
        .order_by(Video.created_at.desc())
        .limit(SEARCH_LIMIT)
    )
    return list(db.scalars(query))


def search_users(db: Session, query_text: str) -> list[User]:
    query_text = query_text.strip()
    if not query_text:
        raise InvalidInputError("Từ khóa tìm kiếm không được để trống")
    query = select(User).where(User.is_active.is_(True))
    if "#" in query_text:
        display_name, discriminator = query_text.rsplit("#", 1)
        if not discriminator.isdigit() or len(discriminator) != 4:
            raise InvalidInputError("Discriminator phải gồm 4 chữ số")
        if display_name:
            query = query.where(
                User.display_name == display_name,
                User.discriminator == discriminator,
            )
        else:
            query = query.where(User.discriminator == discriminator)
    else:
        query = query.where(User.display_name.ilike(f"%{query_text}%"))
    return list(
        db.scalars(
            query.order_by(User.display_name.asc(), User.discriminator.asc()).limit(
                SEARCH_LIMIT
            )
        )
    )
