def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_profile(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "display_name": "User", "password": "password123"},
    )
    assert registered.status_code == 201

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    profile = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "user@example.com"


def test_duplicate_report_is_rejected(client):
    user = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "display_name": "User", "password": "password123"},
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.post(
        "/api/v1/videos",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("sample.mp4", b"not-real-video", "video/mp4")},
    )
    assert response.status_code == 201
    video_id = response.json()["id"]

    first = client.post(
        f"/api/v1/videos/{video_id}/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Nội dung không phù hợp"},
    )
    second = client.post(
        f"/api/v1/videos/{video_id}/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Báo cáo trùng"},
    )
    assert first.status_code == 201
    assert client.get("/api/v1/feed").json() == []
    assert second.status_code == 409
