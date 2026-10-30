"""Test streaming video (UC004) và tìm kiếm/lọc theo nhãn (UC009)."""

from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Label, UserRole, Video, VideoLabel, VideoStatus
from app.services.ai_service import confidence_level


def ensure_label(name: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(Label).where(Label.name == name)) is None:
            db.add(Label(name=name))
            db.commit()


def attach_label(video_id: str, name: str, confidence: float = 0.9) -> None:
    ensure_label(name)
    with SessionLocal() as db:
        label = db.scalar(select(Label).where(Label.name == name))
        db.add(
            VideoLabel(
                video_id=UUID(video_id),
                label_id=label.id,
                confidence=confidence,
                level=confidence_level(confidence),
            )
        )
        db.commit()


def test_stream_published_video_supports_range(client, login, seed_video):
    video = seed_video(status=VideoStatus.published)
    headers = login(video.email)
    url = f"/api/v1/videos/{video.video_id}/stream"

    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers.get("accept-ranges") == "bytes"

    ranged = client.get(url, headers={**headers, "Range": "bytes=0-3"})
    assert ranged.status_code == 206
    assert len(ranged.content) == 4


def test_stream_visibility_rules(client, register, login, seed_video):
    pending = seed_video(status=VideoStatus.pending_review)
    stranger = register("stranger-stream@example.com")
    owner = login(pending.email)
    moderator = register("mod-stream@example.com", role=UserRole.moderator)
    url = f"/api/v1/videos/{pending.video_id}/stream"

    # Video chưa đăng: người lạ 404, chủ video và moderator xem được.
    assert client.get(url, headers=stranger).status_code == 404
    assert client.get(url, headers=owner).status_code == 200
    assert client.get(url, headers=moderator).status_code == 200

    # Video không tồn tại và video chưa bị lưu file.
    assert (
        client.get(
            "/api/v1/videos/00000000-0000-0000-0000-000000000000/stream", headers=stranger
        ).status_code
        == 404
    )
    missing = seed_video(write_file=False)
    assert client.get(f"/api/v1/videos/{missing.video_id}/stream", headers=login(missing.email)).status_code == 404
    assert client.get(url).status_code == 401


def test_search_filters_by_label_exclude_label_and_caption(
    client, register, login, seed_video
):
    adult = seed_video(caption="clip có yếu tố người lớn")
    attach_label(str(adult.video_id), "Adult")
    normal = seed_video(caption="clip bình thường")
    attach_label(str(normal.video_id), "Safe")
    pending = seed_video(caption="chờ kiểm duyệt", status=VideoStatus.pending_review)

    headers = register("searcher@example.com")
    base = "/api/v1/videos"

    by_label = client.get(f"{base}/search?label=Adult", headers=headers).json()
    assert {item["id"] for item in by_label} == {str(adult.video_id)}

    excluded = client.get(f"{base}/search?exclude_label=Adult", headers=headers).json()
    excluded_ids = {item["id"] for item in excluded}
    assert str(adult.video_id) not in excluded_ids
    assert str(normal.video_id) in excluded_ids

    by_caption = client.get(f"{base}/search?q=bình thường", headers=headers).json()
    assert {item["id"] for item in by_caption} == {str(normal.video_id)}

    # Video của người khác đang chờ kiểm duyệt không lọt vào kết quả.
    all_ids = {item["id"] for item in client.get(f"{base}/search", headers=headers).json()}
    assert str(pending.video_id) not in all_ids
    # ... nhưng chủ của nó vẫn thấy video của mình.
    owner_view = {item["id"] for item in client.get(f"{base}/search", headers=login(pending.email)).json()}
    assert str(pending.video_id) in owner_view

    # Kèm nhãn và giới hạn số lượng.
    limited = client.get(f"{base}/search?limit=1", headers=headers).json()
    assert len(limited) == 1
    assert client.get(f"{base}/search?limit=0", headers=headers).status_code == 422

    item = next(entry for entry in by_label if entry["id"] == str(adult.video_id))
    assert [label["name"] for label in item["labels"]] == ["Adult"]
    assert item["owner_display_name"] == "Owner"

    assert client.get(f"{base}/search").status_code == 401
