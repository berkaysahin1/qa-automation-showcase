"""Input validation — the half of an API that is usually untested."""

import pytest

pytestmark = pytest.mark.api


@pytest.mark.parametrize(
    "payload, field",
    [
        pytest.param({"email": "not-an-email", "password": "long-enough-1",
                      "name": "A"}, "email", id="malformed-email"),
        pytest.param({"email": "a@b.test", "password": "short", "name": "A"},
                     "password", id="password-too-short"),
        pytest.param({"email": "a@b.test", "password": "long-enough-1",
                      "name": ""}, "name", id="empty-name"),
        pytest.param({"password": "long-enough-1", "name": "A"}, "email",
                     id="missing-email"),
    ],
)
def test_registration_rejects_invalid_input(api, payload, field):
    response = api.post("/api/auth/register", json=payload)

    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"title": ""}, id="empty-title"),
        pytest.param({"title": "x" * 141}, id="title-too-long"),
        pytest.param({"title": "ok", "priority": "urgent"}, id="unknown-priority"),
        pytest.param({"notes": "no title here"}, id="missing-title"),
    ],
)
def test_task_creation_rejects_invalid_input(authed, payload):
    assert authed.post("/api/tasks", json=payload).status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"limit": 0}, id="limit-below-min"),
        pytest.param({"limit": 101}, id="limit-above-max"),
        pytest.param({"offset": -1}, id="negative-offset"),
        pytest.param({"limit": "many"}, id="non-numeric-limit"),
    ],
)
def test_pagination_parameters_are_bounded(authed, params):
    assert authed.get("/api/tasks", params=params).status_code == 422


def test_title_at_the_boundary_is_accepted(authed):
    """140 chars is valid, 141 is not — the classic off-by-one."""
    assert authed.post("/api/tasks", json={"title": "x" * 140}).status_code == 201
