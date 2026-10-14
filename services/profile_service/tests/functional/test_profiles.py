"""Behavioral tests: authorization, concurrency, privacy, and migration."""

import asyncio
from uuid import uuid4

import pytest
from conftest import A, B
from core.security import ProfileCipher
from cryptography.fernet import Fernet
from models.profile import ProfileAudit, ProfileRecord
from services.exceptions import ProfileNotFound
from sqlalchemy import select

PATH = "/api/v1/profiles/me"
DATA = {
    "first_name": "Анна",
    "last_name": "Иванова",
    "phone": "+1 202-555-0123",
}


def headers(token="a"):
    return {"Authorization": "Bearer " + token}


async def test_profile_lifecycle_is_private_and_audited(api):
    client, app, _ = api
    assert (await client.get(PATH, headers=headers())).status_code == 404
    response = await client.post(PATH, headers=headers(), json=DATA)
    assert response.status_code == 201
    assert response.json()["phone"] == "+12025550123"
    assert response.json()["phone_verified_at"] is None
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert (
        await client.post(PATH, headers=headers(), json=DATA)
    ).status_code == 409
    assert (await client.get(PATH, headers=headers("b"))).status_code == 404
    assert (
        await client.get(f"/api/v1/profiles/{A}", headers=headers("b"))
    ).status_code == 403
    changed = await client.patch(
        PATH, headers=headers(), json={"middle_name": "Петровна"}
    )
    assert changed.status_code == 200
    assert changed.json()["phone"] == "+12025550123"
    async with app.state.session_factory() as session:
        row = await session.get(ProfileRecord, A)
        assert all(
            value not in row.pii_ciphertext
            for value in ["Анна", "Иванова", "+12025550123"]
        )
        assert len(row.phone_index) == 64
        events = (await session.scalars(select(ProfileAudit))).all()
        assert {event.action for event in events} >= {
            "profile.create",
            "profile.update",
        }
    assert (await client.delete(PATH, headers=headers())).status_code == 204
    assert (await client.get(PATH, headers=headers())).status_code == 404
    assert (await client.delete(PATH, headers=headers())).status_code == 404


@pytest.mark.parametrize(
    "token,expected",
    [
        (None, 401),
        ("unknown", 401),
        ("disabled", 403),
        ("unavailable", 503),
        ("bad-contract", 503),
    ],
)
async def test_auth_fails_closed(api, token, expected):
    client, _, _ = api
    response = await client.get(PATH, headers=headers(token) if token else {})
    assert response.status_code == expected


@pytest.mark.parametrize(
    "patch",
    [
        {},
        {"first_name": None},
        {"last_name": " "},
        {"phone": "2025550123"},
        {"phone": "+123"},
        {"user_id": str(B)},
        {"phone_verified_at": "2026-01-01"},
        {"marketing_consent": None},
    ],
)
async def test_validation_rejects_unsafe_or_invalid_updates(api, patch):
    client, _, _ = api
    response = await client.patch(PATH, headers=headers(), json=patch)
    assert response.status_code == 422
    assert all(
        "input" not in error and "ctx" not in error
        for error in response.json()["detail"]
    )


async def test_same_phone_with_different_format_is_unique_and_released(api):
    client, _, _ = api
    assert (
        await client.post(PATH, headers=headers(), json=DATA)
    ).status_code == 201
    other = {**DATA, "phone": "+12025550123"}
    response = await client.post(PATH, headers=headers("b"), json=other)
    assert response.status_code == 409
    assert response.json()["detail"] == "phone_unavailable"
    assert (
        await client.patch(PATH, headers=headers(), json={"phone": None})
    ).status_code == 200
    assert (
        await client.post(PATH, headers=headers("b"), json=other)
    ).status_code == 201


async def test_concurrent_phone_creation_has_one_winner(api):
    client, _, _ = api
    responses = await asyncio.gather(
        *[
            client.post(PATH, headers=headers(token), json=DATA)
            for token in ("a", "b")
        ]
    )
    assert sorted(response.status_code for response in responses) == [201, 409]


async def test_failed_update_rolls_back_entire_profile(api):
    client, _, _ = api
    await client.post(PATH, headers=headers(), json=DATA)
    await client.post(PATH, headers=headers("b"), json={**DATA, "phone": None})
    response = await client.patch(
        PATH,
        headers=headers("b"),
        json={"first_name": "Changed", "phone": DATA["phone"]},
    )
    assert response.status_code == 409
    actual = (await client.get(PATH, headers=headers("b"))).json()
    assert (
        actual["first_name"] == DATA["first_name"] and actual["phone"] is None
    )


async def test_staff_read_pagination_and_permission_revocation(api):
    client, _, identities = api
    await client.post(PATH, headers=headers(), json=DATA)
    await client.post(PATH, headers=headers("b"), json={**DATA, "phone": None})
    page = await client.get(
        "/api/v1/profiles/?limit=1", headers=headers("staff")
    )
    assert page.status_code == 200
    assert page.json()["items"][0]["phone"] == "***0123"
    cursor = page.json()["next_cursor"]
    next_page = await client.get(
        f"/api/v1/profiles/?limit=1&after={cursor}", headers=headers("staff")
    )
    assert next_page.json()["items"][0]["user_id"] == str(B)
    assert next_page.json()["next_cursor"] is None
    detail = await client.get(
        f"/api/v1/profiles/{A}", headers=headers("staff")
    )
    assert detail.json()["phone"] == "+12025550123"
    identities["staff"]["roles"] = []
    assert (
        await client.get(f"/api/v1/profiles/{A}", headers=headers("staff"))
    ).status_code == 403


async def test_worker_endpoint_returns_only_names(api):
    client, app, _ = api
    await client.post(PATH, headers=headers(), json=DATA)
    url = f"/api/v1/internal/profiles/{A}/notification-name"
    assert (await client.get(url, headers=headers("staff"))).status_code == 403
    response = await client.get(
        url,
        headers={
            "X-Service-Token": (
                app.state.settings.notification_token.get_secret_value()
            )
        },
    )
    assert response.status_code == 200
    assert set(response.json()) == {"user_id", "first_name", "last_name"}


async def test_import_does_not_overwrite_or_resurrect(api):
    client, app, _ = api
    service = app.state.profile_service
    assert await service.import_legacy(A, "Old", "Name")
    assert not await service.import_legacy(A, "Other", "Name")
    await client.patch(PATH, headers=headers(), json={"first_name": "New"})
    assert not await service.import_legacy(A, "Old", "Name")
    assert (await client.get(PATH, headers=headers())).json()[
        "first_name"
    ] == "New"
    await client.delete(PATH, headers=headers())
    assert not await service.import_legacy(A, "Old", "Name")
    with pytest.raises(ProfileNotFound):
        await service.get(A, A, "test")


async def test_large_body_is_rejected(api):
    client, _, _ = api
    response = await client.post(PATH, headers=headers(), content=b"x" * 17000)
    assert response.status_code == 413


def test_encryption_binding_and_key_rotation():
    old, new, index = [Fernet.generate_key().decode() for _ in range(3)]
    original = ProfileCipher(old, index)
    encrypted = original.encrypt(A, {"phone": "+12025550123"})
    with pytest.raises(ValueError, match="profile_decryption_failed"):
        original.decrypt(uuid4(), encrypted)
    rotated = ProfileCipher(new + "," + old, index).rotate(encrypted)
    assert (
        ProfileCipher(new, index).decrypt(A, rotated)["phone"]
        == "+12025550123"
    )
    assert original.phone_index("+12025550123") == ProfileCipher(
        new, index
    ).phone_index("+12025550123")
