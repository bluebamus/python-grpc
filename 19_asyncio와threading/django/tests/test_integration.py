"""Django threading 작업 큐 통합 테스트 (순수 HTTP)."""

from django.test import Client

from conftest import poll_until_done

client = Client()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_then_consumer_processes():
    # POST로 작업 투입 -> consumer 스레드가 처리 -> GET으로 done/result 확인
    resp = client.post("/tasks", data={"payload": "hello"}, content_type="application/json")
    assert resp.status_code == 202
    body = resp.json()
    assert body["queued"] is True
    task_id = body["task_id"]

    done = poll_until_done(client, task_id)
    assert done["status"] == "done"
    assert done["result"] == "HELLO"  # _process가 대문자로 변환


def test_stats_processed_count_increases():
    # 여러 작업 투입 시 /stats의 processed 카운트가 그만큼 증가한다.
    before = client.get("/stats").json()["processed"]

    task_ids = []
    for i in range(5):
        r = client.post(
            "/tasks", data={"payload": f"job-{i}"}, content_type="application/json"
        )
        task_ids.append(r.json()["task_id"])
    for tid in task_ids:
        poll_until_done(client, tid)

    after = client.get("/stats").json()
    assert after["processed"] - before == 5


def test_validation_rejects_empty_payload():
    resp = client.post("/tasks", data={"payload": ""}, content_type="application/json")
    assert resp.status_code == 422


def test_unknown_task_returns_404():
    resp = client.get("/tasks/999999")
    assert resp.status_code == 404
