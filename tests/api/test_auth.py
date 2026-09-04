"""Authentication contract: registration, login, and token handling."""

import pytest

pytestmark = pytest.mark.api


def test_register_returns_created_user_without_password(api):
    response = api.post(
        "/api/auth/register",
        json={"email": "ada@example.com", "password": "hunter2-hunter2",
              "name": "Ada"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["name"] == "Ada"
    assert "password" not in body


def test_register_is_case_insensitive_on_email(api):
    payload = {"email": "Ada@Example.com", "password": "hunter2-hunter2",
               "name": "Ada"}
    assert api.post("/api/auth/register", json=payload).status_code == 201

    duplicate = api.post(
        "/api/auth/register",
        json={**payload, "email": "ada@example.com"},
    )
    assert duplicate.status_code == 409


def test_login_returns_a_usable_bearer_token(api, account):
    response = api.post(
        "/api/auth/login",
        json={"email": account.email, "password": account.password},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    me = api.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == account.email


@pytest.mark.parametrize(
    "password", ["wrong-password", "", "CORRECT-HORSE-BATTERY"],
    ids=["wrong", "empty", "case-flipped"],
)
def test_login_rejects_bad_passwords(api, account, password):
    response = api.post(
        "/api/auth/login", json={"email": account.email, "password": password}
    )
    assert response.status_code == 401


def test_login_does_not_leak_whether_an_email_exists(api, account):
    unknown = api.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-123"},
    )
    known_but_wrong = api.post(
        "/api/auth/login",
        json={"email": account.email, "password": "whatever-123"},
    )

    assert unknown.status_code == known_but_wrong.status_code == 401
    assert unknown.json() == known_but_wrong.json()


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-header"),
        pytest.param({"Authorization": "Bearer not-a-jwt"}, id="malformed"),
        pytest.param({"Authorization": "Basic dXNlcjpwYXNz"}, id="wrong-scheme"),
    ],
)
def test_protected_routes_require_a_valid_token(api, headers):
    assert api.get("/api/me", headers=headers).status_code == 401


def test_expired_tokens_are_rejected(api, account, monkeypatch):
    import datetime

    import jwt

    expired = jwt.encode(
        {
            "sub": account.id,
            "exp": datetime.datetime.now(datetime.UTC)
            - datetime.timedelta(minutes=1),
        },
        __import__("os").environ.get("TASKFLOW_SECRET",
                                     "dev-secret-not-for-production"),
        algorithm="HS256",
    )

    response = api.get("/api/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "token expired"


def test_tokens_signed_with_another_key_are_rejected(api, account):
    import jwt

    forged = jwt.encode({"sub": account.id, "exp": 9_999_999_999},
                        "attacker-key", algorithm="HS256")

    assert api.get(
        "/api/me", headers={"Authorization": f"Bearer {forged}"}
    ).status_code == 401
