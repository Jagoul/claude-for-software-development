"""The /v1/tasks API, end to end through FastAPI's TestClient."""

import pytest


def test_create_task_returns_201_with_normalised_fields(client):
    payload = {"title": "  Write docs  ", "tags": [" Docs ", "API"], "priority": "high"}

    response = client.post("/v1/tasks", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Write docs"
    assert body["tags"] == ["docs", "api"]
    assert body["status"] == "todo"


@pytest.mark.parametrize("title", ["", "   "])
def test_create_task_rejects_blank_title(client, title):
    response = client.post("/v1/tasks", json={"title": title})

    assert response.status_code == 422


def test_get_task_returns_the_task(client, make_tasks):
    make_tasks(2)

    response = client.get("/v1/tasks/2")

    assert response.status_code == 200
    assert response.json()["title"] == "Task 2"


def test_get_task_returns_404_for_unknown_id(client):
    response = client.get("/v1/tasks/999")

    assert response.status_code == 404


def test_list_tasks_reports_total_for_each_filter(client, make_tasks):
    make_tasks(3, assignee="ana")
    make_tasks(2, assignee="ben")

    everyone = client.get("/v1/tasks").json()
    ana = client.get("/v1/tasks", params={"assignee": "ana"}).json()

    assert everyone["total"] == 5
    assert ana["total"] == 3


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_list_tasks_rejects_out_of_range_paging(client, params):
    response = client.get("/v1/tasks", params=params)

    assert response.status_code == 422


@pytest.mark.xfail(strict=True, reason="TB-101: page 1 skips the first page of results")
def test_first_page_returns_first_tasks(client, make_tasks):
    make_tasks(3)

    response = client.get("/v1/tasks", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["items"]] == ["Task 1", "Task 2"]


def test_update_task_changes_only_sent_fields(client, make_tasks):
    make_tasks(1, assignee="ana")

    response = client.patch("/v1/tasks/1", json={"status": "in_progress"})

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["assignee"] == "ana"


def test_update_task_rejects_empty_body(client, make_tasks):
    make_tasks(1)

    response = client.patch("/v1/tasks/1", json={})

    assert response.status_code == 422


def test_update_task_rejects_reopening_done_task_to_todo(client, make_tasks):
    make_tasks(1)
    client.patch("/v1/tasks/1", json={"status": "done"})

    response = client.patch("/v1/tasks/1", json={"status": "todo"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_update_task_returns_404_for_unknown_id(client):
    response = client.patch("/v1/tasks/999", json={"title": "x"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_deleted_task_is_gone(client, make_tasks):
    make_tasks(1)

    client.delete("/v1/tasks/1")

    assert client.get("/v1/tasks/1").status_code == 404


def test_healthz_reports_ok(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
