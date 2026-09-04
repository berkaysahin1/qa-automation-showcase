"""Authorization: one user must never reach another user's rows.

These are the tests that stop the bug nobody notices until it is a breach.
"""

import pytest

pytestmark = [pytest.mark.api, pytest.mark.security]


@pytest.fixture
def two_users(base_url, make_account):
    import httpx

    alice, bob = make_account(), make_account()
    with httpx.Client(base_url=base_url, headers=alice.auth_header) as a, \
         httpx.Client(base_url=base_url, headers=bob.auth_header) as b:
        yield a, b


def test_a_user_only_sees_their_own_tasks(two_users):
    alice, bob = two_users
    alice.post("/api/tasks", json={"title": "alice's task"})
    bob.post("/api/tasks", json={"title": "bob's task"})

    titles = [t["title"] for t in alice.get("/api/tasks").json()["items"]]
    assert titles == ["alice's task"]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_users_task_is_reported_as_missing_not_forbidden(two_users, method):
    """404 rather than 403: a 403 would confirm the row exists."""
    alice, bob = two_users
    task_id = alice.post("/api/tasks", json={"title": "private"}).json()["id"]

    kwargs = {"json": {"done": True}} if method == "patch" else {}
    response = getattr(bob, method)(f"/api/tasks/{task_id}", **kwargs)

    assert response.status_code == 404


def test_a_failed_cross_tenant_write_leaves_the_row_untouched(two_users):
    alice, bob = two_users
    task = alice.post("/api/tasks", json={"title": "untouched"}).json()

    bob.patch(f"/api/tasks/{task['id']}", json={"title": "hijacked", "done": True})

    after = alice.get(f"/api/tasks/{task['id']}").json()
    assert after["title"] == "untouched"
    assert after["done"] is False
