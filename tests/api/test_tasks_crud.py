"""Task lifecycle: create, read, filter, paginate, update, delete."""

import pytest

pytestmark = pytest.mark.api


def create_task(client, title="Write the proposal", **overrides):
    response = client.post("/api/tasks", json={"title": title, **overrides})
    response.raise_for_status()
    return response.json()


def test_created_task_starts_open_with_defaults(authed):
    task = create_task(authed)

    assert task["done"] is False
    assert task["priority"] == "normal"
    assert task["notes"] == ""
    assert task["created_at"]


def test_listing_returns_newest_first(authed):
    first = create_task(authed, "first")
    second = create_task(authed, "second")

    titles = [t["title"] for t in authed.get("/api/tasks").json()["items"]]
    assert titles == [second["title"], first["title"]]


def test_done_filter_narrows_the_result_set(authed):
    open_task = create_task(authed, "still open")
    finished = create_task(authed, "finished")
    authed.patch(f"/api/tasks/{finished['id']}", json={"done": True})

    done_only = authed.get("/api/tasks", params={"done": True}).json()
    open_only = authed.get("/api/tasks", params={"done": False}).json()

    assert [t["id"] for t in done_only["items"]] == [finished["id"]]
    assert [t["id"] for t in open_only["items"]] == [open_task["id"]]


def test_pagination_walks_the_whole_set_without_gaps_or_repeats(authed):
    created = {create_task(authed, f"task {i}")["id"] for i in range(7)}

    seen, offset = [], 0
    while True:
        page = authed.get("/api/tasks", params={"limit": 3, "offset": offset}).json()
        assert page["total"] == 7
        seen.extend(t["id"] for t in page["items"])
        if len(page["items"]) < 3:
            break
        offset += 3

    assert len(seen) == len(set(seen)) == 7
    assert set(seen) == created


def test_patch_only_touches_the_fields_supplied(authed):
    task = create_task(authed, "original", notes="keep me", priority="high")

    updated = authed.patch(
        f"/api/tasks/{task['id']}", json={"done": True}
    ).json()

    assert updated["done"] is True
    assert updated["title"] == "original"
    assert updated["notes"] == "keep me"
    assert updated["priority"] == "high"


def test_delete_removes_the_task_and_is_not_repeatable(authed):
    task = create_task(authed)

    assert authed.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert authed.get(f"/api/tasks/{task['id']}").status_code == 404
    assert authed.delete(f"/api/tasks/{task['id']}").status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_unknown_task_ids_return_404(authed, method):
    request = getattr(authed, method)
    kwargs = {"json": {"done": True}} if method == "patch" else {}
    assert request("/api/tasks/does-not-exist", **kwargs).status_code == 404
