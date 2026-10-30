"""Test nhãn (UC007/UC015), appeal (UC011/UC017) và admin (2.2.12/13, UC019/UC020)."""

from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Label, UserRole, VideoStatus


def ensure_label(name: str, active: bool = True) -> UUID:
    with SessionLocal() as db:
        label = db.scalar(select(Label).where(Label.name == name))
        if label is None:
            label = Label(name=name, is_active=active)
            db.add(label)
        else:
            label.is_active = active
        db.commit()
        return label.id


def attach_label(video_id: UUID, name: str, confidence: float = 0.9) -> None:
    from app.models import VideoLabel
    from app.services.ai_service import confidence_level

    ensure_label(name)
    with SessionLocal() as db:
        label = db.scalar(select(Label).where(Label.name == name))
        db.add(
            VideoLabel(
                video_id=video_id,
                label_id=label.id,
                confidence=confidence,
                level=confidence_level(confidence),
            )
        )
        db.commit()


def test_owner_confirms_labels(client, login, seed_video):
    ensure_label("Adult")
    video = seed_video()
    headers = login(video.email)

    response = client.post(
        f"/api/v1/videos/{video.video_id}/labels/confirm",
        json={"labels": [{"name": "Adult", "confidence": 0.87}]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Adult"
    assert response.json()[0]["level"] == "HIGH"

    # Người khác không xác nhận được nhãn của video này.
    other = login(seed_video().email)
    assert (
        client.post(
            f"/api/v1/videos/{video.video_id}/labels/confirm",
            json={"labels": [{"name": "Adult", "confidence": 0.5}]},
            headers=other,
        ).status_code
        == 404
    )


def test_confirm_labels_validates_names(client, login, seed_video):
    video = seed_video()
    headers = login(video.email)
    url = f"/api/v1/videos/{video.video_id}/labels/confirm"

    unknown = client.post(url, json={"labels": [{"name": "ChuaTonTai", "confidence": 0.5}]}, headers=headers)
    assert unknown.status_code == 400
    assert "chưa tồn tại" in unknown.json()["detail"]

    ensure_label("Safe")
    ensure_label("Gore", active=False)
    inactive = client.post(url, json={"labels": [{"name": "Gore", "confidence": 0.5}]}, headers=headers)
    assert inactive.status_code == 400
    assert "vô hiệu hóa" in inactive.json()["detail"]

    ensure_label("Safe", active=True)
    duplicate = client.post(
        url,
        json={
            "labels": [
                {"name": "Safe", "confidence": 0.9},
                {"name": "safe", "confidence": 0.8},
            ]
        },
        headers=headers,
    )
    assert duplicate.status_code == 400
    assert "trùng lặp" in duplicate.json()["detail"]


def test_moderator_replaces_labels_and_owner_cannot(client, register, login, seed_video):
    ensure_label("Adult")
    ensure_label("Safe")
    video = seed_video()
    attach_label(video.video_id, "Safe")

    owner = login(video.email)
    assert (
        client.patch(
            f"/api/v1/videos/{video.video_id}/labels",
            json={"labels": [{"name": "Adult", "confidence": 0.9}]},
            headers=owner,
        ).status_code
        == 403
    )

    moderator = register("label-mod@example.com", role=UserRole.moderator)
    response = client.patch(
        f"/api/v1/videos/{video.video_id}/labels",
        json={"labels": [{"name": "Adult", "confidence": 0.9}]},
        headers=moderator,
    )
    assert response.status_code == 200
    # Nhãn cũ bị thay thế toàn bộ (multi-label nhưng không còn Safe).
    assert [label["name"] for label in response.json()] == ["Adult"]
    assert response.json()[0]["confidence"] == 0.9


def test_admin_label_crud(client, register):
    admin = register("label-admin@example.com", role=UserRole.admin)

    created = client.post("/api/v1/admin/labels", json={"name": "Violence"}, headers=admin)
    assert created.status_code == 201
    assert created.json()["video_count"] == 0

    duplicate = client.post("/api/v1/admin/labels", json={"name": "violence"}, headers=admin)
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/admin/labels", headers=admin)
    assert listed.status_code == 200
    assert {item["name"] for item in listed.json()} == {"Violence"}

    label_id = created.json()["id"]
    deactivated = client.patch(
        f"/api/v1/admin/labels/{label_id}", json={"is_active": False}, headers=admin
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    renamed = client.patch(
        f"/api/v1/admin/labels/{label_id}", json={"name": "Gore"}, headers=admin
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Gore"

    empty_patch = client.patch(f"/api/v1/admin/labels/{label_id}", json={}, headers=admin)
    assert empty_patch.status_code == 422

    missing = client.patch(
        "/api/v1/admin/labels/00000000-0000-0000-0000-000000000000",
        json={"name": "Khac"},
        headers=admin,
    )
    assert missing.status_code == 404

    plain_user = register("plain-label-user@example.com")
    assert client.get("/api/v1/admin/labels", headers=plain_user).status_code == 403


def test_admin_updates_video_status_with_soft_delete(client, register, seed_video):
    admin = register("video-admin@example.com", role=UserRole.admin)
    video = seed_video(status=VideoStatus.published)
    url = f"/api/v1/admin/videos/{video.video_id}/status"

    rejected = client.patch(url, json={"status": "rejected", "reason": "vi phạm"}, headers=admin)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    deleted = client.patch(url, json={"status": "deleted"}, headers=admin)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get("/api/v1/feed").json() == []
    # Đã xóa mềm thì không thấy nữa.
    assert client.patch(url, json={"status": "published"}, headers=admin).status_code == 404

    assert (
        client.patch(
            "/api/v1/admin/videos/00000000-0000-0000-0000-000000000000/status",
            json={"status": "published"},
            headers=admin,
        ).status_code
        == 404
    )
    other = seed_video(status=VideoStatus.published)
    assert (
        client.patch(
            f"/api/v1/admin/videos/{other.video_id}/status",
            json={"status": "processing"},
            headers=admin,
        ).status_code
        == 422
    )


def test_appeal_lifecycle(client, register, login, seed_video):
    admin = register("appeal-admin@example.com", role=UserRole.admin)
    video = seed_video(status=VideoStatus.rejected)
    owner = login(video.email)
    url = f"/api/v1/videos/{video.video_id}/appeals"

    # Video chưa bị từ chối thì không appeal được.
    published = seed_video(status=VideoStatus.published)
    assert (
        client.post(
            f"/api/v1/videos/{published.video_id}/appeals",
            json={"reason": "Tôi không đồng ý"},
            headers=login(published.email),
        ).status_code
        == 400
    )

    created = client.post(url, json={"reason": "Nội dung không vi phạm"}, headers=owner)
    assert created.status_code == 201
    assert created.json()["status"] == "open"
    appeal_id = created.json()["id"]

    # Không tạo trùng appeal đang mở.
    duplicate = client.post(url, json={"reason": "Xử lý lại đi"}, headers=owner)
    assert duplicate.status_code == 409

    # Người khác không appeal thay được (404 theo quyền sở hữu).
    assert (
        client.post(
            url, json={"reason": "Không liên quan"}, headers=login(seed_video().email)
        ).status_code
        == 404
    )

    # User thường không xem được danh sách appeal.
    assert client.get("/api/v1/moderation/appeals", headers=owner).status_code == 403

    queue = client.get("/api/v1/moderation/appeals", headers=admin)
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [appeal_id]
    assert queue.json()[0]["user_display_name"] == "Owner"

    decided = client.post(
        f"/api/v1/moderation/appeals/{appeal_id}/decision",
        json={"action": "approve", "reason": "Xem lại rồi, hợp lệ"},
        headers=admin,
    )
    assert decided.status_code == 204

    # Video được đăng lại và appeal đã đóng.
    with SessionLocal() as db:
        from app.models import Video

        refreshed = db.get(Video, video.video_id)
        assert refreshed.status is VideoStatus.published
    assert client.get("/api/v1/moderation/appeals", headers=admin).json() == []
    assert (
        client.post(
            f"/api/v1/moderation/appeals/{appeal_id}/decision",
            json={"action": "reject"},
            headers=admin,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/moderation/appeals/00000000-0000-0000-0000-000000000000/decision",
            json={"action": "reject"},
            headers=admin,
        ).status_code
        == 404
    )


def test_appeal_rejected_keeps_video_hidden(client, register, login, seed_video):
    moderator = register("appeal-mod@example.com", role=UserRole.moderator)
    video = seed_video(status=VideoStatus.rejected)
    owner = login(video.email)
    created = client.post(
        f"/api/v1/videos/{video.video_id}/appeals",
        json={"reason": "Xin xem lại"},
        headers=owner,
    ).json()

    response = client.post(
        f"/api/v1/moderation/appeals/{created['id']}/decision",
        json={"action": "reject", "reason": "Vẫn vi phạm"},
        headers=moderator,
    )
    assert response.status_code == 204

    with SessionLocal() as db:
        from app.models import Video

        refreshed = db.get(Video, video.video_id)
        assert refreshed.status is VideoStatus.rejected


def test_moderator_and_system_stats(client, register):
    admin = register("stats-admin@example.com", role=UserRole.admin)
    plain = register("stats-user@example.com")

    assert client.get("/api/v1/admin/stats", headers=plain).status_code == 403

    stats = client.get("/api/v1/admin/stats?days=30", headers=admin)
    assert stats.status_code == 200
    body = stats.json()
    assert body["days"] == 30
    assert set(body["videos_by_status"]) == {item.value for item in VideoStatus}
    assert {"open", "resolved", "rejected"} <= set(body["reports_by_status"])
    assert {"open", "approved", "rejected"} <= set(body["appeals_by_status"])
    assert {"pending", "running", "succeeded", "failed"} <= set(body["jobs_by_status"])
    assert body["moderator_workload"] == []
    assert client.get("/api/v1/admin/stats?days=0", headers=admin).status_code == 422

    # UC019: thống kê theo moderator.
    moderator = register("stats-mod@example.com", role=UserRole.moderator)
    moderator_id = client.get("/api/v1/profile", headers=moderator).json()["id"]
    response = client.get(f"/api/v1/admin/moderators/{moderator_id}/stats", headers=admin)
    assert response.status_code == 200
    assert response.json()["videos_reviewed"] == 0
    assert response.json()["appeals_handled"] == 0
    assert response.json()["role"] == "moderator"

    assert (
        client.get(f"/api/v1/admin/moderators/{moderator_id}/stats", headers=plain).status_code
        == 403
    )
    plain_id = client.get("/api/v1/profile", headers=plain).json()["id"]
    not_moderator = client.get(f"/api/v1/admin/moderators/{plain_id}/stats", headers=admin)
    assert not_moderator.status_code == 400
    assert (
        client.get(
            "/api/v1/admin/moderators/00000000-0000-0000-0000-000000000000/stats",
            headers=admin,
        ).status_code
        == 404
    )
